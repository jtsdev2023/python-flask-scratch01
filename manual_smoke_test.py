#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import db
import python_db


BASE_DIR = Path(__file__).resolve().parent
user_payload_json = BASE_DIR / "smoke-test-user-payload.json"



def expect_status(response, expected_status: int, label: str):
    if response.status_code != expected_status:
        raise AssertionError(
            f"{label} returned {response.status_code}, expected {expected_status}: {response.get_json()}"
        )


def main() -> int:
    with TemporaryDirectory(prefix="scratch01-manualtest-") as tmpdir:
        temp_db_path = Path(tmpdir) / "manual_smoke_test.db"

        # Point the app and seed helpers at an isolated SQLite database.
        db.DB_PATH = temp_db_path
        python_db.DB_PATH = temp_db_path

        python_db.create_database()
        python_db.seed_database()

        from app import create_app

        client = create_app().test_client()

        # unique_email = f"manual.test+{uuid4().hex[:8]}@example.com"
        # user_payload = {
        #     "email": unique_email,
        #     "password": "StrongPass123!",
        #     "first_name": "Sheldon",
        #     "last_name": "Cooper",
        #     "phone_number": "5551234567",
        #     "billing_address_line1": "2311 North Los Robles Avenue",
        #     "billing_address_line2": "Apartment 4A",
        #     "billing_city": "Pasadena",
        #     "billing_state": "CA",
        #     "billing_postal_code": "91104",
        #     "payment_method": {
        #         "card_number": "0123456789012345",
        #         "card_brand": "Visa",
        #         "card_exp_month": 12,
        #         "card_exp_year": 2030,
        #     },
        # }

        unique_email = f"manual.test.{uuid4().hex[:8]}@example.com"
        # read and load user payload from file
        user_payload = json.loads(user_payload_json.read_text(encoding="utf-8"))
        user_payload['email'] = unique_email

        health = client.get("/api/health")
        expect_status(health, 200, "GET /api/health")
        print("PASS GET /api/health", health.get_json())

        dvds = client.get("/api/dvds")
        expect_status(dvds, 200, "GET /api/dvds")
        dvd_items = dvds.get_json()["items"]
        if not dvd_items:
            raise AssertionError("GET /api/dvds returned no items.")
        print(f"PASS GET /api/dvds returned {len(dvd_items)} items")

        register = client.post("/api/register", json=user_payload)
        expect_status(register, 201, "POST /api/register")
        register_json = register.get_json()
        cart_id = register_json["cart"]["id"]
        payment_method_id = register_json["payment_method"]["id"]
        print(
            "PASS POST /api/register",
            {
                "user_id": register_json["user"]["id"],
                "cart_id": cart_id,
                "payment_method_id": payment_method_id,
            },
        )

        duplicate_register = client.post("/api/register", json=user_payload)
        expect_status(duplicate_register, 409, "POST /api/register duplicate")
        print("PASS duplicate registration returns 409")

        weak_password_payload = dict(user_payload)
        weak_password_payload["email"] = f"weak+{uuid4().hex[:8]}@example.com"
        weak_password_payload["password"] = "weak"
        weak_password = client.post("/api/register", json=weak_password_payload)
        expect_status(weak_password, 400, "POST /api/register weak password")
        print("PASS weak password returns 400")

        empty_checkout = client.post(
            "/api/checkout",
            json={"cart_id": cart_id, "payment_method_id": payment_method_id},
        )
        expect_status(empty_checkout, 409, "POST /api/checkout empty cart")
        print("PASS empty cart checkout returns 409")

        dvd_id = dvd_items[0]["id"]
        add_item = client.post(
            f"/api/carts/{cart_id}/items",
            json={"dvd_id": dvd_id, "quantity": 1},
        )
        expect_status(add_item, 201, f"POST /api/carts/{cart_id}/items")
        add_item_json = add_item.get_json()
        item_id = add_item_json["items"][0]["id"]
        print("PASS add to cart", add_item_json["summary"])

        view_cart = client.get(f"/api/carts/{cart_id}")
        expect_status(view_cart, 200, f"GET /api/carts/{cart_id}")
        print("PASS view cart", view_cart.get_json()["summary"])

        missing_cart = client.get("/api/carts/999999")
        expect_status(missing_cart, 404, "GET /api/carts/999999")
        print("PASS missing cart returns 404")

        checkout = client.post(
            "/api/checkout",
            json={"cart_id": cart_id, "payment_method_id": payment_method_id},
        )
        expect_status(checkout, 201, "POST /api/checkout")
        print("PASS checkout", checkout.get_json())

        delete_after_checkout = client.delete(f"/api/carts/{cart_id}/items/{item_id}")
        expect_status(
            delete_after_checkout,
            409,
            f"DELETE /api/carts/{cart_id}/items/{item_id} after checkout",
        )
        print("PASS post-checkout cart modification returns 409")

        print("Manual smoke test completed successfully.")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"SMOKE TEST FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
