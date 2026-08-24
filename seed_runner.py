"""One-off seed script for /seed-expense. Uses get_db() pattern."""
import random
import sys
from datetime import date, timedelta

from database.db import get_db

USER_ID = 2
COUNT = 3
MONTHS = 5
TODAY = date.today()

# (category, weight, min_amount, max_amount, descriptions)
CATEGORIES = [
    ("Food",          0.30, 50,  800,
     ["Chai and samosa", "Lunch at office canteen", "Swiggy order",
      "Dinner with friends", "Breakfast at the corner stall",
      "Zomato delivery", "Filter coffee", "Evening snacks"]),
    ("Transport",     0.20, 20,  500,
     ["Ola auto to office", "Metro card top-up", "Uber to airport",
      "Petrol refill", "Rapido bike ride", "Auto rickshaw",
      "Cab to station", "Bus pass recharge"]),
    ("Bills",         0.15, 200, 3000,
     ["Electricity bill", "Mobile recharge", "Broadband bill",
      "Gas cylinder refill", "Water bill", "DTH recharge",
      "Credit card payment", "Society maintenance"]),
    ("Health",        0.05, 100, 2000,
     ["Pharmacy restock", "Doctor consultation", "Lab test",
      "Health supplements", "Dental checkup", "Eye drops"]),
    ("Entertainment", 0.05, 100, 1500,
     ["Movie tickets", "Netflix subscription", "Spotify Premium",
      "Concert tickets", "Board game cafe", "Stand-up show"]),
    ("Shopping",      0.15, 200, 5000,
     ["New t-shirt", "Running shoes", "Groceries from DMart",
      "Kitchen utensils", "Mobile cover", "Books from Amazon",
      "Winter jacket", "Household supplies"]),
    ("Other",         0.10, 50,  1000,
     ["Cloud backup subscription", "Haircut", "Birthday gift",
      "Donation", "Newspaper", "Stationery", "Courier charges"]),
]

CATEGORY_NAMES = [c[0] for c in CATEGORIES]
WEIGHTS = [c[1] for c in CATEGORIES]


def random_date_in_window() -> date:
    end = TODAY
    start = TODAY - timedelta(days=MONTHS * 30)
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def build_expense():
    category = random.choices(CATEGORY_NAMES, weights=WEIGHTS, k=1)[0]
    info = next(c for c in CATEGORIES if c[0] == category)
    _, _, lo, hi, descriptions = info
    amount = round(random.uniform(lo, hi), 2)
    description = random.choice(descriptions)
    expense_date = random_date_in_window().isoformat()
    return (USER_ID, amount, category, expense_date, description)


def main():
    expenses = [build_expense() for _ in range(COUNT)]
    conn = get_db()
    try:
        try:
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                expenses,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()

    dates = sorted(e[3] for e in expenses)
    print(f"Inserted: {len(expenses)} expenses")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print("Sample of 5 inserted records:")
    sample = expenses[:5]
    for row in sample:
        print(f"  user_id={row[0]} amount=Rs {row[1]} category={row[2]} "
              f"date={row[3]} description={row[4]!r}")


if __name__ == "__main__":
    main()
