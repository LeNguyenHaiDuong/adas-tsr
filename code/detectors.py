from __future__ import annotations
import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path

# Type definition for Detections:
# (x1, y1, x2, y2, label, color_rgb_or_bgr, confidence, class_name)
Detection = Tuple[int, int, int, int, str, Tuple[int, int, int], float, str]
Detections = List[Detection]

# Color mappings
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

DEFAULT_HSV_RANGES = {
    "red1": (np.array([0, 70, 50]), np.array([10, 255, 255])),
    "red2": (np.array([170, 70, 50]), np.array([179, 255, 255])),
    "blue": (np.array([100, 80, 50]), np.array([130, 255, 255])),
    "yellow": (np.array([20, 80, 50]), np.array([35, 255, 255])),
}

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

class BaseDetector:
    def detect(self, frame: np.ndarray) -> Detections:
        raise NotImplementedError("Detectors must implement detect()")

class YOLODetector(BaseDetector):
    def __init__(self, weights: str | Path, conf_thres: float = 0.15, imgsz: int = 640):
        from ultralytics import YOLO
        self.model = YOLO(str(weights))
        self.conf_thres = conf_thres
        self.imgsz = imgsz

    def detect(self, frame: np.ndarray) -> Detections:
        # Run inference using a lower threshold (min 0.05) to let tracker associate low confidence detections
        results = self.model(
            frame, 
            imgsz=self.imgsz, 
            conf=min(0.05, self.conf_thres), 
            verbose=False, 
            max_det=20
        )[0]
        
        detections: Detections = []
        names = self.model.names
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_name = names.get(cls_id, str(cls_id))
            col = color_for_class(cls_name)
            detections.append((x1, y1, x2, y2, cls_name, col, round(conf, 2), cls_name.lower()))
        return detections


