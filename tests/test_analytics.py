"""Tests for the Analytics coming soon page."""
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
def logged_in(client, app):
    from database.db import create_user
    import uuid
    email = f"tester_{uuid.uuid4().hex}@example.com"
    user_id = create_user("Tester", email, "Password123!")
    with client.session_transaction() as s:
        s["user_id"] = user_id
    return client


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_unauthenticated_redirects_to_login(client):
    r = client.get("/analytics")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_authenticated_access(logged_in):
    r = logged_in.get("/analytics")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Coming Soon" in body
    assert "Visualise your" in body
    assert "spending" in body


def test_navbar_active_state(logged_in):
    r = logged_in.get("/analytics")
    body = r.get_data(as_text=True)
    # Analytics link should have active class
    assert 'class="active"' in body
    # Profile link should NOT have active class
    assert 'href="/profile" class="active"' not in body
