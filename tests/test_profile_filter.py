"""Tests for the date-range filter on /profile (Step 6)."""
import os
import sqlite3
import tempfile

import pytest


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="session")
def _db_path():
    """Create a temp SQLite DB and patch DB_PATH before app import."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    import database.db as db_mod
    db_mod.DB_PATH = path
    yield path
    os.unlink(path)


@pytest.fixture(scope="session")
def app(_db_path):
    """Build the Flask app against the temp DB and initialize the schema."""
    from app import app as flask_app
    from database.db import init_db
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        init_db()
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_with_expenses(app):
    """One user with 6 expenses spanning 12 months — predictable sums."""
    from database.db import create_user, get_db
    user_id = create_user("Tester", "tester@example.com", "Password123!")

    rows = [
        (user_id, 10.00, "Food",          "2026-08-20", "Lunch"),
        (user_id, 25.00, "Transport",     "2026-08-15", "Train"),
        (user_id, 90.00, "Bills",         "2026-07-10", "Electricity"),
        (user_id, 40.00, "Food",          "2026-06-04", "Groceries"),
        (user_id, 60.00, "Entertainment", "2026-05-12", "Concert"),
        (user_id, 12.00, "Other",         "2025-12-01", "Gift"),
    ]
    conn = get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return user_id


@pytest.fixture()
def logged_in(client, user_with_expenses):
    with client.session_transaction() as s:
        s["user_id"] = user_with_expenses
    return client


# ------------------------------------------------------------------ #
# Helpers (mirror the app's date math so tests stay self-contained)   #
# ------------------------------------------------------------------ #

def _months_ago(d, n):
    year = d.year
    month = d.month - n
    while month <= 0:
        month += 12
        year -= 1
    return d.replace(year=year, month=month)


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_no_params_is_unfiltered(logged_in):
    r = logged_in.get("/profile")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # 6 seeded expenses; sum = 10+25+90+40+60+12 = 237.00
    assert "237.00" in body
    # All Time pill should be active when no params
    assert 'href="/profile"' in body
    assert ">All Time<" in body


def test_this_month_preset(logged_in):
    from datetime import date
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    today_iso = today.isoformat()

    r = logged_in.get(f"/profile?date_from={month_start}&date_to={today_iso}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Only the two August expenses: 10 + 25 = 35
    assert "35.00" in body
    # Active pill is highlighted
    assert "is-active" in body
    assert "This Month" in body


def test_last_3_months_preset(logged_in):
    from datetime import date
    today = date.today()
    r = logged_in.get(
        f"/profile?date_from={_months_ago(today, 3).isoformat()}&date_to={today.isoformat()}"
    )
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # August (35) + July (90) = 125 (June 4 is older than the 3-month window)
    assert "125.00" in body


def test_last_6_months_preset(logged_in):
    from datetime import date
    today = date.today()
    r = logged_in.get(
        f"/profile?date_from={_months_ago(today, 6).isoformat()}&date_to={today.isoformat()}"
    )
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Aug (35) + Jul (90) + Jun (40) + May (60) = 225 (Dec 2025 outside)
    assert "225.00" in body


def test_custom_range_valid(logged_in):
    r = logged_in.get("/profile?date_from=2026-06-01&date_to=2026-07-31")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # June (40) + July (90) = 130
    assert "130.00" in body


def test_inverted_range_flashes_and_falls_back(logged_in):
    r = logged_in.get("/profile?date_from=2026-08-01&date_to=2026-01-01")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Start date must be before end date." in body
    # Falls back to unfiltered total
    assert "237.00" in body


def test_malformed_date_does_not_crash(logged_in):
    r = logged_in.get("/profile?date_from=not-a-date&date_to=2026-08-31")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # No flash error from malformed input
    assert "Start date must be before end date." not in body
    # Falls back to unfiltered total
    assert "237.00" in body


def test_no_expenses_in_range_shows_zeros(app):
    """A user with no expenses in the selected range sees 0.00 totals."""
    from database.db import create_user
    user_id = create_user("Empty", "empty@example.com", "Password123!")
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = user_id
    r = c.get("/profile?date_from=2026-08-01&date_to=2026-08-31")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "0.00" in body
    # Category breakdown should be empty (no rows)
    assert "pie-chart" in body  # section still rendered


def test_unauthenticated_redirects_to_login(client):
    r = client.get("/profile")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_all_time_pill_active_when_no_filter(logged_in):
    r = logged_in.get("/profile")
    body = r.get_data(as_text=True)
    # Find the All Time pill — it's the only anchor with no date_from/date_to
    assert 'href="/profile"' in body
    assert 'is-active' in body


def test_rupee_symbol_preserved_with_filter(logged_in):
    r = logged_in.get("/profile?date_from=2026-08-01&date_to=2026-08-31")
    body = r.get_data(as_text=True)
    assert "₹35.00" in body
