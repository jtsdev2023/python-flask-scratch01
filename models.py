from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampCLS:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class User(TimestampCLS, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_active IN (0, 1)", name="check_users_is_active_boolean"),
        Index("index_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    billing_address_line1: Mapped[str] = mapped_column(String, nullable=False)
    billing_address_line2: Mapped[Optional[str]] = mapped_column(String)
    billing_city: Mapped[str] = mapped_column(String, nullable=False)
    billing_state: Mapped[str] = mapped_column(String, nullable=False)
    billing_postal_code: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    password_history_entries: Mapped[list["PasswordHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    shopping_carts: Mapped[list["ShoppingCart"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class PasswordHistory(Base):
    __tablename__ = "password_history"
    __table_args__ = (
        UniqueConstraint("user_id", "password_hash", name="unique_user_password_hash"),
        Index("index_password_history_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    user: Mapped[User] = relationship(back_populates="password_history_entries")


class PaymentMethod(TimestampCLS, Base):
    __tablename__ = "payment_methods"
    __table_args__ = (
        CheckConstraint("length(card_last4) = 4", name="check_payment_methods_card_last4_length"),
        CheckConstraint("card_exp_month BETWEEN 1 AND 12", name="check_payment_methods_exp_month"),
        CheckConstraint("card_exp_year >= 2000", name="check_payment_methods_exp_year"),
        CheckConstraint("is_default IN (0, 1)", name="check_payment_methods_is_default_boolean"),
        Index("index_payment_methods_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    payment_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    card_brand: Mapped[str] = mapped_column(String, nullable=False)
    card_last4: Mapped[str] = mapped_column(String, nullable=False)
    card_exp_month: Mapped[int] = mapped_column(Integer, nullable=False)
    card_exp_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    user: Mapped[User] = relationship(back_populates="payment_methods")
    orders: Mapped[list["Order"]] = relationship(back_populates="payment_method")


class Dvd(TimestampCLS, Base):
    __tablename__ = "dvds"
    __table_args__ = (
        CheckConstraint("rental_price_cents >= 0", name="check_dvds_rental_price_nonnegative"),
        CheckConstraint("total_copies >= 0", name="check_dvds_total_copies_nonnegative"),
        CheckConstraint(
            "available_copies >= 0 AND available_copies <= total_copies",
            name="check_dvds_available_copies_range",
        ),
        CheckConstraint("is_active IN (0, 1)", name="check_dvds_is_active_boolean"),
        UniqueConstraint("title", "director", "release_year", name="unique_dvd_title_director_year"),
        Index("index_dvds_title", "title"),
        Index("index_dvds_genre", "genre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    director: Mapped[Optional[str]] = mapped_column(String)
    genre: Mapped[Optional[str]] = mapped_column(String)
    release_year: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rental_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    available_copies: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    cart_items: Mapped[list["ShoppingCartItem"]] = relationship(back_populates="dvd")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="dvd")


class ShoppingCart(TimestampCLS, Base):
    __tablename__ = "shopping_carts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'converted', 'abandoned')",
            name="check_shopping_carts_status_valid",
        ),
        Index("index_shopping_carts_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    user: Mapped[User] = relationship(back_populates="shopping_carts")
    items: Mapped[list["ShoppingCartItem"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
    )


class ShoppingCartItem(TimestampCLS, Base):
    __tablename__ = "shopping_cart_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_items_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="check_cart_items_unit_price_nonnegative"),
        UniqueConstraint("cart_id", "dvd_id", name="unique_cart_dvd"),
        Index("index_cart_items_cart_id", "cart_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_carts.id", ondelete="CASCADE"),
        nullable=False,
    )
    dvd_id: Mapped[int] = mapped_column(
        ForeignKey("dvds.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    cart: Mapped[ShoppingCart] = relationship(back_populates="items")
    dvd: Mapped[Dvd] = relationship(back_populates="cart_items")


class Order(TimestampCLS, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal_cents >= 0", name="check_orders_subtotal_nonnegative"),
        CheckConstraint("tax_cents >= 0", name="check_orders_tax_nonnegative"),
        CheckConstraint("total_cents >= 0", name="check_orders_total_nonnegative"),
        CheckConstraint(
            "status IN ('pending', 'placed', 'cancelled')",
            name="check_orders_status_valid",
        ),
        Index("index_orders_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_method_id: Mapped[int] = mapped_column(
        ForeignKey("payment_methods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="placed",
        server_default=text("'placed'"),
    )

    user: Mapped[User] = relationship(back_populates="orders")
    payment_method: Mapped[PaymentMethod] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_items_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="check_order_items_unit_price_nonnegative"),
        CheckConstraint("total_price_cents >= 0", name="check_order_items_total_nonnegative"),
        Index("index_order_items_order_id", "order_id"),
        Index("index_order_items_dvd_id", "dvd_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    dvd_id: Mapped[int] = mapped_column(
        ForeignKey("dvds.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    order: Mapped[Order] = relationship(back_populates="items")
    dvd: Mapped[Dvd] = relationship(back_populates="order_items")
