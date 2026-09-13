import re
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for, abort
from werkzeug.security import check_password_hash

from database.db import create_user, find_user_by_email, find_user_by_id, get_category_breakdown, get_db, get_expense_by_id, get_top_category, get_total_spent, get_transaction_count, init_db, insert_expense, list_recent_transactions, seed_db, update_expense, delete_expense as db_delete_expense

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]



# ------------------------------------------------------------------ #
# Date filter helpers                                                 #
# ------------------------------------------------------------------ #

def _parse_iso_date(value):
    """Return a 'YYYY-MM-DD' string or None if missing/malformed."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _months_ago(d: date, n: int) -> date:
    """Calendar subtract — handles January wrap (e.g. n=1 on Jan 15 → Dec 15 prev year)."""
    year = d.year
    month = d.month - n
    while month <= 0:
        month += 12
        year -= 1
    return d.replace(year=year, month=month)


def _validate_expense_form(amount_raw, category, date_val):
    """Validate expense form inputs. Returns (error_message, cleaned_amount)."""
    amount = None
    try:
        amount = float(amount_raw)
        if amount <= 0:
            return "Please enter a positive amount.", None
    except ValueError:
        return "Please enter a valid numeric amount.", None

    if category not in EXPENSE_CATEGORIES:
        return "Please select a valid category.", None

    try:
        datetime.strptime(date_val, "%Y-%m-%d")
    except ValueError:
        return "Please enter a valid date.", None

    return None, amount


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

@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/logout")

def logout():
    session.clear()
    return redirect(url_for("login"))


@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        user = find_user_by_id(user_id)
        return {"current_user": user, "EXPENSE_CATEGORIES": EXPENSE_CATEGORIES}
    return {"current_user": None, "EXPENSE_CATEGORIES": EXPENSE_CATEGORIES}


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = find_user_by_id(user_id)

    # Date filter — read query params, validate, normalize to YYYY-MM-DD
    raw_from = request.args.get("date_from")
    raw_to = request.args.get("date_to")
    date_from = _parse_iso_date(raw_from)
    date_to = _parse_iso_date(raw_to)

    # If either side was supplied but malformed, drop both for predictable behavior.
    if (raw_from and date_from is None) or (raw_to and date_to is None):
        date_from = None
        date_to = None

    # Inverted range — flash and fall back to unfiltered.
    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to = None

    # Preset date calculations (server local). Used both for queries and
    # for building the preset pill links in the template.
    today = date.today()
    today_iso = today.isoformat()
    this_month_from = today.replace(day=1).isoformat()
    last_3_from = _months_ago(today, 3).isoformat()
    last_6_from = _months_ago(today, 6).isoformat()

    # Determine which preset (if any) is active so the template can highlight it.
    active_preset = None
    if date_from is None and date_to is None:
        active_preset = "all_time"
    else:
        for name, f, t in (
            ("this_month", this_month_from, today_iso),
            ("last_3_months", last_3_from, today_iso),
            ("last_6_months", last_6_from, today_iso),
        ):
            if date_from == f and date_to == t:
                active_preset = name
                break

    # Profile data sourced live from the DB — Step 5 + Step 6 filter.
    profile_data = {
        "user": user,
        "stats": {
            "total_spent": get_total_spent(user_id, date_from, date_to),
            "transaction_count": get_transaction_count(user_id, date_from, date_to),
            "top_category": get_top_category(user_id, date_from, date_to),
        },
        "transactions": list_recent_transactions(user_id, date_from=date_from, date_to=date_to),
        "categories": get_category_breakdown(user_id, date_from, date_to),
        # Filter state for the template
        "date_from": date_from or "",
        "date_to": date_to or "",
        "active_preset": active_preset,
        "today": today_iso,
        "this_month_from": this_month_from,
        "last_3_from": last_3_from,
        "last_6_from": last_6_from,
    }

    return render_template("profile.html", **profile_data)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    context = {"error": None, "form_data": {}}

    if request.method == "POST":
        amount_raw = request.form.get("amount") or ""
        category = request.form.get("category") or ""
        date_val = request.form.get("date") or ""
        description = (request.form.get("description") or "").strip()

        error, amount = _validate_expense_form(amount_raw, category, date_val)

        if error:
            flash(error, "error")
            context["error"] = error
            context["form_data"] = {
                "amount": amount_raw,
                "category": category,
                "date": date_val,
                "description": description,
            }
            return render_template("add_expense.html", **context)

        # Success: Insert into DB
        insert_expense(
            user_id=user_id,
            amount=amount,
            category=category,
            date=date_val,
            description=description if description else None,
        )
        flash("Expense saved successfully!", "success")
        return redirect(url_for("profile"))

    # GET request
    context["form_data"] = {"date": date.today().isoformat()}
    return render_template("add_expense.html", **context)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    context = {"form_data": {}}

    if request.method == "POST":
        amount_raw = request.form.get("amount") or ""
        category = request.form.get("category") or ""
        date_val = request.form.get("date") or ""
        description = (request.form.get("description") or "").strip()

        error, amount = _validate_expense_form(amount_raw, category, date_val)

        if error:
            flash(error, "error")
            context["form_data"] = {
                "amount": amount_raw,
                "category": category,
                "date": date_val,
                "description": description,
            }
            return render_template("edit_expense.html", expense=expense, categories=EXPENSE_CATEGORIES, **context)

        # Success: Update in DB
        update_expense(
            expense_id=id,
            user_id=user_id,
            amount=amount,
            category=category,
            date=date_val,
            description=description if description else None,
        )
        flash("Expense updated successfully!", "success")
        return redirect(url_for("profile"))

    # GET request
    return render_template("edit_expense.html", expense=expense, categories=EXPENSE_CATEGORIES, **context)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Verify ownership
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    # Delete expense
    db_delete_expense(id, user_id)
    flash("Expense deleted successfully!", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()

    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
