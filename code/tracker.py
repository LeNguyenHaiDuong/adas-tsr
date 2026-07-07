from __future__ import annotations
from typing import List, Tuple, Optional

def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    # boxA, boxB format: (x1, y1, x2, y2)
    x1_A, y1_A, x2_A, y2_A = boxA
    x1_B, y1_B, x2_B, y2_B = boxB
    
    # Calculate areas
    area_A = (x2_A - x1_A) * (y2_A - y1_A)
    area_B = (x2_B - x1_B) * (y2_B - y1_B)
    
    # Intersection coordinates
    x1_I = max(x1_A, x1_B)
    y1_I = max(y1_A, y1_B)
    x2_I = min(x2_A, x2_B)
    y2_I = min(y2_A, y2_B)
    
    inter_area = max(0, x2_I - x1_I) * max(0, y2_I - y1_I)
    union_area = area_A + area_B - inter_area
    
    return inter_area / float(union_area + 1e-6)

class SignTrack:
    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int], label: str, color: Tuple[int, int, int], conf: float, key: str):
        self.track_id = track_id
        self.bbox = bbox
        self.label = label
        self.color = color
        self.conf = conf
        self.key = key
        self.lost_count = 0
        self.hits = 1

class SignTracker:
    def __init__(self, iou_threshold: float = 0.3, max_lost: int = 3, min_hits: int = 1, conf_threshold: float = 0.15):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost
        self.min_hits = min_hits
        self.conf_threshold = conf_threshold
        self.next_id = 1
        self.tracks: List[SignTrack] = []

    def update(self, detections: List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str]]) -> List[Tuple[int, int, int, int, str, Tuple[int, int, int], float, str, int]]:
        # input detections format: (x1, y1, x2, y2, label, color, conf, key)
        # returns format: (x1, y1, x2, y2, label, color, conf, key, track_id)
        
        # Split detections into high and low confidence groups (BYTETrack style)
        high_dets = []
        low_dets = []
        for det in detections:
            if det[6] >= self.conf_threshold:
                high_dets.append(det)
            else:
                low_dets.append(det)
        
        matched_high_idx = set()
        matched_low_idx = set()
        matched_tracks = set()
        
        # Sort existing tracks to process those with lower lost_count first (more reliable)
        self.tracks.sort(key=lambda t: t.lost_count)
        
        # 1. First association: Match active tracks with high confidence detections
        for track in self.tracks:
            best_iou = 0.0
            best_idx = -1
            for idx, det in enumerate(high_dets):
                if idx in matched_high_idx:
                    continue
                if track.key != det[7]:
                    continue
                iou = compute_iou(track.bbox, det[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx
            
            if best_iou >= self.iou_threshold and best_idx != -1:
                det = high_dets[best_idx]
                track.bbox = det[:4]
                track.label = det[4]
                track.color = det[5]
                track.conf = det[6]
                track.lost_count = 0
                track.hits += 1
                matched_high_idx.add(best_idx)
                matched_tracks.add(track)

        # 2. Second association: Match remaining unmatched tracks with low confidence detections
        for track in self.tracks:
            if track in matched_tracks:
                continue
            best_iou = 0.0
            best_idx = -1
            for idx, det in enumerate(low_dets):
                if idx in matched_low_idx:
                    continue
                if track.key != det[7]:
                    continue
                iou = compute_iou(track.bbox, det[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx
            
            if best_iou >= self.iou_threshold and best_idx != -1:
                det = low_dets[best_idx]
                track.bbox = det[:4]
                track.label = det[4]
                track.color = det[5]
                track.conf = det[6]
                track.lost_count = 0
                track.hits += 1
                matched_low_idx.add(best_idx)
                matched_tracks.add(track)

        # Update lifecycle of tracks: keep matched ones, increment lost count for unmatched ones
        updated_tracks = []
        for track in self.tracks:
            if track not in matched_tracks:
                track.lost_count += 1
                if track.lost_count <= self.max_lost:
                    updated_tracks.append(track)
            else:
                updated_tracks.append(track)
                    
        # 3. Create new tracks from unmatched high confidence detections ONLY
        for idx, det in enumerate(high_dets):
            if idx not in matched_high_idx:
                new_track = SignTrack(
                    track_id=self.next_id,
                    bbox=det[:4],
                    label=det[4],
                    color=det[5],
                    conf=det[6],
                    key=det[7]
                )
                self.next_id += 1
                updated_tracks.append(new_track)
                
        self.tracks = updated_tracks
        
        # Format results: return currently visible or active tracked signs
        results = []
        for track in self.tracks:
            # Temporal filter: Only output tracks that have been detected at least min_hits times
            if track.hits >= self.min_hits:
                results.append((
                    track.bbox[0], track.bbox[1], track.bbox[2], track.bbox[3],
                    track.label, track.color, track.conf, track.key, track.track_id
                ))
        return results
