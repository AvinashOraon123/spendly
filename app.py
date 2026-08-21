import re
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, find_user_by_email, find_user_by_id, get_category_breakdown, get_db, get_top_category, get_total_spent, get_transaction_count, init_db, list_recent_transactions, seed_db

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

    # Profile data sourced live from the DB — Step 5
    profile_data = {
        "user": user,
        "stats": {
            "total_spent": get_total_spent(user_id),
            "transaction_count": get_transaction_count(user_id),
            "top_category": get_top_category(user_id),
        },
        "transactions": list_recent_transactions(user_id),
        "categories": get_category_breakdown(user_id),
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
