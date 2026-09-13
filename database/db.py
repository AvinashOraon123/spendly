"""SQLite helpers for the Spendly data layer."""
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "spendly.db",
)


def get_db(path=None):
    """Return a SQLite connection with row factory + FK enforcement on.

    If `path` is provided, use it instead of the default DB_PATH.
    """
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables if they don't exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_user(name: str, email: str, password: str) -> int:
    """Insert a new user. Returns new user's id.

    Raises:
        sqlite3.IntegrityError: if email already exists.
    """
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def find_user_by_id(user_id: int):
    """Return the user row matching `user_id`, or None if no match."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return row
    finally:
        conn.close()


def find_user_by_email(email: str):
    """Return the user row matching `email`, or None if no match.

    The caller is expected to pass an email that is already trimmed and
    lowercased so it lines up with what `create_user` stored.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return row
    finally:
        conn.close()


def _date_clause(date_from: str | None, date_to: str | None) -> tuple[list[str], list]:
    """Return (extra_where_clauses, extra_params) for an optional date range.

    Both bounds are inclusive. The caller is responsible for combining with
    its own WHERE clause (typically via " AND ").
    """
    clauses: list[str] = []
    params: list = []
    if date_from is not None:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to is not None:
        clauses.append("date <= ?")
        params.append(date_to)
    return clauses, params


def get_total_spent(
    user_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> float:
    """Return the sum of all expense amounts for `user_id`.

    When both `date_from` and `date_to` are provided, only expenses whose
    `date` falls inclusively within the range are summed. Returns 0.0 when
    the user has no matching expenses.
    """
    extra_clauses, extra_params = _date_clause(date_from, date_to)
    where = " AND ".join(["user_id = ?", *extra_clauses])
    conn = get_db()
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE {where}",
            [user_id, *extra_params],
        ).fetchone()
        return float(row[0])
    finally:
        conn.close()


def get_transaction_count(
    user_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    """Return the number of expenses recorded for `user_id`.

    When `date_from` / `date_to` are provided, only expenses within that
    inclusive range are counted.
    """
    extra_clauses, extra_params = _date_clause(date_from, date_to)
    where = " AND ".join(["user_id = ?", *extra_clauses])
    conn = get_db()
    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM expenses WHERE {where}",
            [user_id, *extra_params],
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def get_top_category(
    user_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Return the category with the highest total spend for `user_id`.

    When `date_from` / `date_to` are provided, only expenses within that
    inclusive range are considered. Returns the category name as a string,
    or None if the user has no matching expenses.
    """
    extra_clauses, extra_params = _date_clause(date_from, date_to)
    where = " AND ".join(["user_id = ?", *extra_clauses])
    conn = get_db()
    try:
        row = conn.execute(
            f"SELECT category FROM expenses WHERE {where} "
            "GROUP BY category "
            "ORDER BY SUM(amount) DESC, category ASC "
            "LIMIT 1",
            [user_id, *extra_params],
        ).fetchone()
        return row["category"] if row else None
    finally:
        conn.close()


def list_recent_transactions(
    user_id: int,
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list:
    """Return up to `limit` of the user's most recent expenses.

    Sorted newest first by date, then by id (insertion order) as a tiebreaker.
    When `date_from` / `date_to` are provided, only expenses within that
    inclusive range are returned. Each entry is a plain dict with keys:
    date, description, category, amount.
    """
    extra_clauses, extra_params = _date_clause(date_from, date_to)
    where = " AND ".join(["user_id = ?", *extra_clauses])
    conn = get_db()
    try:
        rows = conn.execute(
            f"SELECT id, date, description, category, amount "
            f"FROM expenses WHERE {where} "
            "ORDER BY date DESC, id DESC "
            "LIMIT ?",
            [user_id, *extra_params, limit],
        ).fetchall()
        return [
            {
                "id": row["id"],
                "date": row["date"],
                "description": row["description"] or "",
                "category": row["category"],
                "amount": float(row["amount"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_category_breakdown(
    user_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list:
    """Return per-category spend totals for `user_id`, with percentage shares.

    Sorted by total descending. Each entry is a dict with keys:
        name   — category name (str)
        total  — total spend in that category (float)
        percent — integer share of total spend (0–100), with the largest
                  category absorbing the rounding remainder so percentages
                  sum to <=100.

    When `date_from` / `date_to` are provided, only expenses within that
    inclusive range are aggregated. Returns an empty list when the user
    has no matching expenses.
    """
    extra_clauses, extra_params = _date_clause(date_from, date_to)
    where = " AND ".join(["user_id = ?", *extra_clauses])
    conn = get_db()
    try:
        rows = conn.execute(
            f"SELECT category, SUM(amount) AS total "
            f"FROM expenses WHERE {where} "
            "GROUP BY category "
            "ORDER BY total DESC",
            [user_id, *extra_params],
        ).fetchall()
        if not rows:
            return []

        grand_total = sum(float(row["total"]) for row in rows)
        if grand_total <= 0:
            return [{"name": row["category"], "total": 0.0, "percent": 0}
                    for row in rows]

        breakdown = []
        assigned = 0
        for index, row in enumerate(rows):
            name = row["category"]
            total = float(row["total"])
            if index == 0:
                # Largest category absorbs the rounding remainder.
                percent = round((total / grand_total) * 100)
            else:
                percent = int((total / grand_total) * 100)
                assigned += percent
            breakdown.append({"name": name, "total": total, "percent": percent})

        return breakdown
    finally:
        conn.close()


def insert_expense(user_id: int, amount: float, category: str, date: str, description: str | None):
    """Insert a new expense. Returns new expense's id."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id: int, user_id: int):
    """Return the expense row matching `expense_id` and `user_id`, or None if no match."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
        return row
    finally:
        conn.close()


def update_expense(expense_id: int, user_id: int, amount: float, category: str, date: str, description: str | None):
    """Update an existing expense. Scoped to `user_id` for safety."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert demo user + 8 sample expenses once. Idempotent."""
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cur.lastrowid

        sample_expenses = [
            (user_id, 12.50, "Food",          "2026-08-02", "Lunch at the corner cafe"),
            (user_id, 45.00, "Transport",     "2026-08-04", "Weekly metro card top-up"),
            (user_id, 89.99, "Bills",         "2026-08-05", "Internet bill"),
            (user_id, 24.30, "Health",        "2026-08-08", "Pharmacy restock"),
            (user_id, 15.00, "Entertainment", "2026-08-10", "Movie tickets"),
            (user_id, 67.40, "Shopping",      "2026-08-12", "New running shoes"),
            (user_id, 9.99,  "Other",         "2026-08-15", "Cloud backup subscription"),
            (user_id, 22.75, "Food",          "2026-08-17", "Dinner with friends"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            sample_expenses,
        )
        conn.commit()
    finally:
        conn.close()
