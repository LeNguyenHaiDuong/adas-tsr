#!/usr/bin/env python3
"""
TSR Demo - Vietnam Traffic Sign Detection & Tracking
===================================================
Model mặc định: star092304/traffic-sign-detection-vietnam-yolo (best.pt, 82 lớp).
"""

from __future__ import annotations

import argparse
import time
import logging
import json
import re
import psutil
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any
from collections import Counter, defaultdict

import cv2
import numpy as np

from detectors import YOLODetector, Detections
from tracker import SignTracker, ProductionLiteTracker
from visualizer import draw_detections, draw_production_lite_overlay


def classify_family(label: str) -> str:
    key = label.lower().replace('_', ' ')
    if 'speed' in key or re.search(r'\b(5|10|20|30|40|50|60|70|80|90|100|120)\b', key):
        return 'speed'
    if 'stop' in key:
        return 'stop'
    if 'no entry' in key or 'cấm vào' in key:
        return 'no_entry'
    if any(word in key for word in ['warning', 'danger', 'curve', 'slippery', 'children', 'pedestrian']):
        return 'warning'
    if any(word in key for word in ['turn', 'keep', 'one way', 'mandatory', 'roundabout']):
        return 'mandatory'
    if any(word in key for word in ['parking', 'station', 'information']):
        return 'info'
    return 'default'


def extract_speed_limit(label: str) -> int | None:
    digits = re.findall(r'(?<!\d)(\d{2,3})(?!\d)', label)
    if not digits:
        return None
    value = int(digits[0])
    if 5 <= value <= 130:
        return value
    return None


def scale_bbox(x1: int, y1: int, x2: int, y2: int, from_shape: tuple, to_shape: tuple) -> tuple:
    fh, fw = from_shape[:2]
    th, tw = to_shape[:2]
    sx = tw / max(fw, 1)
    sy = th / max(fh, 1)
    return int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)


def assess_frame_quality(frame: np.ndarray) -> dict[str, Any]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur_var = float(cv2.Laplacian(gray, cv2.CV_16S).var())
    mean_luma = float(gray.mean())
    dark_ratio = float((gray < 35).mean())
    bright_ratio = float((gray > 245).mean())

    reasons = []
    if blur_var < 45:
        reasons.append('LOW_SHARPNESS')
    if mean_luma < 45 or dark_ratio > 0.55:
        reasons.append('TOO_DARK')
    if bright_ratio > 0.18:
        reasons.append('GLARE')

    quality_ok = not reasons
    should_infer = 'GLARE' not in reasons and 'TOO_DARK' not in reasons
    return {
        'blur_var': blur_var,
        'mean_luma': mean_luma,
        'dark_ratio': dark_ratio,
        'bright_ratio': bright_ratio,
        'reasons': reasons,
        'quality_ok': quality_ok,
        'should_infer': should_infer,
    }


def odd_gate(quality: dict[str, Any], ego_speed_kph: float, speed_range: tuple[int, int]) -> tuple[bool, list[str]]:
    reasons = []
    if not (speed_range[0] <= ego_speed_kph <= speed_range[1]):
        reasons.append('ODD_SPEED_OUT')
    for reason in quality['reasons']:
        if reason in {'GLARE', 'TOO_DARK'}:
            reasons.append('ODD_QUALITY_OUT')
            break
    return len(reasons) == 0, reasons


def feature_state_from_quality(odd_ok: bool, quality: dict[str, Any]) -> str:
    if not odd_ok:
        return 'UNAVAILABLE'
    if quality['quality_ok']:
        return 'AVAILABLE'
    return 'DEGRADED'


def to_pct(numerator: int | float, denominator: int | float) -> float:
    return 100.0 * float(numerator) / float(denominator) if denominator else 0.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), q))


def summarize_range(values: list[float]) -> str:
    if not values:
        return '-'
    p10 = percentile(values, 10)
    p50 = percentile(values, 50)
    p90 = percentile(values, 90)
    return f'p10={p10:.1f}, p50={p50:.1f}, p90={p90:.1f}'


