import pytest
import sqlite3
from database.db import get_db, get_expense_by_id, delete_expense, init_db
from app import app

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database for each test."""
    db_file = tmp_path / "test_spendly_delete.db"
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

def test_delete_expense_valid(db_conn, test_user, sample_expense):
    delete_expense(sample_expense, test_user)
    row = db_conn.execute(
        "SELECT id FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row is None

def test_delete_expense_wrong_user(db_conn, test_user, sample_expense):
    # Should not delete if user_id is wrong
    delete_expense(sample_expense, 999)
    row = db_conn.execute(
        "SELECT id FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row is not None

def test_delete_expense_non_existent(db_conn, test_user):
    # Should not raise error
    delete_expense(999, test_user)

# ------------------------------------------------------------------ #
# Route Tests                                                        #
# ------------------------------------------------------------------ #

def test_delete_expense_unauthenticated_post(client):
    response = client.post("/expenses/1/delete")
    assert response.status_code == 302
    assert response.location.endswith("/login")

def test_delete_expense_authenticated_valid_post(client, test_user, sample_expense, db_conn):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post(f"/expenses/{sample_expense}/delete")
    assert response.status_code == 302
    assert response.location.endswith("/profile")

    row = db_conn.execute(
        "SELECT id FROM expenses WHERE id = ?",
        (sample_expense,)
    ).fetchone()
    assert row is None

def test_delete_expense_authenticated_get_method_not_allowed(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.get("/expenses/1/delete")
    assert response.status_code == 405

def test_delete_expense_authenticated_other_user_post(client, test_user, sample_expense):
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

    response = client.post(f"/expenses/{sample_expense}/delete")
    assert response.status_code == 404

def test_delete_expense_authenticated_missing_post(client, test_user):
    with client.session_transaction() as sess:
        sess["user_id"] = test_user

    response = client.post("/expenses/999/delete")
    assert response.status_code == 404
