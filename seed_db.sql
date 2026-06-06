INSERT OR IGNORE INTO dvds (
    title,
    director,
    genre,
    release_year,
    description,
    rental_price_cents,
    total_copies,
    available_copies,
    is_active
)
VALUES (
    :title,
    :director,
    :genre,
    :release_year,
    :description,
    :rental_price_cents,
    :total_copies,
    :available_copies,
    :is_active
);
