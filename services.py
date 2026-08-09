from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from db import session_scope
from models import Dvd, Order, OrderItem, PasswordHistory, PaymentMethod, ShoppingCart, ShoppingCartItem, User


SALES_TAX_RATE = Decimal("0.07")
PASSWORD_ITERATIONS = 100_000
PASSWORD_MIN_LENGTH = 12


class ServiceError(Exception):
    pass


class ValidationError(ServiceError):
    pass


class AuthenticationError(ServiceError):
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
        algorithm, _iterations, salt_hex, _digest_hex = stored_hash.split("$", 3)
    except ValueError as error:
        raise ValidationError("Stored password hash is malformed.") from error
    if algorithm != "pbkdf2_sha256":
        raise ValidationError("Unsupported password hash algorithm.")
    comparison = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(comparison, stored_hash)


def _cents_to_decimal(cents: int) -> str:
    return f"{Decimal(cents) / Decimal('100'):.2f}"


def _format_datetime(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d %H:%M:%S")


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


def _ensure_user_exists(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def _ensure_cart(session: Session, cart_id: int) -> ShoppingCart:
    cart = session.get(ShoppingCart, cart_id)
    if cart is None:
        raise NotFoundError("Cart not found.")
    return cart


def _ensure_payment_method(session: Session, payment_method_id: int) -> PaymentMethod:
    payment_method = session.get(PaymentMethod, payment_method_id)
    if payment_method is None:
        raise NotFoundError("Payment method not found.")
    return payment_method


def _ensure_dvd(session: Session, dvd_id: int) -> Dvd:
    dvd = session.get(Dvd, dvd_id)
    if dvd is None:
        raise NotFoundError("DVD not found.")
    return dvd


def _ensure_cart_owner(cart: ShoppingCart, current_user_id: int | None) -> None:
    if current_user_id is not None and cart.user_id != current_user_id:
        raise NotFoundError("Cart not found.")


def _get_payment_method_summary(session: Session, user_id: int) -> dict | None:
    payment_method = session.scalar(
        select(PaymentMethod)
        .where(PaymentMethod.user_id == user_id)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.id.asc())
        .limit(1)
    )
    if payment_method is None:
        return None
    return {
        "id": payment_method.id,
        "card_brand": payment_method.card_brand,
        "card_last4": payment_method.card_last4,
        "card_exp_month": payment_method.card_exp_month,
        "card_exp_year": payment_method.card_exp_year,
        "is_default": bool(payment_method.is_default),
    }


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
    }


def _serialize_dvd(dvd: Dvd) -> dict:
    return {
        "id": dvd.id,
        "title": dvd.title,
        "director": dvd.director,
        "genre": dvd.genre,
        "release_year": dvd.release_year,
        "description": dvd.description,
        "rental_price_cents": dvd.rental_price_cents,
        "rental_price": _cents_to_decimal(dvd.rental_price_cents),
        "total_copies": dvd.total_copies,
        "available_copies": dvd.available_copies,
        "created_at": _format_datetime(dvd.created_at),
        "updated_at": _format_datetime(dvd.updated_at),
        "is_active": bool(dvd.is_active),
    }


def _cart_items_with_dvds(session: Session, cart_id: int) -> list[ShoppingCartItem]:
    statement = (
        select(ShoppingCartItem)
        .options(joinedload(ShoppingCartItem.dvd))
        .where(ShoppingCartItem.cart_id == cart_id)
        .order_by(ShoppingCartItem.id.asc())
    )
    return list(session.scalars(statement))


