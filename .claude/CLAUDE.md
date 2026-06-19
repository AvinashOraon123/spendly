# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Spendly — Flask Expense Tracker

A student/tutorial scaffold for a personal expense tracker. The codebase is built incrementally across numbered "Steps" (Step 1 through Step 9) — many routes and database functions are intentionally left as placeholders for the student to fill in. The product name in the UI/brand is **Spendly**.

## Running the app

```bash
# Activate virtualenv (Windows Git Bash)
source venv/Scripts/activate

# Install deps (already done if venv/ exists)
pip install -r requirements.txt

# Run dev server — port 5001, debug mode ON
python app.py
```

Visit http://localhost:5001

## Running tests

```bash
# All tests
pytest

# Single test file
pytest tests/test_auth.py

# Single test by name
pytest -k "test_login_with_valid_credentials"

# With Flask test client (pytest-flask is in requirements.txt)
pytest --flask-app=app.py
```

Note: there is no `tests/` directory yet — students add it during the testing step. `pytest` and `pytest-flask` are pre-listed in `requirements.txt` so they're ready when needed.

## Architecture

```
app.py                  # Flask app + all route definitions (single file)
database/
  __init__.py
  db.py                 # SQLite helpers: get_db(), init_db(), seed_db() — Step 1 stub
templates/
  base.html             # Layout shell: navbar, main, footer, brand "Spendly"
  landing.html          # Marketing/hero page
  login.html, register.html
  terms.html, privacy.html
static/
  css/style.css         # Single merged stylesheet (DM Sans + DM Serif Display fonts)
  js/main.js            # Empty stub — students add JS here
```

### Key design points

- **Single-file routing in `app.py`** — every route lives in one module. Adding a new route means editing `app.py`, not registering a blueprint.
- **Step-numbered scaffolding** — placeholder comments (`# Step 3`, `# Step 7`, etc.) mark routes/features that are intentionally incomplete. Don't treat "coming in Step X" strings as bugs; they're pedagogical TODOs.
- **Brand is "Spendly"** but the git repo and folder are still named `expense-tracker`. User-facing copy in `templates/` and `static/` uses Spendly.
- **SQLite** is the chosen DB (per `database/db.py` comments). The expected `db.py` interface:
  - `get_db()` → connection with `row_factory=sqlite3.Row` and `PRAGMA foreign_keys=ON`
  - `init_db()` → `CREATE TABLE IF NOT EXISTS` for all tables
  - `seed_db()` → development sample data
  - The SQLite file `expense_tracker.db` is gitignored.
- **Port 5001** (not Flask's default 5000) — don't change without checking for conflicts.
- **No CSS/JS framework** — vanilla CSS with CSS variables (defined at the top of `style.css`) and vanilla JS. The design uses DM Sans + DM Serif Display from Google Fonts.

### Routes defined in `app.py`

| Route | Status |
|---|---|
| `/`, `/register`, `/login`, `/terms`, `/privacy` | Complete — render templates |
| `/logout` | Placeholder (Step 3) |
| `/profile` | Placeholder (Step 4) |
| `/expenses/add` | Placeholder (Step 7) |
| `/expenses/<int:id>/edit` | Placeholder (Step 8) |
| `/expenses/<int:id>/delete` | Placeholder (Step 9) |

### Conventions observed in the code

- Route functions use `snake_case` (`add_expense`, `edit_expense`).
- Section dividers in `app.py` use comment banners like `# ---... #` — match this style when adding new sections.
- Templates extend `base.html` and use Jinja `{% block %}` regions: `title`, `head`, `content`, `scripts`.
- Static assets are referenced via `{{ url_for('static', filename='...') }}`.
- The footer in `base.html` always links to Terms and Privacy — keep both routes wired up.

## Gitignored

`venv/`, `expense_tracker.db`, `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `.DS_Store`, `.claude/plans/`