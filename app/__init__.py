import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from .db import DEFAULT_DATABASE_URL, init_app
from .python_db import ensure_database_ready
from .services import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
    add_item_to_cart,
    authenticate_user,
    checkout_cart,
    create_user,
    get_cart,
    get_or_create_active_cart,
    get_order_details,
    get_user_profile,
    list_dvds,
    remove_item_from_cart,
)


# builds and configures flask application instance
def create_app(config: dict | None = None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        DATABASE_URL=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    if config:
        app.config.update(config)

    init_app(app)
    ensure_database_ready(app)

    # returns the logged-in user's id or raises api route error
    def _require_session_user_id() -> int:
        user_id = session.get("user_id")
        if user_id is None:
            raise AuthenticationError("Authentication required.")
        return int(user_id)

    # returns the logged-in user's id or redirects to login for page route
    def _require_page_user_id():
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("login_page"))
        return int(user_id)

    # exposes auth status to each rendered template
    @app.context_processor
    def inject_template_globals():
        return {"is_authenticated": session.get("user_id") is not None}

    # maps service-layer exceptions to matching http status code
    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        if isinstance(error, AuthenticationError):
            status_code = 401
        elif isinstance(error, ValidationError):
            status_code = 400
        elif isinstance(error, NotFoundError):
            status_code = 404
        elif isinstance(error, ConflictError):
            status_code = 409
        else:
            status_code = 500
        return jsonify({"error": str(error)}), status_code

    # redirects the root url to the homepage
    @app.get("/")
    def root_redirect():
        return redirect(url_for("home_page"))

    # renders the homepage
    @app.get("/home")
    def home_page():
        return render_template("index.html", page_title="Home", page_name="home")

    # renders the login page
    @app.get("/login")
    def login_page():
        return render_template("login.html", page_title="Login", page_name="login")

    # renders the registration page
    @app.get("/register")
    def register_page():
        return render_template("register.html", page_title="Register", page_name="register")

    # renders the dvd catalog page for logged-in users
    @app.get("/catalog")
    def catalog_page():
        page_user_id = _require_page_user_id()
        if not isinstance(page_user_id, int):
            return page_user_id
        return render_template("catalog.html", page_title="Catalog", page_name="catalog")

    # renders the shopping cart page for logged-in users
    @app.get("/cart")
    def cart_page():
        page_user_id = _require_page_user_id()
        if not isinstance(page_user_id, int):
            return page_user_id
        return render_template("cart.html", page_title="Your Cart", page_name="cart")

    # renders the order detail page for logged-in users
    @app.get("/orders/<int:order_id>")
    def order_page(order_id: int):
        page_user_id = _require_page_user_id()
        if not isinstance(page_user_id, int):
            return page_user_id
        return render_template(
            "order_detail.html",
            page_title=f"Order #{order_id}",
            page_name="order",
            order_id=order_id,
        )

    # health check endpoint
    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok"})

    # creates a new account and starts a session
    @app.post("/api/register")
    def register_user():
        payload = request.get_json(silent=True) or {}
        result = create_user(payload)
        session["user_id"] = result["user"]["id"]
        return jsonify(result), 201

    # authenticates a user and starts a session
    @app.post("/api/login")
    def login_user():
        payload = request.get_json(silent=True) or {}
        email = payload.get("email")
        password = payload.get("password")
        if not email or not password:
            raise ValidationError("email and password are required.")
        result = authenticate_user(str(email), str(password))
        session["user_id"] = result["user"]["id"]
        return jsonify(result)

    # clears the current session
    @app.post("/api/logout")
    def logout_user():
        session.clear()
        return jsonify({"message": "Logged out."})

    # returns the logged-in user's profile
    @app.get("/api/me")
    def current_user_profile():
        user_id = _require_session_user_id()
        return jsonify(get_user_profile(user_id))

    # returns the logged-in user's active cart
    @app.get("/api/me/cart")
    def current_user_cart():
        user_id = _require_session_user_id()
        return jsonify(get_or_create_active_cart(user_id))

    # returns the dvd catalog... can be filtered by title/genre
    @app.get("/api/dvds")
    def browse_dvds():
        title_search = request.args.get("title_search", "%")
        genre = request.args.get("genre")
        active_only = request.args.get("active_only", "1") not in {"0", "false", "False"}
        return jsonify({"items": list_dvds(title_search=title_search, genre=genre, active_only=active_only)})

    # returns a cart's contents and computed totals
    @app.get("/api/carts/<int:cart_id>")
    def view_cart(cart_id: int):
        user_id = _require_session_user_id()
        return jsonify(get_cart(cart_id, current_user_id=user_id))

    # adds a dvd to a cart
    @app.post("/api/carts/<int:cart_id>/items")
    def add_cart_item(cart_id: int):
        user_id = _require_session_user_id()
        payload = request.get_json(silent=True) or {}
        dvd_id = payload.get("dvd_id")
        quantity = int(payload.get("quantity", 1))
        if dvd_id is None:
            raise ValidationError("dvd_id is required.")
        return jsonify(add_item_to_cart(cart_id, int(dvd_id), quantity, current_user_id=user_id)), 201

    # removes an item from a cart
    @app.delete("/api/carts/<int:cart_id>/items/<int:item_id>")
    def delete_cart_item(cart_id: int, item_id: int):
        user_id = _require_session_user_id()
        return jsonify(remove_item_from_cart(cart_id, item_id, current_user_id=user_id))

    # checks out a cart and creates an order
    @app.post("/api/checkout")
    def checkout():
        user_id = _require_session_user_id()
        payload = request.get_json(silent=True) or {}
        cart_id = payload.get("cart_id")
        payment_method_id = payload.get("payment_method_id")
        if cart_id is None or payment_method_id is None:
            raise ValidationError("cart_id and payment_method_id are required.")
        return jsonify(checkout_cart(int(cart_id), int(payment_method_id), current_user_id=user_id)), 201

    # returns order details
    @app.get("/api/orders/<int:order_id>")
    def view_order(order_id: int):
        user_id = _require_session_user_id()
        return jsonify(get_order_details(order_id, current_user_id=user_id))

    return app


