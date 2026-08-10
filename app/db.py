from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flask import Flask, current_app
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DATABASE_URL = f"sqlite+pysqlite:///{INSTANCE_DIR / 'dvdrental_test.db'}"
DATABASE_EXTENSION_KEY = "database"


# creates an sqlalchemy engine, enabling foreign keys for sqlite connections
def _build_engine(database_url: str) -> Engine:
    engine_kwargs = {}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)

    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        # enables foreign key enforcement on each new sqlite connection
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# attaches an db engine and session factory to the flask app
def init_app(app: Flask) -> None:
    database_url = app.config.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = _build_engine(database_url)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app.extensions[DATABASE_EXTENSION_KEY] = {
        "engine": engine,
        "session_factory": session_factory,
    }


# returns the engine attached to the input or current app
def get_engine(app: Flask | None = None) -> Engine:
    resolved_app = app or current_app
    return resolved_app.extensions[DATABASE_EXTENSION_KEY]["engine"]


# returns the session factory attached to the input or current app
def get_session_factory(app: Flask | None = None) -> sessionmaker[Session]:
    resolved_app = app or current_app
    return resolved_app.extensions[DATABASE_EXTENSION_KEY]["session_factory"]


@contextmanager
# yields a session, committing on success and rolling back on error
def session_scope(app: Flask | None = None) -> Iterator[Session]:
    session = get_session_factory(app)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
