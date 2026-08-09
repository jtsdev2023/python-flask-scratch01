import { apiRequest, formatCurrency, hideAlert, setButtonBusy, showAlert } from "./api.js";

const catalogState = {
    cartId: null,
    genres: new Set(),
};

function renderGenres(selectElement) {
    const genres = [...catalogState.genres].sort((a, b) => a.localeCompare(b));
    const currentValue = selectElement.dataset.currentValue || "";
    selectElement.innerHTML = '<option value="">All genres</option>';
    for (const genre of genres) {
        const option = document.createElement("option");
        option.value = genre;
        option.textContent = genre;
        if (genre === currentValue) {
            option.selected = true;
        }
        selectElement.appendChild(option);
    }
}

function createCard(item, feedbackElement) {
    const column = document.createElement("div");
    column.className = "col-md-6 col-xl-4";

    const availability = item.available_copies > 0
        ? `${item.available_copies} available`
        : "Currently unavailable";

    column.innerHTML = `
        <article class="catalog-card card border-0">
            <div class="card-body p-4">
                <div class="d-flex justify-content-between align-items-start gap-3 mb-3">
                    <div>
                        <h2 class="h4 mb-1">${item.title}</h2>
                        <div class="catalog-meta">${item.director || "Unknown director"} · ${item.release_year || "Year not listed"}</div>
                    </div>
                    <span class="price-pill">${formatCurrency(item.rental_price)}</span>
                </div>
                <div class="catalog-meta mb-3">${item.genre || "Uncategorized"}</div>
                <p class="text-secondary flex-grow-1 mb-4">${item.description || "No description provided."}</p>
                <div class="d-flex justify-content-between align-items-center mt-auto gap-3">
                    <span class="status-pill">${availability}</span>
                    <button class="btn btn-dark" type="button">Add to cart</button>
                </div>
            </div>
        </article>
    `;

    const button = column.querySelector("button");
    if (!item.is_active || item.available_copies <= 0) {
        button.disabled = true;
        button.textContent = "Unavailable";
    }

    button.addEventListener("click", async () => {
        setButtonBusy(button, true, "Adding...");
        hideAlert(feedbackElement);
        try {
            if (!catalogState.cartId) {
                const cartData = await apiRequest("/api/me/cart");
                catalogState.cartId = cartData.cart.id;
            }
            await apiRequest(`/api/carts/${catalogState.cartId}/items`, {
                method: "POST",
                body: JSON.stringify({ dvd_id: item.id, quantity: 1 }),
            });
            showAlert(feedbackElement, `${item.title} was added to your cart.`, "success");
            setButtonBusy(button, false);
        } catch (error) {
            showAlert(feedbackElement, error.message);
            setButtonBusy(button, false);
        }
    });

    return column;
}

async function loadCatalog(form, grid, loading, feedback) {
    hideAlert(feedback);
    loading.classList.remove("d-none");
    grid.innerHTML = "";

    const formData = new FormData(form);
    const titleSearch = formData.get("title_search")?.trim() || "";
    const genre = formData.get("genre")?.trim() || "";
    const query = new URLSearchParams();
    if (titleSearch) {
        query.set("title_search", `%${titleSearch}%`);
    }
    if (genre) {
        query.set("genre", genre);
    }

    try {
        const [profile, dvdResponse] = await Promise.all([
            apiRequest("/api/me"),
            apiRequest(`/api/dvds${query.toString() ? `?${query.toString()}` : ""}`),
        ]);
        catalogState.cartId = profile.cart.id;

        const items = dvdResponse.items || [];
        const genreSelect = document.getElementById("genre_filter");
        for (const item of items) {
            if (item.genre) {
                catalogState.genres.add(item.genre);
            }
        }
        genreSelect.dataset.currentValue = genre;
        renderGenres(genreSelect);

        if (!items.length) {
            grid.innerHTML = '<div class="col-12"><div class="surface-card p-4 text-center text-secondary">No DVDs matched your filters.</div></div>';
            loading.classList.add("d-none");
            return;
        }

        for (const item of items) {
            grid.appendChild(createCard(item, feedback));
        }
        loading.classList.add("d-none");
    } catch (error) {
        loading.classList.add("d-none");
        showAlert(feedback, error.message);
    }
}

export function initCatalogPage() {
    const form = document.getElementById("catalog-filter-form");
    const grid = document.getElementById("catalog-grid");
    const loading = document.getElementById("catalog-loading");
    const feedback = document.getElementById("catalog-feedback");
    if (!form || !grid || !loading || !feedback) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await loadCatalog(form, grid, loading, feedback);
    });

    loadCatalog(form, grid, loading, feedback);
}
