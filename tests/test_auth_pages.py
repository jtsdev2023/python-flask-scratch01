from __future__ import annotations

import re

from test_support import build_user_payload


def fill_register_form(page, user_payload: dict):
    page.get_by_label("First name").fill(user_payload["first_name"])
    page.get_by_label("Last name").fill(user_payload["last_name"])
    page.get_by_label("Email address").fill(user_payload["email"])
    page.get_by_label("Phone number").fill(user_payload["phone_number"])
    page.get_by_label("Password").fill(user_payload["password"])
    page.get_by_label("Billing address line 1").fill(user_payload["billing_address_line1"])
    page.get_by_label("Billing address line 2").fill(user_payload["billing_address_line2"])
    page.get_by_label("Billing city").fill(user_payload["billing_city"])
    page.get_by_label("Billing state").fill(user_payload["billing_state"])
    page.get_by_label("Zip code").fill(user_payload["billing_postal_code"])
    page.get_by_label("Card number").fill(user_payload["payment_method"]["card_number"])
    page.get_by_label("Card brand").fill(user_payload["payment_method"]["card_brand"])
    page.get_by_label("Month").fill(str(user_payload["payment_method"]["card_exp_month"]))
    page.get_by_label("Year").fill(str(user_payload["payment_method"]["card_exp_year"]))


def register_user_via_browser(page, live_server: str) -> dict:
    user_payload = build_user_payload()
    page.goto(f"{live_server}/register")
    fill_register_form(page, user_payload)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url(f"{live_server}/catalog")
    page.locator("#catalog-grid .catalog-card").first.wait_for()
    return user_payload


def create_user_via_api(flask_app) -> dict:
    user_payload = build_user_payload()
    client = flask_app.test_client()
    response = client.post("/api/register", json=user_payload)
    assert response.status_code == 201, response.get_json()
    return user_payload


def login_user_via_browser(page, live_server: str, user_payload: dict):
    page.goto(f"{live_server}/login")
    page.get_by_label("Email address").fill(user_payload["email"])
    page.get_by_label("Password").fill(user_payload["password"])
    page.get_by_role("button", name="Login").click()
    page.wait_for_url(f"{live_server}/catalog")
    page.locator("#catalog-grid .catalog-card").first.wait_for()


def add_first_catalog_item_to_cart(page):
    first_card = page.locator("#catalog-grid .catalog-card").first
    item_title = first_card.locator("h2").text_content().strip()
    first_card.get_by_role("button", name="Add to cart").click()
    page.locator("#catalog-feedback").get_by_text(f"{item_title} was added to your cart.").wait_for()
    return item_title


def open_cart(page, live_server: str):
    page.goto(f"{live_server}/cart")
    page.locator("#cart-loading").wait_for(state="hidden")


def test_register_page_creates_account_and_redirects_to_catalog(page, live_server):
    register_user_via_browser(page, live_server)

    assert page.locator("body").get_attribute("data-page") == "catalog"
    assert page.locator("[data-logout-button]").is_visible()
    assert "Catalog" in page.title()


def test_login_page_signs_in_existing_user(page, live_server, flask_app):
    user_payload = create_user_via_api(flask_app)

    login_user_via_browser(page, live_server, user_payload)

    assert page.locator("body").get_attribute("data-page") == "catalog"
    assert page.locator("[data-logout-button]").is_visible()
    assert "Catalog" in page.title()


def test_logout_button_signs_user_out_and_returns_to_home(page, live_server):
    register_user_via_browser(page, live_server)

    page.locator("[data-logout-button]").click()
    page.wait_for_url(re.compile(rf"{re.escape(live_server)}/(?:home)?$"))

    assert page.locator("body").get_attribute("data-page") == "home"
    assert page.locator("#siteNav").get_by_role("link", name="Login").is_visible()
    assert page.locator("[data-logout-button]").count() == 0


def test_cart_page_adds_and_removes_items(page, live_server):
    register_user_via_browser(page, live_server)
    item_title = add_first_catalog_item_to_cart(page)

    open_cart(page, live_server)

    assert page.locator("#cart-items").get_by_role("heading", name=item_title).is_visible()
    assert page.locator("#checkout-button").is_enabled()

    page.locator("#cart-items article").first.get_by_role("button", name="Remove").click()
    page.locator("#cart-feedback").get_by_text(f"{item_title} was removed from your cart.").wait_for()

    assert page.locator("#cart-empty").is_visible()
    assert page.locator("#checkout-button").is_disabled()


def test_checkout_flow_places_order_and_returns_to_empty_active_cart(page, live_server):
    register_user_via_browser(page, live_server)
    item_title = add_first_catalog_item_to_cart(page)

    open_cart(page, live_server)
    page.get_by_role("button", name="Complete checkout").click()
    page.wait_for_url(re.compile(rf"{re.escape(live_server)}/orders/\d+$"))
    page.locator("#order-content").wait_for()

    assert page.locator("body").get_attribute("data-page") == "order"
    assert page.get_by_role("heading", name=item_title).is_visible()
    assert page.locator("#order-number").text_content().startswith("Order #")

    page.get_by_role("link", name="View active cart").click()
    page.wait_for_url(f"{live_server}/cart")
    page.locator("#cart-loading").wait_for(state="hidden")

    assert page.locator("#cart-empty").is_visible()
    assert page.locator("#checkout-button").is_disabled()
