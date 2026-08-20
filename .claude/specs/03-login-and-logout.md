## 1. Overview

Implement working **login** and **logout** for Spendly.

This step turns the existing `GET /login` and `GET /logout` stubs into real authentication flows:
- Users submit email + password through the existing form
- The server verifies the credentials against the `users` table using `werkzeug`
- On success, the user's `id` is stored in the Flask session and they are redirected to `/profile`
- On failure, the login page is re-rendered with an error and the previously submitted email preserved
- `/logout` clears the session and redirects to `/login`

All future authenticated features (profile, expense tracking) depend on the session established here.

---

## 2. Depends on

- **Step 1 — Database setup**
  - `users` table with `id`, `name`, `email`, `password_hash`, `created_at`
  - `get_db()` helper available in `database/db.py`
- **Step 2 — Registration**
  - A `create_user()` helper that hashes passwords with `werkzeug.security.generate_password_hash`
  - Email is stored lowercased in `users.email`
  - Passwords are stored as `werkzeug` hashes (never plaintext)

---

## 3. Routes

### A. `GET /login` — already exists, expand to handle POST

- Renders `templates/login.html`
- No authentication required
- The same `login` view function handles both `GET` and `POST`

### B. `POST /login` — new

- Accepts `email` and `password` from the form
- Looks up the user by email (lowercased, trimmed)
- Verifies the password using `werkzeug.security.check_password_hash`
- On success:
  - Stores `user_id` in the Flask session (`session["user_id"] = user["id"]`)
  - Redirects to `/profile`
- On failure:
  - Re-renders `login.html` with a generic error message and the previously submitted email
  - Never reveals whether the email or the password was wrong

### C. `GET /logout` — replace stub

- Clears the Flask session (`session.clear()`)
- Redirects to `/login`
- No template to render — this is a redirect-only endpoint
- No authentication required to call (calling it while already logged out is harmless)

---

## 4. Database Changes

None. Reads the existing `users` table.

---

## 5. Functions to Implement

---

### A. `database/db.py` — new helper: `find_user_by_email(email)`

- Accepts an email that is already trimmed and lowercased
- Returns a single `sqlite3.Row` for the matching user, or `None` if no match
- Query (parameterized):
  ```
  SELECT id, name, email, password_hash FROM users WHERE email = ?
  ```
- Returns `None` on no match — does not raise

---

### B. `app.py` — configure a session secret key

- Add at module level, near the top of the file:
  ```
  app.secret_key = "dev-secret-change-me"
  ```
- The literal value is fine for local development. The real production secret will come from the environment in a later step.
- Without this, Flask refuses to sign session cookies.

---

## 6. Changes to `app.py`

- Update imports:
  - From `flask`: add `session`
  - From `database.db`: add `find_user_by_email`
- Set `app.secret_key` (see §5.B above)
- Replace the current `login()` stub with a `GET`/`POST` view that mirrors the `register()` pattern:
  - Initialize `context = {"error": None, "form_data": {"email": ""}}`
  - On POST:
    - Read and normalize `email` (`.strip().lower()`) and `password`
    - If either is missing → set error, re-render
    - Otherwise call `find_user_by_email(email)`
    - If no row, OR `check_password_hash(row["password_hash"], password)` returns `False` → set the generic error, re-render
    - On success → `session["user_id"] = row["id"]` and `redirect(url_for("profile"))`
  - Always end with `return render_template("login.html", **context), 200` on GET/error paths
- Replace the current `logout()` stub:
  - `session.clear()`
  - `return redirect(url_for("login"))`
- Pseudo-code block:

  ```
  @app.route("/login", methods=["GET", "POST"])
  def login():
      context = {"error": None, "form_data": {"email": ""}}

      if request.method == "POST":
          email    = (request.form.get("email") or "").strip().lower()
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


  @app.route("/logout")
  def logout():
      session.clear()
      return redirect(url_for("login"))
  ```

- One responsibility only: parse form, look up user, verify password, set session, redirect or re-render
- All SQL stays in `database/db.py` — never inline `SELECT` in the route

---

## 7. Files to Change

- `app.py` — set `app.secret_key`, expand `login()` to handle POST, replace `logout()` stub, update imports
- `database/db.py` — add `find_user_by_email()` helper

---

## 8. Files to Create

- None
  - `templates/login.html` already exists
  - `/logout` is redirect-only — no template needed

---

## 9. Dependencies

- No new pip packages
- Use:
  - `werkzeug.security.check_password_hash` (already installed; mirrors `generate_password_hash` from Step 2)
  - `flask.session` (ships with Flask — requires `app.secret_key`)