def bbox_size_metrics(bbox: list[int] | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = map(int, bbox)
    w = max(0, x2 - x1)
    h = max(0, y2 - y1)
    area = w * h
    short_side = min(w, h)
    return w, h, area, short_side


def size_bin_for_bbox(bbox: list[int] | tuple[int, int, int, int]) -> str:
    _, _, _, short_side = bbox_size_metrics(bbox)
    if short_side < 16:
        return '0-15 px'
    if short_side < 32:
        return '16-31 px'
    if short_side < 64:
        return '32-63 px'
    return '64+ px'


def iou(box_a: tuple, box_b: tuple) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter + 1e-6
    return inter / union


def match_key(obj: dict[str, Any], mode: str) -> str:
    if mode == 'label':
        return str(obj.get('label', ''))
    family = obj.get('family')
    if family:
        return str(family)
    return classify_family(str(obj.get('label', '')))


def load_optional_gt(path_like: str | Path | None) -> dict[int, list[dict[str, Any]]]:
    if not path_like:
        return {}
    path = Path(path_like)
    if not path.exists():
        raise FileNotFoundError(f'GT file not found: {path}')
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'frames' in payload:
        frames = payload['frames']
    elif isinstance(payload, list):
        frames = payload
    else:
        raise ValueError('GT JSON phải là list hoặc dict có key frames')

    gt_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in frames:
        frame_idx = int(item['frame_idx'])
        objects = item.get('objects') or item.get('detections') or item.get('gt') or []
        for obj in objects:
            bbox = list(map(int, obj['bbox']))
            label = obj.get('label', obj.get('class', 'unknown'))
            family = obj.get('family') or classify_family(str(label))
            gt_by_frame[frame_idx].append({
                'bbox': bbox,
                'label': label,
                'family': family,
            })
    return gt_by_frame


def evaluate_against_gt(events: list[dict[str, Any]], gt_by_frame: dict[int, list[dict[str, Any]]], conf_threshold: float, match_mode: str, iou_threshold: float) -> dict[str, Any]:
    tp = 0
    fp = 0
    fn = 0
    gt_size_counter = Counter()
    gt_size_hit_counter = Counter()
    family_tp = Counter()
    family_fp = Counter()
    family_fn = Counter()

    event_by_frame = {int(event['frame_idx']): event for event in events}
    frame_ids = sorted(set(event_by_frame) | set(gt_by_frame))

    for frame_idx in frame_ids:
        preds = [
            pred for pred in event_by_frame.get(frame_idx, {}).get('detections', [])
            if float(pred.get('conf', 0.0)) >= conf_threshold
        ]
        gts = list(gt_by_frame.get(frame_idx, []))
        matched_gt = set()

        preds = sorted(preds, key=lambda item: float(item.get('conf', 0.0)), reverse=True)
        for gt in gts:
            gt_size_counter[size_bin_for_bbox(gt['bbox'])] += 1

        for pred in preds:
            best_idx = None
            best_iou = 0.0
            for gt_idx, gt in enumerate(gts):
                if gt_idx in matched_gt:
                    continue
                if match_key(pred, match_mode) != match_key(gt, match_mode):
                    continue
                score = iou(pred['bbox'], gt['bbox'])
                if score >= iou_threshold and score > best_iou:
                    best_iou = score
                    best_idx = gt_idx
            if best_idx is None:
                fp += 1
                family_fp[match_key(pred, match_mode)] += 1
            else:
                matched_gt.add(best_idx)
                gt = gts[best_idx]
                tp += 1
                family_tp[match_key(gt, match_mode)] += 1
                gt_size_hit_counter[size_bin_for_bbox(gt['bbox'])] += 1

        for gt_idx, gt in enumerate(gts):
            if gt_idx not in matched_gt:
                fn += 1
                family_fn[match_key(gt, match_mode)] += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    size_rows = []
    for size_bin in ['0-15 px', '16-31 px', '32-63 px', '64+ px']:
        total_gt = gt_size_counter[size_bin]
        hit_gt = gt_size_hit_counter[size_bin]
        size_rows.append({
            'size_bin': size_bin,
            'gt_count': total_gt,
            'matched': hit_gt,
            'recall': f'{to_pct(hit_gt, total_gt):.1f}%' if total_gt else '-',
        })

    family_keys = sorted(set(family_tp) | set(family_fp) | set(family_fn))
    family_rows = []
    for key in family_keys:
        tp_k = family_tp[key]
        fp_k = family_fp[key]
        fn_k = family_fn[key]
        prec_k = tp_k / max(tp_k + fp_k, 1)
        rec_k = tp_k / max(tp_k + fn_k, 1)
        family_rows.append({
            'family_or_label': key,
            'tp': tp_k,
            'fp': fp_k,
            'fn': fn_k,
            'precision': f'{100.0 * prec_k:.1f}%',
            'recall': f'{100.0 * rec_k:.1f}%',
        })

    return {
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'size_rows': size_rows,
        'family_rows': family_rows,
    }

# Setup logger
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger("TSR")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
DEFAULT_VIDEO = ROOT / "videos" / "traffic_sign_test.mp4"
VN_HF_REPO = "star092304/traffic-sign-detection-vietnam-yolo"


def apply_clahe(frame: np.ndarray) -> np.ndarray:
    # Convert BGR to LAB color space
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L (lightness) channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


def preprocess(frame: np.ndarray, max_width: int = 960, clahe: bool = False) -> np.ndarray:
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    if clahe:
        frame = apply_clahe(frame)
    return frame





def scale_detections(dets: List, from_shape: tuple, to_shape: tuple) -> List:
    """Scale detection boxes from proc_frame size back to original frame size."""
    if not dets:
        return dets
    fh, fw = from_shape[:2]
    th, tw = to_shape[:2]
    if fh == th and fw == tw:
        return list(dets)
    sx = tw / max(fw, 1)
    sy = th / max(fh, 1)
    scaled = []
    for det in dets:
        x1, y1, x2, y2 = det[:4]
        rest = det[4:]
        scaled.append((
            int(x1 * sx), int(y1 * sy),
            int(x2 * sx), int(y2 * sy),
            *rest
        ))
    return scaled


def filter_by_roi(dets: List, frame_shape: Tuple[int, int]) -> List:
    if not dets:
        return dets
    h, w = frame_shape[:2]
    filtered = []
    for det in dets:
        x1, y1, x2, y2 = det[:4]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # 1. Filter out bottom 15% (dashboard/bonnet)
        if cy > h * 0.85:
            continue
        # 2. Filter out top 5% (extreme sky)
        if cy < h * 0.05:
            continue
        # 3. Filter out immediate center bottom (road lanes directly in front of the car)
        if (w * 0.30 < cx < w * 0.70) and (cy > h * 0.70):
            continue
            
        filtered.append(det)
    return filtered


def resolve_weights(weights: Path) -> Path:
    if weights.is_file():
        return weights
    if weights.name == "best.pt":
        try:
            from huggingface_hub import hf_hub_download
            logger.info(f"Tải model từ HuggingFace: {VN_HF_REPO}")
            cached = hf_hub_download(repo_id=VN_HF_REPO, filename="best.pt")
            return Path(cached)
        except Exception as exc:
            raise SystemExit(f"[ERROR] Không tìm thấy {weights} và tải HF thất bại: {exc}") from exc
    raise SystemExit(f"[ERROR] Không tìm thấy model: {weights}")


def resolve_source(source: str):
    try:
        return int(source)
    except ValueError:
        path = Path(source)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return str(path)


def main():
    parser = argparse.ArgumentParser(description="TSR Inference Demo (YOLO .pt & Tracking & Lvl 2 Filters)")
    parser.add_argument("--source", type=str, default=str(DEFAULT_VIDEO), help="Video path hoặc camera index")
    parser.add_argument("--output", type=str, default=str(ROOT / "videos" / "tsr_demo_output.mp4"), help="Video annotated output")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="Đường dẫn file .pt")
    parser.add_argument("--conf", type=float, default=0.15, help="Confidence threshold (VN model: 0.15 khuyến nghị)")
    parser.add_argument("--skip", type=int, default=0, help="Bỏ qua N frame giữa các lần inference")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước inference YOLO")
    parser.add_argument("--max-width", type=int, default=1280, help="Resize frame nếu rộng hơn giá trị này")
    parser.add_argument("--hold", type=int, default=3, help="Giữ detection cũ N frame khi frame mới trống (chỉ dùng nếu tắt tracker)")
    parser.add_argument("--no-display", action="store_true", help="Headless mode")
    parser.add_argument("--no-tracker", action="store_true", help="Tắt tính năng theo vết đối tượng (Tracker)")
    parser.add_argument("--clahe", action="store_true", help="Bật cân bằng sáng thích ứng CLAHE để cải thiện độ tương phản")
    parser.add_argument("--roi-filter", action="store_true", help="Bật lọc tọa độ vùng quan tâm ROI để loại bỏ nhiễu mặt đường/táp-lô")
    parser.add_argument("--min-hits", type=int, default=1, help="Số frame nhận diện liên tiếp tối thiểu để hiển thị biển báo (default: 1)")
    
    # Production-lite arguments
    parser.add_argument("--production-lite", action="store_true", help="Bật chế độ mô phỏng production-lite")
    parser.add_argument("--events-log", type=str, default=None, help="Đường dẫn lưu log events JSONL (chỉ dùng trong production-lite)")
    parser.add_argument("--ego-speed", type=float, default=50.0, help="Tốc độ xe ego km/h (chỉ dùng trong production-lite)")
    parser.add_argument("--map-speed-limit", type=int, default=None, help="Stub giới hạn tốc độ bản đồ (chỉ dùng trong production-lite)")
    parser.add_argument("--profile", type=str, default="auto", choices=["high", "medium", "low", "auto"], help="Profile tài nguyên RAM (chỉ dùng trong production-lite)")
    parser.add_argument("--gt-path", type=str, default=None, help="Đường dẫn file ground-truth JSON để đánh giá (chỉ dùng trong production-lite)")
    args = parser.parse_args()

    weights = resolve_weights(Path(args.weights))

    src = resolve_source(args.source)
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"[ERROR] Không mở được nguồn: {args.source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_in = cap.get(cv2.CAP_PROP_FPS)
    if not fps_in or fps_in < 1.0 or fps_in > 240.0:
        fps_in = 30.0
    fps_in = float(fps_in)

    writer = None
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        w = None
        if out_path.suffix.lower() == ".mp4":
            for cc in ("mp4v", "avc1", "H264"):
                fourcc = cv2.VideoWriter_fourcc(*cc)
                w = cv2.VideoWriter(str(out_path), fourcc, fps_in, (width, height))
                if w.isOpened():
                    logger.info(f"Ghi video ra: {out_path} (fourcc={cc})")
                    break
                w.release()
                w = None
        if w is None:
            fourcc = cv2.VideoWriter_fourcc(*("mp4v" if out_path.suffix.lower() == ".mp4" else "XVID"))
            w = cv2.VideoWriter(str(out_path), fourcc, fps_in, (width, height))
            logger.info(f"Ghi video ra: {out_path} (fourcc default)")
        if not w.isOpened():
            logger.warning("VideoWriter không mở được, bỏ ghi output.")
            w = None
        writer = w

    # Resolve settings based on production-lite profile
    if args.production_lite:
        total_ram = psutil.virtual_memory().total / (1024 ** 3)
        if args.profile == "auto":
            profile_name = "high" if total_ram >= 20 else ("medium" if total_ram >= 10 else "low")
        else:
            profile_name = args.profile
            
        profiles = {
            'high': {'imgsz': 640, 'max_width': 1600, 'skip': 0, 'conf': 0.15},
            'medium': {'imgsz': 640, 'max_width': 1280, 'skip': 0, 'conf': 0.15},
            'low': {'imgsz': 512, 'max_width': 960, 'skip': 1, 'conf': 0.15},
        }
        profile_cfg = profiles[profile_name]
        
        imgsz = profile_cfg['imgsz']
        max_width = profile_cfg['max_width']
        skip = profile_cfg['skip']
        conf_thres = args.conf if args.conf is not None and args.conf != 0.15 else profile_cfg['conf']
        logger.info(f"[PROD-LITE] RAM: {total_ram:.2f} GB -> Profile: {profile_name.upper()} (imgsz={imgsz}, max_width={max_width}, skip={skip}, conf={conf_thres:.2f})")
    else:
        imgsz = args.imgsz
        max_width = args.max_width
        skip = args.skip
        conf_thres = args.conf

    # Load detectors
    logger.info(f"Đang tải model YOLO: {weights}")
    yolo_detector = YOLODetector(weights, conf_thres=conf_thres, imgsz=imgsz)

    # Initialize tracker
    if args.production_lite:
        tracker = ProductionLiteTracker(
            assoc_iou=0.20,
            min_confirm_hits=3,
            max_candidate_misses=2,
            max_stale_misses=4,
            expire_misses=6,
            map_speed_limit_kph=args.map_speed_limit
        )
        logger.info("[PROD-LITE] Khởi tạo ProductionLiteTracker")
    else:
        tracker = None if args.no_tracker else SignTracker(max_lost=args.hold, min_hits=args.min_hits, conf_threshold=conf_thres)

    if args.production_lite:
        logger.info(f"Config Prod-Lite: conf={conf_thres} | imgsz={imgsz} | skip={skip} | ego_speed={args.ego_speed}")
    else:
        logger.info(f"Config: conf={conf_thres} | imgsz={imgsz}")
        logger.info(
            f"Nguồn: {args.source} | "
            f"Tracker={'OFF' if args.no_tracker else f'ON (min-hits={args.min_hits})'} | "
            f"CLAHE={'ON' if args.clahe else 'OFF'} | "
            f"ROI-Filter={'ON' if args.roi_filter else 'OFF'}"
        )

    frame_idx = 0
    fps_smooth = 0.0
    last_detections = []
    hold_left = 0
    total_detections = 0

    # Profiling timers
    total_prep_time = 0.0
    total_inf_time = 0.0
    total_post_time = 0.0
    total_track_time = 0.0
    total_draw_time = 0.0

    # Setup events logging and preview directories
    f_jsonl = None
    events_jsonl = None
    preview_dir = None
    preview_paths = []
    saved_preview_tids = set()
    
    if args.production_lite:
        events_jsonl = Path(args.events_log) if args.events_log else Path(args.output).parent / "events.jsonl"
        events_jsonl.parent.mkdir(parents=True, exist_ok=True)
        f_jsonl = open(events_jsonl, 'w', encoding='utf-8')
        
        preview_dir = Path(args.output).parent / "preview_frames"
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        published_counter = Counter()
        state_counter = Counter()
        quality_reason_counter = Counter()
        family_counter = Counter()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            run_inference = skip <= 0 or (frame_idx % (skip + 1) == 1)
            detections = []

            if args.production_lite:
                t_prep_start = time.time()
                proc_frame = preprocess(frame, max_width=max_width)
                quality = assess_frame_quality(proc_frame)
                odd_ok, odd_reasons = odd_gate(quality, args.ego_speed, (0, 90))
                feature_state = feature_state_from_quality(odd_ok, quality)
                total_prep_time += (time.time() - t_prep_start)

                if run_inference and quality['should_infer']:
                    t_inf_start = time.time()
                    proc_dets = yolo_detector.detect(proc_frame)
                    total_inf_time += (time.time() - t_inf_start)

                    t_post_start = time.time()
                    for d in proc_dets:
                        x1, y1, x2, y2, label, _, conf, _ = d
                        if conf >= conf_thres:
                            sx1, sy1, sx2, sy2 = scale_bbox(x1, y1, x2, y2, proc_frame.shape, frame.shape)
                            detections.append({
                                'bbox': (sx1, sy1, sx2, sy2),
                                'label': label,
                                'conf': conf,
                                'family': classify_family(label),
                                'speed_limit': extract_speed_limit(label),
                            })
                    total_post_time += (time.time() - t_post_start)
                    total_detections += len(detections)

                t_track_start = time.time()
                tracks = tracker.update(detections, odd_ok, quality['quality_ok'])
                primary_track = tracker.choose_primary_track()
                total_track_time += (time.time() - t_track_start)

                # Compute smoothing FPS
                dt_total = time.time() - t_prep_start
                inst_fps = 1.0 / dt_total if dt_total > 0 else 0
                fps_smooth = 0.85 * fps_smooth + 0.15 * inst_fps if fps_smooth > 0 else inst_fps

                # Log events
                if f_jsonl is not None:
                    event = {
                        'frame_idx': frame_idx,
                        'feature_state': feature_state,
                        'odd_ok': odd_ok,
                        'odd_reasons': odd_reasons,
                        'quality': quality,
                        'detections': [
                            {
                                'label': det['label'],
                                'family': det['family'],
                                'conf': det['conf'],
                                'bbox': list(map(int, det['bbox'])),
                                'speed_limit': det['speed_limit'],
                            }
                            for det in detections
                        ],
                        'tracks': [
                            {
                                'track_id': track.track_id,
                                'label': track.label,
                                'family': track.family,
                                'state': track.state,
                                'warning_level': track.warning_level,
                                'conf': round(float(track.confidence), 4),
                                'hit_count': track.hit_count,
                                'miss_count': track.miss_count,
                                'speed_limit': track.speed_limit,
                                'source': track.source,
                            }
                            for track in tracks
                        ],
                        'primary_track_id': primary_track.track_id if primary_track else None,
                        'primary_warning_level': primary_track.warning_level if primary_track else 0,
                        'primary_label': primary_track.label if primary_track else None,
                        'runtime': {
                            'fps_smooth': round(float(fps_smooth), 3),
                            'run_inference': run_inference,
                        },
                    }
                    f_jsonl.write(json.dumps(event, ensure_ascii=False) + '\n')

                # Update counters
                for reason in quality['reasons']:
                    quality_reason_counter[reason] += 1
                for track in tracks:
                    family_counter[track.family] += 1
                    state_counter[track.state] += 1
                if primary_track is not None:
                    published_counter[f'L{primary_track.warning_level}:{primary_track.family}'] += 1

                t_draw_start = time.time()
                annotated = draw_production_lite_overlay(frame, tracks, quality, feature_state, fps=fps_smooth if fps_smooth > 0 else None)
                total_draw_time += (time.time() - t_draw_start)

                if writer is not None:
                    writer.write(annotated)

                if primary_track is not None and len(preview_paths) < 4 and primary_track.warning_level >= 1:
                    if primary_track.track_id not in saved_preview_tids:
                        preview_path = preview_dir / f'frame_{frame_idx:05d}_track_{primary_track.track_id}.jpg'
                        cv2.imwrite(str(preview_path), annotated)
                        preview_paths.append(preview_path)
                        saved_preview_tids.add(primary_track.track_id)

                if not args.no_display:
                    cv2.imshow("TSR Production-Lite Demo (q to quit)", annotated)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        break

                if frame_idx % 15 == 0:
                    logger.info(f"[PROD-LITE] Frame {frame_idx} | FPS~{fps_smooth:.1f} | Feature: {feature_state} | Tracks: {len(tracks)}")

            else:
                # 1. Preprocessing (includes optional CLAHE)
                t_start = time.time()
                proc_frame = preprocess(frame, max_width=max_width, clahe=args.clahe)
                t_prep = time.time() - t_start
                total_prep_time += t_prep

                if run_inference:
                    # 2. Inference
                    t_inf_start = time.time()
                    yolo_dets = yolo_detector.detect(proc_frame)
                    t_inf = time.time() - t_inf_start
                    total_inf_time += t_inf

                    # 3. Postprocessing
                    t_post_start = time.time()
                    
                    # Scale boxes from proc_frame back to original resolution
                    scaled_dets = scale_detections(yolo_dets, proc_frame.shape, frame.shape)
                    
                    # Apply ROI-Filter if enabled
                    if args.roi_filter:
                        scaled_dets = filter_by_roi(scaled_dets, frame.shape)
                        
                    t_post = time.time() - t_post_start
                    total_post_time += t_post

                    # 4. Tracking / Hold stabilization
                    t_track_start = time.time()
                    if tracker is not None:
                        detections = tracker.update(scaled_dets)
                    else:
                        filtered_dets = [d for d in scaled_dets if d[6] >= conf_thres]
                        if filtered_dets:
                            detections = filtered_dets
                            last_detections = filtered_dets
                            hold_left = args.hold
                        elif hold_left > 0 and last_detections:
                            detections = last_detections
                            hold_left -= 1
                    t_track = time.time() - t_track_start
                    total_track_time += t_track

                    total_detections += len(detections)
                    dt_total = t_prep + t_inf + t_post + t_track
                    inst_fps = 1.0 / dt_total if dt_total > 0 else 0
                    fps_smooth = 0.85 * fps_smooth + 0.15 * inst_fps if fps_smooth > 0 else inst_fps
                else:
                    t_track_start = time.time()
                    if tracker is not None:
                        detections = tracker.update([])
                    else:
                        if hold_left > 0 and last_detections:
                            detections = last_detections
                            hold_left -= 1
                    t_track = time.time() - t_track_start
                    total_track_time += t_track

                # 5. Drawing & Rendering
                t_draw_start = time.time()
                annotated = draw_detections(frame, detections, fps=fps_smooth)
                t_draw = time.time() - t_draw_start
                total_draw_time += t_draw

                if writer is not None:
                    writer.write(annotated)

                if not args.no_display:
                    cv2.imshow("TSR Demo (q to quit)", annotated)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        break

                if frame_idx % 15 == 0:
                    logger.info(f"Frame {frame_idx} | FPS~{fps_smooth:.1f} | Signs: {len(detections)}")

    finally:
        cap.release()
        if writer:
            writer.release()
        if f_jsonl is not None:
            f_jsonl.close()
        cv2.destroyAllWindows()

    # Latency Breakdown Printout
    logger.info("=" * 40)
    logger.info("DEMO HOÀN TẤT - BÁO CÁO HIỆU NĂNG")
    logger.info("=" * 40)
    logger.info(f"Tổng số frame xử lý: {frame_idx}")
    logger.info(f"Tổng số lượt phát hiện (có hold/track): {total_detections}")
    if frame_idx > 0:
        logger.info(f"Thời gian TB Preprocess:  {total_prep_time/frame_idx*1000:.2f} ms")
        logger.info(f"Thời gian TB Inference:   {total_inf_time/max(1, frame_idx // (skip + 1))*1000:.2f} ms")
        logger.info(f"Thời gian TB Postprocess: {total_post_time/max(1, frame_idx // (skip + 1))*1000:.2f} ms")
        logger.info(f"Thời gian TB Tracking:    {total_track_time/frame_idx*1000:.2f} ms")
        logger.info(f"Thời gian TB Rendering:   {total_draw_time/frame_idx*1000:.2f} ms")
    logger.info("=" * 40)

    # Print Production-Lite details and Evaluation if enabled
    if args.production_lite:
        logger.info("=" * 40)
        logger.info("PRODUCTION-LITE REPLAY SUMMARY REPORT")
        logger.info("=" * 40)
        summary = {
            'frames_processed': frame_idx,
            'output_video': str(args.output) if args.output else "None",
            'events_jsonl': str(events_jsonl) if args.events_log else "None",
            'profile': {
                'name': profile_name,
                'imgsz': imgsz,
                'max_width': max_width,
                'skip': skip,
                'conf': conf_thres
            },
            'published_counter': dict(published_counter),
            'state_counter': dict(state_counter),
            'quality_reason_counter': dict(quality_reason_counter),
            'family_counter': dict(family_counter),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        logger.info("=" * 40)

        # Ground-truth evaluation
        if args.gt_path:
            logger.info(f"Đang chạy đánh giá với file ground-truth: {args.gt_path}")
            try:
                events_list = []
                with open(events_jsonl, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            events_list.append(json.loads(line))
                
                gt_by_frame = load_optional_gt(args.gt_path)
                gt_result = evaluate_against_gt(
                    events=events_list,
                    gt_by_frame=gt_by_frame,
                    conf_threshold=conf_thres,
                    match_mode='family',
                    iou_threshold=0.5
                )
                
                logger.info("=" * 40)
                logger.info("BÁO CÁO ĐÁNH GIÁ GROUND-TRUTH (IoU=0.5)")
                logger.info("=" * 40)
                print(f"TP: {gt_result['tp']} | FP: {gt_result['fp']} | FN: {gt_result['fn']}")
                print(f"Precision: {100.0 * gt_result['precision']:.2f}%")
                print(f"Recall:    {100.0 * gt_result['recall']:.2f}%")
                print(f"F1-Score:  {100.0 * gt_result['f1']:.2f}%")
                
                print("\nRecall theo kích thước:")
                for r in gt_result['size_rows']:
                    print(f"  {r['size_bin']}: GT count={r['gt_count']}, matched={r['matched']}, recall={r['recall']}")
                    
                print("\nChi tiết theo Family:")
                for r in gt_result['family_rows']:
                    print(f"  {r['family_or_label']}: TP={r['tp']}, FP={r['fp']}, FN={r['fn']}, Prec={r['precision']}, Recall={r['recall']}")
                logger.info("=" * 40)
            except Exception as e:
                logger.error(f"Lỗi khi chạy đánh giá ground-truth: {e}")


if __name__ == "__main__":
    main()
