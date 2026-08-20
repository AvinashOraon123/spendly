## 1. Overview

Implement working **user registration** for Spendly.

This step turns the existing `GET /register` stub into a real account-creation flow:
- Users submit name, email, and password through the existing form
- Passwords are hashed with `werkzeug` and persisted to the `users` table
- Successful registration redirects to `/login`
- Validation errors are rendered back on the registration page

All future authenticated features (login, profile, expense tracking) depend on users being able to register.

---

## 2. Depends on

- **Step 1 — Database setup**
  - `users` table with `id`, `name`, `email`, `password_hash`, `created_at`
  - `get_db()` helper available in `database/db.py`
  - Email column enforces UNIQUE constraint at the DB layer

---

## 3. Routes

### A. `GET /register` — keep as-is

- Renders `templates/register.html`
- No authentication required

### B. `POST /register` — new

- Accepts `name`, `email`, `password` from the form
- Validates input
- Inserts a new row into the `users` table
- On success: redirect to `/login`
- On failure: re-render `register.html` with an error message and the previously submitted `name` and `email`

The same `register` view function handles both `GET` and `POST`.

---

## 4. Database Changes

None. Uses the `users` table created in Step 1.

---

## 5. Functions to Implement

---

### A. `database/db.py` — new helper: `create_user(name, email, password)`

- Accepts raw values (not pre-hashed)
- Hashes the password using `werkzeug.security.generate_password_hash`
- Inserts a row into `users`:

  ```
  INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)
  ```

- Returns the new user's `id` (use `cursor.lastrowid`)
- Lets `sqlite3.IntegrityError` propagate on duplicate email — the route handles it

---

## 6. Changes to `app.py`

- Update imports:
  - `from flask import Flask, render_template, request, redirect, url_for`
  - Add `create_user` to the existing `database.db` import
- Replace the current `register()` stub with a `GET`/`POST` view:

  ```
  @app.route("/register", methods=["GET", "POST"])
  def register():
      if request.method == "POST":
          name     = request.form.get("name", "").strip()
          email    = request.form.get("email", "").strip().lower()
          password = request.form.get("password", "")

          # validate → render_template("register.html", error=..., form_data=...)

          # duplicate email → sqlite3.IntegrityError → render with friendly error

          # success → redirect(url_for("login"))
      return render_template("register.html")
  ```

- One responsibility only: parse form, call `create_user`, redirect or re-render
- All SQL stays in `database/db.py` — never inline `INSERT` in the route

---

## 7. Files to Change

- `app.py` — expand `register()` to handle POST, update imports
- `database/db.py` — add `create_user()` helper

---

## 8. Files to Create

- None (template already exists at `templates/register.html`)

---

## 9. Dependencies

- No new pip packages
- Use:
  - `werkzeug.security.generate_password_hash` (already installed)
  - `sqlite3.IntegrityError` from the standard library to detect duplicate emails

---

## 10. Validation Rules

### Name
- Required
- Trim whitespace
- Min length: 2 characters
- Max length: 100 characters

### Email
- Required
- Trim whitespace
- Lowercased before storage
- Must match a basic email pattern (contains `@` and `.` after the `@`)
- Uniqueness enforced at the DB layer (UNIQUE constraint on `users.email`)

### Password
- Required
- Minimum length: 8 characters
- Maximum length: 128 characters (avoid DoS via absurdly long hashing input)
- No other complexity rules

---

## 11. Error Messages

Render these inline at the top of the registration card using the existing `auth-error` class:

| Condition | Message |
| --- | --- |
| Missing name | "Please enter your name." |
| Name too short | "Name must be at least 2 characters." |
| Missing email | "Please enter your email." |
| Invalid email format | "Please enter a valid email address." |
| Missing password | "Please enter a password." |
| Password too short | "Password must be at least 8 characters." |
| Password too long | "Password is too long." |
| Duplicate email | "An account with this email already exists." |

On any failure: re-render the form with the user's previously submitted `name` and `email` (never the password) populated back into the inputs.

---

## 12. Rules for Implementation

- One responsibility per route — no SQL in route functions
- Use parameterized queries (`?` placeholders) for all DB calls
- Hash passwords with `werkzeug.security.generate_password_hash` — never store plaintext
- Lowercase email before insert so future logins are case-insensitive
- Catch `sqlite3.IntegrityError` from `create_user()` and map to the duplicate-email message
- On success: `redirect(url_for("login"))` — never render the login template directly
- Re-rendering `register.html` on error must preserve `name` and `email` from the previous submission
- Never echo the password back into the form

---

## 13. Template Notes (`templates/register.html`)

- Form already exists and submits `POST` to `/register`
- Already references `{{ error }}` for an error block
- Add `value="{{ form_data.name or '' }}"` and `value="{{ form_data.email or '' }}"` to the relevant inputs so the user doesn't retype them
- Keep the existing `{{ url_for('login') }}` link in the "Already have an account?" footer

---

## 14. Expected Behavior

- `GET /register` shows the empty form
- Submitting valid data:
  - Hashes the password
  - Inserts a new `users` row
  - Redirects to `/login`
- Submitting invalid data:
  - Shows the matching error at the top of the form
  - Preserves `name` and `email` in the inputs
  - Does NOT create a row in `users`
- Submitting an email that already exists:
  - Shows "An account with this email already exists."
  - Does NOT update or duplicate the existing row
- After successful registration, the user is **not** logged in automatically — that's Step 3 (login)

---

## 15. Error Handling Expectations

- `sqlite3.IntegrityError` from duplicate email → friendly inline error, page re-renders with prior input
- Any other unexpected DB error → propagate to Flask's default 500 handler (not a raw `return "error"`)
- Missing or empty form fields → handled by validation, not by exceptions

---

## 16. Definition of Done

- [ ]  `POST /register` creates a new row in `users` with a hashed password
- [ ]  Passwords are stored as `werkzeug` hashes — never plaintext
- [ ]  Emails are stored lowercased
- [ ]  All listed validation rules produce the listed error messages
- [ ]  Form preserves `name` and `email` on validation failure
- [ ]  Duplicate email shows a friendly error and does not duplicate the row
- [ ]  Successful registration redirects to `/login` (not a re-render)
- [ ]  No SQL appears in `app.py` — all DB work is in `database/db.py`
- [ ]  All queries use parameterized SQL
- [ ]  App still starts without errors; existing routes unchanged
