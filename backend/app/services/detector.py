"""YOLO-World open-vocabulary object detector.

Detects characters, items, locations, and objects in anime frames
using YOLO-World's zero-shot detection capabilities.
"""

import numpy as np
from loguru import logger

from app.core.config import settings
from app.models.schemas import Detection

# Heavy ML import — loaded lazily on first use
_YOLOWorld = None


_yolo_available: bool | None = None  # None = not yet checked


def _get_yolo_world_cls():
    global _YOLOWorld, _yolo_available
    if _yolo_available is False:
        return None
    if _YOLOWorld is None:
        try:
            from ultralytics import YOLOWorld as _Y  # noqa: PLC0415
            _YOLOWorld = _Y
            _yolo_available = True
        except ImportError:
            logger.warning(
                "ultralytics not installed — character detection disabled. "
                "Run: pip install ultralytics"
            )
            _yolo_available = False
            return None
    return _YOLOWorld


# Default anime-relevant classes for open-vocabulary detection
ANIME_CLASSES = [
    "person", "character", "face", "hair",
    "sword", "weapon", "gun", "shield", "staff", "bow",
    "building", "castle", "house", "temple", "school",
    "tree", "mountain", "ocean", "sky", "forest",
    "car", "vehicle", "ship", "mech", "robot",
    "book", "scroll", "potion", "ring", "necklace",
    "monster", "dragon", "creature", "animal",
    "food", "drink",
]


class Detector:
    """YOLO-World open-vocabulary detector for anime frames."""

    def __init__(self):
        self._model = None
        self._classes = ANIME_CLASSES.copy()

    @property
    def model(self):
        if self._model is None:
            YOLOWorld = _get_yolo_world_cls()
            if YOLOWorld is None:
                return None  # ultralytics not installed
            logger.info(f"Loading YOLO-World model: {settings.yolo_model}")
            try:
                self._model = YOLOWorld(settings.yolo_model)
                self._model.set_classes(self._classes)
                logger.info(f"YOLO-World loaded with {len(self._classes)} classes")
            except Exception as exc:
                logger.warning(f"YOLO-World failed to load ({exc}) — detection disabled")
                return None
        return self._model

    def set_classes(self, classes: list[str]):
        """Update the detection vocabulary."""
        self._classes = classes
        if self._model is not None:
            self._model.set_classes(classes)
        logger.info(f"Detection classes updated: {len(classes)} classes")

    def detect(self, frame: np.ndarray, confidence: float | None = None) -> list[Detection]:
        """
        Run detection on a single frame.

        Args:
            frame: BGR numpy array (H, W, 3)
            confidence: Override confidence threshold

        Returns:
            List of Detection objects
        """
        conf = confidence or settings.yolo_confidence

        if self.model is None:
            return []  # package not installed — skip silently

        results = self.model.predict(
            source=frame,
            conf=conf,
            device=settings.yolo_device,
            verbose=False,
        )

        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy().tolist()
                cls_id = int(boxes.cls[i].cpu().numpy())
                conf_score = float(boxes.conf[i].cpu().numpy())
                label = self._classes[cls_id] if cls_id < len(self._classes) else "unknown"

                detections.append(Detection(
                    bbox=bbox,
                    label=label,
                    confidence=conf_score,
                ))

        return detections

    def detect_batch(self, frames: list[np.ndarray], confidence: float | None = None) -> list[list[Detection]]:
        """Run detection on a batch of frames."""
        return [self.detect(frame, confidence) for frame in frames]


# Singleton
_detector: Detector | None = None


def get_detector() -> Detector:
    global _detector
    if _detector is None:
        _detector = Detector()
    return _detector
