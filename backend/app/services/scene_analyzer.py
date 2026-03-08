"""Scene analyzer — detects scene cuts and analyzes scene content.

Uses frame difference metrics and CLIP embeddings to detect
scene transitions and characterize each scene.
"""

import cv2
import numpy as np
from loguru import logger

from app.core.config import settings


class SceneAnalyzer:
    """Detects scene changes and characterizes scenes in anime footage."""

    def __init__(self):
        self._prev_frame: np.ndarray | None = None
        self._prev_hist: np.ndarray | None = None
        self._scene_count = 0
        self._threshold = settings.scene_change_threshold

    def reset(self):
        """Reset state for a new session."""
        self._prev_frame = None
        self._prev_hist = None
        self._scene_count = 0

    def detect_scene_change(self, frame: np.ndarray) -> bool:
        """
        Detect if the current frame represents a scene change.

        Uses a combination of:
        1. Color histogram comparison
        2. Structural similarity

        Args:
            frame: BGR numpy array (H, W, 3)

        Returns:
            True if a scene change is detected
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()

        if self._prev_hist is None:
            self._prev_hist = hist
            self._prev_frame = gray
            self._scene_count += 1
            return True  # First frame is always a new scene

        # Color histogram correlation
        hist_score = cv2.compareHist(
            self._prev_hist, hist, cv2.HISTCMP_CORREL
        )

        # Structural difference
        if self._prev_frame is not None:
            # Resize for fast comparison
            small_prev = cv2.resize(self._prev_frame, (160, 90))
            small_curr = cv2.resize(gray, (160, 90))
            diff = cv2.absdiff(small_prev, small_curr)
            structural_score = 1.0 - (np.mean(diff) / 255.0)
        else:
            structural_score = 1.0

        # Combined score (lower = more different)
        combined_score = 0.6 * hist_score + 0.4 * structural_score

        self._prev_hist = hist
        self._prev_frame = gray

        is_scene_change = combined_score < (1.0 - self._threshold)

        if is_scene_change:
            self._scene_count += 1
            logger.debug(
                f"Scene change detected (#{self._scene_count}): "
                f"hist={hist_score:.3f}, struct={structural_score:.3f}, "
                f"combined={combined_score:.3f}"
            )

        return is_scene_change

    def force_new_scene(self) -> None:
        """Manually increment the scene counter (used for time-based forced keyframes)."""
        self._scene_count += 1
        logger.info(f"Forced keyframe (#{self._scene_count})")

    @property
    def scene_count(self) -> int:
        return self._scene_count

    @staticmethod
    def extract_scene_thumbnail(frame: np.ndarray, max_size: int = 1280) -> np.ndarray:
        """Create a thumbnail from a scene's representative frame."""
        h, w = frame.shape[:2]
        scale = min(max_size / w, max_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    @staticmethod
    def compute_frame_embedding(frame: np.ndarray) -> np.ndarray:
        """
        Compute a simple perceptual hash embedding for fast comparison.
        For semantic embeddings, use CLIP via FeatureExtractor.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (64, 64))
        dct = cv2.dct(np.float32(resized))
        dct_low = dct[:16, :16]
        return dct_low.flatten()


# Singleton
_analyzer: SceneAnalyzer | None = None


def get_scene_analyzer() -> SceneAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SceneAnalyzer()
    return _analyzer
