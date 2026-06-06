INSERT OR IGNORE INTO dvd (
    title,
    director,
    genre,
    release_year,
    description,
    rental_price,
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
    :rental_price,
    :total_copies,
    :available_copies,
    :is_active
);