---

## 10. Validation Rules

### Email
- Required
- Trim whitespace
- Lowercased before lookup
- No format check at login time — if the row doesn't exist, the same "incorrect email or password" message is shown
  - Rationale: avoids revealing whether an email is registered

### Password
- Required
- No length check at login time — `check_password_hash` handles any input
  - Rationale: avoids leaking which constraint failed (length vs. wrong value)

---

## 11. Error Messages

Render inline at the top of the login card using the existing `auth-error` class.

| Condition | Message |
| --- | --- |
| Missing email | "Please enter your email." |
| Missing password | "Please enter your password." |
| Unknown email OR wrong password | "Incorrect email or password." |

Use a **single** combined message for the last two cases — never reveal which one was wrong.

On any failure: re-render the form with the user's previously submitted `email` populated back into the input. Never echo the password.

---

## 12. Rules for Implementation

- One responsibility per route — no SQL in route functions
- Use parameterized queries (`?` placeholders) for all DB calls
- Verify passwords with `werkzeug.security.check_password_hash` — never roll a custom comparison
- Look up the user by the same lowercased email that registration stored
- On successful login: store only `user_id` in the session — don't stash the password hash, name, or email
- On successful login: redirect to `/profile` (the existing stub) — never render the profile template directly
- On logout: `session.clear()` then redirect to `/login`
- The "incorrect email or password" message is identical whether the email is unknown or the password is wrong
- Re-rendering `login.html` on error must preserve the previously submitted email
- Never echo the password back into the form
- Do not change `/profile` in this step — it's still a stub, but `/login` redirects there on success so the path is wired up for Step 4

---

## 13. Template Notes (`templates/login.html`)

- Form already exists and submits `POST` to `/login`
- Already references `{{ error }}` for an error block
- Add `value="{{ form_data.email or '' }}"` to the email input so the user doesn't retype it on error
- The password input has no `value=` (matches the registration template)
- Keep the existing `{{ url_for('register') }}` link in the "Don't have an account?" footer
- Keep the existing `{{ url_for('login') }}` link in the base navbar — do not yet switch to a logged-in nav (that's Step 4 / profile)

---

## 14. Expected Behavior

- `GET /login` shows the empty form
- Submitting valid credentials:
  - Looks up the user by lowercased email
  - Verifies the password against the stored hash
  - Sets `session["user_id"]`
  - Redirects to `/profile`
- Submitting an unknown email:
  - Shows "Incorrect email or password."
  - Does NOT redirect
  - Preserves the submitted email
- Submitting the right email with a wrong password:
  - Shows the same "Incorrect email or password." message (indistinguishable from the unknown-email case)
  - Preserves the submitted email
- Submitting missing email or missing password:
  - Shows the matching "Please enter your ..." message
  - Preserves the submitted email (if present)
- `GET /logout`:
  - Clears the session
  - Redirects to `/login`
  - Works whether or not the user is currently logged in
- After successful login, subsequent requests in the same browser can identify the user via `session["user_id"]`. No `current_user` template variable is introduced in this step — that's Step 4.

---

## 15. Error Handling Expectations

- Unknown email → friendly inline error, page re-renders with prior email
- Wrong password → same friendly inline error (indistinguishable from unknown email), page re-renders with prior email
- Any unexpected DB error → propagate to Flask's default 500 handler (not a raw `return "error"`)
- Missing or empty form fields → handled by validation, not by exceptions
- Calling `/logout` while not logged in → no error; the empty session is cleared and the redirect still happens

---

## 16. Definition of Done

- [ ]  `POST /login` looks up the user by lowercased email
- [ ]  Passwords are verified with `werkzeug.security.check_password_hash` — never plaintext compare
- [ ]  On success, `session["user_id"]` is set and the user is redirected to `/profile`
- [ ]  On any login failure (unknown email, wrong password, missing field), the login page is re-rendered with an inline error
- [ ]  The "Incorrect email or password." message is used for both unknown-email and wrong-password cases
- [ ]  Form preserves the previously submitted `email` on validation failure
- [ ]  Passwords are never echoed back into the form
- [ ]  `GET /logout` clears the session and redirects to `/login`
- [ ]  `app.secret_key` is set so Flask will sign session cookies
- [ ]  No SQL appears in `app.py` — all DB work is in `database/db.py`
- [ ]  All queries use parameterized SQL
- [ ]  App still starts without errors; existing routes unchanged
- [ ]  No new pip packages added
