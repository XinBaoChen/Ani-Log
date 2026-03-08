"""API route modules — each exposes an APIRouter instance."""

from app.api.routes import capture, characters, scenes, sessions, search, summary

__all__ = ["capture", "characters", "scenes", "sessions", "search", "summary"]
