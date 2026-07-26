import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = 'pennybook.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the SQLite database and populates mock data if it is new or empty.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Accounts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Cash, Bank, Credit Card, Wallet, UPI, Business Account
        balance REAL DEFAULT 0.0,
        initial_balance REAL DEFAULT 0.0
    )
    ''')
    
    # 2. Transactions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        date TEXT NOT NULL, -- YYYY-MM-DD
        type TEXT NOT NULL, -- income, expense, transfer
        category TEXT NOT NULL, -- Food, Fuel, Salary, etc.
        account_id INTEGER,
        to_account_id INTEGER, -- For transfers only
        notes TEXT,
        tags TEXT,
        receipt_path TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(id),
        FOREIGN KEY (to_account_id) REFERENCES accounts(id)
    )
    ''')
    
    # 3. Budgets
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        period TEXT NOT NULL -- weekly, monthly, yearly
    )
    ''')
    
    # 4. Savings Goals
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        saved_amount REAL DEFAULT 0.0,
        target_date TEXT NOT NULL
    )
    ''')
    
    # 5. Debts (Borrowed/Lent/Loans)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL, -- borrowed, lent
        person TEXT NOT NULL,
        amount REAL NOT NULL,
        interest_rate REAL DEFAULT 0.0, -- Annual percentage
        compounding_period TEXT DEFAULT 'none', -- none, monthly, yearly
        remaining_balance REAL NOT NULL,
        emi_amount REAL DEFAULT 0.0,
        start_date TEXT NOT NULL,
        due_date TEXT,
        notes TEXT
    )
    ''')
    
    # 6. Investments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Stocks, FD, Gold, Crypto, Mutual Funds
        invested_amount REAL NOT NULL,
        current_value REAL NOT NULL,
        notes TEXT
    )
    ''')
    
    # 7. Subscriptions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        renewal_date TEXT NOT NULL, -- YYYY-MM-DD
        billing_cycle TEXT NOT NULL, -- monthly, yearly
        account_id INTEGER,
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )
    ''')
    
    # 8. Recurring Transactions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recurring_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- income, expense
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        account_id INTEGER,
        frequency TEXT NOT NULL, -- daily, weekly, monthly
        next_occurrence TEXT NOT NULL, -- YYYY-MM-DD
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )
    ''')
    
    # 9. Bills
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Electricity, Water, Internet, Gas, Phone
        amount REAL NOT NULL,
        due_date TEXT NOT NULL, -- YYYY-MM-DD
        status TEXT DEFAULT 'unpaid', -- paid, unpaid
        account_id INTEGER,
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )
    ''')
    
    # 10. Split Groups
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    )
    ''')
    
    # 11. Group Members
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
    )
    ''')
    
    # 12. Group Expenses
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        paid_by_member_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        split_type TEXT NOT NULL, -- equal, unequal, percentage, quantity, item
        details TEXT NOT NULL, -- JSON string detailing the split
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
        FOREIGN KEY (paid_by_member_id) REFERENCES group_members(id) ON DELETE CASCADE
    )
    ''')
    
    # 13. Group Payments (Cash Settlements)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        from_member_id INTEGER NOT NULL,
        to_member_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
        FOREIGN KEY (from_member_id) REFERENCES group_members(id) ON DELETE CASCADE,
        FOREIGN KEY (to_member_id) REFERENCES group_members(id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    conn.close()

def recalculate_account_balances_connection(conn):
    """
    Recalculates account balances using connection `conn`.
    Account balance = initial_balance + sum(incomes) - sum(expenses) + sum(transfers_in) - sum(transfers_out).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, initial_balance FROM accounts")
    accounts = cursor.fetchall()
    
    for acc in accounts:
        acc_id = acc["id"]
        init_bal = acc["initial_balance"]
        
        # Sum income
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE account_id = ? AND type = 'income'", (acc_id,))
        inc_sum = cursor.fetchone()[0] or 0.0
        
        # Sum expense
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE account_id = ? AND type = 'expense'", (acc_id,))
        exp_sum = cursor.fetchone()[0] or 0.0
        
        # Sum transfers out
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE account_id = ? AND type = 'transfer'", (acc_id,))
        trans_out = cursor.fetchone()[0] or 0.0
        
        # Sum transfers in
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE to_account_id = ? AND type = 'transfer'", (acc_id,))
        trans_in = cursor.fetchone()[0] or 0.0
        
        new_balance = init_bal + inc_sum - exp_sum - trans_out + trans_in
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (round(new_balance, 2), acc_id))
        
    conn.commit()

def recalculate_account_balances():
    """
    Opens db connection, runs recalculation, commits and closes.
    """
    conn = get_db_connection()
    recalculate_account_balances_connection(conn)
    conn.close()

# ----------------- ACCOUNTS CRUD -----------------
def get_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_account(name, acc_type, initial_balance):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO accounts (name, type, balance, initial_balance) VALUES (?, ?, ?, ?)",
        (name, acc_type, float(initial_balance), float(initial_balance))
    )
    conn.commit()
    conn.close()
    recalculate_account_balances()

def delete_account(account_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete related transactions first or set them to NULL
    cursor.execute("DELETE FROM transactions WHERE account_id = ? OR to_account_id = ?", (account_id, account_id))
    cursor.execute("DELETE FROM subscriptions WHERE account_id = ?", (account_id,))
    cursor.execute("DELETE FROM bills WHERE account_id = ?", (account_id,))
    cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    recalculate_account_balances()

# ----------------- TRANSACTIONS CRUD -----------------
def get_transactions(filters=None):
    """
    Returns transactions with their account names.
    Supports filters: category, type, text search, date range, amount range, account.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT t.*, a.name as account_name, a2.name as to_account_name 
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        LEFT JOIN accounts a2 ON t.to_account_id = a2.id
        WHERE 1=1
    """
    params = []
    
    if filters:
        if filters.get("category"):
            query += " AND t.category = ?"
            params.append(filters["category"])
        if filters.get("type"):
            query += " AND t.type = ?"
            params.append(filters["type"])
        if filters.get("account_id"):
            query += " AND (t.account_id = ? OR t.to_account_id = ?)"
            params.append(filters["account_id"])
            params.append(filters["account_id"])
        if filters.get("search_text"):
            query += " AND (t.notes LIKE ? OR t.tags LIKE ? OR t.category LIKE ?)"
            term = f"%{filters['search_text']}%"
            params.extend([term, term, term])
        if filters.get("date_start"):
            query += " AND t.date >= ?"
            params.append(filters["date_start"])
        if filters.get("date_end"):
            query += " AND t.date <= ?"
            params.append(filters["date_end"])
        if filters.get("amount_min"):
            query += " AND t.amount >= ?"
            params.append(float(filters["amount_min"]))
        if filters.get("amount_max"):
            query += " AND t.amount <= ?"
            params.append(float(filters["amount_max"]))
            
    query += " ORDER BY t.date DESC, t.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_transaction(amount, date, t_type, category, account_id, to_account_id=None, notes=None, tags=None, receipt_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (amount, date, type, category, account_id, to_account_id, notes, tags, receipt_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (float(amount), date, t_type, category, account_id, to_account_id, notes, tags, receipt_path))
    conn.commit()
    conn.close()
    recalculate_account_balances()

def delete_transaction(transaction_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    recalculate_account_balances()

# ----------------- BUDGETS CRUD -----------------
def get_budgets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM budgets")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_budget(category, amount, period):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO budgets (category, amount, period) VALUES (?, ?, ?)", (category, float(amount), period))
    conn.commit()
    conn.close()

def delete_budget(budget_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    conn.close()

# ----------------- SAVINGS GOALS CRUD -----------------
def get_savings_goals():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM savings_goals")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_savings_goal(name, target_amount, saved_amount, target_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO savings_goals (name, target_amount, saved_amount, target_date) VALUES (?, ?, ?, ?)",
                   (name, float(target_amount), float(saved_amount), target_date))
    conn.commit()
    conn.close()

def update_savings_goal(goal_id, saved_amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE savings_goals SET saved_amount = ? WHERE id = ?", (float(saved_amount), goal_id))
    conn.commit()
    conn.close()

def delete_savings_goal(goal_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()

# ----------------- DEBTS CRUD -----------------
def get_debts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM debts")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_debt(d_type, person, amount, interest_rate, compounding_period, remaining_balance, emi_amount, start_date, due_date, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO debts (type, person, amount, interest_rate, compounding_period, remaining_balance, emi_amount, start_date, due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (d_type, person, float(amount), float(interest_rate), compounding_period, float(remaining_balance), float(emi_amount), start_date, due_date, notes))
    conn.commit()
    conn.close()

def update_debt_balance(debt_id, payment_amount):
    """
    Subtracted paid amount from remaining balance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT remaining_balance FROM debts WHERE id = ?", (debt_id,))
    row = cursor.fetchone()
    if row:
        new_bal = max(0.0, row["remaining_balance"] - float(payment_amount))
        cursor.execute("UPDATE debts SET remaining_balance = ? WHERE id = ?", (round(new_bal, 2), debt_id))
        conn.commit()
    conn.close()

def delete_debt(debt_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
    conn.commit()
    conn.close()

# ----------------- INVESTMENTS CRUD -----------------
def get_investments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investments")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_investment(name, i_type, invested_amount, current_value, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO investments (name, type, invested_amount, current_value, notes) VALUES (?, ?, ?, ?, ?)",
                   (name, i_type, float(invested_amount), float(current_value), notes))
    conn.commit()
    conn.close()

def update_investment_value(investment_id, current_value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE investments SET current_value = ? WHERE id = ?", (float(current_value), investment_id))
    conn.commit()
    conn.close()

def delete_investment(investment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM investments WHERE id = ?", (investment_id,))
    conn.commit()
    conn.close()

# ----------------- SUBSCRIPTIONS CRUD -----------------
def get_subscriptions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, a.name as account_name 
        FROM subscriptions s
        LEFT JOIN accounts a ON s.account_id = a.id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_subscription(name, amount, renewal_date, billing_cycle, account_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO subscriptions (name, amount, renewal_date, billing_cycle, account_id) VALUES (?, ?, ?, ?, ?)",
                   (name, float(amount), renewal_date, billing_cycle, account_id))
    conn.commit()
    conn.close()

def update_subscription_renewal(sub_id, new_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE subscriptions SET renewal_date = ? WHERE id = ?", (new_date, sub_id))
    conn.commit()
    conn.close()

def delete_subscription(sub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()

# ----------------- RECURRING CRUD & PROCESSOR -----------------
def get_recurring_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, a.name as account_name 
        FROM recurring_transactions r
        LEFT JOIN accounts a ON r.account_id = a.id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_recurring_transaction(name, type, amount, category, account_id, frequency, next_occurrence):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recurring_transactions (name, type, amount, category, account_id, frequency, next_occurrence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, type, float(amount), category, account_id, frequency, next_occurrence))
    conn.commit()
    conn.close()

def delete_recurring_transaction(rt_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recurring_transactions WHERE id = ?", (rt_id,))
    conn.commit()
    conn.close()

def run_recurring_transaction_check():
    """
    Checks if any recurring transaction is due (next_occurrence <= today).
    If so, creates a transaction, updates the next_occurrence, and recalculates balances.
    Runs recursively if the next occurrence is also in the past (e.g. app hasn't been opened for 2 months).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    cursor.execute("SELECT * FROM recurring_transactions")
    recur_items = cursor.fetchall()
    
    triggered_any = False
    
    for item in recur_items:
        rt_id = item["id"]
        name = item["name"]
        t_type = item["type"]
        amount = item["amount"]
        category = item["category"]
        account_id = item["account_id"]
        frequency = item["frequency"]
        next_occ_str = item["next_occurrence"]
        
        next_occ = datetime.strptime(next_occ_str, "%Y-%m-%d").date()
        
        while next_occ <= today:
            triggered_any = True
            # Insert standard transaction
            cursor.execute("""
                INSERT INTO transactions (amount, date, type, category, account_id, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (amount, next_occ.strftime("%Y-%m-%d"), t_type, category, account_id, f"Recurring: {name}", "recurring"))
            
            # Calculate next occurrence date
            if frequency == 'daily':
                next_occ += timedelta(days=1)
            elif frequency == 'weekly':
                next_occ += timedelta(weeks=1)
            elif frequency == 'monthly':
                # Add a month safely
                year = next_occ.year
                month = next_occ.month + 1
                if month > 12:
                    month = 1
                    year += 1
                day = min(next_occ.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
                next_occ = date(year, month, day)
            else:
                break # unknown frequency
                
        if triggered_any:
            cursor.execute("UPDATE recurring_transactions SET next_occurrence = ? WHERE id = ?", (next_occ.strftime("%Y-%m-%d"), rt_id))
            
    if triggered_any:
        conn.commit()
        recalculate_account_balances_connection(conn)
        
    conn.close()

# ----------------- BILLS CRUD -----------------
def get_bills():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, a.name as account_name 
        FROM bills b
        LEFT JOIN accounts a ON b.account_id = a.id
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_bill(name, type, amount, due_date, status, account_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bills (name, type, amount, due_date, status, account_id) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, type, float(amount), due_date, status, account_id))
    conn.commit()
    conn.close()

def pay_bill(bill_id, account_id):
    """
    Marks bill as paid and records an expense transaction in the ledger.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE id = ?", (bill_id,))
    bill = cursor.fetchone()
    if bill and bill["status"] != 'paid':
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("UPDATE bills SET status = 'paid', account_id = ? WHERE id = ?", (account_id, bill_id))
        # Insert transaction
        cursor.execute("""
            INSERT INTO transactions (amount, date, type, category, account_id, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (bill["amount"], today_str, "expense", bill["type"], account_id, f"Paid Bill: {bill['name']}", "bill"))
        conn.commit()
    conn.close()
    recalculate_account_balances()

def delete_bill(bill_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
    conn.commit()
    conn.close()

# ----------------- SPLIT GROUPS CRUD & CALCULATIONS -----------------
def get_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_group_details(group_id):
    """
    Returns full details for a group including member names, expenses, and payments.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
    group_row = cursor.fetchone()
    if not group_row:
        conn.close()
        return None
        
    group = dict(group_row)
    
    # Fetch members
    cursor.execute("SELECT * FROM group_members WHERE group_id = ?", (group_id,))
    members = [dict(m) for m in cursor.fetchall()]
    group["members"] = members
    
    # Fetch expenses with member names
    cursor.execute("""
        SELECT e.*, m.name as paid_by_member_name 
        FROM group_expenses e
        LEFT JOIN group_members m ON e.paid_by_member_id = m.id
        WHERE e.group_id = ?
        ORDER BY e.date DESC, e.id DESC
    """, (group_id,))
    expenses = [dict(e) for e in cursor.fetchall()]
    
    # Parse json details for each expense
    for exp in expenses:
        try:
            exp["details"] = json.loads(exp["details"])
        except:
            exp["details"] = {}
    group["expenses"] = expenses
    
    # Fetch payments (settlement cash transfers)
    cursor.execute("""
        SELECT p.*, m_from.name as from_member_name, m_to.name as to_member_name 
        FROM group_payments p
        LEFT JOIN group_members m_from ON p.from_member_id = m_from.id
        LEFT JOIN group_members m_to ON p.to_member_id = m_to.id
        WHERE p.group_id = ?
        ORDER BY p.date DESC, p.id DESC
    """, (group_id,))
    payments = [dict(p) for p in cursor.fetchall()]
    group["payments"] = payments
    
    conn.close()
    return group

def add_group(name, description, member_names):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO groups (name, description) VALUES (?, ?)", (name, description))
    group_id = cursor.lastrowid
    
    for m_name in member_names:
        if m_name.strip():
            cursor.execute("INSERT INTO group_members (group_id, name) VALUES (?, ?)", (group_id, m_name.strip()))
            
    conn.commit()
    conn.close()
    return group_id

def delete_group(group_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM group_payments WHERE group_id = ?", (group_id,))
    cursor.execute("DELETE FROM group_expenses WHERE group_id = ?", (group_id,))
    cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
    cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()

def add_group_expense(group_id, description, amount, paid_by_member_id, date, split_type, details_dict, personal_account_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO group_expenses (group_id, description, amount, paid_by_member_id, date, split_type, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (group_id, description, float(amount), paid_by_member_id, date, split_type, json.dumps(details_dict)))
    
    expense_id = cursor.lastrowid
    
    if personal_account_id:
        cursor.execute("""
            INSERT INTO transactions (amount, date, type, category, account_id, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (float(amount), date, 'expense', 'Other', int(personal_account_id), f"Split Group Expense: {description}", f"group_expense_{expense_id}"))
        recalculate_account_balances_connection(conn)
        
    conn.commit()
    conn.close()

def delete_group_expense(expense_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM group_expenses WHERE id = ?", (expense_id,))
    cursor.execute("DELETE FROM transactions WHERE tags = ?", (f"group_expense_{expense_id}",))
    recalculate_account_balances_connection(conn)
    conn.commit()
    conn.close()

def add_group_payment(group_id, from_member_id, to_member_id, amount, date, personal_account_id=None, personal_action=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO group_payments (group_id, from_member_id, to_member_id, amount, date)
        VALUES (?, ?, ?, ?, ?)
    """, (group_id, from_member_id, to_member_id, float(amount), date))
    
    payment_id = cursor.lastrowid
    
    if personal_account_id and personal_action:
        # Get names for nice note details
        cursor.execute("SELECT name FROM group_members WHERE id = ?", (from_member_id,))
        from_row = cursor.fetchone()
        from_name = from_row['name'] if from_row else 'Member'
        
        cursor.execute("SELECT name FROM group_members WHERE id = ?", (to_member_id,))
        to_row = cursor.fetchone()
        to_name = to_row['name'] if to_row else 'Member'
        
        notes = f"Group Settlement: {from_name} paid {to_name}"
        
        cursor.execute("""
            INSERT INTO transactions (amount, date, type, category, account_id, notes, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (float(amount), date, personal_action, 'Other', int(personal_account_id), notes, f"group_payment_{payment_id}"))
        recalculate_account_balances_connection(conn)
        
    conn.commit()
    conn.close()

def delete_group_payment(payment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM group_payments WHERE id = ?", (payment_id,))
    cursor.execute("DELETE FROM transactions WHERE tags = ?", (f"group_payment_{payment_id}",))
    recalculate_account_balances_connection(conn)
    conn.commit()
    conn.close()

def calculate_group_balances(group_id):
    """
    Computes running balances of a group.
    For each member:
      balance = Sum(expenses paid by member) - Sum(shares owed by member in all expenses) 
                + Sum(payments received by member) - Sum(payments sent by member).
    """
    group = get_group_details(group_id)
    if not group:
        return {}
        
    members = group["members"]
    member_names = [m["name"] for m in members]
    member_id_to_name = {m["id"]: m["name"] for m in members}
    
    # Initialize net balances
    balances = {m_name: 0.0 for m_name in member_names}
    
    # 1. Process Expenses
    from settlement import calculate_split
    for exp in group["expenses"]:
        payer_id = exp["paid_by_member_id"]
        payer_name = member_id_to_name.get(payer_id)
        if not payer_name:
            continue
            
        amt = exp["amount"]
        split_t = exp["split_type"]
        details = exp["details"]
        
        # Credit the payer
        balances[payer_name] += amt
        
        # Calculate shares
        shares = calculate_split(amt, split_t, member_names, details)
        
        # Debit each member their share
        for m_name, share in shares.items():
            if m_name in balances:
                balances[m_name] -= share
                
    # 2. Process Payments (Settlements)
    for pay in group["payments"]:
        from_id = pay["from_member_id"]
        to_id = pay["to_member_id"]
        amt = pay["amount"]
        
        from_name = member_id_to_name.get(from_id)
        to_name = member_id_to_name.get(to_id)
        
        if from_name:
            balances[from_name] += amt # they paid out, reducing their debt (adding to balance)
        if to_name:
            balances[to_name] -= amt # they received money, reducing their credit (subtracting from balance)
            
    # Round all values
    for m in balances:
        balances[m] = round(balances[m], 2)
        
    return balances
