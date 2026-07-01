from __future__ import annotations

import copy
from uuid import uuid4

import pytest

from test_support import generate_unique_email, load_user_payloads


@pytest.fixture
def anonymous_client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def client_a(flask_app):
    return flask_app.test_client()


@pytest.fixture
def client_b(flask_app):
    return flask_app.test_client()


@pytest.fixture
def user_payloads() -> list[dict]:
    return load_user_payloads()


@pytest.fixture
def user_a_payload(user_payloads) -> dict:
    return copy.deepcopy(user_payloads[0])


@pytest.fixture
def user_b_payload(user_payloads) -> dict:
    return copy.deepcopy(user_payloads[1])


def register_user(client, payload: dict) -> dict:
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def login_user(client, email: str, password: str) -> dict:
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_health_check(anonymous_client):
    response = anonymous_client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_list_dvds_returns_items(anonymous_client):
    response = anonymous_client.get("/api/dvds")

    assert response.status_code == 200
    data = response.get_json()
    assert data["items"]


def test_unauthenticated_me_returns_401(anonymous_client):
    response = anonymous_client.get("/api/me")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required."


def test_register_user_creates_session_and_active_cart(client_a, user_a_payload):
    register_data = register_user(client_a, user_a_payload)

    me_response = client_a.get("/api/me")
    assert me_response.status_code == 200
    me_data = me_response.get_json()

    assert me_data["user"]["email"] == user_a_payload["email"].lower()
    assert me_data["cart"]["id"] == register_data["cart"]["id"]
    assert register_data["cart"]["status"] == "active"


def test_duplicate_registration_returns_409(client_b, user_b_payload):
    register_user(client_b, user_b_payload)

    duplicate_response = client_b.post("/api/register", json=user_b_payload)

    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json()["error"] == "An account with that email already exists."


def test_weak_password_returns_400(anonymous_client, user_b_payload):
    weak_password_payload = copy.deepcopy(user_b_payload)
    weak_password_payload["email"] = f"weak+{uuid4().hex[:8]}@example.com"
    weak_password_payload["password"] = "weak"

    response = anonymous_client.post("/api/register", json=weak_password_payload)

    assert response.status_code == 400
    assert "Password must be at least" in response.get_json()["error"]


def test_cross_user_cart_access_returns_404(client_a, client_b, user_a_payload, user_b_payload):
    register_a = register_user(client_a, user_a_payload)
    register_user(client_b, user_b_payload)
    cart_a_id = register_a["cart"]["id"]

    response = client_b.get(f"/api/carts/{cart_a_id}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Cart not found."


def test_logout_clears_session(client_b, user_b_payload):
    register_user(client_b, user_b_payload)

    logout_response = client_b.post("/api/logout")
    me_response = client_b.get("/api/me")
    cart_response = client_b.get("/api/me/cart")

    assert logout_response.status_code == 200
    assert logout_response.get_json() == {"message": "Logged out."}
    assert me_response.status_code == 401
    assert cart_response.status_code == 401


def test_invalid_login_returns_400(client_b, user_b_payload):
    register_user(client_b, user_b_payload)
    client_b.post("/api/logout")

    response = client_b.post(
        "/api/login",
        json={"email": user_b_payload["email"], "password": "WrongPass123!"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid email or password."


def test_login_returns_profile_and_expected_active_cart(client_b, user_b_payload):
    register_data = register_user(client_b, user_b_payload)
    cart_b_id = register_data["cart"]["id"]
    client_b.post("/api/logout")

    login_user(client_b, user_b_payload["email"], user_b_payload["password"])
    me_response = client_b.get("/api/me")
    cart_response = client_b.get("/api/me/cart")

    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["email"] == user_b_payload["email"].lower()
    assert cart_response.status_code == 200
    assert cart_response.get_json()["cart"]["id"] == cart_b_id


def test_empty_cart_checkout_returns_409(client_b, user_b_payload):
    register_data = register_user(client_b, user_b_payload)

    response = client_b.post(
        "/api/checkout",
        json={
            "cart_id": register_data["cart"]["id"],
            "payment_method_id": register_data["payment_method"]["id"],
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "Cannot checkout an empty cart."


def test_add_item_then_view_cart(client_b, anonymous_client, user_b_payload):
    register_data = register_user(client_b, user_b_payload)
    cart_b_id = register_data["cart"]["id"]

    dvd_response = anonymous_client.get("/api/dvds")
    dvd_id = dvd_response.get_json()["items"][0]["id"]

    add_response = client_b.post(
        f"/api/carts/{cart_b_id}/items",
        json={"dvd_id": dvd_id, "quantity": 1},
    )
    view_response = client_b.get(f"/api/carts/{cart_b_id}")

    assert add_response.status_code == 201
    add_data = add_response.get_json()
    assert add_data["items"]
    assert view_response.status_code == 200
    assert view_response.get_json()["summary"]["total"] == add_data["summary"]["total"]


def test_missing_cart_returns_404(client_b, user_b_payload):
    register_user(client_b, user_b_payload)

    response = client_b.get("/api/carts/999999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Cart not found."


def test_checkout_creates_order_and_new_active_cart(client_b, anonymous_client, user_b_payload):
    register_data = register_user(client_b, user_b_payload)
    cart_b_id = register_data["cart"]["id"]
    payment_method_id = register_data["payment_method"]["id"]

    dvd_id = anonymous_client.get("/api/dvds").get_json()["items"][0]["id"]
    add_response = client_b.post(
        f"/api/carts/{cart_b_id}/items",
        json={"dvd_id": dvd_id, "quantity": 1},
    )
    item_id = add_response.get_json()["items"][0]["id"]

    checkout_response = client_b.post(
        "/api/checkout",
        json={"cart_id": cart_b_id, "payment_method_id": payment_method_id},
    )

    assert checkout_response.status_code == 201
    checkout_data = checkout_response.get_json()
    order_id = checkout_data["order_id"]
    next_cart_id = checkout_data["next_cart_id"]

    order_response = client_b.get(f"/api/orders/{order_id}")
    current_cart_response = client_b.get("/api/me/cart")
    delete_after_checkout = client_b.delete(f"/api/carts/{cart_b_id}/items/{item_id}")

    assert order_response.status_code == 200
    assert order_response.get_json()["order"]["id"] == order_id
    assert current_cart_response.status_code == 200
    current_cart_data = current_cart_response.get_json()
    assert current_cart_data["cart"]["id"] == next_cart_id
    assert current_cart_data["items"] == []
    assert delete_after_checkout.status_code == 409


def test_cross_user_order_access_returns_404(client_a, client_b, anonymous_client, user_a_payload, user_b_payload):
    register_user(client_a, user_a_payload)
    register_b = register_user(client_b, user_b_payload)
    cart_b_id = register_b["cart"]["id"]
    payment_method_id = register_b["payment_method"]["id"]

    dvd_id = anonymous_client.get("/api/dvds").get_json()["items"][0]["id"]
    client_b.post(f"/api/carts/{cart_b_id}/items", json={"dvd_id": dvd_id, "quantity": 1})
    checkout_response = client_b.post(
        "/api/checkout",
        json={"cart_id": cart_b_id, "payment_method_id": payment_method_id},
    )
    order_id = checkout_response.get_json()["order_id"]

    response = client_a.get(f"/api/orders/{order_id}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Order not found."
