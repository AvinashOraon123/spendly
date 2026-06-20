"""Seed a single random Indian user into the Spendly DB.

Run with:
    source venv/Scripts/activate
    python seed_user.py
"""

import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db


# Realistic Indian first names across regions.
FIRST_NAMES = [
    # North
    "Rahul", "Priya", "Amit", "Neha", "Vikram", "Pooja", "Rohit", "Anjali",
    "Arjun", "Kavita", "Sandeep", "Ritu",
    # South
    "Arjun", "Divya", "Karthik", "Lakshmi", "Ramesh", "Anitha", "Suresh", "Meena",
    # East
    "Suman", "Rina", "Amitava", "Pallabi",
    # West
    "Nikhil", "Sneha", "Hardik", "Mira",
    # Central / misc
    "Aditya", "Sakshi", "Manish", "Tanvi",
]

# Common Indian last names across regions/communities.
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Patel", "Reddy", "Iyer", "Nair", "Khan",
    "Singh", "Kumar", "Joshi", "Mehta", "Banerjee", "Mukherjee", "Chatterjee",
    "Pillai", "Menon", "Bhat", "Rao", "Kapoor", "Malhotra", "Saxena",
    "Chauhan", "Yadav", "Tiwari", "Mishra",
]

# Common Indian email providers.
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]


def generate_email(first: str, last: str) -> str:
    """Build `first.last<2-3 digits>@<domain>` (lowercase)."""
    domain = random.choice(EMAIL_DOMAINS)
    suffix_digits = random.randint(2, 3)
    suffix = "".join(str(random.randint(0, 9)) for _ in range(suffix_digits))
    return f"{first.lower()}.{last.lower()}{suffix}@{domain}"


def main():
    conn = get_db()
    cur = conn.cursor()

    # Loop until we find an email that isn't taken.
    while True:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = generate_email(first, last)

        cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
        if cur.fetchone() is None:
            break

    password_hash = generate_password_hash("password123")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        """
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, email, password_hash, created_at),
    )
    conn.commit()

    user_id = cur.lastrowid
    conn.close()

    print(f"id:    {user_id}")
    print(f"name:  {name}")
    print(f"email: {email}")


if __name__ == "__main__":
    main()