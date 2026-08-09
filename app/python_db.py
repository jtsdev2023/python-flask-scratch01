#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .db import DEFAULT_DATABASE_URL, get_engine, init_app, session_scope
from .models import Base, Dvd


BASE_DIR = Path(__file__).resolve().parent
SEED_PATH = BASE_DIR / "seed.json"


def create_database(app: Flask | None = None) -> None:
    Base.metadata.create_all(bind=get_engine(app))


def query_dvds(
    title_search: str = "%",
    genre: str | None = None,
    active_only: bool = True,
    app: Flask | None = None,
):
    statement = select(Dvd).where(Dvd.title.like(title_search)).order_by(Dvd.title.asc())
    if genre is not None:
        statement = statement.where(Dvd.genre == genre)
    if active_only:
        statement = statement.where(Dvd.is_active.is_(True))

    with session_scope(app) as session:
        return list(session.scalars(statement))


def seed_database(app: Flask | None = None) -> None:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH.resolve()}")

    seed_data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_params = [
        {
            "title": dvd["title"],
            "director": dvd["director"],
            "genre": dvd["genre"],
            "release_year": dvd["release_year"],
            "description": dvd["description"],
            "rental_price_cents": round(dvd["rental_price"] * 100),
            "total_copies": dvd["total_copies"],
            "available_copies": dvd["available_copies"],
            "is_active": bool(dvd["is_active"]),
        }
        for dvd in seed_data
    ]

    if not seed_params:
        return

    statement = sqlite_insert(Dvd).values(seed_params)
    statement = statement.on_conflict_do_nothing(
        index_elements=["title", "director", "release_year"],
    )

    with session_scope(app) as session:
        session.execute(statement)


def ensure_database_ready(app: Flask | None = None) -> None:
    create_database(app)
    with session_scope(app) as session:
        dvd_count = session.scalar(select(Dvd.id).limit(1))
    if dvd_count is None:
        seed_database(app)


if __name__ == "__main__":
    # relative imports require invocation as `python -m app.python_db`
    scratch_app = Flask(__name__)
    scratch_app.config["DATABASE_URL"] = DEFAULT_DATABASE_URL
    init_app(scratch_app)
    create_database(scratch_app)
    seed_database(scratch_app)
    for dvd in query_dvds(app=scratch_app):
        print(dvd.title)
