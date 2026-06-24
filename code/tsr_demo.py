#!/usr/bin/env python3
"""
TSR Demo - Vietnam Traffic Sign Detection (Inference only)
==========================================================
Model mặc định: star092304/traffic-sign-detection-vietnam-yolo (best.pt, 82 lớp).

Ví dụ:
    python tsr_demo.py --no-display
    python tsr_demo.py --weights ../models/custom.pt
    python tsr_demo.py --source 0 --traditional
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except Exception:
    HAS_ULTRALYTICS = False

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
DEFAULT_VIDEO = ROOT / "videos" / "traffic_sign_test.mp4"
VN_HF_REPO = "star092304/traffic-sign-detection-vietnam-yolo"

Detection = Tuple[int, int, int, int, str, Tuple[int, int, int], float, str]
Detections = List[Detection]

SIGN_COLORS = {
    "stop": (0, 0, 255),
    "speed": (0, 0, 255),
    "no_entry": (0, 0, 255),
    "yield": (0, 165, 255),
    "warning": (0, 200, 255),
    "mandatory": (255, 0, 0),
    "danger": (0, 200, 255),
    "caution": (0, 200, 255),
    "default": (0, 180, 0),
}

CRITICAL_KEYWORDS = (
    "stop", "speed", "no entry", "no parking", "no overtaking", "danger",
    "slow down", "red light", "children crossing", "pedestrian crossing",
    "road work", "accident",
)

HSV_RANGES = {
    "red1": (np.array([0, 70, 50]), np.array([10, 255, 255])),
    "red2": (np.array([170, 70, 50]), np.array([179, 255, 255])),
    "blue": (np.array([100, 80, 50]), np.array([130, 255, 255])),
    "yellow": (np.array([20, 80, 50]), np.array([35, 255, 255])),
}


def preprocess(frame: np.ndarray, max_width: int = 960) -> np.ndarray:
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    return frame


def display_label(cls_name: str) -> str:
    return cls_name


def color_for_class(cls_name: str) -> Tuple[int, int, int]:
    key = cls_name.lower()
    if "speed limit" in key or key.isdigit():
        return SIGN_COLORS["speed"]
    if "stop" in key or "no entry" in key or "no parking" in key or "no overtaking" in key:
        return SIGN_COLORS["stop"]
    if "red light" in key:
        return SIGN_COLORS["stop"]
    if "danger" in key or "slow down" in key or "curve" in key or "slippery" in key or "uneven" in key:
        return SIGN_COLORS["warning"]
    if "keep" in key or "turn left" in key or "turn right" in key or "roundabout" in key or "one way" in key:
        return SIGN_COLORS["mandatory"]
    if "green light" in key:
        return SIGN_COLORS["default"]
    return SIGN_COLORS["default"]


def is_critical(cls_name: str) -> bool:
    key = cls_name.lower().replace("_", " ")
    compact = key.replace(" ", "")
    for word in CRITICAL_KEYWORDS:
        if word in key or word.replace(" ", "") in compact:
            return True
    return False


def find_contours(mask, min_area=350, max_area_ratio=0.25):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape[:2]
    max_area = h * w * max_area_ratio
    good = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        peri = cv2.arcLength(c, True)
        if peri < 40:
            continue
        good.append((c, area, peri))
    return good


def classify_shape(contour: np.ndarray, area: float, peri: float) -> str:
    approx = cv2.approxPolyDP(contour, 0.035 * peri, True)
    n_sides = len(approx)
    circularity = 4 * np.pi * area / (peri * peri) if peri > 0 else 0.0
    x, y, bw, bh = cv2.boundingRect(contour)
    aspect = bw / float(bh) if bh > 0 else 1.0
    if circularity > 0.72 and 0.75 < aspect < 1.35:
        return "circle"
    if n_sides == 3:
        return "triangle"
    if n_sides == 4:
        return "rectangle"
    if n_sides >= 7 and circularity > 0.55:
        return "circle"
    if n_sides >= 5:
        return "polygon"
    return "unknown"


def detect_signs_traditional(frame, min_area=380) -> Detections:
    detections: Detections = []
    h, w = frame.shape[:2]
    hsv = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), (5, 5), 0)

    masks = {}
    for name, (lo, hi) in HSV_RANGES.items():
        m = cv2.inRange(hsv, lo, hi)
        kernel = np.ones((5, 5), np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel, iterations=1)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=1)
        masks[name] = m

    red_mask = cv2.bitwise_or(masks["red1"], masks["red2"])
    for mask, color_name in ((red_mask, "red"), (masks["blue"], "blue"), (masks["yellow"], "yellow")):
        for contour, area, peri in find_contours(mask, min_area=min_area):
            shape = classify_shape(contour, area, peri)
            x, y, bw, bh = cv2.boundingRect(contour)
            if color_name == "red" and shape == "circle":
                label = "SpeedLimit (heuristic)"
                key = "speed"
            elif color_name == "red":
                label = "Stop/Prohibitory (heuristic)"
                key = "stop"
            elif color_name == "yellow":
                label = "Warning (heuristic)"
                key = "warning"
            else:
                label = "Mandatory (heuristic)"
                key = "mandatory"
            conf = min(0.9, 0.6 + area / (h * w * 0.08))
            detections.append((x, y, x + bw, y + bh, label, color_for_class(key), round(conf, 2), key))

    return non_max_suppression_simple(detections, iou_thresh=0.45)


def non_max_suppression_simple(dets: Detections, iou_thresh=0.45) -> Detections:
    if not dets:
        return []
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


def detect_with_yolo(frame, yolo_model, conf_thres=0.15, imgsz=640) -> Detections:
    if yolo_model is None:
        return []
    results = yolo_model(frame, imgsz=imgsz, conf=conf_thres, verbose=False, max_det=20)[0]
    detections: Detections = []
    names = yolo_model.names
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_name = names.get(cls_id, str(cls_id))
        label = display_label(cls_name)
        col = color_for_class(cls_name)
        detections.append((x1, y1, x2, y2, label, col, round(conf, 2), cls_name.lower()))
    return detections


def draw_detections(frame, detections: Detections, fps=None):
    annotated = frame.copy()
    critical_detected = any(is_critical(d[7]) for d in detections)

    for x1, y1, x2, y2, label, color, conf, _ in detections:
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if critical_detected:
        alert = "CANH BAO - BIEN BAO NGUY HIEM"
        (aw, _), _ = cv2.getTextSize(alert, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cx = (annotated.shape[1] - aw) // 2
        cv2.putText(annotated, alert, (cx, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    if fps is not None:
        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"Signs: {len(detections)}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

    return annotated


def scale_detections(dets: Detections, from_shape: tuple, to_shape: tuple) -> Detections:
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
    for x1, y1, x2, y2, label, col, conf, key in dets:
        scaled.append((
            int(x1 * sx), int(y1 * sy),
            int(x2 * sx), int(y2 * sy),
            label, col, conf, key
        ))
    return scaled


def resolve_weights(weights: Path) -> Path:
    if weights.is_file():
        return weights
    if weights.name == "best.pt":
        try:
            from huggingface_hub import hf_hub_download
            print(f"[INFO] Tải model từ HuggingFace: {VN_HF_REPO}")
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
    parser = argparse.ArgumentParser(description="TSR Inference Demo (YOLO .pt)")
    parser.add_argument("--source", type=str, default=str(DEFAULT_VIDEO), help="Video path hoặc camera index")
    parser.add_argument("--output", type=str, default=str(ROOT / "videos" / "tsr_demo_output.mp4"), help="Video annotated output")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="Đường dẫn file .pt")
    parser.add_argument("--conf", type=float, default=0.15, help="Confidence threshold (VN model: 0.15 khuyến nghị)")
    parser.add_argument("--skip", type=int, default=0, help="Bỏ qua N frame giữa các lần inference")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước inference YOLO")
    parser.add_argument("--max-width", type=int, default=1280, help="Resize frame nếu rộng hơn giá trị này")
    parser.add_argument("--hold", type=int, default=3, help="Giữ detection cũ N frame khi frame mới trống")
    parser.add_argument("--traditional", action="store_true", help="Bật thêm nhánh CV truyền thống")
    parser.add_argument("--no-display", action="store_true", help="Headless mode")
    args = parser.parse_args()

    if not HAS_ULTRALYTICS:
        raise SystemExit("[ERROR] Cần cài ultralytics: pip install ultralytics")

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
        # Prefer avc1 (H.264) for .mp4 to improve player compatibility and timing
        w = None
        if out_path.suffix.lower() == ".mp4":
            for cc in ("avc1", "mp4v", "H264"):
                fourcc = cv2.VideoWriter_fourcc(*cc)
                w = cv2.VideoWriter(str(out_path), fourcc, fps_in, (width, height))
                if w.isOpened():
                    print(f"[INFO] Ghi video ra: {out_path} (fourcc={cc})")
                    break
                w.release()
                w = None
        if w is None:
            fourcc = cv2.VideoWriter_fourcc(*("mp4v" if out_path.suffix.lower() == ".mp4" else "XVID"))
            w = cv2.VideoWriter(str(out_path), fourcc, fps_in, (width, height))
            print(f"[INFO] Ghi video ra: {out_path}")
        if not w.isOpened():
            print("[WARN] VideoWriter không mở được, bỏ ghi output.")
            w = None
        writer = w

    print(f"[INFO] Đang tải model: {weights}")
    yolo_model = YOLO(str(weights))
    print(
        f"[INFO] Classes: {len(yolo_model.names)} | conf={args.conf} | "
        f"imgsz={args.imgsz} | max_width={args.max_width} | skip={args.skip}"
    )
    print(f"[INFO] Nguồn: {args.source} | Traditional={'ON' if args.traditional else 'OFF'}")

    frame_idx = 0
    fps_smooth = 0.0
    last_detections: Detections = []
    hold_left = 0
    total_detections = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        run_inference = args.skip <= 0 or (frame_idx % (args.skip + 1) == 1)
        detections: Detections = []

        proc_frame = preprocess(frame, max_width=args.max_width)

        if run_inference:
            t1 = time.time()
            detections = detect_with_yolo(proc_frame, yolo_model, conf_thres=args.conf, imgsz=args.imgsz)
            if args.traditional:
                trad = detect_signs_traditional(proc_frame)
                detections = non_max_suppression_simple(detections + trad)
            # Scale boxes from (possibly downscaled) proc_frame back to original resolution
            detections = scale_detections(detections, proc_frame.shape, frame.shape)
            if detections:
                last_detections = detections
                hold_left = args.hold
            elif hold_left > 0 and last_detections:
                detections = last_detections
                hold_left -= 1
            total_detections += len(detections)
            dt = time.time() - t1
            inst_fps = 1.0 / dt if dt > 0 else 0
            fps_smooth = 0.85 * fps_smooth + 0.15 * inst_fps if fps_smooth > 0 else inst_fps
        else:
            # Skip inference: carry forward held detections (already scaled)
            if hold_left > 0 and last_detections:
                detections = last_detections
                hold_left -= 1

        # Always draw on CURRENT original frame (preserve full motion + correct speed)
        # Boxes use held detections when inference was skipped
        annotated = draw_detections(frame, detections, fps=fps_smooth)

        if writer is not None:
            writer.write(annotated)

        if not args.no_display:
            cv2.imshow("TSR Demo (q to quit)", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

        if frame_idx % 15 == 0:
            print(f"[INFO] Frame {frame_idx} | FPS~{fps_smooth:.1f} | Signs: {len(detections)}")

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Demo hoàn tất. Tổng detection (có hold): {total_detections}")
    if total_detections == 0:
        print("[WARN] Không có detection — thử giảm --conf (vd: 0.10) hoặc tăng --imgsz 640.")


if __name__ == "__main__":
    main()
