# DVD Rental Service - MVP Database Schema

## Design Goal
This schema is intentionally small so the project can be completed within the capstone timeline. It supports the core MVP workflow:

1. Create an account
2. Store a fictional payment method and billing details
3. Browse DVDs
4. Add DVDs to a cart
5. Complete a simulated checkout

Return processing, shipping workflow, refunds, and admin reporting are out of scope for the MVP.

## Tables Overview

### 1. Users Table
Stores customer account and billing contact information.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `email` (String, Unique): Login username
- `password_hash` (String): Password hash using PBKDF2-HMAC-SHA256
- `first_name` (String): Customer first name
- `last_name` (String): Customer last name
- `phone_number` (String): Customer phone number
- `billing_address_line1` (String): Billing street address
- `billing_address_line2` (String, Nullable): Apartment or suite number
- `billing_city` (String): Billing city
- `billing_state` (String): Billing state or province
- `billing_postal_code` (String): Billing ZIP or postal code
- `created_at` (DateTime): Account creation timestamp
- `updated_at` (DateTime): Last update timestamp
- `is_active` (Boolean): Account status

### 2. Payment Methods Table
Stores a fictional payment method for the MVP checkout flow.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `user_id` (Integer, FK): Reference to Users table
- `payment_token` (String): Mock token used by the simulation
- `card_brand` (String): Example values: Visa, Mastercard
- `card_last4` (String): Last four digits only
- `card_exp_month` (Integer): Expiration month
- `card_exp_year` (Integer): Expiration year
- `is_default` (Boolean): Whether this is the user default payment method
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Last update timestamp

**Notes:**
- Do not store a full card number.
- Do not store CVV data.
- This table is only for simulated checkout and college-project purposes.

### 3. DVDs Table
Stores the DVD catalog and inventory.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `title` (String, Indexed): DVD title
- `director` (String): Director name
- `genre` (String, Indexed): Movie genre
- `release_year` (Integer): Release year
- `description` (Text): Movie description
- `rental_price_cents` (Integer): Rental price stored in cents
- `total_copies` (Integer): Total copies in inventory
- `available_copies` (Integer): Copies currently available
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Last update timestamp
- `is_active` (Boolean): Availability status

### 4. Shopping Carts Table
Tracks a user's active cart.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `user_id` (Integer, FK): Reference to Users table
- `status` (String): Example values: active, converted, abandoned
- `created_at` (DateTime): Cart creation timestamp
- `updated_at` (DateTime): Last update timestamp

### 5. Shopping Cart Items Table
Stores DVDs currently in a user's cart.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `cart_id` (Integer, FK): Reference to Shopping Carts table
- `dvd_id` (Integer, FK): Reference to DVDs table
- `quantity` (Integer): Number of copies selected
- `unit_price_cents` (Integer): Price per copy at the time it was added
- `created_at` (DateTime): Item added timestamp
- `updated_at` (DateTime): Last update timestamp

### 6. Orders Table
Records completed simulated checkout transactions.

**Fields:**
- `id` (Integer, PK): Unique order identifier
- `user_id` (Integer, FK): Reference to Users table
- `payment_method_id` (Integer, FK): Reference to Payment Methods table
- `order_date` (DateTime): When checkout was completed
- `subtotal_cents` (Integer): Sum of item prices before tax
- `tax_cents` (Integer): Sales tax amount
- `total_cents` (Integer): Final order total
- `status` (String): Example values: pending, placed, cancelled
- `created_at` (DateTime): Record creation timestamp
- `updated_at` (DateTime): Last update timestamp

### 7. Order Items Table
Stores the DVDs purchased in a completed order.

**Fields:**
- `id` (Integer, PK): Unique identifier
- `order_id` (Integer, FK): Reference to Orders table
- `dvd_id` (Integer, FK): Reference to DVDs table
- `quantity` (Integer): Number of copies purchased
- `unit_price_cents` (Integer): Price per copy at checkout time
- `total_price_cents` (Integer): Quantity multiplied by unit price
- `created_at` (DateTime): Record creation timestamp

## Relationships

```text
Users (1) ──── (Many) Payment Methods
Users (1) ──── (Many) Shopping Carts
Shopping Carts (1) ──── (Many) Shopping Cart Items
Users (1) ──── (Many) Orders
Payment Methods (1) ──── (Many) Orders
Orders (1) ──── (Many) Order Items
DVDs (1) ──── (Many) Shopping Cart Items
DVDs (1) ──── (Many) Order Items
```

## Security And Scope Notes

- Store passwords with a strong one-way hash and per-password salt.
- Do not store raw credit card numbers or CVV values.
- Use a mock payment token or last-four display fields for the fictional checkout flow.
- Keep all payment data fictional and clearly non-production.
- Use integer cents for monetary values to avoid floating-point rounding issues.
- Keep return processing out of the MVP.

## Recommended Indexes

- `users.email` - Fast login lookup
- `dvds.title` - Search by title
- `dvds.genre` - Filter by genre
- `shopping_carts.user_id` - Find a user's active cart
- `shopping_cart_items.cart_id` - Load cart contents
- `orders.user_id` - Load order history
- `order_items.order_id` - Load order details

## MVP Build Order

1. Create the `users` and `payment_methods` tables.
2. Create the `dvds` table and seed the catalog.
3. Add `shopping_carts` and `shopping_cart_items`.
4. Add `orders` and `order_items` for simulated checkout.
5. Implement Python business logic, then Flask routes, then React UI.