def _serialize_cart(session: Session, cart: ShoppingCart) -> dict:
    items = []
    subtotal_cents = 0

    for item in _cart_items_with_dvds(session, cart.id):
        total_price_cents = item.quantity * item.unit_price_cents
        subtotal_cents += total_price_cents
        items.append(
            {
                "id": item.id,
                "dvd_id": item.dvd_id,
                "title": item.dvd.title,
                "director": item.dvd.director,
                "genre": item.dvd.genre,
                "release_year": item.dvd.release_year,
                "description": item.dvd.description,
                "quantity": item.quantity,
                "unit_price_cents": item.unit_price_cents,
                "unit_price": _cents_to_decimal(item.unit_price_cents),
                "total_price_cents": total_price_cents,
                "total_price": _cents_to_decimal(total_price_cents),
                "available_copies": item.dvd.available_copies,
            }
        )

    tax_cents = int(
        (Decimal(subtotal_cents) * SALES_TAX_RATE).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )
    total_cents = subtotal_cents + tax_cents
    return {
        "cart": {
            "id": cart.id,
            "user_id": cart.user_id,
            "status": cart.status,
            "created_at": _format_datetime(cart.created_at),
            "updated_at": _format_datetime(cart.updated_at),
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


def _get_or_create_active_cart(session: Session, user_id: int) -> dict:
    _ensure_user_exists(session, user_id)
    active_cart = session.scalar(
        select(ShoppingCart)
        .where(ShoppingCart.user_id == user_id, ShoppingCart.status == "active")
        .order_by(ShoppingCart.id.desc())
        .limit(1)
    )
    if active_cart is None:
        active_cart = ShoppingCart(user_id=user_id, status="active")
        session.add(active_cart)
        session.flush()
    return _serialize_cart(session, active_cart)


def _profile_payload(session: Session, user: User) -> dict:
    cart_details = _get_or_create_active_cart(session, user.id)
    return {
        "user": _user_summary(user),
        "payment_method": _get_payment_method_summary(session, user.id),
        "cart": {
            "id": cart_details["cart"]["id"],
            "status": cart_details["cart"]["status"],
        },
    }


def authenticate_user(email: str, password: str) -> dict:
    with session_scope() as session:
        normalized_email = _normalize_email(email)
        user = session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not user.is_active:
            raise ValidationError("Invalid email or password.")
        if not verify_password(password, user.password_hash):
            raise ValidationError("Invalid email or password.")
        return _profile_payload(session, user)


def get_user_profile(user_id: int) -> dict:
    with session_scope() as session:
        user = _ensure_user_exists(session, user_id)
        return _profile_payload(session, user)


def get_or_create_active_cart(user_id: int) -> dict:
    with session_scope() as session:
        return _get_or_create_active_cart(session, user_id)


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
    is_default = bool(payment_method.get("is_default", True))

    if not card_brand:
        raise ValidationError("Card brand is required.")
    if card_exp_month < 1 or card_exp_month > 12:
        raise ValidationError("Card expiration month must be between 1 and 12.")
    if card_exp_year < 2000:
        raise ValidationError("Card expiration year is invalid.")

    password_hash = hash_password(password)
    card_last4 = _validate_card_last4(card_number)

    with session_scope() as session:
        existing_user = session.scalar(select(User.id).where(User.email == email))
        if existing_user is not None:
            raise ConflictError("An account with that email already exists.")

        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            billing_address_line1=billing_address_line1,
            billing_address_line2=billing_address_line2.strip() or None,
            billing_city=billing_city,
            billing_state=billing_state,
            billing_postal_code=billing_postal_code,
        )
        session.add(user)
        session.flush()

        payment_record = PaymentMethod(
            user_id=user.id,
            payment_token=payment_token,
            card_brand=card_brand,
            card_last4=card_last4,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            is_default=is_default,
        )
        session.add(payment_record)

        session.add(PasswordHistory(user_id=user.id, password_hash=password_hash))

        cart = ShoppingCart(user_id=user.id, status="active")
        session.add(cart)
        session.flush()

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
            },
            "payment_method": {
                "id": payment_record.id,
                "card_brand": payment_record.card_brand,
                "card_last4": payment_record.card_last4,
                "card_exp_month": payment_record.card_exp_month,
                "card_exp_year": payment_record.card_exp_year,
                "is_default": bool(payment_record.is_default),
            },
            "cart": {
                "id": cart.id,
                "status": cart.status,
            },
        }


def list_dvds(title_search: str = "%", genre: str | None = None, active_only: bool = True) -> list[dict]:
    with session_scope() as session:
        statement = select(Dvd).where(Dvd.title.like(title_search)).order_by(Dvd.title.asc())
        if genre is not None:
            statement = statement.where(Dvd.genre == genre)
        if active_only:
            statement = statement.where(Dvd.is_active.is_(True))
        dvds = list(session.scalars(statement))
        return [_serialize_dvd(dvd) for dvd in dvds]


def get_cart(cart_id: int, current_user_id: int | None = None) -> dict:
    with session_scope() as session:
        cart = _ensure_cart(session, cart_id)
        _ensure_cart_owner(cart, current_user_id)
        _ensure_user_exists(session, cart.user_id)
        return _serialize_cart(session, cart)


def add_item_to_cart(
    cart_id: int,
    dvd_id: int,
    quantity: int = 1,
    current_user_id: int | None = None,
) -> dict:
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    with session_scope() as session:
        cart = _ensure_cart(session, cart_id)
        _ensure_cart_owner(cart, current_user_id)
        if cart.status != "active":
            raise ConflictError("Only active carts can be modified.")

        dvd = _ensure_dvd(session, dvd_id)
        if not dvd.is_active:
            raise ConflictError("This DVD is not available for purchase.")

        existing_item = session.scalar(
            select(ShoppingCartItem).where(
                ShoppingCartItem.cart_id == cart_id,
                ShoppingCartItem.dvd_id == dvd_id,
            )
        )
        existing_quantity = existing_item.quantity if existing_item is not None else 0
        total_quantity = existing_quantity + quantity
        if total_quantity > dvd.available_copies:
            raise ConflictError("Not enough copies are available.")

        if existing_item is None:
            session.add(
                ShoppingCartItem(
                    cart_id=cart_id,
                    dvd_id=dvd_id,
                    quantity=quantity,
                    unit_price_cents=dvd.rental_price_cents,
                )
            )
        else:
            existing_item.quantity = total_quantity

        session.flush()
        return _serialize_cart(session, cart)


