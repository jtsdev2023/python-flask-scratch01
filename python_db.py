#!/usr/bin/env python3

import json
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dvdrental_test.db"
SCHEMA_PATH = BASE_DIR / "schema_test.sql"
QUERY_PATH = BASE_DIR / "query_dvds.sql"
SEED_PATH = BASE_DIR / "seed.json"
SEED_SQL_PATH = BASE_DIR / "seed_db.sql"


def create_database():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH.resolve()}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            connection.executescript(schema_sql)
            connection.commit()
        print(f"Database created successfully: {DB_PATH.resolve()}")
    except sqlite3.Error as error:
        raise RuntimeError(f"SQLite error: {error}") from error


def query_dvds(title_search="%", genre=None, active_only=True):
    if not QUERY_PATH.exists():
        raise FileNotFoundError(f"Query file not found: {QUERY_PATH.resolve()}")

    query_sql = QUERY_PATH.read_text(encoding="utf-8")

    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(
            query_sql,
            {
                "title_search": title_search,
                "genre": genre,
                "active_only": active_only,
            },
        )
        return cursor.fetchall()


def seed_database():
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH.resolve()}")
    if not SEED_SQL_PATH.exists():
        raise FileNotFoundError(f"Seed SQL file not found: {SEED_SQL_PATH.resolve()}")

    seed_data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_sql = SEED_SQL_PATH.read_text(encoding="utf-8")
    seed_params = [
        {
            "title": dvd["title"],
            "director": dvd["director"],
            "genre": dvd["genre"],
            "release_year": dvd["release_year"],
            "description": dvd["description"],
            "rental_price": dvd["rental_price"],
            "total_copies": dvd["total_copies"],
            "available_copies": dvd["available_copies"],
            "is_active": dvd["is_active"],
        }
        for dvd in seed_data
    ]

    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            cursor = connection.cursor()
            cursor.executemany(seed_sql, seed_params)
            inserted = cursor.rowcount
            connection.commit()
        print(
            f"Seed process completed from: {SEED_PATH.resolve()} "
            f"({inserted} rows inserted)"
        )
    except sqlite3.IntegrityError as error:
        raise RuntimeError(f"Database seed failed: {error}") from error
    except sqlite3.Error as error:
        raise RuntimeError(f"SQLite error while seeding database: {error}") from error


if __name__ == "__main__":
    create_database()
    seed_database()
    rows = query_dvds()
    for row in rows:
        print(dict(row))
