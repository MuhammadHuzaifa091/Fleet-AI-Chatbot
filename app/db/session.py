from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from loguru import logger
from app.db.base_class import Base

_mysql_engine = None
_mysql_session = None
_sqlite_engine = None
_sqlite_session = None

SessionLocal = None

async def _get_sqlite_session():
    global _sqlite_engine, _sqlite_session
    if _sqlite_engine is None:
        _sqlite_engine = create_async_engine("sqlite+aiosqlite:///./planner.db", echo=False)
        async with _sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _sqlite_session = async_sessionmaker(
            autocommit=False, autoflush=False,
            bind=_sqlite_engine, class_=AsyncSession,
            expire_on_commit=False
        )
    session = _sqlite_session()
    try:
        yield session
    finally:
        await session.close()

async def _check_mysql():
    global _mysql_engine, _mysql_session
    if _mysql_engine is None:
        try:
            _mysql_engine = create_async_engine(
                settings.ASYNC_DATABASE_URL,
                echo=False, pool_size=5, max_overflow=10
            )
            _mysql_session = async_sessionmaker(
                autocommit=False, autoflush=False,
                bind=_mysql_engine, class_=AsyncSession,
                expire_on_commit=False
            )
        except Exception as e:
            logger.warning(f"MySQL engine creation failed: {e}")
            _mysql_engine = None
    if _mysql_engine:
        try:
            async with _mysql_session() as session:
                await session.execute(text("SELECT 1"))
            # Try to create tables; if DDL fails, fall back to SQLite
            async with _mysql_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return True
        except Exception as e:
            logger.warning(f"MySQL unreachable or table creation failed: {e}")
            _mysql_engine = None
    return False


async def get_db():
    # Always use SQLite for planner data to avoid FK/DDL issues with Traccar MySQL
    async for s in _get_sqlite_session():
        yield s
