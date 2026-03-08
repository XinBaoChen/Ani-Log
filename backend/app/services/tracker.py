"""Multi-Object Tracker with CLIP-based re-identification.

Handles the core engineering challenge: tracking characters across
scene cuts using a combination of IoU-based tracking (ByteTrack-style)
and CLIP feature matching via the vector database.
"""

import numpy as np
from dataclasses import dataclass, field
from scipy.optimize import linear_sum_assignment
from loguru import logger

from app.core.config import settings
from app.models.schemas import Detection


@dataclass
class Track:
    """A tracked entity across frames."""
    track_id: int
    label: str
    bbox: list[float]
    feature: np.ndarray | None = None
    age: int = 0
    hits: int = 1
    time_since_update: int = 0
    character_id: str | None = None  # linked character in DB
    history: list[list[float]] = field(default_factory=list)


class MultiObjectTracker:
    """
    ByteTrack-style MOT with CLIP re-identification.

    When a character leaves and re-enters the frame (or across scene cuts),
    we use CLIP features stored in ChromaDB to re-identify them.
    """

    def __init__(self):
        self._next_id = 1
        self._active_tracks: dict[int, Track] = {}
        self._lost_tracks: dict[int, Track] = {}
        self._max_age = settings.tracker_max_age
        self._min_hits = settings.tracker_min_hits
        self._iou_threshold = settings.tracker_iou_threshold
        self._reid_threshold = settings.reidentification_threshold

    def reset(self):
        """Reset all tracks (e.g., new session)."""
        self._active_tracks.clear()
        self._lost_tracks.clear()
        self._next_id = 1

    def update(
        self,
        detections: list[Detection],
        features: list[np.ndarray] | None = None,
    ) -> list[Track]:
        """
        Update tracks with new detections.

        Args:
            detections: List of detections in current frame
            features: Corresponding CLIP features for each detection

        Returns:
            List of active tracks
        """
        if not detections:
            self._age_tracks()
            return list(self._active_tracks.values())

        det_bboxes = np.array([d.bbox for d in detections])
        det_labels = [d.label for d in detections]
        det_features = features or [None] * len(detections)

        # ─── Stage 1: Match active tracks with IoU ───────────
        matched, unmatched_dets, unmatched_tracks = self._iou_matching(
            self._active_tracks, det_bboxes, det_labels
        )

        # Update matched tracks
        for track_id, det_idx in matched:
            track = self._active_tracks[track_id]
            track.bbox = det_bboxes[det_idx].tolist()
            track.label = det_labels[det_idx]
            track.hits += 1
            track.time_since_update = 0
            track.age += 1
            if det_features[det_idx] is not None:
                track.feature = det_features[det_idx]
            track.history.append(track.bbox)

        # ─── Stage 2: Re-ID unmatched detections with lost tracks ─
        if unmatched_dets and self._lost_tracks and features:
            reid_matched = self._feature_matching(
                self._lost_tracks, det_bboxes, det_features, unmatched_dets
            )

            for track_id, det_idx in reid_matched:
                track = self._lost_tracks.pop(track_id)
                track.bbox = det_bboxes[det_idx].tolist()
                track.label = det_labels[det_idx]
                track.hits += 1
                track.time_since_update = 0
                if det_features[det_idx] is not None:
                    track.feature = det_features[det_idx]
                self._active_tracks[track_id] = track
                unmatched_dets.remove(det_idx)
                logger.debug(f"Re-identified track {track_id} (character: {track.character_id})")

        # ─── Stage 3: Create new tracks for remaining detections ─
        for det_idx in unmatched_dets:
            new_track = Track(
                track_id=self._next_id,
                label=det_labels[det_idx],
                bbox=det_bboxes[det_idx].tolist(),
                feature=det_features[det_idx] if det_features[det_idx] is not None else None,
            )
            new_track.history.append(new_track.bbox)
            self._active_tracks[self._next_id] = new_track
            self._next_id += 1

        # ─── Stage 4: Move unmatched tracks to lost ──────────
        for track_id in unmatched_tracks:
            track = self._active_tracks.pop(track_id)
            self._lost_tracks[track_id] = track

        self._age_tracks()

        return list(self._active_tracks.values())

    def _iou_matching(
        self,
        tracks: dict[int, Track],
        det_bboxes: np.ndarray,
        det_labels: list[str],
    ) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        """IoU-based matching between tracks and detections."""
        if not tracks or len(det_bboxes) == 0:
            return [], list(range(len(det_bboxes))), list(tracks.keys())

        track_ids = list(tracks.keys())
        track_bboxes = np.array([tracks[tid].bbox for tid in track_ids])

        iou_matrix = self._compute_iou_matrix(track_bboxes, det_bboxes)

        # Hungarian assignment
        matched = []
        unmatched_dets = list(range(len(det_bboxes)))
        unmatched_tracks = list(track_ids)

        if iou_matrix.size > 0:
            row_indices, col_indices = linear_sum_assignment(-iou_matrix)

            for r, c in zip(row_indices, col_indices):
                if iou_matrix[r, c] >= self._iou_threshold:
                    matched.append((track_ids[r], c))
                    if c in unmatched_dets:
                        unmatched_dets.remove(c)
                    if track_ids[r] in unmatched_tracks:
                        unmatched_tracks.remove(track_ids[r])

        return matched, unmatched_dets, unmatched_tracks

    def _feature_matching(
        self,
        lost_tracks: dict[int, Track],
        det_bboxes: np.ndarray,
        det_features: list[np.ndarray | None],
        unmatched_det_indices: list[int],
    ) -> list[tuple[int, int]]:
        """CLIP feature-based re-identification for lost tracks."""
        matched = []
        track_ids = [
            tid for tid, t in lost_tracks.items() if t.feature is not None
        ]

        if not track_ids:
            return matched

        track_features = np.array([lost_tracks[tid].feature for tid in track_ids])

        for det_idx in unmatched_det_indices:
            if det_features[det_idx] is None:
                continue

            det_feat = det_features[det_idx].reshape(1, -1)
            similarities = np.dot(track_features, det_feat.T).flatten()
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]

            if best_score >= self._reid_threshold:
                matched.append((track_ids[best_idx], det_idx))
                # Remove matched track from candidates
                track_ids.pop(best_idx)
                track_features = np.delete(track_features, best_idx, axis=0)

                if len(track_ids) == 0:
                    break

        return matched

    def _age_tracks(self):
        """Age all tracks and remove expired ones."""
        for track_id in list(self._active_tracks.keys()):
            self._active_tracks[track_id].time_since_update += 1
            self._active_tracks[track_id].age += 1

        expired = [
            tid for tid, t in self._lost_tracks.items()
            if t.time_since_update > self._max_age
        ]
        for tid in expired:
            del self._lost_tracks[tid]

    @staticmethod
    def _compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
        """Compute IoU between two sets of bounding boxes."""
        x1 = np.maximum(boxes_a[:, 0:1], boxes_b[:, 0:1].T)
        y1 = np.maximum(boxes_a[:, 1:2], boxes_b[:, 1:2].T)
        x2 = np.minimum(boxes_a[:, 2:3], boxes_b[:, 2:3].T)
        y2 = np.minimum(boxes_a[:, 3:4], boxes_b[:, 3:4].T)

        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)

        area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
        area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])

        union = area_a[:, np.newaxis] + area_b[np.newaxis, :] - intersection

        return intersection / (union + 1e-6)


# Singleton
_tracker: MultiObjectTracker | None = None


def get_tracker() -> MultiObjectTracker:
    global _tracker
    if _tracker is None:
        _tracker = MultiObjectTracker()
    return _tracker
