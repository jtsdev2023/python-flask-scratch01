import { apiRequest, formatCurrency, hideAlert, showAlert } from "./api.js";

// renders subtotal/tax/total summary list for order
function renderSummary(target, order) {
    target.innerHTML = `
        <dt>Subtotal</dt><dd>${formatCurrency(order.subtotal)}</dd>
        <dt>Tax</dt><dd>${formatCurrency(order.tax)}</dd>
        <dt>Total</dt><dd>${formatCurrency(order.total)}</dd>
    `;
}

// loads and renders single order details
export function initOrderPage() {
    const orderId = document.body.dataset.orderId;
    const loading = document.getElementById("order-loading");
    const content = document.getElementById("order-content");
    const items = document.getElementById("order-items");
    const summary = document.getElementById("order-summary");
    const feedback = document.getElementById("order-feedback");
    const orderNumber = document.getElementById("order-number");
    const orderDate = document.getElementById("order-date");
    const orderStatus = document.getElementById("order-status");

    if (!orderId || !loading || !content || !items || !summary || !feedback) {
        return;
    }

    // fetches order and populates page
    async function loadOrder() {
        hideAlert(feedback);
        try {
            const data = await apiRequest(`/api/orders/${orderId}`);
            loading.classList.add("d-none");
            content.classList.remove("d-none");
            orderNumber.textContent = `Order #${data.order.id}`;
            orderDate.textContent = `Placed on ${data.order.order_date}`;
            orderStatus.textContent = data.order.status;
            renderSummary(summary, data.order);
            items.innerHTML = "";

            for (const item of data.items) {
                const row = document.createElement("article");
                row.className = "order-item";
                row.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start gap-3">
                        <div>
                            <h2 class="h5 mb-1">${item.title}</h2>
                            <div class="text-secondary small">Quantity: ${item.quantity} · Unit price: ${formatCurrency(item.unit_price)}</div>
                        </div>
                        <strong>${formatCurrency(item.total_price)}</strong>
                    </div>
                `;
                items.appendChild(row);
            }
        } catch (error) {
            loading.classList.add("d-none");
            showAlert(feedback, error.message);
        }
    }

    loadOrder();
}
