from __future__ import annotations
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from tracker import ProductionLiteTrack

CRITICAL_KEYWORDS = (
    "stop", "speed", "no entry", "no parking", "no overtaking", "danger",
    "slow down", "red light", "children crossing", "pedestrian crossing",
    "road work", "accident",
)

def is_critical(cls_name: str) -> bool:
    key = cls_name.lower().replace("_", " ")
    compact = key.replace(" ", "")
    for word in CRITICAL_KEYWORDS:
        if word in key or word.replace(" ", "") in compact:
            return True
    return False

def draw_detections(
    frame: np.ndarray, 
    detections: List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str, ...]], 
    fps: Optional[float] = None
) -> np.ndarray:
    annotated = frame.copy()
    # Check if there is a critical detection
    critical_detected = any(is_critical(d[7]) for d in detections)

    for det in detections:
        x1, y1, x2, y2, label, color, conf, key = det[:8]
        track_id = det[8] if len(det) > 8 else None
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        if track_id is not None:
            text = f"ID:{track_id} {label} {conf:.2f}"
        else:
            text = f"{label} {conf:.2f}"
            
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    if critical_detected:
        alert = "CANH BAO - BIEN BAO NGUY HIEM"
        (aw, _), _ = cv2.getTextSize(alert, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cx = (annotated.shape[1] - aw) // 2
        cv2.putText(annotated, alert, (cx, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    if fps is not None:
        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated, f"Signs: {len(detections)}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

    return annotated


SIGN_COLORS_LITE = {
    'stop': (0, 0, 255),
    'speed': (0, 0, 255),
    'no_entry': (0, 0, 255),
    'warning': (0, 200, 255),
    'mandatory': (255, 0, 0),
    'info': (0, 180, 0),
    'default': (0, 180, 0),
}


def draw_production_lite_overlay(
    frame: np.ndarray,
    tracks: List[ProductionLiteTrack],
    quality: Dict[str, Any],
    feature_state: str,
    fps: Optional[float] = None
) -> np.ndarray:
    annotated = frame.copy()
    for track in tracks:
        if track.state not in {'CANDIDATE', 'CONFIRMED', 'ACTIVE', 'STALE'}:
            continue
        x1, y1, x2, y2 = track.bbox
        color = SIGN_COLORS_LITE.get(track.family, SIGN_COLORS_LITE['default'])
        if track.state == 'STALE':
            color = (128, 128, 255)
        
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        text = f"T{track.track_id} {track.label} | {track.state} | L{track.warning_level} | {track.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(annotated, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), color, -1)
        cv2.putText(annotated, text, (x1 + 2, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    status_lines = [
        f"Feature: {feature_state}",
        f"QualityOK: {quality['quality_ok']}",
        f"Reasons: {','.join(quality['reasons']) if quality['reasons'] else 'NONE'}",
        f"BlurVar: {quality['blur_var']:.1f} | Luma: {quality['mean_luma']:.1f}",
    ]
    if fps is not None:
        status_lines.append(f"Infer FPS: {fps:.1f}")

    y = 24
    for line in status_lines:
        cv2.putText(annotated, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        y += 22

    return annotated
