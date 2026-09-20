#!/usr/bin/env python3
"""
Spatial-Temporal Multi-Object Tracker (ByteTrack + Kalman Filter + Temporal Majority Voting)
==========================================================================================
Dành riêng cho bài toán ADAS Traffic Sign Recognition (TSR).
Tích hợp:
1. Kalman Filter 8D (vị trí + tỷ lệ khung hình + vận tốc biến thiên).
2. Thuật toán phân bổ hai tầng ByteTrack (kết hợp cả detection điểm cao và điểm thấp).
3. Temporal Majority Voting (bầu chọn nhãn theo thời gian, chống chớp tắt và nhảy nhầm class).
4. Khử rung bounding box và nội suy vị trí khi biển bị cần gạt nước hoặc vật cản che khuất tạm thời.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment


class TrackState(IntEnum):
    New = 0
    Tracked = 1
    Lost = 2
    Removed = 3


class KalmanFilter:
    """
    Kalman Filter 8 chiều cho bounding box tracking:
    Trạng thái: [cx, cy, a, h, v_cx, v_cy, v_a, v_h]
    với cx, cy là tâm; a = w / h (tỷ lệ khung hình); h là chiều cao.
    """

    def __init__(self):
        ndim = 4
        dt = 1.0

        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        self._update_mat = np.eye(ndim, 2 * ndim)

        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T)) + motion_cov
        return mean, covariance

    def project(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        mean = np.dot(self._update_mat, mean)
        covariance = np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T)) + innovation_cov
        return mean, covariance

    def update(
        self, mean: np.ndarray, covariance: np.ndarray, measurement: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        projected_mean, projected_cov = self.project(mean, covariance)

        chol_factor, lower = np.linalg.cholesky(projected_cov), True
        kalman_gain = np.linalg.solve(
            chol_factor,
            np.dot(covariance, self._update_mat.T).T
        ).T
        kalman_gain = np.linalg.solve(chol_factor.T, kalman_gain.T).T

        innovation = measurement - projected_mean
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot((kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance


def xyxy2xyah(box: np.ndarray) -> np.ndarray:
    """Chuyển đổi [x1, y1, x2, y2] sang [center_x, center_y, aspect_ratio, height]."""
    x1, y1, x2, y2 = box
    w = max(1.0, float(x2 - x1))
    h = max(1.0, float(y2 - y1))
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0
    a = w / h
    return np.array([cx, cy, a, h], dtype=np.float32)


def xyah2xyxy(xyah: np.ndarray) -> np.ndarray:
    """Chuyển đổi [center_x, center_y, aspect_ratio, height] sang [x1, y1, x2, y2]."""
    cx, cy, a, h = xyah
    w = max(1.0, float(a * h))
    x1 = cx - w / 2.0
    y1 = cy - h / 2.0
    x2 = cx + w / 2.0
    y2 = cy + h / 2.0
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def bbox_ious(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
    """Tính ma trận IoU giữa N hộp và M hộp."""
    if len(boxes1) == 0 or len(boxes2) == 0:
        return np.zeros((len(boxes1), len(boxes2)), dtype=np.float32)

    b1_x1, b1_y1, b1_x2, b1_y2 = boxes1[:, 0], boxes1[:, 1], boxes1[:, 2], boxes1[:, 3]
    b2_x1, b2_y1, b2_x2, b2_y2 = boxes2[:, 0], boxes2[:, 1], boxes2[:, 2], boxes2[:, 3]

    inter_x1 = np.maximum(b1_x1[:, None], b2_x1[None, :])
    inter_y1 = np.maximum(b1_y1[:, None], b2_y1[None, :])
    inter_x2 = np.minimum(b1_x2[:, None], b2_x2[None, :])
    inter_y2 = np.minimum(b1_y2[:, None], b2_y2[None, :])

    inter_w = np.maximum(0.0, inter_x2 - inter_x1)
    inter_h = np.maximum(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area1 = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    area2 = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)
    union_area = area1[:, None] + area2[None, :] - inter_area

    return inter_area / np.maximum(union_area, 1e-6)


class STrack:
    """Quản lý thông tin và vòng đời của một biển báo duy nhất (Tracklet)."""

    shared_kalman = KalmanFilter()
    _count = 0

    def __init__(
        self,
        tlbr: np.ndarray,
        score: float,
        label: str,
        color: Tuple[int, int, int],
        class_key: str,
        max_history: int = 15,
    ):
        self.tlbr_orig = np.asarray(tlbr, dtype=np.float32)
        self.score = float(score)
        self.label = label
        self.color = color
        self.class_key = class_key

        self.kalman_filter = self.shared_kalman
        self.mean: Optional[np.ndarray] = None
        self.covariance: Optional[np.ndarray] = None

        self.track_id = 0
        self.state = TrackState.New
        self.is_activated = False
        self.frame_id = 0
        self.start_frame = 0
        self.tracklet_len = 0

        # Lịch sử quan sát cho Temporal Voting
        self.max_history = max_history
        self.class_history: deque = deque(maxlen=max_history)
        self.class_history.append((self.label, self.color, self.class_key, self.score))

    @property
    def tlbr(self) -> np.ndarray:
        """Tọa độ [x1, y1, x2, y2] được dự báo hoặc lọc bởi Kalman Filter."""
        if self.mean is None:
            return self.tlbr_orig
        return xyah2xyxy(self.mean[:4])

    def activate(self, kalman_filter: KalmanFilter, frame_id: int):
        self.kalman_filter = kalman_filter
        self.track_id = self.next_id()
        self.mean, self.covariance = self.kalman_filter.initiate(xyxy2xyah(self.tlbr_orig))
        self.tracklet_len = 1
        self.state = TrackState.Tracked
        self.frame_id = frame_id
        self.start_frame = frame_id
        self.is_activated = True

    def re_activate(self, new_track: "STrack", frame_id: int, new_id: bool = False):
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, xyxy2xyah(new_track.tlbr_orig)
        )
        self.tracklet_len += 1
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        self.score = new_track.score

        self.class_history.append((new_track.label, new_track.color, new_track.class_key, new_track.score))
        if new_id:
            self.track_id = self.next_id()

    def update(self, new_track: "STrack", frame_id: int):
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.score = new_track.score
        self.mean, self.covariance = self.kalman_filter.update(
            self.mean, self.covariance, xyxy2xyah(new_track.tlbr_orig)
        )
        self.state = TrackState.Tracked
        self.is_activated = True
        self.class_history.append((new_track.label, new_track.color, new_track.class_key, new_track.score))

    def predict(self):
        if self.mean is not None:
            self.mean, self.covariance = self.kalman_filter.predict(self.mean, self.covariance)

    def mark_lost(self):
        self.state = TrackState.Lost

    def mark_removed(self):
        self.state = TrackState.Removed

    def get_voted_classification(self, min_confirm_frames: int = 3) -> Tuple[str, Tuple[int, int, int], str, float, bool]:
        """
        Bầu chọn đa số theo thời gian (Temporal Majority Voting).
        Trả về: (label, color, class_key, avg_conf, is_confirmed)
        """
        if not self.class_history:
            return self.label, self.color, self.class_key, self.score, False

        # Đếm tần suất xuất hiện của từng label
        labels = [item[0] for item in self.class_history]
        counts = Counter(labels)
        best_label, freq = counts.most_common(1)[0]

        # Lấy thông tin màu và class_key tương ứng
        matching_entries = [item for item in self.class_history if item[0] == best_label]
        best_color = matching_entries[-1][1]
        best_key = matching_entries[-1][2]
        avg_score = sum(item[3] for item in matching_entries) / len(matching_entries)

        is_confirmed = (freq >= min_confirm_frames) or (self.tracklet_len >= min_confirm_frames and freq / len(labels) >= 0.5)
        return best_label, best_color, best_key, round(avg_score, 2), is_confirmed

    @classmethod
    def next_id(cls) -> int:
        cls._count += 1
        return cls._count

    @classmethod
    def reset_counter(cls):
        cls._count = 0


class RobustTSRTracker:
    """
    ByteTrack Multi-Object Tracker cho biển báo giao thông:
    - 2-stage association (High confidence + Low confidence).
    - Giữ biển báo qua các frame bị mất dấu (Lost buffer).
    - Temporal Majority Voting chống false positive tức thời.
    """

    def __init__(
        self,
        track_thresh: float = 0.25,
        low_thresh: float = 0.10,
        track_buffer: int = 15,
        match_thresh: float = 0.75,
        min_confirm_frames: int = 3,
    ):
        self.track_thresh = track_thresh
        self.low_thresh = low_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.min_confirm_frames = min_confirm_frames

        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []

        self.frame_id = 0
        self.kalman_filter = KalmanFilter()
        STrack.reset_counter()

    def reset(self):
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.removed_stracks.clear()
        self.frame_id = 0
        STrack.reset_counter()

    def update(
        self,
        raw_detections: List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str]],
    ) -> List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str, int, bool]]:
        """
        Cập nhật tracker từ danh sách raw_detections dạng:
        (x1, y1, x2, y2, label, color, conf, key)

        Trả về danh sách các biển được theo dõi:
        (x1, y1, x2, y2, label, color, conf, key, track_id, is_confirmed)
        """
        self.frame_id += 1
        activated_stracks: List[STrack] = []
        refind_stracks: List[STrack] = []
        lost_stracks: List[STrack] = []
        removed_stracks: List[STrack] = []

        # 1. Phân loại detection điểm cao và điểm thấp
        detections_high: List[STrack] = []
        detections_low: List[STrack] = []

        for d in raw_detections:
            x1, y1, x2, y2, label, color, conf, key = d
            box = np.array([x1, y1, x2, y2], dtype=np.float32)
            tracklet = STrack(box, conf, label, color, key)
            if conf >= self.track_thresh:
                detections_high.append(tracklet)
            elif conf >= self.low_thresh:
                detections_low.append(tracklet)

        # 2. Kalman Predict cho các track đang sống
        unconfirmed: List[STrack] = []
        tracked_pool: List[STrack] = []
        for t in self.tracked_stracks:
            if not t.is_activated:
                unconfirmed.append(t)
            else:
                tracked_pool.append(t)

        strack_pool = tracked_pool + self.lost_stracks
        for strack in strack_pool:
            strack.predict()

        # 3. Association tầng 1: Giữa Tracklet đang sống và Detections điểm cao
        dists = self._iou_distance(strack_pool, detections_high)
        matches_a, u_track_a, u_detection_a = self._linear_assignment(dists, thresh=self.match_thresh)

        for itracked, idet in matches_a:
            track = strack_pool[itracked]
            det = detections_high[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_stracks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        # 4. Association tầng 2 (ByteTrack cốt lõi):
        # Dùng detections điểm thấp để cứu các track bị mất dấu (do chói sáng, gạt mưa, hoặc motion blur)
        r_tracked_stracks = [
            strack_pool[i] for i in u_track_a if strack_pool[i].state == TrackState.Tracked
        ]
        dists = self._iou_distance(r_tracked_stracks, detections_low)
        matches_b, u_track_b, _ = self._linear_assignment(dists, thresh=0.6)

        for itracked, idet in matches_b:
            track = r_tracked_stracks[itracked]
            det = detections_low[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_stracks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        for it in u_track_b:
            track = r_tracked_stracks[it]
            if track.state != TrackState.Lost:
                track.mark_lost()
                lost_stracks.append(track)

        # 5. Xử lý các detection điểm cao chưa match: Match với unconfirmed tracks
        detections_rem = [detections_high[i] for i in u_detection_a]
        dists = self._iou_distance(unconfirmed, detections_rem)
        matches_c, u_unconfirmed, u_detection_c = self._linear_assignment(dists, thresh=0.7)

        for itracked, idet in matches_c:
            unconfirmed[itracked].update(detections_rem[idet], self.frame_id)
            activated_stracks.append(unconfirmed[itracked])

        for it in u_unconfirmed:
            track = unconfirmed[it]
            track.mark_removed()
            removed_stracks.append(track)

        # Khởi tạo các track mới từ detection điểm cao còn dư
        for inew in u_detection_c:
            track = detections_rem[inew]
            if track.score >= self.track_thresh:
                track.activate(self.kalman_filter, self.frame_id)
                activated_stracks.append(track)

        # 6. Dọn dẹp các track bị Lost quá thời gian quy định
        for track in self.lost_stracks:
            if self.frame_id - track.frame_id > self.track_buffer:
                track.mark_removed()
                removed_stracks.append(track)

        # Cập nhật danh sách nội bộ
        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked]
        self.tracked_stracks = self._merge_tracks(self.tracked_stracks, activated_stracks)
        self.tracked_stracks = self._merge_tracks(self.tracked_stracks, refind_stracks)

        self.lost_stracks = [t for t in self.lost_stracks if t.state == TrackState.Lost]
        self.lost_stracks = self._merge_tracks(self.lost_stracks, lost_stracks)
        self.lost_stracks = [t for t in self.lost_stracks if t not in self.tracked_stracks]

        self.removed_stracks.extend(removed_stracks)

        # 7. Trích xuất kết quả đầu ra có kèm Temporal Majority Voting
        output: List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str, int, bool]] = []
        for track in self.tracked_stracks:
            if not track.is_activated:
                continue
            v_label, v_color, v_key, v_score, is_confirmed = track.get_voted_classification(
                min_confirm_frames=self.min_confirm_frames
            )
            x1, y1, x2, y2 = map(int, track.tlbr)
            output.append((x1, y1, x2, y2, v_label, v_color, v_score, v_key, track.track_id, is_confirmed))

        return output

    @staticmethod
    def _iou_distance(atracks: List[STrack], btracks: List[STrack]) -> np.ndarray:
        if not atracks or not btracks:
            return np.zeros((len(atracks), len(btracks)), dtype=np.float32)
        aboxes = np.ascontiguousarray([track.tlbr for track in atracks], dtype=np.float32)
        bboxes = np.ascontiguousarray([track.tlbr for track in btracks], dtype=np.float32)
        ious = bbox_ious(aboxes, bboxes)
        return 1.0 - ious

    @staticmethod
    def _linear_assignment(cost_matrix: np.ndarray, thresh: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        if cost_matrix.size == 0:
            return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        matches: List[Tuple[int, int]] = []
        unmatched_a: List[int] = list(set(range(cost_matrix.shape[0])) - set(row_ind))
        unmatched_b: List[int] = list(set(range(cost_matrix.shape[1])) - set(col_ind))

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] <= thresh:
                matches.append((r, c))
            else:
                unmatched_a.append(r)
                unmatched_b.append(c)

        return matches, sorted(unmatched_a), sorted(unmatched_b)

    @staticmethod
    def _merge_tracks(current: List[STrack], new_tracks: List[STrack]) -> List[STrack]:
        track_map = {t.track_id: t for t in current}
        for t in new_tracks:
            track_map[t.track_id] = t
        return list(track_map.values())
