# My Project Work Notes
## Run this with the project venv Python:
```python
from pathlib import Path
import tempfile

import db
import python_db

tmpdir = Path(tempfile.mkdtemp(prefix="scratch01-manualtest-"))
tmpdb = tmpdir / "manual_test.db"

# Isolate the test run from your working database
db.DB_PATH = tmpdb
python_db.DB_PATH = tmpdb

python_db.create_database()
python_db.seed_database()

from app import create_app

client = create_app().test_client()

user_payload = {
    "email": "manual.test@example.com",
    "password": "StrongPass123!",
    "first_name": "Manual",
    "last_name": "Tester",
    "phone_number": "5551234567",
    "billing_address_line1": "123 Main St",
    "billing_city": "Testville",
    "billing_state": "CA",
    "billing_postal_code": "90001",
    "payment_method": {
        "card_number": "4111111111111111",
        "card_brand": "Visa",
        "card_exp_month": 12,
        "card_exp_year": 2030,
    },
}

health = client.get("/api/health")
print("health:", health.status_code, health.get_json())

dvds = client.get("/api/dvds")
dvd_items = dvds.get_json()["items"]
print("dvds:", dvds.status_code, len(dvd_items), "items")

register = client.post("/api/register", json=user_payload)
register_json = register.get_json()
print("register:", register.status_code, register_json)

cart_id = register_json["cart"]["id"]
payment_method_id = register_json["payment_method"]["id"]
dvd_id = dvd_items[0]["id"]

add_item = client.post(f"/api/carts/{cart_id}/items", json={"dvd_id": dvd_id, "quantity": 1})
add_item_json = add_item.get_json()
print("add_item:", add_item.status_code, add_item_json["summary"])

item_id = add_item_json["items"][0]["id"]

view_cart = client.get(f"/api/carts/{cart_id}")
print("view_cart:", view_cart.status_code, view_cart.get_json()["summary"])

checkout = client.post("/api/checkout", json={
    "cart_id": cart_id,
    "payment_method_id": payment_method_id,
})
print("checkout:", checkout.status_code, checkout.get_json())

post_checkout_delete = client.delete(f"/api/carts/{cart_id}/items/{item_id}")
print("delete_after_checkout:", post_checkout_delete.status_code, post_checkout_delete.get_json())

print("temp database:", tmpdb)
```

### What to manually verify after that:
- GET /api/health returns 200
- GET /api/dvds returns seeded inventory
- POST /api/register returns 201 and creates user, payment_method, and cart
- POST /api/carts/<id>/items returns 201 and computes subtotal/tax/total
- POST /api/checkout returns 201, creates an order, and converts the cart
- Modifying the cart after checkout returns 409

### Useful negative-path checks:
- Duplicate email registration should return 409
- Weak password should return 400
- Empty cart checkout should return 409
- Missing cart should return 404

Verified this flow locally against the project code: health, DVD listing, register, add-to-cart, and checkout all worked in an isolated temp DB, and the expected error cases returned 400/404/409 appropriately.

## Smoke Test Python Script

The smoke test script uses `tempfile.TemporaryDirectory()` so each run gets an isolated SQLite database that is cleaned up automatically.
The script seeds the temp DB, exercises the main Flask routes through `app.test_client()`, and checks both happy-path and a few important error-path behaviors.

Run it with one command:
```bash
./.pyscratch_venv/bin/python scripts/manual_smoke_test.py
```

```python
#!/usr/bin/env python3
# manual_smoke_test.py

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import db
import python_db


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

        unique_email = f"manual.test+{uuid4().hex[:8]}@example.com"
        user_payload = {
            "email": unique_email,
            "password": "StrongPass123!",
            "first_name": "Manual",
            "last_name": "Tester",
            "phone_number": "5551234567",
            "billing_address_line1": "123 Main St",
            "billing_city": "Testville",
            "billing_state": "CA",
            "billing_postal_code": "90001",
            "payment_method": {
                "card_number": "4111111111111111",
                "card_brand": "Visa",
                "card_exp_month": 12,
                "card_exp_year": 2030,
            },
        }

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

```

Smoke test verified June 10, 2026.


Passed Checks:
- health
- DVD listing
- registration
- duplicate registration
- weak-password validation
- empty-cart checkout
- add-to-cart
- cart retrieval
- missing-cart handling
- checkout
- post-checkout cart protection
