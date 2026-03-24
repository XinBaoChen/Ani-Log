"""Hybrid detector for anime character faces.

Detection priority:
1) anime-face-detector (best for anime face boxes + landmarks)
2) InsightFace detector (RetinaFace-like, broad fallback)
3) YOLO-World fallback (generic open-vocab)
"""

import numpy as np
from loguru import logger

from app.core.config import settings
from app.models.schemas import Detection

# Lazy optional imports
_create_anime_detector = None
_FaceAnalysis = None
_YOLOWorld = None

_anime_detector_available: bool | None = None
_insightface_available: bool | None = None
_yolo_available: bool | None = None


# Default anime-relevant classes for open-vocabulary fallback detection
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


def _get_anime_detector_factory():
    global _create_anime_detector, _anime_detector_available
    if _anime_detector_available is False:
        return None
    if _create_anime_detector is None:
        try:
            from anime_face_detector import create_detector as _c  # noqa: PLC0415  # type: ignore[import-not-found]
            _create_anime_detector = _c
            _anime_detector_available = True
        except ImportError:
            logger.warning(
                "anime-face-detector not installed. "
                "Install optional stack to improve anime detection."
            )
            _anime_detector_available = False
            return None
    return _create_anime_detector


def _get_insightface_face_analysis_cls():
    global _FaceAnalysis, _insightface_available
    if _insightface_available is False:
        return None
    if _FaceAnalysis is None:
        try:
            from insightface.app import FaceAnalysis as _fa  # noqa: PLC0415
            _FaceAnalysis = _fa
            _insightface_available = True
        except ImportError:
            logger.warning("insightface not installed — InsightFace detector fallback disabled")
            _insightface_available = False
            return None
    return _FaceAnalysis


def _get_yolo_world_cls():
    global _YOLOWorld, _yolo_available
    if _yolo_available is False:
        return None
    if _YOLOWorld is None:
        try:
            from ultralytics import YOLOWorld as _Y  # noqa: PLC0415  # type: ignore[import-not-found]
            _YOLOWorld = _Y
            _yolo_available = True
        except ImportError:
            logger.warning(
                "ultralytics not installed — YOLO fallback disabled. "
                "Run: pip install ultralytics"
            )
            _yolo_available = False
            return None
    return _YOLOWorld


class Detector:
    """Hybrid anime-first detector."""

    def __init__(self):
        self._anime_detector = None
        self._face_app = None
        self._yolo_model = None
        self._classes = ANIME_CLASSES.copy()

    def _load_anime_detector(self):
        if self._anime_detector is not None:
            return self._anime_detector
        factory = _get_anime_detector_factory()
        if factory is None:
            return None
        try:
            # 'yolov3' is the documented pretrained detector in this package.
            self._anime_detector = factory("yolov3")
            logger.info("anime-face-detector loaded")
        except Exception as exc:
            logger.warning(f"anime-face-detector failed to load: {exc}")
            self._anime_detector = None
        return self._anime_detector

    def _load_face_app(self):
        if self._face_app is not None:
            return self._face_app
        FaceAnalysis = _get_insightface_face_analysis_cls()
        if FaceAnalysis is None:
            return None
        try:
            self._face_app = FaceAnalysis(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            ctx_id = 0 if settings.clip_device.startswith("cuda") else -1
            self._face_app.prepare(ctx_id=ctx_id, det_size=(640, 640))
            logger.info("InsightFace detector loaded")
        except Exception as exc:
            logger.warning(f"InsightFace detector failed to load: {exc}")
            self._face_app = None
        return self._face_app

    def _load_yolo(self):
        if self._yolo_model is not None:
            return self._yolo_model
        YOLOWorld = _get_yolo_world_cls()
        if YOLOWorld is None:
            return None
        try:
            self._yolo_model = YOLOWorld(settings.yolo_model)
            self._yolo_model.set_classes(self._classes)
            logger.info(f"YOLO-World loaded with {len(self._classes)} classes")
        except Exception as exc:
            logger.warning(f"YOLO-World failed to load ({exc})")
            self._yolo_model = None
        return self._yolo_model

    def set_classes(self, classes: list[str]):
        self._classes = classes
        if self._yolo_model is not None:
            self._yolo_model.set_classes(classes)
        logger.info(f"Detection classes updated: {len(classes)} classes")

    def _detect_with_anime_model(self, frame: np.ndarray) -> list[Detection]:
        detector = self._load_anime_detector()
        if detector is None:
            return []
        try:
            preds = detector(frame)
        except Exception as exc:
            logger.warning(f"anime-face-detector inference failed: {exc}")
            return []

        out: list[Detection] = []
        for p in preds:
            bbox_raw = p.get("bbox")
            if bbox_raw is None or len(bbox_raw) < 4:
                continue
            arr = np.asarray(bbox_raw, dtype=np.float32).tolist()
            x1, y1, x2, y2 = [float(v) for v in arr[:4]]
            score = float(arr[4]) if len(arr) >= 5 else 0.9
            out.append(
                Detection(
                    bbox=[x1, y1, x2, y2],
                    label="face",
                    confidence=score,
                )
            )
        return out

    def _detect_with_insightface(self, frame: np.ndarray) -> list[Detection]:
        app = self._load_face_app()
        if app is None:
            return []
        try:
            faces = app.get(frame)
        except Exception as exc:
            logger.warning(f"InsightFace detection inference failed: {exc}")
            return []

        out: list[Detection] = []
        for face in faces:
            if not hasattr(face, "bbox"):
                continue
            x1, y1, x2, y2 = [float(v) for v in face.bbox.tolist()]
            score = float(getattr(face, "det_score", 0.9))
            out.append(
                Detection(
                    bbox=[x1, y1, x2, y2],
                    label="face",
                    confidence=score,
                )
            )
        return out

    def _detect_with_yolo(self, frame: np.ndarray, confidence: float | None = None) -> list[Detection]:
        conf = confidence or settings.yolo_confidence
        model = self._load_yolo()
        if model is None:
            return []

        results = model.predict(
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
                detections.append(Detection(bbox=bbox, label=label, confidence=conf_score))
        return detections

    def detect(self, frame: np.ndarray, confidence: float | None = None) -> list[Detection]:
        # Anime-first detector path
        detections = self._detect_with_anime_model(frame)
        if detections:
            return detections

        # InsightFace detector fallback
        detections = self._detect_with_insightface(frame)
        if detections:
            return detections

        # Generic fallback
        return self._detect_with_yolo(frame, confidence)

    def detect_batch(self, frames: list[np.ndarray], confidence: float | None = None) -> list[list[Detection]]:
        return [self.detect(frame, confidence) for frame in frames]


# Singleton
_detector: Detector | None = None


def get_detector() -> Detector:
    global _detector
    if _detector is None:
        _detector = Detector()
    return _detector
