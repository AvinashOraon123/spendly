import pytest
import sqlite3
from database.db import get_db, get_expense_by_id, update_expense, init_db
from app import app

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database for each test."""
    db_file = tmp_path / "test_spendly_edit_spec.db"
    import database.db
    original_path = database.db.DB_PATH
    database.db.DB_PATH = str(db_file)

    init_db()

    yield str(db_file)

    database.db.DB_PATH = original_path

@pytest.fixture
def client(test_db):
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_conn(test_db):
    conn = get_db()
    yield conn
    conn.close()

@pytest.fixture
def test_user(db_conn):
    """Create a test user and return their ID."""
    cur = db_conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "test@example.com", "hash"),
    )
    db_conn.commit()
    return cur.lastrowid

@pytest.fixture
def sample_expense(db_conn, test_user):
    """Create a sample expense for the test user."""
    cur = db_conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (test_user, 50.0, "Food", "2026-03-20", "Lunch"),
    )
    db_conn.commit()
    return cur.lastrowid

# ------------------------------------------------------------------ #
# Unit Tests                                                         #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_valid(db_conn, test_user, sample_expense):
    row = get_expense_by_id(sample_expense, test_user)
    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"

def test_get_expense_by_id_wrong_user(db_conn, sample_expense):
    row = get_expense_by_id(sample_expense, 999) # Non-existent user
    assert row is None

def test_get_expense_by_id_non_existent(db_conn, test_user):
    row = get_expense_by_id(999, test_user)
    assert row is None

def test_update_expense_valid(db_conn, test_user, sample_expense):
    update_expense(sample_expense, test_user, 75.0, "Shopping", "2026-03-21", "Shoes")
    row = db_conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row["amount"] == 75.0
    assert row["category"] == "Shopping"
    assert row["date"] == "2026-03-21"
    assert row["description"] == "Shoes"

def test_update_expense_wrong_user(db_conn, test_user, sample_expense):
    # This should not update the row
    update_expense(sample_expense, 999, 75.0, "Shopping", "2026-03-21", "Shoes")
    row = db_conn.execute(
        "SELECT amount FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row["amount"] == 50.0 # Unchanged

# ------------------------------------------------------------------ #
# Route Tests                                                        #
# ------------------------------------------------------------------ #

def test_edit_expense_unauthenticated_get(client):
    response = client.get("/expenses/1/edit")
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_edit_expense_unauthenticated_post(client):
    response = client.post("/expenses/1/edit", data={"amount": "10.0"})
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_edit_expense_authenticated_get_own(client, test_user, sample_expense):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.get(f"/expenses/{sample_expense}/edit")
    assert response.status_code == 200
    assert b"Edit Expense" in response.data
    assert b"50.0" in response.data
    assert b"Food" in response.data
    assert b"2026-03-20" in response.data
    assert b"Lunch" in response.data

def test_edit_expense_authenticated_get_other(client, test_user, sample_expense):
    import database.db
    conn = database.db.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@example.com", "hash"),
    )
    other_user_id = cur.lastrowid
    conn.commit()
    conn.close()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user_id

    response = client.get(f"/expenses/{sample_expense}/edit")
    assert response.status_code == 404

def test_edit_expense_authenticated_get_missing(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.get("/expenses/999/edit")
    assert response.status_code == 404

def test_edit_expense_authenticated_valid_post(client, test_user, sample_expense, db_conn):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    data = {
        "amount": "100.0",
        "category": "Bills",
        "date": "2026-03-22",
        "description": "Electricity"
    }
    response = client.post(f"/expenses/{sample_expense}/edit", data=data)
    assert response.status_code == 302
    assert response.location.endswith("/profile")

    row = db_conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row["amount"] == 100.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-03-22"
    assert row["description"] == "Electricity"

def test_edit_expense_authenticated_invalid_post(client, test_user, sample_expense):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    # Test zero amount
    response = client.post(f"/expenses/{sample_expense}/edit", data={"amount": "0", "category": "Food", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please enter a positive amount" in response.data
    assert b'value="0"' in response.data

    # Test non-numeric amount
    response = client.post(f"/expenses/{sample_expense}/edit", data={"amount": "abc", "category": "Food", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please enter a valid numeric amount" in response.data
    assert b'value="abc"' in response.data

    # Test invalid category
    response = client.post(f"/expenses/{sample_expense}/edit", data={"amount": "10.0", "category": "Invalid", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please select a valid category" in response.data

    # Test invalid date
    response = client.post(f"/expenses/{sample_expense}/edit", data={"amount": "10.0", "category": "Food", "date": "not-a-date"})
    assert response.status_code == 200
    assert b"Please enter a valid date" in response.data

def test_edit_expense_authenticated_post_other(client, test_user, sample_expense):
    import database.db
    conn = database.db.get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@example.com", "hash"),
    )
    other_user_id = cur.lastrowid
    conn.commit()
    conn.close()

    with client.session_transaction() as sess:
        sess["user_id"] = other_user_id

    data = {
        "amount": "100.0",
        "category": "Bills",
        "date": "2026-03-22",
        "description": "Electricity"
    }
    response = client.post(f"/expenses/{sample_expense}/edit", data=data)
    assert response.status_code == 404

def test_edit_expense_authenticated_no_description(client, test_user, sample_expense, db_conn):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    data = {
        "amount": "10.0",
        "category": "Food",
        "date": "2026-03-21",
        "description": ""
    }
    response = client.post(f"/expenses/{sample_expense}/edit", data=data)
    assert response.status_code == 302
    assert response.location.endswith("/profile")

    row = db_conn.execute(
        "SELECT description FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row["description"] is None
