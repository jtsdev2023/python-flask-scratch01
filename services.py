from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from db import execute, fetch_all, fetch_one, get_connection


SALES_TAX_RATE = Decimal("0.07")
PASSWORD_ITERATIONS = 100_000
PASSWORD_MIN_LENGTH = 12


class ServiceError(Exception):
    pass


class ValidationError(ServiceError):
    pass


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _password_strength_errors(password: str) -> list[str]:
    errors = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must include at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include at least one uppercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must include at least one number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include at least one special character.")
    return errors


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
    except ValueError as error:
        raise ValidationError("Stored password hash is malformed.") from error
    if algorithm != "pbkdf2_sha256":
        raise ValidationError("Unsupported password hash algorithm.")
    comparison = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(comparison, stored_hash)


def _cents_to_decimal(cents: int) -> str:
    return f"{Decimal(cents) / Decimal('100'):.2f}"


def _validate_phone_number(phone_number: str) -> str:
    normalized = re.sub(r"[\s\-().]", "", phone_number)
    if not re.fullmatch(r"\d{10,15}", normalized):
        raise ValidationError("Phone number must contain 10 to 15 digits.")
    return phone_number.strip()


def _validate_card_number(card_number: str) -> str:
    normalized = re.sub(r"\s", "", card_number)
    if not re.fullmatch(r"\d{12,19}", normalized):
        raise ValidationError("Card number must contain 12 to 19 digits.")
    return normalized


def _validate_card_last4(card_number: str) -> str:
    return card_number[-4:]


