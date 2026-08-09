#!/usr/bin/env python3
"""
TSR Demo - Vietnam Traffic Sign Detection (Inference only)
==========================================================
Model mặc định: star092304/traffic-sign-detection-vietnam-yolo (best.pt, 82 lớp).

Ví dụ:
    python tsr_demo.py --no-display
    python tsr_demo.py --weights ../models/custom.pt
    python tsr_demo.py --source 0 --traditional
    python tsr_demo.py --no-display --hold 3 --verify-threshold 0.25
    python tsr_demo.py --no-display --thermal-threshold 80
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"
DEFAULT_VIDEO = ROOT / "videos" / "traffic_sign_test.mp4"
VN_HF_REPO = "star092304/traffic-sign-detection-vietnam-yolo"


def load_cta_monitor_class():
    try:
        from cta_monitor import IEEE2020CTAMonitorV2
        return IEEE2020CTAMonitorV2
    except ImportError:
        monitor_path = CODE_DIR / "cta_monitor.py"
        spec = importlib.util.spec_from_file_location("cta_monitor", monitor_path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules["cta_monitor"] = module
        spec.loader.exec_module(module)
        return module.IEEE2020CTAMonitorV2


IEEE2020CTAMonitorV2 = load_cta_monitor_class()

Detection = Tuple[int, int, int, int, str, Tuple[int, int, int], float, str]
Detections = List[Detection]

QUALITY_OK = "AVAILABLE"
QUALITY_DEGRADED = "DEGRADED"
QUALITY_UNAVAILABLE = "UNAVAILABLE"
MODE_NORMAL = "NORMAL"
MODE_DEGRADED = "DEGRADED"

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


@dataclass
class ImageQuality:
    """Runtime proxy for IEEE 2020 CTA/CSNR-style image quality gating."""

    state: str
    cta: float
    csnr: float
    cdp: float
    blur: float
    saturation_ratio: float
    reason: str
    sotif_action: str


@dataclass
class ThermalState:
    mode: str = MODE_NORMAL
    max_temp_c: Optional[float] = None
    reason: str = "thermal_unavailable"


class StateManager:
    """Hold-based display state manager used before publishing demo/HMI output."""

    def __init__(self, hold_frames: int = 3):
        self.hold_frames = max(0, hold_frames)
        self.last_detections: Detections = []
        self.hold_left = 0
        self.reason = "empty"

    def update(self, detections: Detections, quality: ImageQuality, accept_new: bool = True) -> Detections:
        if quality.state == QUALITY_UNAVAILABLE:
            self.last_detections = []
            self.hold_left = 0
            self.reason = f"cleared:{quality.reason}"
            return []

        if detections and accept_new:
            self.last_detections = list(detections)
            self.hold_left = self.hold_frames
            self.reason = "new_detection"
            return list(detections)

        if self.last_detections and self.hold_left > 0:
            self.hold_left -= 1
            self.reason = "held_detection" if accept_new else f"held_due_quality:{quality.reason}"
            return list(self.last_detections)

        if not accept_new and detections:
            self.reason = f"suppressed_due_quality:{quality.reason}"
        else:
            self.reason = "empty"
        self.last_detections = []
        return []


class ThermalMonitor:
    """Lightweight sysfs thermal monitor for Jetson/Linux edge targets."""

    def __init__(self, threshold_c: float = 80.0, enabled: bool = True, sample_period: int = 15):
        self.threshold_c = threshold_c
        self.enabled = enabled
        self.sample_period = max(1, sample_period)
        self.state = ThermalState(reason="thermal_disabled" if not enabled else "thermal_unavailable")

    def update(self, frame_idx: int) -> ThermalState:
        if not self.enabled:
            self.state = ThermalState(reason="thermal_disabled")
            return self.state
        if frame_idx % self.sample_period != 1:
            return self.state

        temps = []
        thermal_root = Path("/sys/devices/virtual/thermal")
        try:
            for temp_file in thermal_root.glob("thermal_zone*/temp"):
                raw = temp_file.read_text(encoding="utf-8").strip()
                if not raw:
                    continue
                value = float(raw)
                temps.append(value / 1000.0 if value > 200 else value)
        except (OSError, ValueError):
            temps = []

        if not temps:
            self.state = ThermalState(reason="thermal_unavailable")
            return self.state

        max_temp = max(temps)
        if max_temp >= self.threshold_c:
            self.state = ThermalState(MODE_DEGRADED, max_temp, f"thermal_ge_{self.threshold_c:.0f}c")
        else:
            self.state = ThermalState(MODE_NORMAL, max_temp, "thermal_ok")
        return self.state


def preprocess(frame: np.ndarray, max_width: int = 960) -> np.ndarray:
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    return frame


def clamp_box(x1: int, y1: int, x2: int, y2: int, shape: tuple, pad_ratio: float = 0.0) -> Tuple[int, int, int, int]:
    h, w = shape[:2]
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    pad_x = int(bw * pad_ratio)
    pad_y = int(bh * pad_ratio)
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(w, x2 + pad_x),
        min(h, y2 + pad_y),
    )


CTA_MONITOR = IEEE2020CTAMonitorV2(
    cta_threshold=0.35,
    csnr_threshold=4.0,
    sharpness_threshold=50.0,
    saturation_threshold=0.35,
)


def compute_image_quality(frame: np.ndarray, monitor: IEEE2020CTAMonitorV2 = CTA_MONITOR) -> ImageQuality:
    """Compute IEEE 2020 CTA/CSNR/CDP proxies from upper-third ROI before HMI publish."""
    if frame.size == 0:
        return ImageQuality(
            QUALITY_UNAVAILABLE,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            "empty_frame",
            "IGNORE",
        )

    result = monitor.analyze_frame_upper_third(frame)
    if result.status == "SAFE":
        state = QUALITY_OK
        reason = "image_ok"
    elif result.status == "DEGRADED_BLUR":
        state = QUALITY_DEGRADED
        reason = "blur_high"
    elif result.status == "UNSAFE_RAIN_OR_GLARE":
        state = QUALITY_UNAVAILABLE
        reason = "low_cta_or_csnr_or_glare"
    else:
        state = QUALITY_UNAVAILABLE
        reason = result.status.lower()

    return ImageQuality(
        state,
        round(result.cta, 3),
        round(result.csnr, 2),
        round(result.cdp, 3),
        round(result.sharpness, 1),
        round(result.saturation_ratio, 3),
        reason,
        result.sotif_action,
    )


def hmi_state_for(quality: ImageQuality, thermal: ThermalState) -> str:
    if quality.state == QUALITY_UNAVAILABLE:
        return QUALITY_UNAVAILABLE
    if quality.state == QUALITY_DEGRADED or thermal.mode == MODE_DEGRADED:
        return QUALITY_DEGRADED
    return QUALITY_OK


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


def color_ratios_from_hsv(hsv_roi: np.ndarray) -> dict:
    total = max(1, hsv_roi.shape[0] * hsv_roi.shape[1])
    ratios = {}
    for name, (lo, hi) in HSV_RANGES.items():
        ratios[name] = float(np.count_nonzero(cv2.inRange(hsv_roi, lo, hi))) / total
    ratios["red"] = ratios.get("red1", 0.0) + ratios.get("red2", 0.0)
    return ratios


def best_sign_color(frame_roi: np.ndarray) -> Tuple[str, float]:
    if frame_roi.size == 0:
        return "unknown", 0.0
    hsv_roi = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2HSV)
    ratios = color_ratios_from_hsv(hsv_roi)
    candidates = {
        "red": ratios.get("red", 0.0),
        "blue": ratios.get("blue", 0.0),
        "yellow": ratios.get("yellow", 0.0),
    }
    return max(candidates.items(), key=lambda item: item[1])


def label_for_traditional(color_name: str, shape: str, source: str) -> Tuple[str, str]:
    suffix = "hough+hsv" if source == "hough" else "hsv+contour"
    if color_name == "red" and shape == "circle":
        return f"SpeedLimit ({suffix})", "speed"
    if color_name == "red":
        return f"Stop/Prohibitory ({suffix})", "stop"
    if color_name == "yellow":
        return f"Warning ({suffix})", "warning"
    if color_name == "blue":
        return f"Mandatory ({suffix})", "mandatory"
    return f"SignCandidate ({suffix})", "default"


def detect_hough_hsv_candidates(frame: np.ndarray, min_color_ratio: float = 0.055) -> Detections:
    detections: Detections = []
    h, w = frame.shape[:2]
    if h < 32 or w < 32:
        return detections

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    min_radius = max(8, min(h, w) // 80)
    max_radius = max(min_radius + 2, min(h, w) // 7)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(24, min(h, w) // 12),
        param1=90,
        param2=24,
        minRadius=min_radius,
        maxRadius=max_radius,
    )
    if circles is None:
        return detections

    for cx, cy, radius in np.round(circles[0, :]).astype(int):
        x1, y1, x2, y2 = clamp_box(cx - radius, cy - radius, cx + radius, cy + radius, frame.shape, pad_ratio=0.18)
        roi = frame[y1:y2, x1:x2]
        color_name, color_ratio = best_sign_color(roi)
        if color_ratio < min_color_ratio:
            continue
        label, key = label_for_traditional(color_name, "circle", "hough")
        conf = round(min(0.88, 0.56 + color_ratio * 2.2), 2)
        detections.append((x1, y1, x2, y2, label, color_for_class(key), conf, key))
    return detections


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
    detections: Detections = detect_hough_hsv_candidates(frame)
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
                label = "SpeedLimit (hsv+contour)"
                key = "speed"
            elif color_name == "red":
                label = "Stop/Prohibitory (hsv+contour)"
                key = "stop"
            elif color_name == "yellow":
                label = "Warning (hsv+contour)"
                key = "warning"
            else:
                label = "Mandatory (hsv+contour)"
                key = "mandatory"
            conf = min(0.9, 0.6 + area / (h * w * 0.08))
            detections.append((x, y, x + bw, y + bh, label, color_for_class(key), round(conf, 2), key))

    return non_max_suppression_simple(detections, iou_thresh=0.45)


def verify_low_confidence_yolo(
    detections: Detections,
    frame: np.ndarray,
    publish_conf: float,
    verify_threshold: float = 0.25,
) -> Detections:
    verified: Detections = []
    high_conf = max(publish_conf, verify_threshold)
    for det in detections:
        x1, y1, x2, y2, label, color, conf, key = det
        if conf >= high_conf:
            verified.append(det)
            continue

        cx1, cy1, cx2, cy2 = clamp_box(x1, y1, x2, y2, frame.shape, pad_ratio=0.35)
        roi = frame[cy1:cy2, cx1:cx2]
        trad = detect_signs_traditional(roi, min_area=80)
        if not trad:
            continue

        best = max(trad, key=lambda d: d[6])
        raised_conf = round(min(0.65, max(conf + 0.18, publish_conf, verify_threshold, best[6] * 0.7)), 2)
        suffix = " +CV" if "+CV" not in label else ""
        verified.append((x1, y1, x2, y2, f"{label}{suffix}", color, raised_conf, f"{key}|cv_verified"))
    return verified


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


def draw_detections(
    frame,
    detections: Detections,
    fps=None,
    quality: Optional[ImageQuality] = None,
    thermal: Optional[ThermalState] = None,
    hmi_state: str = QUALITY_OK,
    state_reason: str = "",
):
    annotated = frame.copy()
    critical_detected = any(is_critical(d[7]) for d in detections)
    alert_enabled = hmi_state == QUALITY_OK

    for x1, y1, x2, y2, label, color, conf, _ in detections:
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if critical_detected and alert_enabled:
        alert = "CANH BAO - BIEN BAO NGUY HIEM"
        (aw, _), _ = cv2.getTextSize(alert, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cx = (annotated.shape[1] - aw) // 2
        cv2.putText(annotated, alert, (cx, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    elif critical_detected and hmi_state != QUALITY_OK:
        alert = f"TSR {hmi_state} - CANH BAO TAM NGAT"
        (aw, _), _ = cv2.getTextSize(alert, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cx = max(10, (annotated.shape[1] - aw) // 2)
        cv2.putText(annotated, alert, (cx, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)

    if fps is not None:
        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"Signs: {len(detections)}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    if quality is not None:
        status_color = (0, 255, 0) if hmi_state == QUALITY_OK else (0, 165, 255)
        if hmi_state == QUALITY_UNAVAILABLE:
            status_color = (0, 0, 255)
        quality_text = (
            f"HMI: {hmi_state} | CTA={quality.cta:.3f} CSNR={quality.csnr:.2f} "
            f"CDP={quality.cdp:.2f} Sharp={quality.blur:.0f} | {quality.reason}"
        )
        cv2.putText(annotated, quality_text, (10, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)
    if thermal is not None:
        temp = "NA" if thermal.max_temp_c is None else f"{thermal.max_temp_c:.1f}C"
        thermal_text = f"Edge: {thermal.mode} | Temp={temp} | State={state_reason}"
        cv2.putText(annotated, thermal_text, (10, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 1)

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


def load_yolo(weights: Path):
    try:
        from ultralytics import YOLO
    except Exception as exc:
        raise SystemExit("[ERROR] Cần cài ultralytics: pip install ultralytics") from exc
    return YOLO(str(weights))


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
    parser.add_argument("--verify-threshold", type=float, default=0.25, help="YOLO confidence dưới ngưỡng này cần Hough+HSV xác minh")
    parser.add_argument("--no-quality-gate", action="store_true", help="Tắt quality gate CTA/CSNR runtime")
    parser.add_argument("--thermal-threshold", type=float, default=80.0, help="Ngưỡng nhiệt độ để vào Degraded Mode")
    parser.add_argument("--no-thermal-monitor", action="store_true", help="Tắt đọc nhiệt độ sysfs")
    parser.add_argument("--traditional", action="store_true", help="Bật thêm nhánh CV truyền thống")
    parser.add_argument("--no-display", action="store_true", help="Headless mode")
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
    yolo_model = load_yolo(weights)
    print(
        f"[INFO] Classes: {len(yolo_model.names)} | conf={args.conf} | "
        f"imgsz={args.imgsz} | max_width={args.max_width} | skip={args.skip} | hold={args.hold}"
    )
    print(
        f"[INFO] Nguồn: {args.source} | Traditional={'ON' if args.traditional else 'OFF'} | "
        f"verify_low_conf<{args.verify_threshold}"
    )

    frame_idx = 0
    fps_smooth = 0.0
    total_detections = 0
    state_manager = StateManager(hold_frames=args.hold)
    thermal_monitor = ThermalMonitor(
        threshold_c=args.thermal_threshold,
        enabled=not args.no_thermal_monitor,
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        thermal = thermal_monitor.update(frame_idx)
        runtime_degraded = thermal.mode == MODE_DEGRADED
        effective_imgsz = min(args.imgsz, 512) if runtime_degraded else args.imgsz
        effective_skip = max(args.skip, 2) if runtime_degraded else args.skip
        effective_traditional = args.traditional and not runtime_degraded
        run_inference = effective_skip <= 0 or (frame_idx % (effective_skip + 1) == 1)
        raw_detections: Detections = []

        proc_frame = preprocess(frame, max_width=args.max_width)
        quality = (
            ImageQuality(QUALITY_OK, 1.0, 99.0, 1.0, 999.0, 0.0, "quality_gate_disabled", "DISPLAY_CONFIRMED")
            if args.no_quality_gate
            else compute_image_quality(proc_frame)
        )

        if run_inference and quality.state != QUALITY_UNAVAILABLE:
            t1 = time.time()
            model_conf = min(args.conf, args.verify_threshold)
            yolo_detections = detect_with_yolo(proc_frame, yolo_model, conf_thres=model_conf, imgsz=effective_imgsz)
            raw_detections = verify_low_confidence_yolo(
                yolo_detections,
                proc_frame,
                publish_conf=args.conf,
                verify_threshold=args.verify_threshold,
            )
            if effective_traditional and quality.state == QUALITY_OK:
                trad = detect_signs_traditional(proc_frame)
                raw_detections = non_max_suppression_simple(raw_detections + trad)
            # Scale boxes from (possibly downscaled) proc_frame back to original resolution
            raw_detections = scale_detections(raw_detections, proc_frame.shape, frame.shape)
            dt = time.time() - t1
            inst_fps = 1.0 / dt if dt > 0 else 0
            fps_smooth = 0.85 * fps_smooth + 0.15 * inst_fps if fps_smooth > 0 else inst_fps

        accept_new = args.no_quality_gate or quality.state == QUALITY_OK
        detections = state_manager.update(raw_detections, quality, accept_new=accept_new)
        total_detections += len(detections)

        hmi_state = hmi_state_for(quality, thermal)
        annotated = draw_detections(
            frame,
            detections,
            fps=fps_smooth,
            quality=quality,
            thermal=thermal,
            hmi_state=hmi_state,
            state_reason=state_manager.reason,
        )

        if writer is not None:
            writer.write(annotated)

        if not args.no_display:
            cv2.imshow("TSR Demo (q to quit)", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

        if frame_idx % 15 == 0:
            temp = "NA" if thermal.max_temp_c is None else f"{thermal.max_temp_c:.1f}C"
            print(
                f"[INFO] Frame {frame_idx} | FPS~{fps_smooth:.1f} | Signs: {len(detections)} | "
                f"HMI={hmi_state} | Q={quality.reason} | Edge={thermal.mode}/{temp} | "
                f"imgsz={effective_imgsz} skip={effective_skip}"
            )

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Demo hoàn tất. Tổng detection (có hold): {total_detections}")
    if total_detections == 0:
        print("[WARN] Không có detection — thử giảm --conf (vd: 0.10) hoặc tăng --imgsz 640.")


if __name__ == "__main__":
    main()
