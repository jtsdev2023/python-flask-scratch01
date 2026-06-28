import { apiRequest, hideAlert, setButtonBusy, showAlert } from "./api.js";

function formDataToObject(form) {
    return Object.fromEntries(new FormData(form).entries());
}

export function initLogoutButton() {
    const logoutButton = document.querySelector("[data-logout-button]");
    if (!logoutButton) {
        return;
    }

    logoutButton.addEventListener("click", async () => {
        setButtonBusy(logoutButton, true, "Logging out...");
        try {
            await apiRequest("/api/logout", { method: "POST", body: JSON.stringify({}) });
            window.location.href = "/";
        } catch (error) {
            showAlert(document.getElementById("page-alert"), error.message);
            setButtonBusy(logoutButton, false);
        }
    });
}

export function initLoginPage() {
    const form = document.getElementById("login-form");
    const alert = document.getElementById("form-alert");
    const submitButton = form?.querySelector("[data-submit-button]");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alert);
        setButtonBusy(submitButton, true, "Logging in...");
        try {
            const payload = formDataToObject(form);
            await apiRequest("/api/login", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            window.location.href = "/catalog";
        } catch (error) {
            showAlert(alert, error.message);
            setButtonBusy(submitButton, false);
        }
    });
}

export function initRegisterPage() {
    const form = document.getElementById("register-form");
    const alert = document.getElementById("form-alert");
    const submitButton = form?.querySelector("[data-submit-button]");
    if (!form) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alert);
        setButtonBusy(submitButton, true, "Creating account...");

        try {
            const payload = formDataToObject(form);
            const requestBody = {
                email: payload.email,
                password: payload.password,
                first_name: payload.first_name,
                last_name: payload.last_name,
                phone_number: payload.phone_number,
                billing_address_line1: payload.billing_address_line1,
                billing_address_line2: payload.billing_address_line2,
                billing_city: payload.billing_city,
                billing_state: payload.billing_state,
                billing_postal_code: payload.billing_postal_code,
                payment_method: {
                    card_number: payload.card_number,
                    card_brand: payload.card_brand,
                    card_exp_month: Number(payload.card_exp_month),
                    card_exp_year: Number(payload.card_exp_year),
                },
            };

            await apiRequest("/api/register", {
                method: "POST",
                body: JSON.stringify(requestBody),
            });
            window.location.href = "/catalog";
        } catch (error) {
            showAlert(alert, error.message);
            setButtonBusy(submitButton, false);
        }
    });
}
