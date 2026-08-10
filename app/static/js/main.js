import { initCatalogPage } from "./catalog.js";
import { initCartPage } from "./cart.js";
import { initLoginPage, initLogoutButton, initRegisterPage } from "./auth.js";
import { initOrderPage } from "./order.js";

const initializers = {
    login: initLoginPage,
    register: initRegisterPage,
    catalog: initCatalogPage,
    cart: initCartPage,
    order: initOrderPage,
};

// runs logout and initializer for current page
window.addEventListener("DOMContentLoaded", () => {
    initLogoutButton();
    const pageName = document.body.dataset.page;
    const initPage = initializers[pageName];
    if (initPage) {
        initPage();
    }
});
