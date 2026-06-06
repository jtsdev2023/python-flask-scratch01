from flask import Flask, jsonify, request

from services import (
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
    add_item_to_cart,
    checkout_cart,
    create_user,
    get_cart,
    list_dvds,
    remove_item_from_cart,
)


def create_app():
    app = Flask(__name__)

    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        if isinstance(error, ValidationError):
            status_code = 400
        elif isinstance(error, NotFoundError):
            status_code = 404
        elif isinstance(error, ConflictError):
            status_code = 409
        else:
            status_code = 500
        return jsonify({"error": str(error)}), status_code

    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.post("/api/register")
    def register_user():
        payload = request.get_json(silent=True) or {}
        result = create_user(payload)
        return jsonify(result), 201

    @app.get("/api/dvds")
    def browse_dvds():
        title_search = request.args.get("title_search", "%")
        genre = request.args.get("genre")
        active_only = request.args.get("active_only", "1") not in {"0", "false", "False"}
        return jsonify({"items": list_dvds(title_search=title_search, genre=genre, active_only=active_only)})

    @app.get("/api/carts/<int:cart_id>")
    def view_cart(cart_id: int):
        return jsonify(get_cart(cart_id))

    @app.post("/api/carts/<int:cart_id>/items")
    def add_cart_item(cart_id: int):
        payload = request.get_json(silent=True) or {}
        dvd_id = payload.get("dvd_id")
        quantity = int(payload.get("quantity", 1))
        if dvd_id is None:
            raise ValidationError("dvd_id is required.")
        return jsonify(add_item_to_cart(cart_id, int(dvd_id), quantity)), 201

    @app.delete("/api/carts/<int:cart_id>/items/<int:item_id>")
    def delete_cart_item(cart_id: int, item_id: int):
        return jsonify(remove_item_from_cart(cart_id, item_id))

    @app.post("/api/checkout")
    def checkout():
        payload = request.get_json(silent=True) or {}
        cart_id = payload.get("cart_id")
        payment_method_id = payload.get("payment_method_id")
        if cart_id is None or payment_method_id is None:
            raise ValidationError("cart_id and payment_method_id are required.")
        return jsonify(checkout_cart(int(cart_id), int(payment_method_id))), 201

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)