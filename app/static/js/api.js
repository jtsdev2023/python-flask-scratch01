// parses fetch response body as json... allow empty/invalid bodies
async function parseJson(response) {
    const text = await response.text();
    if (!text) {
        return {};
    }
    try {
        return JSON.parse(text);
    } catch {
        return {};
    }
}

// sends json fetch request and redirect to login on http 401
export async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const data = await parseJson(response);

    if (!response.ok) {
        const error = {
            status: response.status,
            message: data.error || "Something went wrong.",
            data,
        };
        if (response.status === 401) {
            window.location.href = "/login";
        }
        throw error;
    }

    return data;
}

// returns shared page-level alert element
export function getPageAlert() {
    return document.getElementById("page-alert");
}

// shows alert message w/ bootstrap variant style
export function showAlert(element, message, variant = "danger") {
    if (!element) {
        return;
    }
    element.textContent = message;
    element.className = `alert alert-${variant}`;
    element.classList.remove("d-none");
}

// clears and hides alert element
export function hideAlert(element) {
    if (!element) {
        return;
    }
    element.textContent = "";
    element.className = "alert d-none";
}

// disables a button and swaps label while action is in progress
export function setButtonBusy(button, isBusy, busyText = "Working...") {
    if (!button) {
        return;
    }
    if (!button.dataset.defaultText) {
        button.dataset.defaultText = button.textContent;
    }
    button.disabled = isBusy;
    button.textContent = isBusy ? busyText : button.dataset.defaultText;
}

// format decimal price string as currency
export function formatCurrency(value) {
    return `$${value}`;
}
