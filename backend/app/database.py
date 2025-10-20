from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).resolve().parent.parent / "minutes.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

environment_engine_kwargs = {
    "connect_args": {"check_same_thread": False},
    "future": True,
}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **environment_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


@contextmanager
def session_scope() -> Iterator[sessionmaker]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    from . import models  # noqa: F401

    models.Base.metadata.create_all(bind=engine)
