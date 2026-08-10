import { apiRequest, formatCurrency, hideAlert, setButtonBusy, showAlert } from "./api.js";

const cartState = {
    cartId: null,
    paymentMethodId: null,
};

// renders subtotal/tax/total summary list
function renderSummary(target, summary) {
    target.innerHTML = `
        <dt>Subtotal</dt><dd>${formatCurrency(summary.subtotal)}</dd>
        <dt>Tax</dt><dd>${formatCurrency(summary.tax)}</dd>
        <dt>Total</dt><dd>${formatCurrency(summary.total)}</dd>
    `;
}

// renders each cart line item w/ remove button
function renderCartItems(items, container, feedback, refreshFn) {
    container.innerHTML = "";
    for (const item of items) {
        const row = document.createElement("article");
        row.className = "cart-item d-flex flex-column flex-md-row justify-content-between gap-3";
        row.innerHTML = `
            <div>
                <h2 class="h5 mb-1">${item.title}</h2>
                <div class="text-secondary mb-2">${item.genre || "Uncategorized"} · ${item.release_year || "Year not listed"}</div>
                <div class="small text-secondary">Quantity: ${item.quantity} · Unit price: ${formatCurrency(item.unit_price)}</div>
            </div>
            <div class="d-flex flex-column align-items-md-end gap-2">
                <strong>${formatCurrency(item.total_price)}</strong>
                <button class="btn btn-outline-dark btn-sm" type="button">Remove</button>
            </div>
        `;

        const button = row.querySelector("button");
        button.addEventListener("click", async () => {
            setButtonBusy(button, true, "Removing...");
            hideAlert(feedback);
            try {
                const updatedCart = await apiRequest(`/api/carts/${cartState.cartId}/items/${item.id}`, {
                    method: "DELETE",
                });
                await refreshFn(updatedCart);
                showAlert(feedback, `${item.title} was removed from your cart.`, "success");
            } catch (error) {
                showAlert(feedback, error.message);
                setButtonBusy(button, false);
            }
        });

        container.appendChild(row);
    }
}

// loads cart page... renders contents w/ checkout
export function initCartPage() {
    const loading = document.getElementById("cart-loading");
    const emptyState = document.getElementById("cart-empty");
    const itemsContainer = document.getElementById("cart-items");
    const summary = document.getElementById("cart-summary");
    const feedback = document.getElementById("cart-feedback");
    const checkoutButton = document.getElementById("checkout-button");
    if (!loading || !emptyState || !itemsContainer || !summary || !feedback || !checkoutButton) {
        return;
    }

    // renders current cart state... toggling empty-cart view
    async function renderCart(cartData) {
        cartState.cartId = cartData.cart.id;
        loading.classList.add("d-none");
        renderSummary(summary, cartData.summary);

        if (!cartData.items.length) {
            emptyState.classList.remove("d-none");
            itemsContainer.classList.add("d-none");
            itemsContainer.innerHTML = "";
            checkoutButton.disabled = true;
            return;
        }

        emptyState.classList.add("d-none");
        itemsContainer.classList.remove("d-none");
        checkoutButton.disabled = false;
        renderCartItems(cartData.items, itemsContainer, feedback, renderCart);
    }

    // fetches profile and active cart... then renders cart
    async function loadCart() {
        hideAlert(feedback);
        try {
            const [profile, cartData] = await Promise.all([
                apiRequest("/api/me"),
                apiRequest("/api/me/cart"),
            ]);
            cartState.paymentMethodId = profile.payment_method?.id || null;
            await renderCart(cartData);
        } catch (error) {
            loading.classList.add("d-none");
            showAlert(feedback, error.message);
        }
    }

    checkoutButton.addEventListener("click", async () => {
        if (!cartState.cartId || !cartState.paymentMethodId) {
            showAlert(feedback, "Unable to locate an active cart or payment method for checkout.");
            return;
        }

        setButtonBusy(checkoutButton, true, "Processing...");
        hideAlert(feedback);
        try {
            const order = await apiRequest("/api/checkout", {
                method: "POST",
                body: JSON.stringify({
                    cart_id: cartState.cartId,
                    payment_method_id: cartState.paymentMethodId,
                }),
            });
            window.location.href = `/orders/${order.order_id}`;
        } catch (error) {
            showAlert(feedback, error.message);
            setButtonBusy(checkoutButton, false);
        }
    });

    loadCart();
}
