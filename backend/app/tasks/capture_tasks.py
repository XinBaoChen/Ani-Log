"""Background tasks for batch video processing."""

import cv2
import numpy as np
from pathlib import Path
from loguru import logger

from app.services.frame_processor import get_frame_processor
from app.services.detector import get_detector
from app.services.feature_extractor import get_feature_extractor
from app.services.scene_analyzer import get_scene_analyzer
from app.core.config import settings


async def process_video_file(
    session_id: str,
    video_path: str,
    fps: int | None = None,
):
    """
    Process a video file through the full pipeline.

    Alternative to live capture — processes a pre-recorded video file.

    Args:
        session_id: Capture session ID
        video_path: Path to video file
        fps: Sample rate (frames per second to analyze)
    """
    sample_fps = fps or settings.capture_fps
    processor = get_frame_processor()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, int(video_fps / sample_fps))

    logger.info(
        f"Processing video: {video_path} "
        f"({total_frames} frames @ {video_fps:.1f} FPS, "
        f"sampling every {frame_interval} frames)"
    )

    frame_count = 0
    processed = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            if frame_count % frame_interval != 0:
                continue

            timestamp = frame_count / video_fps

            await processor.process_frame(frame, timestamp)
            processed += 1

            if processed % 50 == 0:
                logger.info(f"Processed {processed} frames ({frame_count}/{total_frames})")

    finally:
        cap.release()
        logger.info(f"Video processing complete: {processed} frames processed")
