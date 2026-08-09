#!/usr/bin/env python3
"""
IEEE 2020 CTA/CSNR image quality monitor for TSR.

This module is intentionally small and CPU-only so it can be reused by
`tsr_demo.py` and by Colab/notebook experiments without pulling YOLO/Torch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class CTAResult:
    status: str
    cta: float
    csnr: float
    cdp: float
    sharpness: float
    saturation_ratio: float
    sotif_action: str

    def as_dict(self) -> Dict[str, float | str]:
        return {
            "status": self.status,
            "cta": self.cta,
            "csnr": self.csnr,
            "cdp": self.cdp,
            "sharpness": self.sharpness,
            "saturation_ratio": self.saturation_ratio,
            "sotif_action": self.sotif_action,
        }


class IEEE2020CTAMonitorV2:
    """
    In-line quality monitor inspired by IEEE Std 2020-2024 image-quality KPIs.

    The implementation uses runtime proxies suitable for demo/production-lite:
    Michelson contrast for CTA, foreground/background ring contrast for CSNR,
    normal-CDF based CDP, Laplacian variance for sharpness, and saturation ratio
    for glare/over-exposure detection.
    """

    def __init__(
        self,
        cta_threshold: float = 0.35,
        csnr_threshold: float = 4.0,
        sharpness_threshold: float = 50.0,
        saturation_threshold: float = 0.35,
    ):
        self.cta_threshold = cta_threshold
        self.csnr_threshold = csnr_threshold
        self.sharpness_threshold = sharpness_threshold
        self.saturation_threshold = saturation_threshold

    def _get_luminance(self, bgr_img: np.ndarray) -> np.ndarray:
        """Convert BGR image to luminance using OpenCV's BT.601 grayscale path."""
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float32)

    def _normal_cdf(self, x: float) -> float:
        """Normal cumulative distribution function without SciPy dependency."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _clip_bbox(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = map(int, bbox)
        h, w = frame.shape[:2]
        return max(0, x1), max(0, y1), min(w, x2), min(h, y2)

    def analyze_roi(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> CTAResult:
        """
        Analyze a traffic-sign ROI.

        Args:
            frame: BGR image.
            bbox: `(x1, y1, x2, y2)` in frame coordinates.
        """
        x1, y1, x2, y2 = self._clip_bbox(frame, bbox)
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            return CTAResult(
                status="INVALID_ROI",
                cta=0.0,
                csnr=0.0,
                cdp=0.0,
                sharpness=0.0,
                saturation_ratio=0.0,
                sotif_action="IGNORE",
            )

        roi = frame[y1:y2, x1:x2]
        roi_y = self._get_luminance(roi)

        l_min, l_max, _, _ = cv2.minMaxLoc(roi_y)
        denom = l_max + l_min
        cta = (l_max - l_min) / denom if denom > 0 else 0.0

        rh, rw = roi_y.shape
        cy, cx = rh // 2, rw // 2
        dy, dx = max(1, int(rh * 0.25)), max(1, int(rw * 0.25))

        fg_mask = np.zeros_like(roi_y, dtype=np.uint8)
        cv2.rectangle(fg_mask, (cx - dx, cy - dy), (cx + dx, cy + dy), 255, -1)
        bg_mask = cv2.bitwise_not(fg_mask)

        fg_pixels = roi_y[fg_mask == 255]
        bg_pixels = roi_y[bg_mask == 255]
        if len(fg_pixels) > 0 and len(bg_pixels) > 0:
            mean_fg = float(np.mean(fg_pixels))
            mean_bg = float(np.mean(bg_pixels))
            corner_block = roi_y[: min(5, rh), : min(5, rw)]
            std_noise = max(float(np.std(corner_block)), 0.5)
            contrast_diff = abs(mean_fg - mean_bg)
            csnr = contrast_diff / std_noise
            cdp = self._normal_cdf((contrast_diff - 5.0) / std_noise)
        else:
            csnr = 0.0
            cdp = 0.0

        sharpness = float(cv2.Laplacian(roi_y, cv2.CV_32F).var())
        saturation_ratio = float(np.mean(roi[:, :, 2] >= 245))

        is_cta_ok = cta >= self.cta_threshold
        is_csnr_ok = csnr >= self.csnr_threshold
        is_sharp_ok = sharpness >= self.sharpness_threshold
        is_saturation_ok = saturation_ratio < self.saturation_threshold

        if is_cta_ok and is_csnr_ok and is_sharp_ok and is_saturation_ok:
            status = "SAFE"
            sotif_action = "DISPLAY_CONFIRMED"
        elif not is_cta_ok or not is_csnr_ok or not is_saturation_ok:
            status = "UNSAFE_RAIN_OR_GLARE"
            sotif_action = "DEGRADED_VERIFICATION_REQUIRED"
        else:
            status = "DEGRADED_BLUR"
            sotif_action = "HOLD_PREVIOUS_DECISION"

        return CTAResult(
            status=status,
            cta=float(cta),
            csnr=float(csnr),
            cdp=float(cdp),
            sharpness=float(sharpness),
            saturation_ratio=float(saturation_ratio),
            sotif_action=sotif_action,
        )

    def analyze_frame_upper_third(self, frame: np.ndarray) -> CTAResult:
        """Analyze the upper-third area where TSR signs commonly appear."""
        h, w = frame.shape[:2]
        return self.analyze_roi(frame, (0, 0, w, max(10, h // 3)))
