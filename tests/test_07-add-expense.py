import os
import pytest
import sqlite3
from database.db import get_db, insert_expense, init_db
from app import app

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database for each test."""
    db_file = tmp_path / "test_spendly.db"
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

# --- Unit Tests ---

def test_insert_expense_valid(db_conn, test_user):
    """Verify that insert_expense adds a valid expense to the DB."""
    expense_id = insert_expense(
        user_id=test_user,
        amount=50.0,
        category="Food",
        date="2026-03-20",
        description="Lunch",
    )
    assert expense_id is not None

    row = db_conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE id = ?",
        (expense_id,)
    ).fetchone()
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"

def test_insert_expense_no_description(db_conn, test_user):
    """Verify that insert_expense works when description is None."""
    expense_id = insert_expense(
        user_id=test_user,
        amount=20.0,
        category="Transport",
        date="2026-03-21",
        description=None,
    )
    assert expense_id is not None

    row = db_conn.execute(
        "SELECT description FROM expenses WHERE id = ?",
        (expense_id,)
    ).fetchone()
    assert row["description"] is None

# --- Route Tests ---

def test_add_expense_unauthenticated_get(client):
    """GET /expenses/add should redirect to /login if not authenticated."""
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_add_expense_unauthenticated_post(client):
    """POST /expenses/add should redirect to /login if not authenticated."""
    response = client.post("/expenses/add", data={"amount": "10.0", "category": "Food", "date": "2026-01-01"})
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_add_expense_authenticated_get(client, test_user):
    """GET /expenses/add should render the form for authenticated users."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.get("/expenses/add")
    assert response.status_code == 200
    assert b"Amount" in response.data
    assert b"Food" in response.data
    assert b"Transport" in response.data
    assert b"Bills" in response.data
    assert b"Health" in response.data
    assert b"Entertainment" in response.data
    assert b"Shopping" in response.data
    assert b"Other" in response.data
    assert b'method="POST"' in response.data

def test_add_expense_authenticated_valid_post(client, test_user, db_conn):
    """POST /expenses/add with valid data should redirect to profile and save to DB."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    data = {
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 302
    assert response.location.endswith("/profile")

    row = db_conn.execute(
        "SELECT amount, category FROM expenses WHERE user_id = ? AND amount = 50.0",
        (test_user,)
    ).fetchone()
    assert row is not None
    assert row["category"] == "Food"

def test_add_expense_invalid_amount_zero(client, test_user):
    """POST /expenses/add with amount=0 should return error."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post("/expenses/add", data={"amount": "0", "category": "Food", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please enter a positive amount" in response.data

def test_add_expense_invalid_amount_non_numeric(client, test_user):
    """POST /expenses/add with non-numeric amount should return error."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post("/expenses/add", data={"amount": "abc", "category": "Food", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please enter a valid numeric amount" in response.data

def test_add_expense_invalid_category(client, test_user):
    """POST /expenses/add with invalid category should return error."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post("/expenses/add", data={"amount": "10.0", "category": "InvalidCat", "date": "2026-01-01"})
    assert response.status_code == 200
    assert b"Please select a valid category" in response.data

def test_add_expense_invalid_date(client, test_user):
    """POST /expenses/add with invalid date should return error."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post("/expenses/add", data={"amount": "10.0", "category": "Food", "date": "not-a-date"})
    assert response.status_code == 200
    assert b"Please enter a valid date" in response.data

def test_add_expense_no_description(client, test_user, db_conn):
    """POST /expenses/add without description should save as NULL."""
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    data = {
        "amount": "10.0",
        "category": "Food",
        "date": "2026-03-21",
        "description": ""
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 302

    row = db_conn.execute(
        "SELECT description FROM expenses WHERE user_id = ? AND amount = 10.0",
        (test_user,)
    ).fetchone()
    assert row["description"] is None
