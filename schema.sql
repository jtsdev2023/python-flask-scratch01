
CREATE TABLE IF NOT EXISTS dvd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    director TEXT,
    genre TEXT,
    release_year INTEGER,
    description TEXT,
    rental_price REAL NOT NULL DEFAULT 0.00,
    total_copies INTEGER NOT NULL DEFAULT 0,
    available_copies INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT FALSE CHECK (is_active IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_dvd_title
ON dvd (title);

CREATE INDEX IF NOT EXISTS idx_dvd_genre
ON dvd (genre);
