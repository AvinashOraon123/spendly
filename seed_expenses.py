"""
Seed realistic dummy expenses for a specific user.

Usage: python seed_expenses.py <user_id> <count> <months>

Follows the connection pattern from database/db.py — does NOT hardcode
the DB filename. Uses parameterised queries only and inserts all rows
in a single transaction (rollback on any failure).
"""

import random
import sys
from datetime import date, timedelta

from database.db import get_db, init_db


# Category config: (name, amount_min, amount_max, relative_weight, sample_descriptions)
CATEGORIES = [
    (
        "Food",
        50, 800,
        6,
        [
            "Lunch at campus canteen",
            "Chai and samosa",
            "Dinner with friends",
            "South Indian thali",
            "Street food — pani puri",
            "Biryani at Paradise",
            "Subway sandwich",
            "Pizza at Domino's",
            "Breakfast idli-dosa",
            "Cold coffee at CCD",
            "Momos from roadside stall",
            "Chole bhature",
        ],
    ),
    (
        "Transport",
        20, 500,
        5,
        [
            "Auto rickshaw to station",
            "Uber to office",
            "Rapido bike ride",
            "Metro card recharge",
            "Petrol for bike",
            "Ola mini ride",
            "Bus ticket to hometown",
            "Cab to airport",
        ],
    ),
    (
        "Bills",
        200, 3000,
        3,
        [
            "Electricity bill",
            "Mobile recharge — Jio",
            "Broadband bill",
            "Water bill",
            "Gas cylinder refill",
            "DTH recharge",
            "WiFi monthly bill",
            "Credit card bill payment",
        ],
    ),
    (
        "Health",
        100, 2000,
        1,
        [
            "Pharmacy — vitamins",
            "Doctor consultation",
            "Gym membership",
            "Lab tests",
            "Dental checkup",
            "Medicines — cold & flu",
            "Yoga class",
        ],
    ),
    (
        "Entertainment",
        100, 1500,
        1,
        [
            "Movie ticket — PVR",
            "Netflix subscription",
            "Spotify Premium",
            "Book from Crossword",
            "Concert ticket",
            "Stand-up show",
            "Gaming top-up",
        ],
    ),
    (
        "Shopping",
        200, 5000,
        3,
        [
            "New t-shirt",
            "Groceries — BigBasket",
            "Headphones from Amazon",
            "Footwear at Reliance",
            "Cosmetics — Lakme",
            "Home essentials",
            "Gift for friend",
            "Stationery and notebooks",
        ],
    ),
    (
        "Other",
        50, 1000,
        2,
        [
            "Miscellaneous",
            "Salon visit",
            "Laundry",
            "Donation to temple",
            "Birthday gift",
            "Repair work",
            "Parking charges",
            "Courier charges",
        ],
    ),
]

WEIGHTS = [c[3] for c in CATEGORIES]
NAMES = [c[0] for c in CATEGORIES]
DESCRIPTIONS = {c[0]: c[4] for c in CATEGORIES}
AMOUNT_RANGES = {c[0]: (c[1], c[2]) for c in CATEGORIES}


def pick_category():
    return random.choices(NAMES, weights=WEIGHTS, k=1)[0]


def pick_date(months: int) -> date:
    today = date.today()
    span_days = months * 30
    offset = random.randint(0, span_days)
    return today - timedelta(days=offset)


def parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise SystemExit(f"{name} must be an integer, got {value!r}")


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: python seed_expenses.py <user_id> <count> <months>")
        print("Example: python seed_expenses.py 1 50 6")
        sys.exit(1)

    user_id = parse_int(sys.argv[1], "user_id")
    count = parse_int(sys.argv[2], "count")
    months = parse_int(sys.argv[3], "months")

    if count <= 0 or months <= 0:
        print("count and months must be positive integers.")
        sys.exit(1)

    # Make sure the schema exists before we touch it.
    init_db()

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
        if user is None:
            print(f"No user found with id {user_id}.")
            conn.close()
            sys.exit(1)

        rows = []
        for _ in range(count):
            category = pick_category()
            lo, hi = AMOUNT_RANGES[category]
            amount = round(random.uniform(lo, hi), 2)
            d = pick_date(months)
            description = random.choice(DESCRIPTIONS[category])
            rows.append((user_id, amount, category, d.isoformat(), description))

        # Single transaction: rollback on any failure.
        try:
            cur.executemany(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Insert failed, rolled back: {e}")
            conn.close()
            sys.exit(1)

        # Confirmation report
        dates = sorted(r[3] for r in rows)
        first_date, last_date = dates[0], dates[-1]
        print(f"Inserted {len(rows)} expenses for user '{user['name']}' (id={user_id}).")
        print(f"Date range: {first_date}  ->  {last_date}")
        print("Sample (5 records):")
        rupee = "Rs."
        for r in random.sample(rows, k=min(5, len(rows))):
            amount, category, d, desc = r[1], r[2], r[3], r[4]
            print(f"  {d}  {rupee}{amount:>7.2f}  {category:<14} {desc}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