def remove_item_from_cart(cart_id: int, item_id: int, current_user_id: int | None = None) -> dict:
    with session_scope() as session:
        cart = _ensure_cart(session, cart_id)
        _ensure_cart_owner(cart, current_user_id)
        if cart.status != "active":
            raise ConflictError("Only active carts can be modified.")

        item = session.scalar(
            select(ShoppingCartItem).where(
                ShoppingCartItem.id == item_id,
                ShoppingCartItem.cart_id == cart_id,
            )
        )
        if item is None:
            raise NotFoundError("Cart item not found.")

        session.delete(item)
        session.flush()
        return _serialize_cart(session, cart)


def checkout_cart(cart_id: int, payment_method_id: int, current_user_id: int | None = None) -> dict:
    with session_scope() as session:
        cart = _ensure_cart(session, cart_id)
        _ensure_cart_owner(cart, current_user_id)
        if cart.status != "active":
            raise ConflictError("This cart has already been checked out or closed.")

        payment_method = _ensure_payment_method(session, payment_method_id)
        if current_user_id is not None and payment_method.user_id != current_user_id:
            raise NotFoundError("Payment method not found.")
        if payment_method.user_id != cart.user_id:
            raise ConflictError("Payment method does not belong to this cart owner.")

        items = _cart_items_with_dvds(session, cart.id)
        if not items:
            raise ConflictError("Cannot checkout an empty cart.")

        subtotal_cents = 0
        for item in items:
            if item.dvd is None:
                raise NotFoundError("A DVD in the cart no longer exists.")
            if item.dvd.available_copies < item.quantity:
                raise ConflictError(f"Not enough copies available for {item.dvd.title}.")
            subtotal_cents += item.quantity * item.unit_price_cents

        tax_cents = int(
            (Decimal(subtotal_cents) * SALES_TAX_RATE).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        total_cents = subtotal_cents + tax_cents

        order = Order(
            user_id=cart.user_id,
            payment_method_id=payment_method_id,
            subtotal_cents=subtotal_cents,
            tax_cents=tax_cents,
            total_cents=total_cents,
            status="placed",
        )
        session.add(order)
        session.flush()

        for item in items:
            total_price_cents = item.quantity * item.unit_price_cents
            session.add(
                OrderItem(
                    order_id=order.id,
                    dvd_id=item.dvd_id,
                    quantity=item.quantity,
                    unit_price_cents=item.unit_price_cents,
                    total_price_cents=total_price_cents,
                )
            )
            item.dvd.available_copies -= item.quantity

        cart.status = "converted"

        next_cart = ShoppingCart(user_id=cart.user_id, status="active")
        session.add(next_cart)
        session.flush()

        return {
            "order_id": order.id,
            "cart_id": cart.id,
            "user_id": cart.user_id,
            "payment_method_id": payment_method_id,
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "subtotal": _cents_to_decimal(subtotal_cents),
            "tax": _cents_to_decimal(tax_cents),
            "total": _cents_to_decimal(total_cents),
            "status": order.status,
            "next_cart_id": next_cart.id,
        }


def get_order_details(order_id: int, current_user_id: int) -> dict:
    with session_scope() as session:
        order = session.scalar(
            select(Order)
            .where(Order.id == order_id, Order.user_id == current_user_id)
            .limit(1)
        )
        if order is None:
            raise NotFoundError("Order not found.")

        rows = list(
            session.scalars(
                select(OrderItem)
                .options(joinedload(OrderItem.dvd))
                .where(OrderItem.order_id == order_id)
                .order_by(OrderItem.id.asc())
            )
        )
        return {
            "order": {
                "id": order.id,
                "user_id": order.user_id,
                "payment_method_id": order.payment_method_id,
                "order_date": _format_datetime(order.order_date),
                "status": order.status,
                "subtotal_cents": order.subtotal_cents,
                "tax_cents": order.tax_cents,
                "total_cents": order.total_cents,
                "subtotal": _cents_to_decimal(order.subtotal_cents),
                "tax": _cents_to_decimal(order.tax_cents),
                "total": _cents_to_decimal(order.total_cents),
            },
            "items": [
                {
                    "dvd_id": row.dvd_id,
                    "title": row.dvd.title,
                    "quantity": row.quantity,
                    "unit_price_cents": row.unit_price_cents,
                    "unit_price": _cents_to_decimal(row.unit_price_cents),
                    "total_price_cents": row.total_price_cents,
                    "total_price": _cents_to_decimal(row.total_price_cents),
                }
                for row in rows
            ],
        }
