"""Screen capture fallback (Python) and frame processor.

Provides a Python-based screen capture for when the C++ engine
isn't available, and the main frame processing orchestration.
"""

import time
import asyncio
import uuid
import cv2
import numpy as np
import mss
import zmq
import zmq.asyncio
from pathlib import Path
from datetime import datetime
from loguru import logger

from app.core.config import settings
from app.core.database import async_session
from app.models.models import CaptureSession, Character, Scene, CharacterAppearance, DetectedItem
from app.models.schemas import Detection, FrameAnalysis
from app.services.detector import get_detector
from app.services.feature_extractor import get_feature_extractor
from app.services.tracker import get_tracker, Track
from app.services.scene_analyzer import get_scene_analyzer
from app.services.vector_store import get_vector_store


class FrameProcessor:
    """
    Orchestrates the full vision pipeline:
    Screen Capture → Frame Sampling → Detection → Feature Extraction →
    Tracking → Re-identification → Scene Analysis → Storage
    """

    def __init__(self):
        self._running = False
        self._session_id: str | None = None
        self._frame_count = 0
        self._start_time = 0.0
        self._capture: mss.mss | None = None
        self._data_dir = settings.data_dir.resolve()   # always absolute
        self._fps: int = settings.capture_fps
        self._current_scene_id: str | None = None
        self._scene_start_time: float = 0.0
        self._last_keyframe_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict:
        elapsed = time.time() - self._start_time if self._running else 0
        return {
            "session_id": self._session_id,
            "running": self._running,
            "frame_count": self._frame_count,
            "elapsed_seconds": elapsed,
        }

    async def start_capture(
        self,
        session_id: str,
        source: str = "screen",
        fps: int | None = None,
        title: str = "Untitled Session",
    ):
        """Start the capture + processing loop.

        Args:
            session_id: Unique session identifier.
            source: Capture source — "screen", "window", or "zmq" (C++ engine).
            fps: Target frames per second to analyse (overrides config default).
            title: Human-readable session title.
        """
        if self._running:
            logger.warning("Capture already running")
            return

        self._running = True
        self._session_id = session_id
        self._frame_count = 0
        self._start_time = time.time()
        self._fps = fps or settings.capture_fps
        self._last_keyframe_time = 0.0
        self._current_scene_id = None

        # Reset components
        get_tracker().reset()
        get_scene_analyzer().reset()

        logger.info(f"Starting capture session: {session_id} at {self._fps} FPS")

        # Create session data directory
        session_dir = self._data_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "scenes").mkdir(exist_ok=True)
        (session_dir / "characters").mkdir(exist_ok=True)

        # Persist CaptureSession to SQLite
        await self._create_db_session(session_id, title)

        # Start capture loop
        try:
            if source == "zmq":
                await self._zmq_capture_loop(session_dir)
            else:
                await self._capture_loop(session_dir)
        except Exception as e:
            logger.exception(f"Capture loop terminated with error: {e}")
        finally:
            self._running = False
            await self._finalise_db_session(session_id)
            logger.info(f"Capture session ended. Frames processed: {self._frame_count}")

    async def stop_capture(self):
        """Stop the capture loop."""
        self._running = False
        logger.info("Capture stop requested")

    # ── Database helpers ─────────────────────────────────────

    async def _create_db_session(self, session_id: str, title: str):
        """Insert a new CaptureSession row."""
        async with async_session() as db:
            db_session = CaptureSession(
                id=session_id,
                title=title,
                status="capturing",
            )
            db.add(db_session)
            await db.commit()
            logger.info(f"DB session created: {session_id}")

    async def _finalise_db_session(self, session_id: str):
        """Mark the session as done and record end time / frame count."""
        async with async_session() as db:
            from sqlalchemy import select

            result = await db.execute(
                select(CaptureSession).where(CaptureSession.id == session_id)
            )
            row = result.scalar_one_or_none()
            if row:
                row.status = "done"
                row.ended_at = datetime.utcnow()
                row.total_frames = self._frame_count
                await db.commit()

    async def _persist_character(
        self, char_id: str, track: "Track", timestamp: float, session_dir: Path, frame: np.ndarray
    ):
        """Save a Character row + thumbnail to disk & SQLite."""
        # Save thumbnail crop
        x1, y1, x2, y2 = [int(c) for c in track.bbox]
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        thumb_dir = session_dir / "characters"
        thumb_path = thumb_dir / f"{char_id}.jpg"
        if crop.size > 0:
            cv2.imwrite(str(thumb_path), crop)

        rel_thumb = thumb_path.relative_to(self._data_dir.resolve())
        async with async_session() as db:
            character = Character(
                id=char_id,
                name="Unknown",
                chroma_id=char_id,
                thumbnail_path=rel_thumb.as_posix(),
                first_seen_at=datetime.utcnow(),
                metadata_={"session_id": self._session_id, "track_id": track.track_id},
            )
            db.add(character)
            await db.commit()

    async def _persist_scene(self, scene_index: int, timestamp: float, thumb_path: str):
        """Save a Scene row to SQLite."""
        scene_id = str(uuid.uuid4())
        self._current_scene_id = scene_id
        self._scene_start_time = timestamp

        async with async_session() as db:
            scene = Scene(
                id=scene_id,
                session_id=self._session_id or "",
                scene_index=scene_index,
                start_time=timestamp,
                thumbnail_path=thumb_path,
            )
            db.add(scene)
            await db.commit()
        return scene_id

    async def _persist_appearance(
        self, character_id: str, scene_id: str, timestamp: float, confidence: float, bbox: list[float]
    ):
        """Record a CharacterAppearance linking character ↔ scene."""
        async with async_session() as db:
            app = CharacterAppearance(
                id=str(uuid.uuid4()),
                character_id=character_id,
                scene_id=scene_id,
                timestamp=timestamp,
                confidence=confidence,
                bbox=bbox,
            )
            db.add(app)
            await db.commit()

    async def process_frame(self, frame: np.ndarray, timestamp: float) -> FrameAnalysis:
        """
        Process a single frame through the full pipeline.

        Pipeline:
        1. Scene change detection
        2. Object detection (YOLO-World)
        3. Feature extraction (CLIP) for person detections
        4. Multi-object tracking with re-identification
        5. Store to vector database

        Args:
            frame: BGR numpy array
            timestamp: Frame timestamp in seconds

        Returns:
            FrameAnalysis with detections and metadata
        """
        detector = get_detector()
        extractor = get_feature_extractor()
        tracker = get_tracker()
        scene_analyzer = get_scene_analyzer()
        vector_store = get_vector_store()

        # 1. Detect scene change (or force a keyframe on a time interval)
        scene_changed = scene_analyzer.detect_scene_change(frame)
        if not scene_changed and timestamp - self._last_keyframe_time >= settings.keyframe_interval:
            scene_analyzer.force_new_scene()
            scene_changed = True
            logger.debug(f"Force keyframe at t={timestamp:.1f}s (interval={settings.keyframe_interval}s)")

        # 2. Run detection
        detections = detector.detect(frame)

        # 3. Extract CLIP features for person/character detections
        person_detections = [d for d in detections if d.label in ("person", "character", "face")]
        person_bboxes = [d.bbox for d in person_detections]
        features = extractor.batch_extract(frame, person_bboxes) if person_bboxes else []

        # 4. Track objects
        tracks = tracker.update(person_detections, features if features else None)

        # 5. Re-identify and store new characters
        session_dir = self._data_dir / "sessions" / (self._session_id or "unknown")
        for i, track in enumerate(tracks):
            if track.feature is not None and track.hits >= settings.tracker_min_hits:
                matches = vector_store.find_similar_character(track.feature, top_k=1)
                if matches and matches[0]["score"] >= settings.reidentification_threshold:
                    track.character_id = matches[0]["id"]
                elif track.character_id is None:
                    # New character — store embedding + persist to DB
                    char_id = f"char_{track.track_id}_{self._session_id}"
                    vector_store.add_character(
                        character_id=char_id,
                        embedding=track.feature,
                        metadata={
                            "track_id": track.track_id,
                            "label": track.label,
                            "session_id": self._session_id,
                            "first_seen": timestamp,
                        },
                    )
                    track.character_id = char_id
                    await self._persist_character(char_id, track, timestamp, session_dir, frame)

                # Record appearance in current scene
                if track.character_id and self._current_scene_id:
                    await self._persist_appearance(
                        character_id=track.character_id,
                        scene_id=self._current_scene_id,
                        timestamp=timestamp,
                        confidence=person_detections[min(i, len(person_detections) - 1)].confidence
                        if person_detections else 0.0,
                        bbox=track.bbox,
                    )

        # Update detections with track IDs
        for i, det in enumerate(person_detections):
            matching_tracks = [
                t for t in tracks
                if self._bbox_overlap(det.bbox, t.bbox) > 0.5
            ]
            if matching_tracks:
                det.track_id = matching_tracks[0].track_id

        # 6. Store scene data if scene changed → persist to both disk & SQLite
        if scene_changed:
            self._last_keyframe_time = timestamp
            thumbnail = scene_analyzer.extract_scene_thumbnail(frame)
            scene_dir = self._data_dir / "sessions" / (self._session_id or "unknown") / "scenes"
            scene_dir.mkdir(parents=True, exist_ok=True)
            thumb_path = scene_dir / f"scene_{scene_analyzer.scene_count:04d}.jpg"
            cv2.imwrite(str(thumb_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 92])

            # Close previous scene's end_time
            if self._current_scene_id:
                async with async_session() as db:
                    from sqlalchemy import select

                    result = await db.execute(
                        select(Scene).where(Scene.id == self._current_scene_id)
                    )
                    prev = result.scalar_one_or_none()
                    if prev:
                        prev.end_time = timestamp
                        await db.commit()

            # Store path relative to data_dir so it maps to /data/{rel} URL
            rel_thumb = thumb_path.relative_to(self._data_dir.resolve())
            await self._persist_scene(
                scene_index=scene_analyzer.scene_count,
                timestamp=timestamp,
                thumb_path=rel_thumb.as_posix(),
            )

        self._frame_count += 1

        return FrameAnalysis(
            frame_index=self._frame_count,
            timestamp=timestamp,
            detections=detections,
            scene_changed=scene_changed,
        )

    async def _capture_loop(self, session_dir: Path):
        """Main capture loop using mss (Python fallback)."""
        interval = 1.0 / self._fps
        logger.info(f"Python capture loop started — target {self._fps} FPS (interval {interval*1000:.1f} ms)")

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor

            while self._running:
                start = time.time()

                # Grab screenshot
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                # mss returns BGRA, convert to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                timestamp = time.time() - self._start_time

                # Process frame — catch per-frame errors so the loop keeps running
                try:
                    await self.process_frame(frame, timestamp)
                except Exception as frame_err:
                    logger.warning(f"Frame {self._frame_count} processing error (skipping): {frame_err}")

                # Maintain target FPS — only sleep if we have time left
                elapsed = time.time() - start
                sleep_time = interval - elapsed
                if sleep_time > 0.001:
                    await asyncio.sleep(sleep_time)
                else:
                    # Yield control to event loop without sleeping (already behind schedule)
                    await asyncio.sleep(0)

    async def _zmq_capture_loop(self, session_dir: Path):
        """Receive frames from the C++ capture engine via ZeroMQ."""
        ctx = zmq.asyncio.Context()
        receiver = ctx.socket(zmq.PULL)
        receiver.bind(f"tcp://*:{settings.zmq_capture_port}")
        logger.info(f"ZMQ receiver listening on port {settings.zmq_capture_port}")

        # Optional: sender for results back to C++ engine
        sender = ctx.socket(zmq.PUSH)
        sender.bind(f"tcp://*:{settings.zmq_result_port}")

        try:
            while self._running:
                try:
                    msg = await asyncio.wait_for(receiver.recv_multipart(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue

                # Protocol: [timestamp_bytes, frame_bytes]
                if len(msg) < 2:
                    continue

                ts = float(msg[0].decode())
                frame_data = msg[1]
                frame = cv2.imdecode(
                    np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if frame is None:
                    logger.warning("ZMQ: failed to decode frame")
                    continue

                analysis = await self.process_frame(frame, ts)

                # Send result summary back to C++ engine
                try:
                    sender.send_json(
                        {
                            "frame_index": analysis.frame_index,
                            "detections": len(analysis.detections),
                            "scene_changed": analysis.scene_changed,
                        },
                        flags=zmq.NOBLOCK,
                    )
                except zmq.ZMQError:
                    pass
        finally:
            receiver.close()
            sender.close()
            ctx.term()

    @staticmethod
    def _bbox_overlap(box_a: list[float], box_b: list[float]) -> float:
        """Compute IoU between two bboxes."""
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union = area_a + area_b - intersection

        return intersection / (union + 1e-6)


# Singleton
_processor: FrameProcessor | None = None


def get_frame_processor() -> FrameProcessor:
    global _processor
    if _processor is None:
        _processor = FrameProcessor()
    return _processor
