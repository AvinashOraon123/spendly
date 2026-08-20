import re
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, find_user_by_email, find_user_by_id, get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    context = {"error": None, "form_data": {"name": "", "email": ""}}

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        error = None
        if not name:
            error = "Please enter your name."
        elif len(name) < 2:
            error = "Name must be at least 2 characters."
        elif not email:
            error = "Please enter your email."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif not password:
            error = "Please enter a password."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif len(password) > 128:
            error = "Password is too long."

        if error is None:
            try:
                create_user(name, email, password)
            except sqlite3.IntegrityError:
                context["error"] = "An account with this email already exists."
                context["form_data"] = {"name": name, "email": email}
                return render_template("register.html", **context), 200
            else:
                return redirect(url_for("login"))

        context["error"] = error
        context["form_data"] = {"name": name, "email": email}

    return render_template("register.html", **context), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    context = {"error": None, "form_data": {"email": ""}}

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email:
            context["error"] = "Please enter your email."
        elif not password:
            context["error"] = "Please enter your password."
        else:
            row = find_user_by_email(email)
            if row is None or not check_password_hash(row["password_hash"], password):
                context["error"] = "Incorrect email or password."
            else:
                session["user_id"] = row["id"]
                return redirect(url_for("profile"))

        context["form_data"] = {"email": email}

    return render_template("login.html", **context), 200


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = find_user_by_id(user_id)
        return {"current_user": user}
    return {"current_user": None}


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = find_user_by_id(user_id)

    # Hardcoded data for Step 4 — no DB queries
    profile_data = {
        "user": user,
        "stats": {
            "total_spent": 286.93,
            "transaction_count": 8,
            "top_category": "Food",
        },
        "transactions": [
            {"date": "2026-08-17", "description": "Dinner with friends", "category": "Food", "amount": 22.75},
            {"date": "2026-08-15", "description": "Cloud backup subscription", "category": "Other", "amount": 9.99},
            {"date": "2026-08-12", "description": "New running shoes", "category": "Shopping", "amount": 67.40},
            {"date": "2026-08-10", "description": "Movie tickets", "category": "Entertainment", "amount": 15.00},
            {"date": "2026-08-08", "description": "Pharmacy restock", "category": "Health", "amount": 24.30},
            {"date": "2026-08-05", "description": "Internet bill", "category": "Bills", "amount": 89.99},
            {"date": "2026-08-04", "description": "Weekly metro card top-up", "category": "Transport", "amount": 45.00},
            {"date": "2026-08-02", "description": "Lunch at the corner cafe", "category": "Food", "amount": 12.50},
        ],
        "categories": [
            {"name": "Food", "total": 35.25, "percent": 12},
            {"name": "Bills", "total": 89.99, "percent": 31},
            {"name": "Shopping", "total": 67.40, "percent": 23},
            {"name": "Transport", "total": 45.00, "percent": 16},
            {"name": "Health", "total": 24.30, "percent": 8},
            {"name": "Entertainment", "total": 15.00, "percent": 5},
            {"name": "Other", "total": 9.99, "percent": 3},
        ],
    }

    return render_template("profile.html", **profile_data)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
