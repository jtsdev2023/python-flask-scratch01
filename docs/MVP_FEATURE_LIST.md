# MVP Feature List

## Project Goal
Build a focused mail-order DVD rental web application that supports account creation, DVD browsing, cart management, and a simulated checkout flow.

## In Scope for MVP

### 1. User Account Creation
- Users can register with an email address as their username.
- Users must create a password that meets reasonable security requirements.
- The application should enforce a minimum password length.
- The application should enforce basic password complexity rules.
- The application should prevent password reuse.
- Users must provide a credit card for payment setup during registration.
- Users must provide a billing address.
- Users must provide a phone number.
- All payment and contact information will be fictitious for the purposes of this college project.

### 2. DVD Browsing
- Registered users can view the DVD catalog.
- Users can browse available DVDs after account creation.
- Users can view basic DVD details such as title, genre, description, release year, and rental price.

### 3. Shopping Cart
- Users can select DVDs from the catalog.
- Users can add selected DVDs to their shopping cart.
- Users can view the items currently in their cart.
- Users can remove items from their cart before checkout.

### 4. Simulated Checkout
- Users can review cart contents before checkout.
- Users can complete a simulated checkout process.
- The application can record that an order was placed.
- The application can reduce available inventory after checkout.
- The checkout flow does not need to connect to a real payment processor.

## Out of Scope for MVP
- DVD returns.
- Real payment processing.
- Shipment tracking.
- Refund handling.
- Admin dashboards and advanced reporting.
- Recommendation engines.
- Multi-address shipping support.

## Suggested Build Order
1. Finalize the database schema for users, payment details, carts, and orders.
2. Build the Python business logic around account creation, catalog browsing, cart updates, and checkout.
3. Add a minimal Flask API on top of the business logic.
4. Build the React frontend against the stable API endpoints.

## Notes
- Keep the MVP intentionally small so the database design and core workflow are complete within the 9-week timeline.
- If scope starts to expand, prioritize account creation, browsing, cart management, and checkout over any return or fulfillment features.