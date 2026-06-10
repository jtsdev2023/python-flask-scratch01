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