def _ensure_user_exists(user_id: int):
    user = fetch_one("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
    if user is None:
        raise NotFoundError("User not found.")
    return user


def _ensure_cart(cart_id: int):
    cart = fetch_one("SELECT * FROM shopping_carts WHERE id = :cart_id", {"cart_id": cart_id})
    if cart is None:
        raise NotFoundError("Cart not found.")
    return cart


def _ensure_payment_method(payment_method_id: int):
    payment_method = fetch_one(
        "SELECT * FROM payment_methods WHERE id = :payment_method_id",
        {"payment_method_id": payment_method_id},
    )
    if payment_method is None:
        raise NotFoundError("Payment method not found.")
    return payment_method


def _ensure_dvd(dvd_id: int):
    dvd = fetch_one("SELECT * FROM dvds WHERE id = :dvd_id", {"dvd_id": dvd_id})
    if dvd is None:
        raise NotFoundError("DVD not found.")
    return dvd


def create_user(payload: dict) -> dict:
    required_fields = [
        "email",
        "password",
        "first_name",
        "last_name",
        "phone_number",
        "billing_address_line1",
        "billing_city",
        "billing_state",
        "billing_postal_code",
        "payment_method",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    email = _normalize_email(payload["email"])
    password = payload["password"]
    first_name = payload["first_name"].strip()
    last_name = payload["last_name"].strip()
    phone_number = _validate_phone_number(payload["phone_number"])
    billing_address_line1 = payload["billing_address_line1"].strip()
    billing_address_line2 = payload.get("billing_address_line2", "")
    billing_city = payload["billing_city"].strip()
    billing_state = payload["billing_state"].strip()
    billing_postal_code = payload["billing_postal_code"].strip()
    payment_method = payload["payment_method"]

    if not email:
        raise ValidationError("Email is required.")
    if not first_name or not last_name:
        raise ValidationError("First and last name are required.")

    password_errors = _password_strength_errors(password)
    if password_errors:
        raise ValidationError(" ".join(password_errors))

    payment_required_fields = ["card_number", "card_brand", "card_exp_month", "card_exp_year"]
    missing_payment = [field for field in payment_required_fields if field not in payment_method]
    if missing_payment:
        raise ValidationError(f"Missing payment method fields: {', '.join(missing_payment)}")

    card_number = _validate_card_number(str(payment_method["card_number"]))
    card_brand = str(payment_method["card_brand"]).strip()
    card_exp_month = int(payment_method["card_exp_month"])
    card_exp_year = int(payment_method["card_exp_year"])
    payment_token = str(payment_method.get("payment_token") or f"pm_{uuid4().hex}")
    is_default = int(bool(payment_method.get("is_default", True)))

    if not card_brand:
        raise ValidationError("Card brand is required.")
    if card_exp_month < 1 or card_exp_month > 12:
        raise ValidationError("Card expiration month must be between 1 and 12.")
    if card_exp_year < 2000:
        raise ValidationError("Card expiration year is invalid.")

    existing_user = fetch_one("SELECT id FROM users WHERE email = :email", {"email": email})
    if existing_user is not None:
        raise ConflictError("An account with that email already exists.")

    password_hash = hash_password(password)
    card_last4 = _validate_card_last4(card_number)

    with get_connection() as connection:
        user_cursor = connection.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                first_name,
                last_name,
                phone_number,
                billing_address_line1,
                billing_address_line2,
                billing_city,
                billing_state,
                billing_postal_code
            )
            VALUES (
                :email,
                :password_hash,
                :first_name,
                :last_name,
                :phone_number,
                :billing_address_line1,
                :billing_address_line2,
                :billing_city,
                :billing_state,
                :billing_postal_code
            )
            """,
            {
                "email": email,
                "password_hash": password_hash,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "billing_address_line1": billing_address_line1,
                "billing_address_line2": billing_address_line2.strip() or None,
                "billing_city": billing_city,
                "billing_state": billing_state,
                "billing_postal_code": billing_postal_code,
            },
        )
        user_id = user_cursor.lastrowid

        payment_cursor = connection.execute(
            """
            INSERT INTO payment_methods (
                user_id,
                payment_token,
                card_brand,
                card_last4,
                card_exp_month,
                card_exp_year,
                is_default
            )
            VALUES (
                :user_id,
                :payment_token,
                :card_brand,
                :card_last4,
                :card_exp_month,
                :card_exp_year,
                :is_default
            )
            """,
            {
                "user_id": user_id,
                "payment_token": payment_token,
                "card_brand": card_brand,
                "card_last4": card_last4,
                "card_exp_month": card_exp_month,
                "card_exp_year": card_exp_year,
                "is_default": is_default,
            },
        )
        payment_method_id = payment_cursor.lastrowid

        connection.execute(
            "INSERT INTO password_history (user_id, password_hash) VALUES (:user_id, :password_hash)",
            {"user_id": user_id, "password_hash": password_hash},
        )

        cart_cursor = connection.execute(
            "INSERT INTO shopping_carts (user_id, status) VALUES (:user_id, 'active')",
            {"user_id": user_id},
        )
        cart_id = cart_cursor.lastrowid

    return {
        "user": {
            "id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
        },
        "payment_method": {
            "id": payment_method_id,
            "card_brand": card_brand,
            "card_last4": card_last4,
            "card_exp_month": card_exp_month,
            "card_exp_year": card_exp_year,
            "is_default": bool(is_default),
        },
        "cart": {
            "id": cart_id,
            "status": "active",
        },
    }


def list_dvds(title_search: str = "%", genre: str | None = None, active_only: bool = True) -> list[dict]:
    query = """
        SELECT
            id,
            title,
            director,
            genre,
            release_year,
            description,
            rental_price_cents,
            total_copies,
            available_copies,
            created_at,
            updated_at,
            is_active
        FROM dvds
        WHERE title LIKE :title_search
          AND (:genre IS NULL OR genre = :genre)
          AND (:active_only = 0 OR is_active = 1)
        ORDER BY title ASC
    """
    rows = fetch_all(
        query,
        {
            "title_search": title_search,
            "genre": genre,
            "active_only": 1 if active_only else 0,
        },
    )
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "director": row["director"],
            "genre": row["genre"],
            "release_year": row["release_year"],
            "description": row["description"],
            "rental_price_cents": row["rental_price_cents"],
            "rental_price": _cents_to_decimal(row["rental_price_cents"]),
            "total_copies": row["total_copies"],
            "available_copies": row["available_copies"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": bool(row["is_active"]),
        }
        for row in rows
    ]


def get_cart(cart_id: int) -> dict:
    cart = _ensure_cart(cart_id)
    user = _ensure_user_exists(cart["user_id"])
    rows = fetch_all(
        """
        SELECT
            sci.id,
            sci.cart_id,
            sci.dvd_id,
            sci.quantity,
            sci.unit_price_cents,
            sci.created_at,
            sci.updated_at,
            d.title,
            d.director,
            d.genre,
            d.release_year,
            d.description,
            d.available_copies
        FROM shopping_cart_items sci
        JOIN dvds d ON d.id = sci.dvd_id
        WHERE sci.cart_id = :cart_id
        ORDER BY sci.id ASC
        """,
        {"cart_id": cart_id},
    )

    items = []
    subtotal_cents = 0
    for row in rows:
        total_price_cents = row["quantity"] * row["unit_price_cents"]
        subtotal_cents += total_price_cents
        items.append(
            {
                "id": row["id"],
                "dvd_id": row["dvd_id"],
                "title": row["title"],
                "director": row["director"],
                "genre": row["genre"],
                "release_year": row["release_year"],
                "description": row["description"],
                "quantity": row["quantity"],
                "unit_price_cents": row["unit_price_cents"],
                "unit_price": _cents_to_decimal(row["unit_price_cents"]),
                "total_price_cents": total_price_cents,
                "total_price": _cents_to_decimal(total_price_cents),
                "available_copies": row["available_copies"],
            }
        )

    tax_cents = int((Decimal(subtotal_cents) * SALES_TAX_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_cents = subtotal_cents + tax_cents
    return {
        "cart": {
            "id": cart["id"],
            "user_id": user["id"],
            "status": cart["status"],
            "created_at": cart["created_at"],
            "updated_at": cart["updated_at"],
        },
        "items": items,
        "summary": {
            "subtotal_cents": subtotal_cents,
            "subtotal": _cents_to_decimal(subtotal_cents),
            "tax_cents": tax_cents,
            "tax": _cents_to_decimal(tax_cents),
            "total_cents": total_cents,
            "total": _cents_to_decimal(total_cents),
        },
    }


def add_item_to_cart(cart_id: int, dvd_id: int, quantity: int = 1) -> dict:
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    cart = _ensure_cart(cart_id)
    if cart["status"] != "active":
        raise ConflictError("Only active carts can be modified.")

    dvd = _ensure_dvd(dvd_id)
    if not dvd["is_active"]:
        raise ConflictError("This DVD is not available for purchase.")

    existing_item = fetch_one(
        "SELECT * FROM shopping_cart_items WHERE cart_id = :cart_id AND dvd_id = :dvd_id",
        {"cart_id": cart_id, "dvd_id": dvd_id},
    )
    existing_quantity = existing_item["quantity"] if existing_item is not None else 0
    total_quantity = existing_quantity + quantity
    if total_quantity > dvd["available_copies"]:
        raise ConflictError("Not enough copies are available.")

    with get_connection() as connection:
        if existing_item is None:
            connection.execute(
                """
                INSERT INTO shopping_cart_items (
                    cart_id,
                    dvd_id,
                    quantity,
                    unit_price_cents
                )
                VALUES (
                    :cart_id,
                    :dvd_id,
                    :quantity,
                    :unit_price_cents
                )
                """,
                {
                    "cart_id": cart_id,
                    "dvd_id": dvd_id,
                    "quantity": quantity,
                    "unit_price_cents": dvd["rental_price_cents"],
                },
            )
        else:
            connection.execute(
                """
                UPDATE shopping_cart_items
                SET quantity = :quantity,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :item_id
                """,
                {"quantity": total_quantity, "item_id": existing_item["id"]},
            )

    return get_cart(cart_id)


def remove_item_from_cart(cart_id: int, item_id: int) -> dict:
    cart = _ensure_cart(cart_id)
    if cart["status"] != "active":
        raise ConflictError("Only active carts can be modified.")

    item = fetch_one(
        "SELECT id FROM shopping_cart_items WHERE id = :item_id AND cart_id = :cart_id",
        {"item_id": item_id, "cart_id": cart_id},
    )
    if item is None:
        raise NotFoundError("Cart item not found.")

    execute("DELETE FROM shopping_cart_items WHERE id = :item_id", {"item_id": item_id})
    return get_cart(cart_id)


def checkout_cart(cart_id: int, payment_method_id: int) -> dict:
    cart = _ensure_cart(cart_id)
    if cart["status"] != "active":
        raise ConflictError("This cart has already been checked out or closed.")

    payment_method = _ensure_payment_method(payment_method_id)
    if payment_method["user_id"] != cart["user_id"]:
        raise ConflictError("Payment method does not belong to this cart owner.")

    cart_details = get_cart(cart_id)
    if not cart_details["items"]:
        raise ConflictError("Cannot checkout an empty cart.")

    with get_connection() as connection:
        dvd_state = {}
        for item in cart_details["items"]:
            row = connection.execute(
                "SELECT id, available_copies FROM dvds WHERE id = :dvd_id",
                {"dvd_id": item["dvd_id"]},
            ).fetchone()
            if row is None:
                raise NotFoundError("A DVD in the cart no longer exists.")
            if row["available_copies"] < item["quantity"]:
                raise ConflictError(f"Not enough copies available for {item['title']}.")
            dvd_state[item["dvd_id"]] = row["available_copies"]

        subtotal_cents = cart_details["summary"]["subtotal_cents"]
        tax_cents = cart_details["summary"]["tax_cents"]
        total_cents = cart_details["summary"]["total_cents"]

        order_cursor = connection.execute(
            """
            INSERT INTO orders (
                user_id,
                payment_method_id,
                subtotal_cents,
                tax_cents,
                total_cents,
                status
            )
            VALUES (
                :user_id,
                :payment_method_id,
                :subtotal_cents,
                :tax_cents,
                :total_cents,
                'placed'
            )
            """,
            {
                "user_id": cart["user_id"],
                "payment_method_id": payment_method_id,
                "subtotal_cents": subtotal_cents,
                "tax_cents": tax_cents,
                "total_cents": total_cents,
            },
        )
        order_id = order_cursor.lastrowid

        for item in cart_details["items"]:
            total_price_cents = item["total_price_cents"]
            connection.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    dvd_id,
                    quantity,
                    unit_price_cents,
                    total_price_cents
                )
                VALUES (
                    :order_id,
                    :dvd_id,
                    :quantity,
                    :unit_price_cents,
                    :total_price_cents
                )
                """,
                {
                    "order_id": order_id,
                    "dvd_id": item["dvd_id"],
                    "quantity": item["quantity"],
                    "unit_price_cents": item["unit_price_cents"],
                    "total_price_cents": total_price_cents,
                },
            )
            connection.execute(
                """
                UPDATE dvds
                SET available_copies = available_copies - :quantity,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :dvd_id
                """,
                {"quantity": item["quantity"], "dvd_id": item["dvd_id"]},
            )

        connection.execute(
            """
            UPDATE shopping_carts
            SET status = 'converted',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :cart_id
            """,
            {"cart_id": cart_id},
        )

    return {
        "order_id": order_id,
        "cart_id": cart_id,
        "user_id": cart["user_id"],
        "payment_method_id": payment_method_id,
        "subtotal_cents": subtotal_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "subtotal": _cents_to_decimal(subtotal_cents),
        "tax": _cents_to_decimal(tax_cents),
        "total": _cents_to_decimal(total_cents),
        "status": "placed",
    }