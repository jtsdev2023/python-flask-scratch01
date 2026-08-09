from __future__ import annotations

import sys
import time
from pathlib import Path
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from werkzeug.serving import make_server

from app import create_app
from app.db import get_engine

playwright_sync_api = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync_api.sync_playwright
PlaywrightError = playwright_sync_api.Error


class LiveServer:
    def __init__(self, app):
        self._server = make_server("127.0.0.1", 0, app)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self.base_url = f"http://127.0.0.1:{self._server.server_port}"

    def start(self):
        self._thread.start()
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with urlopen(f"{self.base_url}/api/health", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except URLError:
                time.sleep(0.05)
        raise RuntimeError("Live test server did not become ready in time.")

    def stop(self):
        self._server.shutdown()
        self._thread.join(timeout=5)


@pytest.fixture
def flask_app(tmp_path):
    # Each test gets a fresh seeded SQLite database via the app factory config.
    temp_db_path = tmp_path / "playwright-tests.db"
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite+pysqlite:///{temp_db_path}",
        }
    )
    yield app
    get_engine(app).dispose()


@pytest.fixture
def live_server(flask_app):
    server = LiveServer(flask_app)
    server.start()
    yield server.base_url
    server.stop()


@pytest.fixture
def browser():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            message = str(error)
            if (
                "error while loading shared libraries" in message
                or "Host system is missing dependencies" in message
                or "Executable doesn't exist" in message
            ):
                pytest.skip(
                    "Playwright browser launch skipped because Chromium dependencies are missing. "
                    f"Details: {message}"
                )
            raise
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(base_url="http://127.0.0.1")
    page = context.new_page()
    yield page
    context.close()
