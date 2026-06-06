CREATE TABLE IF NOT EXISTS dvd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    director TEXT,
    genre TEXT,
    release_year INTEGER,
    description TEXT,
    rental_price REAL NOT NULL DEFAULT 0.00 CHECK (rental_price >= 0),
    total_copies INTEGER NOT NULL DEFAULT 0 CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 0
        CHECK (available_copies >= 0 AND available_copies <= total_copies),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),

    CONSTRAINT unique_dvd_title_director_year UNIQUE (title, director, release_year)
);

CREATE INDEX IF NOT EXISTS idx_dvd_title
ON dvd (title);

CREATE INDEX IF NOT EXISTS idx_dvd_genre
ON dvd (genre);

-- Keep updated_at current on any row change.
-- The WHEN guard prevents the trigger from recursing on its own write and
-- lets callers set updated_at explicitly when they need to.
CREATE TRIGGER IF NOT EXISTS trg_dvd_updated_at
AFTER UPDATE ON dvd
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE dvd
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;