#!/usr/bin/env python3

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dvdrental_test.db"
SCHEMA_PATH = BASE_DIR / "schema_test.sql"
QUERY_PATH = BASE_DIR / "query_dvds.sql"
SEED_PATH = BASE_DIR / "seed.json"


def create_database():
    if DB_PATH.exists():
        print(f"Database already exists, skipping creation: {DB_PATH.resolve()}")
        return

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file is not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = None

    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.executescript(schema_sql)
        connection.commit()
        print(f"Database created successfully: {DB_PATH.resolve()}")
    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise RuntimeError(f"SQLite error: {error}") from error
    finally:
        if connection is not None:
            connection.close()


def query_dvds(title_search="%", genre=None, active_only=True):
    if not QUERY_PATH.exists():
        raise FileNotFoundError(f"Query file is not found: {QUERY_PATH}")

    query_sql = QUERY_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as connection:
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
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}")

    seed_data = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        for dvd in seed_data:
            cursor.execute(
                seed_db.sql,
                {
                    "title": dvd["title"],
                    "director": dvd["director"],
                    "genre": dvd["genre"],
                    "release_year": dvd["release_year"],
                    "rental_price": dvd["rental_price"],

                    # These fields are not currently in seed.json,
                    # so this function provides default inventory values.
                    "total_copies": dvd.get("total_copies", 0),
                    "available_copies": dvd.get("available_copies", 0),
                    "is_active": dvd.get("is_active", False),
                },
            )

            connection.commit()
            print(f"Database seeded successfully from: {SEED_PATH.resolve()}")

    except sqlite3.IntegrityError as error:
        if connection is not None:
            connection.rollback()
        raise RuntimeError(
            f"Database seed failed. A record primary key may already exist: {error}") from error

    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise RuntimeError(f"SQLite error while seeding database: {error}") from error

    finally:
        if connection is not None:
            connection.close()




if __name__ == "__main__":
    create_database()
    seed_database()
    rows = query_dvds()
    for row in rows:
        print(dict(row))
