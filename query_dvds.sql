-- query_dvds.sql
-- Query active DVD records from the dvd table.
--
-- This file is designed to be read by a Python script and executed with
-- sqlite3 using named parameters.
--
-- Expected Python parameters:
--   :title_search - partial DVD title search, for example "%matrix%"
--   :genre        - genre filter, for example "Science Fiction"
--   :active_only  - 1 for active DVDs only, 0 to include inactive DVDs
--
-- Example Python params:
-- {
--     "title_search": "%matrix%",
--     "genre": "Science Fiction",
--     "active_only": 1
-- }

SELECT
    id,
    title,
    director,
    genre,
    release_year,
    description,
    rental_price,
    total_copies,
    available_copies,
    created_at,
    updated_at,
    is_active
FROM dvd
WHERE
    title LIKE :title_search
    AND (:genre IS NULL OR genre = :genre)
    AND (:active_only = 0 OR is_active = 1)
ORDER BY
    title ASC;