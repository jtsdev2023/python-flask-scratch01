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

export function getPageAlert() {
    return document.getElementById("page-alert");
}

export function showAlert(element, message, variant = "danger") {
    if (!element) {
        return;
    }
    element.textContent = message;
    element.className = `alert alert-${variant}`;
    element.classList.remove("d-none");
}

export function hideAlert(element) {
    if (!element) {
        return;
    }
    element.textContent = "";
    element.className = "alert d-none";
}

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

export function formatCurrency(value) {
    return `$${value}`;
}
