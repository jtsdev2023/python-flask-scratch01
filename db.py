from contextlib import contextmanager
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dvdrental_test.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(query, params=None):
    with get_connection() as connection:
        cursor = connection.execute(query, params or {})
        return cursor.fetchall()


def fetch_one(query, params=None):
    with get_connection() as connection:
        cursor = connection.execute(query, params or {})
        return cursor.fetchone()


def execute(query, params=None):
    with get_connection() as connection:
        cursor = connection.execute(query, params or {})
        return cursor.lastrowid, cursor.rowcount