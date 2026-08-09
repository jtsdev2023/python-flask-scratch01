#!/usr/bin/env python3

from __future__ import annotations

import copy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.db import get_engine
from tests.test_support import load_user_payloads


def expect_status(response, expected_status: int, label: str):
    if response.status_code != expected_status:
        raise AssertionError(
            f"{label} returned {response.status_code}, expected {expected_status}: {response.get_json()}"
        )


def main() -> int:
    with TemporaryDirectory(prefix="scratch01-manualtest-") as tmpdir:
        temp_db_path = Path(tmpdir) / "manual_smoke_test.db"
        app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": f"sqlite+pysqlite:///{temp_db_path}",
            }
        )
        anonymous_client = app.test_client()
        client_a = app.test_client()
        client_b = app.test_client()

        user_payloads = load_user_payloads()
        user_a = user_payloads[0]
        user_b = user_payloads[1]

        health = anonymous_client.get("/api/health")
        expect_status(health, 200, "GET /api/health")
        print("PASS GET /api/health", health.get_json())

        dvds = anonymous_client.get("/api/dvds")
        expect_status(dvds, 200, "GET /api/dvds")
        dvd_items = dvds.get_json()["items"]
        if not dvd_items:
            raise AssertionError("GET /api/dvds returned no items.")
        print(f"PASS GET /api/dvds returned {len(dvd_items)} items")

        unauthenticated_me = anonymous_client.get("/api/me")
        expect_status(unauthenticated_me, 401, "GET /api/me unauthenticated")
        print("PASS unauthenticated GET /api/me returns 401")

        register_a = client_a.post("/api/register", json=user_a)
        expect_status(register_a, 201, "POST /api/register user A")
        register_a_json = register_a.get_json()
        cart_a_id = register_a_json["cart"]["id"]
        print("PASS POST /api/register user A", register_a_json)

        me_after_register_a = client_a.get("/api/me")
        expect_status(me_after_register_a, 200, "GET /api/me after register user A")
        print("PASS GET /api/me after register user A", me_after_register_a.get_json())

        register_b = client_b.post("/api/register", json=user_b)
        expect_status(register_b, 201, "POST /api/register user B")
        register_b_json = register_b.get_json()
        cart_b_id = register_b_json["cart"]["id"]
        payment_method_b_id = register_b_json["payment_method"]["id"]
        print("PASS POST /api/register user B", register_b_json)

        duplicate_register = client_b.post("/api/register", json=user_b)
        expect_status(duplicate_register, 409, "POST /api/register duplicate")
        print("PASS duplicate registration returns 409")

        weak_password_payload = copy.deepcopy(user_b)
        weak_password_payload["email"] = f"weak+{uuid4().hex[:8]}@example.com"
        weak_password_payload["password"] = "weak"
        weak_password = anonymous_client.post("/api/register", json=weak_password_payload)
        expect_status(weak_password, 400, "POST /api/register weak password")
        print("PASS weak password returns 400")

        cross_user_cart = client_b.get(f"/api/carts/{cart_a_id}")
        expect_status(cross_user_cart, 404, "GET /api/carts/<user A cart> as user B")
        print("PASS cross-user cart access returns 404")

        logout_b = client_b.post("/api/logout")
        expect_status(logout_b, 200, "POST /api/logout")
        print("PASS POST /api/logout", logout_b.get_json())

        me_after_logout = client_b.get("/api/me")
        expect_status(me_after_logout, 401, "GET /api/me after logout")
        cart_after_logout = client_b.get("/api/me/cart")
        expect_status(cart_after_logout, 401, "GET /api/me/cart after logout")
        print("PASS logout clears session for /api/me and /api/me/cart")

        invalid_login = client_b.post(
            "/api/login",
            json={"email": user_b["email"], "password": "WrongPass123!"},
        )
        expect_status(invalid_login, 400, "POST /api/login invalid password")
        print("PASS invalid login returns 400")

        login_b = client_b.post(
            "/api/login",
            json={"email": user_b["email"], "password": user_b["password"]},
        )
        expect_status(login_b, 200, "POST /api/login user B")
        login_b_json = login_b.get_json()
        print("PASS POST /api/login user B", login_b_json)

        me_b = client_b.get("/api/me")
        expect_status(me_b, 200, "GET /api/me user B")
        print("PASS GET /api/me user B", me_b.get_json())

        cart_b = client_b.get("/api/me/cart")
        expect_status(cart_b, 200, "GET /api/me/cart user B")
        cart_b_json = cart_b.get_json()
        if cart_b_json["cart"]["id"] != cart_b_id:
            raise AssertionError("GET /api/me/cart did not return the expected active cart for user B.")
        print("PASS GET /api/me/cart user B", cart_b_json["cart"])

        empty_checkout = client_b.post(
            "/api/checkout",
            json={"cart_id": cart_b_id, "payment_method_id": payment_method_b_id},
        )
        expect_status(empty_checkout, 409, "POST /api/checkout empty cart")
        print("PASS empty cart checkout returns 409")

        dvd_id = dvd_items[0]["id"]
        add_item = client_b.post(
            f"/api/carts/{cart_b_id}/items",
            json={"dvd_id": dvd_id, "quantity": 1},
        )
        expect_status(add_item, 201, f"POST /api/carts/{cart_b_id}/items")
        add_item_json = add_item.get_json()
        item_id = add_item_json["items"][0]["id"]
        print("PASS add to cart", add_item_json["summary"])

        view_cart = client_b.get(f"/api/carts/{cart_b_id}")
        expect_status(view_cart, 200, f"GET /api/carts/{cart_b_id}")
        print("PASS view cart", view_cart.get_json()["summary"])

        missing_cart = client_b.get("/api/carts/999999")
        expect_status(missing_cart, 404, "GET /api/carts/999999")
        print("PASS missing cart returns 404")

        checkout = client_b.post(
            "/api/checkout",
            json={"cart_id": cart_b_id, "payment_method_id": payment_method_b_id},
        )
        expect_status(checkout, 201, "POST /api/checkout")
        checkout_json = checkout.get_json()
        order_id = checkout_json["order_id"]
        next_cart_id = checkout_json["next_cart_id"]
        print("PASS checkout", checkout_json)

        order_details = client_b.get(f"/api/orders/{order_id}")
        expect_status(order_details, 200, f"GET /api/orders/{order_id}")
        print("PASS order details", order_details.get_json())

        cross_user_order = client_a.get(f"/api/orders/{order_id}")
        expect_status(cross_user_order, 404, "GET /api/orders/<user B order> as user A")
        print("PASS cross-user order access returns 404")

        current_cart_after_checkout = client_b.get("/api/me/cart")
        expect_status(current_cart_after_checkout, 200, "GET /api/me/cart after checkout")
        current_cart_json = current_cart_after_checkout.get_json()
        if current_cart_json["cart"]["id"] != next_cart_id:
            raise AssertionError("GET /api/me/cart did not return the new active cart after checkout.")
        if current_cart_json["items"]:
            raise AssertionError("New active cart after checkout should be empty.")
        print("PASS checkout auto-created next cart", current_cart_json["cart"])

        delete_after_checkout = client_b.delete(f"/api/carts/{cart_b_id}/items/{item_id}")
        expect_status(
            delete_after_checkout,
            409,
            f"DELETE /api/carts/{cart_b_id}/items/{item_id} after checkout",
        )
        print("PASS post-checkout cart modification returns 409")

        print("\nManual smoke test completed successfully.\n")
        get_engine(app).dispose()
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"SMOKE TEST FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
