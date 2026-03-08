"""CLIP-based feature extraction for character re-identification.

Extracts semantic embeddings from cropped character regions
to enable re-identification across scene cuts.
"""

import numpy as np
from loguru import logger

from app.core.config import settings

# Heavy ML imports — loaded lazily on first use
_torch = None
_open_clip = None
_Image = None


_torch_available: bool | None = None
_clip_available: bool | None = None


def _get_torch():
    global _torch, _torch_available
    if _torch_available is False:
        return None
    if _torch is None:
        try:
            import torch as _t  # noqa: PLC0415
            _torch = _t
            _torch_available = True
        except ImportError:
            logger.warning("torch not installed — CLIP feature extraction disabled. Run: pip install torch")
            _torch_available = False
            return None
    return _torch


def _get_open_clip():
    global _open_clip, _clip_available
    if _clip_available is False:
        return None
    if _open_clip is None:
        try:
            import open_clip as _oc  # noqa: PLC0415
            _open_clip = _oc
            _clip_available = True
        except ImportError:
            logger.warning("open_clip not installed — CLIP feature extraction disabled. Run: pip install open-clip-torch")
            _clip_available = False
            return None
    return _open_clip


def _get_pil_image():
    global _Image
    if _Image is None:
        try:
            from PIL import Image as _I  # noqa: PLC0415
            _Image = _I
        except ImportError:
            logger.warning("Pillow not installed. Run: pip install Pillow")
            return None
    return _Image


class FeatureExtractor:
    """CLIP feature extractor for character re-identification."""

    def __init__(self):
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._device = settings.clip_device

    def _load_model(self):
        if self._model is None:
            open_clip = _get_open_clip()
            if open_clip is None:
                return  # package not installed — stay as None
            try:
                logger.info(f"Loading CLIP model: {settings.clip_model}")
                self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                    settings.clip_model,
                    pretrained=settings.clip_pretrained,
                    device=self._device,
                )
                self._tokenizer = open_clip.get_tokenizer(settings.clip_model)
                self._model.eval()
                logger.info("CLIP model loaded successfully")
            except Exception as exc:
                logger.warning(f"CLIP model failed to load ({exc}) — feature extraction disabled")

    @property
    def model(self):
        self._load_model()
        return self._model

    @property
    def preprocess(self):
        self._load_model()
        return self._preprocess

    @property
    def tokenizer(self):
        self._load_model()
        return self._tokenizer

    def extract_image_features(self, image) -> np.ndarray:
        """
        Extract CLIP embedding from a PIL image.

        Args:
            image: PIL Image (e.g., cropped character region)

        Returns:
            Normalized feature vector (768-d for ViT-L/14)
        """
        torch = _get_torch()
        if torch is None or self.model is None:
            return np.zeros(768, dtype=np.float32)
        img_tensor = self.preprocess(image).unsqueeze(0).to(self._device)

        with torch.no_grad(), torch.cuda.amp.autocast():
            features = self.model.encode_image(img_tensor)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten()

    def extract_from_frame(self, frame: np.ndarray, bbox: list[float]) -> np.ndarray:
        """
        Extract features from a bounding box region of a frame.

        Args:
            frame: BGR numpy array (H, W, 3)
            bbox: [x1, y1, x2, y2]

        Returns:
            Normalized feature vector
        """
        x1, y1, x2, y2 = [int(c) for c in bbox]

        # Ensure valid crop
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 - x1 < 10 or y2 - y1 < 10:
            return np.zeros(768, dtype=np.float32)

        crop = frame[y1:y2, x1:x2]
        # BGR to RGB
        crop_rgb = crop[:, :, ::-1]
        Image = _get_pil_image()
        if Image is None:
            return np.zeros(768, dtype=np.float32)
        image = Image.fromarray(crop_rgb)

        return self.extract_image_features(image)

    def extract_text_features(self, text: str) -> np.ndarray:
        """
        Extract CLIP embedding from a text query.

        Args:
            text: Description string (e.g., "blue-haired anime girl with sword")

        Returns:
            Normalized feature vector
        """
        tokens = self.tokenizer([text]).to(self._device)
        torch = _get_torch()

        with torch.no_grad(), torch.cuda.amp.autocast():
            features = self.model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten()

    def compute_similarity(self, feat_a: np.ndarray, feat_b: np.ndarray) -> float:
        """Cosine similarity between two feature vectors."""
        return float(np.dot(feat_a, feat_b))

    def batch_extract(self, frame: np.ndarray, bboxes: list[list[float]]) -> list[np.ndarray]:
        """Extract features from multiple bounding boxes in a single frame."""
        if self.model is None:
            return []
        return [self.extract_from_frame(frame, bbox) for bbox in bboxes]


# Singleton
_extractor: FeatureExtractor | None = None


def get_feature_extractor() -> FeatureExtractor:
    global _extractor
    if _extractor is None:
        _extractor = FeatureExtractor()
    return _extractor
