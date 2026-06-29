from __future__ import annotations
import cv2
import numpy as np
from typing import List, Tuple, Optional

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
