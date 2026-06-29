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
        # Run inference using the YOLO model
        results = self.model(
            frame, 
            imgsz=self.imgsz, 
            conf=self.conf_thres, 
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

class TraditionalDetector(BaseDetector):
    def __init__(self, min_area: int = 380, hsv_ranges: Optional[Dict] = None):
        self.min_area = min_area
        self.hsv_ranges = hsv_ranges or DEFAULT_HSV_RANGES

    def find_contours(self, mask, max_area_ratio=0.25):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = mask.shape[:2]
        max_area = h * w * max_area_ratio
        good = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area or area > max_area:
                continue
            peri = cv2.arcLength(c, True)
            if peri < 40:
                continue
            good.append((c, area, peri))
        return good

    def classify_shape(self, contour: np.ndarray, area: float, peri: float) -> str:
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

    def detect(self, frame: np.ndarray) -> Detections:
        detections: Detections = []
        h, w = frame.shape[:2]
        hsv = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV), (5, 5), 0)

        masks = {}
        for name, (lo, hi) in self.hsv_ranges.items():
            m = cv2.inRange(hsv, lo, hi)
            kernel = np.ones((5, 5), np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel, iterations=1)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=1)
            masks[name] = m

        red_mask = cv2.bitwise_or(masks["red1"], masks["red2"])
        for mask, color_name in ((red_mask, "red"), (masks["blue"], "blue"), (masks["yellow"], "yellow")):
            for contour, area, peri in self.find_contours(mask):
                shape = self.classify_shape(contour, area, peri)
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

        return detections
