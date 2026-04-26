from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import Settings, get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine(settings: Settings | None = None) -> Engine:
    active_settings = settings or get_settings()
    return create_engine(
        active_settings.sqlalchemy_database_url,
        connect_args={
            "connect_timeout": active_settings.db_connect_timeout,
            "options": f"-c search_path={active_settings.db_search_path}",
        },
        pool_pre_ping=True,
    )


@contextmanager
def get_session(settings: Settings | None = None) -> Iterator[Session]:
    session_factory = sessionmaker(
        bind=get_engine(settings),
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Iterator[Session]:
    with get_session() as session:
        yield session


def ping_database(settings: Settings | None = None) -> bool:
    with get_session(settings) as session:
        return session.execute(text("SELECT 1")).scalar_one() == 1
