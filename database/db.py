"""
SQLite data layer for Spendly.

Exposes:
    get_db()    — returns a SQLite connection with row_factory set
                  and PRAGMA foreign_keys = ON.
    init_db()   — creates the users and expenses tables (idempotent).
    seed_db()   — inserts a demo user and sample expenses (idempotent).

All queries use parameterized SQL. The DB file lives at the project root
as `expense_tracker.db` (matches .gitignore + CLAUDE.md).
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash


# Resolve the DB path relative to this file, not CWD — so the app works
# no matter where it's launched from.
DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "expense_tracker.db")
)


def get_db():
    """Open a new SQLite connection with dict-like rows and FK enforcement."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create users and expenses tables if they don't already exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
        """
    )

    conn.commit()
    conn.close()


def seed_db():
    """
    Insert a demo user and 8 sample expenses.

    Idempotent: returns early if the users table is already populated.
    """
    conn = get_db()
    cur = conn.cursor()

    # Dedupe guard — never insert sample data twice.
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # --- demo user ---
    cur.execute(
        """
        INSERT INTO users (name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        (
            "Demo User",
            "demo@spendly.com",
            generate_password_hash("demo123"),
        ),
    )
    demo_user_id = cur.lastrowid

    # --- 8 sample expenses, all categories represented ---
    sample_expenses = [
        (250.00,  "Food",          "2026-06-02", "Lunch at campus canteen"),
        (180.00,  "Transport",     "2026-06-05", "Auto rickshaw to station"),
        (1500.00, "Bills",         "2026-06-07", "Electricity bill"),
        (420.00,  "Health",        "2026-06-09", "Pharmacy — vitamins"),
        (599.00,  "Entertainment", "2026-06-11", "Movie ticket"),
        (1299.00, "Shopping",      "2026-06-14", "New t-shirt"),
        (80.00,   "Other",         "2026-06-16", "Miscellaneous"),
        (350.00,  "Food",          "2026-06-18", "Dinner with friends"),
    ]

    cur.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(demo_user_id, amount, category, date, description)
         for (amount, category, date, description) in sample_expenses],
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Allow `python database/db.py` to bootstrap the DB standalone.
    init_db()
    seed_db()
    print(f"Database ready at: {DB_PATH}")
