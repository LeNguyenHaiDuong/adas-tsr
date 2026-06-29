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
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

from detectors import YOLODetector, TraditionalDetector, Detections
from tracker import SignTracker
from visualizer import draw_detections

# Setup logger
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger("TSR")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
DEFAULT_VIDEO = ROOT / "videos" / "traffic_sign_test.mp4"
VN_HF_REPO = "star092304/traffic-sign-detection-vietnam-yolo"


def preprocess(frame: np.ndarray, max_width: int = 960) -> np.ndarray:
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    return frame


def non_max_suppression_simple(dets: Detections, iou_thresh=0.45) -> Detections:
    if not dets:
        return []
    # Sort by bounding box area descending
    dets = sorted(dets, key=lambda d: int(d[2] - d[0]) * int(d[3] - d[1]), reverse=True)
    keep: Detections = []
    for d in dets:
        x1, y1, x2, y2 = map(int, d[:4])
        discard = False
        for k in keep:
            kx1, ky1, kx2, ky2 = map(int, k[:4])
            inter_x1, inter_y1 = max(x1, kx1), max(y1, ky1)
            inter_x2, inter_y2 = min(x2, kx2), min(y2, ky2)
            inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
            area1 = (x2 - x1) * (y2 - y1)
            area2 = (kx2 - kx1) * (ky2 - ky1)
            if inter / (area1 + area2 - inter + 1e-6) > iou_thresh:
                discard = True
                break
        if not discard:
            keep.append(d)
    return keep


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
    parser = argparse.ArgumentParser(description="TSR Inference Demo (YOLO .pt & Tracking)")
    parser.add_argument("--source", type=str, default=str(DEFAULT_VIDEO), help="Video path hoặc camera index")
    parser.add_argument("--output", type=str, default=str(ROOT / "videos" / "tsr_demo_output.mp4"), help="Video annotated output")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="Đường dẫn file .pt")
    parser.add_argument("--conf", type=float, default=0.15, help="Confidence threshold (VN model: 0.15 khuyến nghị)")
    parser.add_argument("--skip", type=int, default=0, help="Bỏ qua N frame giữa các lần inference")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước inference YOLO")
    parser.add_argument("--max-width", type=int, default=1280, help="Resize frame nếu rộng hơn giá trị này")
    parser.add_argument("--hold", type=int, default=3, help="Giữ detection cũ N frame khi frame mới trống (chỉ dùng nếu tắt tracker)")
    parser.add_argument("--traditional", action="store_true", help="Bật thêm nhánh CV truyền thống")
    parser.add_argument("--no-display", action="store_true", help="Headless mode")
    parser.add_argument("--no-tracker", action="store_true", help="Tắt tính năng theo vết đối tượng (Tracker)")
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
        # Try multiple encoders
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

    # Load detectors
    logger.info(f"Đang tải model YOLO: {weights}")
    yolo_detector = YOLODetector(weights, conf_thres=args.conf, imgsz=args.imgsz)
    
    trad_detector = TraditionalDetector() if args.traditional else None
    
    # Initialize tracker
    tracker = None if args.no_tracker else SignTracker(max_lost=args.hold)

    logger.info(f"Config: conf={args.conf} | imgsz={args.imgsz}")
    logger.info(f"Nguồn: {args.source} | Traditional={'ON' if args.traditional else 'OFF'} | Tracker={'OFF' if args.no_tracker else 'ON'}")

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

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        run_inference = args.skip <= 0 or (frame_idx % (args.skip + 1) == 1)
        detections = []

        # 1. Preprocessing
        t_start = time.time()
        proc_frame = preprocess(frame, max_width=args.max_width)
        t_prep = time.time() - t_start
        total_prep_time += t_prep

        if run_inference:
            # 2. Inference
            t_inf_start = time.time()
            yolo_dets = yolo_detector.detect(proc_frame)
            t_inf = time.time() - t_inf_start
            total_inf_time += t_inf

            # 3. Postprocessing (including Traditional CV if enabled)
            t_post_start = time.time()
            if trad_detector is not None:
                trad_dets = trad_detector.detect(proc_frame)
                yolo_dets = non_max_suppression_simple(yolo_dets + trad_dets)
            
            # Scale boxes from proc_frame back to original resolution
            scaled_dets = scale_detections(yolo_dets, proc_frame.shape, frame.shape)
            t_post = time.time() - t_post_start
            total_post_time += t_post

            # 4. Tracking / Hold stabilization
            t_track_start = time.time()
            if tracker is not None:
                detections = tracker.update(scaled_dets)
            else:
                # Basic hold mechanism
                if scaled_dets:
                    detections = scaled_dets
                    last_detections = scaled_dets
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
            # Skip inference frame: carry forward held/tracked detections
            t_track_start = time.time()
            if tracker is not None:
                # Empty update to update tracker frames lost
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

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()

    # Latency Breakdown Printout
    logger.info("=" * 40)
    logger.info("DEMO HOÀN TẤT - BÁO CÁO HIỆU NĂNG")
    logger.info("=" * 40)
    logger.info(f"Tổng số frame xử lý: {frame_idx}")
    logger.info(f"Tổng số lượt phát hiện (có hold/track): {total_detections}")
    if frame_idx > 0:
        logger.info(f"Thời gian TB Preprocess:  {total_prep_time/frame_idx*1000:.2f} ms")
        logger.info(f"Thời gian TB Inference:   {total_inf_time/max(1, frame_idx // (args.skip + 1))*1000:.2f} ms")
        logger.info(f"Thời gian TB Postprocess: {total_post_time/max(1, frame_idx // (args.skip + 1))*1000:.2f} ms")
        logger.info(f"Thời gian TB Tracking:    {total_track_time/frame_idx*1000:.2f} ms")
        logger.info(f"Thời gian TB Rendering:   {total_draw_time/frame_idx*1000:.2f} ms")
    logger.info("=" * 40)


if __name__ == "__main__":
    main()
