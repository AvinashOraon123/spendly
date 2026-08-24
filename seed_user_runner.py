"""One-off seed script for /seed-user. Uses get_db() + create_user()."""
import random

from database.db import get_db, create_user

FIRST_NAMES = [
    # North
    "Rahul", "Aman", "Vikas", "Sandeep", "Rohit", "Ankit", "Pooja", "Neha",
    "Priya", "Anjali", "Amit", "Suresh",
    # South
    "Karthik", "Arun", "Vignesh", "Meena", "Lakshmi", "Ravi", "Divya",
    "Srinivas", "Anitha",
    # East
    "Avinash", "Suman", "Rakesh", "Priyanka", "Bikram", "Sushmita",
    "Manish", "Kavita",
    # West
    "Harsh", "Pratik", "Sanjay", "Nisha", "Vivek", "Rucha", "Kunal",
    # Generic pan-Indian
    "Arjun", "Aditya", "Riya", "Sneha", "Vikram",
]

LAST_NAMES = [
    "Sharma", "Verma", "Kumar", "Singh", "Gupta", "Patel", "Shah",
    "Reddy", "Nair", "Iyer", "Pillai", "Rao", "Naidu", "Menon",
    "Oraon", "Munda", "Tiwari", "Mishra", "Pandey", "Yadav",
    "Chatterjee", "Banerjee", "Mukherjee", "Das", "Bose", "Ghosh",
    "Khan", "Ahmed", "Patil", "Deshmukh", "Jadhav", "Kulkarni",
    "Joshi", "Mehta", "Kapoor", "Bhat", "Hegde",
]


def random_name() -> tuple[str, str]:
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def make_email(first: str, last: str) -> str:
    first_clean = first.lower().replace(" ", "")
    last_clean = last.lower().replace(" ", "")
    suffix = random.randint(10, 999)
    return f"{first_clean}.{last_clean}{suffix}@gmail.com"


def main():
    conn = get_db()
    try:
        while True:
            first, last = random_name()
            full_name = f"{first} {last}"
            email = make_email(first, last)
            existing = conn.execute(
                "SELECT 1 FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing is None:
                break
    finally:
        conn.close()

    new_id = create_user(full_name, email, "password123")

    print(f"id:    {new_id}")
    print(f"name:  {full_name}")
    print(f"email: {email}")


if __name__ == "__main__":
    main()
