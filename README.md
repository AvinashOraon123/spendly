# 💰 Spendly - Personal Expense Tracker

Spendly is a lightweight, secure, and efficient personal expense tracker built with **Flask** and **SQLite**. It allows users to register, manage their daily expenses, and gain insights into their spending habits through a clean, intuitive interface.

## 🚀 Features

- **User Authentication**: Secure registration and login system.
- **Expense Management**: 
  - Add new expenses with amount, category, date, and description.
  - Edit existing expense entries.
  - Delete expenses with ownership verification.
- **Personalized Profile**: 
  - Overview of total spending and transaction counts.
  - Identification of the top spending category.
  - Recent transaction history.
- **Advanced Filtering**: 
  - Filter expenses by custom date ranges.
  - Quick-filter presets: "This Month", "Last 3 Months", and "Last 6 Months".
- **Spending Analytics**: Category-wise breakdown of expenses.

## 🛠️ Tech Stack

- **Backend**: Python 3.10+ / Flask
- **Database**: SQLite (with manual Foreign Key enforcement)
- **Frontend**: Jinja2 Templates, Vanilla CSS, Vanilla JavaScript
- **Testing**: Pytest

## 📂 Project Structure

```text
spendly/
├── app.py              # Application routes and business logic
├── database/
│   └── db.py           # SQLite database helpers and queries
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Shared layout
│   └── *.html          # Page-specific templates
├── static/              # Static assets
│   ├── css/            # Global and page-specific styles
│   └── js/             # Client-side logic (Vanilla JS)
└── requirements.txt    # Project dependencies
```

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher installed on your system.

### Setup Steps
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd expense-tracker
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```
   The app will be available at `http://127.0.0.1:5001`.

## 🧪 Testing

The project uses `pytest` for ensuring reliability.

- **Run all tests**:
  ```bash
  pytest
  ```
- **Run a specific test file**:
  ```bash
  pytest tests/test_foo.py
  ```
- **Run tests with verbose output**:
  ```bash
  pytest -s
  ```

## 🛡️ Security & Design Principles

- **Parameterized Queries**: All database interactions use `?` placeholders to prevent SQL Injection.
- **Password Hashing**: Uses `werkzeug.security` for secure password storage.
- **Ownership Validation**: Ensures users can only edit or delete their own expenses.
- **Minimalist Frontend**: No heavy JS frameworks; built with a focus on speed and accessibility.
