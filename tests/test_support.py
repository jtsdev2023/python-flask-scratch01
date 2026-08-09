from __future__ import annotations

import copy
import json
from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent
USER_PAYLOAD_PATH = BASE_DIR / "smoke-test-user-payload.json"


def generate_unique_email(first_name: str, last_name: str) -> str:
    unique_str = uuid4().hex[:6]
    return f"{first_name}.{last_name}_{unique_str}@example.com"


def load_user_payloads() -> list[dict]:
    payloads = json.loads(USER_PAYLOAD_PATH.read_text(encoding="utf-8"))
    for user in payloads:
        user["email"] = generate_unique_email(user["first_name"], user["last_name"])
    return payloads


def build_user_payload(index: int = 0) -> dict:
    return copy.deepcopy(load_user_payloads()[index])
