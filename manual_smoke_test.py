#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

# test
import sqlite3

import db
import python_db


BASE_DIR = Path(__file__).resolve().parent

user_payload_json_file_name = BASE_DIR / "smoke-test-user-payload.json"



def expect_status(response, expected_status: int, label: str):
    if response.status_code != expected_status:
        raise AssertionError(
            f"{label} returned {response.status_code}, expected {expected_status}: {response.get_json()}"
        )

def generate_unique_email(first_name: str, last_name: str) -> str:
    """Create unique user email for smoke test"""
    unique_str = uuid4().hex[:6]
    return f"{first_name}.{last_name}_{unique_str}@example.com"



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

        ##### need to wrap this is a loop for use with multiple users
        # unique_email = f"manual.test.{uuid4().hex[:8]}@example.com"
        # # read and load user payload from file
        # user_payload = json.loads(user_payload_json_file_name.read_text(encoding="utf-8"))
        # user_payload['email'] = unique_email

        # user payload loop
        # even a single user should be in a list obj
        user_payload = json.loads(
            user_payload_json_file_name.read_text(encoding="utf-8"))

        for user in user_payload:
            unique_email = \
                generate_unique_email(user["first_name"], user["last_name"])
            
            # user payload seed file starts with email as empty string
            # populate user email
            user["email"] = unique_email

        ######


        health = client.get("/api/health")
        expect_status(health, 200, "GET /api/health")
        print("PASS GET /api/health", health.get_json())

        dvds = client.get("/api/dvds")
        expect_status(dvds, 200, "GET /api/dvds")
        dvd_items = dvds.get_json()["items"]
        if not dvd_items:
            raise AssertionError("GET /api/dvds returned no items.")
        print(f"PASS GET /api/dvds returned {len(dvd_items)} items")
        # print a DVD item for example
        print(f"\nPRINT DVD ITEM EXAMPLE:")
        for k, v in dvd_items[0].items():
            print(k, v)
        print()

        #####   need to fix client registration now that test json is list[dict]
        #       instead of just dict
        for user in user_payload:
            register = client.post("/api/register", json=user)
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

            duplicate_register = client.post("/api/register", json=user)
            expect_status(duplicate_register, 409, "POST /api/register duplicate")
            print("PASS duplicate registration returns 409")

            weak_password_payload = dict(user)
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

        # test getting specific user
        tmp_user_query = """
        SELECT
            email,
            first_name,
            last_name,
            phone_number,
            billing_address_line1,
            billing_address_line2,
            billing_city,
            billing_state,
            billing_postal_code
        FROM users
        WHERE last_name LIKE 'hofstadter'
        """
        test_connection = sqlite3.connect(temp_db_path)
        test_cursor = test_connection.cursor()
        test_cursor.execute(tmp_user_query)
        test_rows = test_cursor.fetchall()
        test_connection.close()
        print("\nPRINT TEST USER INFO\n")

        if not test_rows:
            print("No matching users found.")
        else:
            r = test_rows[0]
            address_line_2 = f" {r[5]}" if r[5] else ""
            user_info_rows = [
                ("Email:", r[0]),
                ("First Name:", r[1]),
                ("Last Name:", r[2]),
                ("Phone:", r[3]),
                ("Address:", f"{r[4]}{address_line_2}"),
                ("", f"{r[6]}, {r[7]} {r[8]}"),
            ]
            label_width = max(len(label) for label, _ in user_info_rows) + 2
            user_info_lines = [
                f"{label:<{label_width}}{value}"
                for label, value in user_info_rows
            ]
            print("\n".join(user_info_lines))

        print("\nManual smoke test completed successfully.\n")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"SMOKE TEST FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
