"""SQLAlchemy async database & ChromaDB vector store connections."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from loguru import logger

from app.core.config import settings


# ─── SQLAlchemy (Metadata Store) ─────────────────────────────
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency: yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_capture_session_columns(conn)
    logger.info("SQLite tables created")


async def _ensure_capture_session_columns(conn) -> None:
    """Add lightweight columns used by newer session responses."""
    if not str(engine.url).startswith("sqlite"):
        return

    result = await conn.execute(text("PRAGMA table_info(capture_sessions)"))
    existing = {row[1] for row in result.fetchall()}

    wanted_columns = {
        "video_url": "TEXT",
        "capture_error": "TEXT",
    }

    for column_name, column_type in wanted_columns.items():
        if column_name in existing:
            continue
        await conn.execute(
            text(f"ALTER TABLE capture_sessions ADD COLUMN {column_name} {column_type}")
        )
        logger.info(f"Added capture_sessions.{column_name} column")


# ─── ChromaDB (Vector Store) ─────────────────────────────────
# chromadb imported lazily to avoid Pydantic V1 issues at module load time
_chroma_client = None


def get_chroma_client():
    """Singleton ChromaDB HTTP client (lazy import)."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb  # noqa: PLC0415
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
    return _chroma_client


def get_collection(name: str):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
