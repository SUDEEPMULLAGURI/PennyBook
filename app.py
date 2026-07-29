from flask import Flask, request, jsonify, render_template, send_file, Response, send_from_directory, redirect
import os
import io
import csv
import uuid
import threading
import time
import webbrowser
from datetime import datetime, date
import calendar
import webview

# Import project modules
import database
import math_engine
import settlement

LAST_SYNC_TIME = 0

import sys
if getattr(sys, 'frozen', False):
    # The application is running in a PyInstaller bundle
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['TEMPLATES_AUTO_RELOAD'] = True
RECEIPTS_DIR = os.path.abspath('receipts')

@app.after_request
def update_last_sync_time(response):
    global LAST_SYNC_TIME
    if request.method in ['POST', 'PUT', 'DELETE'] and request.path.startswith('/api/'):
        if response.status_code in [200, 201]:
            LAST_SYNC_TIME = time.time()
    return response

# Ensure receipts directory exists
if not os.path.exists(RECEIPTS_DIR):
    os.makedirs(RECEIPTS_DIR)

# Initialize database on startup
database.init_db()

# ----------------- RECURRING RUNNER BACKGROUND THREAD -----------------
def start_recurring_scheduler_loop():
    """
    Runs a check for recurring transactions on boot, and then every hour.
    """
    time.sleep(3) # Wait for database to initialize fully
    while True:
        try:
            database.run_recurring_transaction_check()
        except Exception as e:
            print(f"Error in background recurring scheduler: {e}")
        time.sleep(3600) # hourly check

# Start background thread
threading.Thread(target=start_recurring_scheduler_loop, daemon=True).start()

import socket
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route('/api/system/ip')
def system_ip():
    return jsonify({"ip": get_local_ip(), "port": 5000})

# ----------------- STATIC VIEWS -----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mobile')
def mobile_companion_redirect():
    return redirect('/m')

@app.route('/m')
def mobile_companion():
    return render_template('mobile.html')

@app.route('/mobile-sw.js')
def mobile_sw():
    return send_from_directory('static/mobile', 'sw.js', mimetype='application/javascript')

@app.route('/mobile-manifest.json')
def mobile_manifest():
    return send_from_directory('static/mobile', 'manifest.json', mimetype='application/json')

@app.route('/api/mobile/metadata', methods=['GET'])
def mobile_metadata():
    accounts = database.get_accounts()
    groups = database.get_groups()
    for g in groups:
        details = database.get_group_details(g['id'])
        if details:
            g['members'] = details.get('members', [])
    return jsonify({"accounts": accounts, "groups": groups})

# ----------------- ACCOUNTS APIs -----------------
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    return jsonify(database.get_accounts())

@app.route('/api/accounts', methods=['POST'])
def add_account():
    data = request.json
    database.add_account(data['name'], data['type'], data['initial_balance'])
    return jsonify({"status": "success"})

@app.route('/api/accounts/<int:acc_id>', methods=['DELETE'])
def delete_account(acc_id):
    database.delete_account(acc_id)
    return jsonify({"status": "success"})


# ----------------- TRANSACTIONS APIs -----------------
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    return jsonify(database.get_transactions())

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    # Read forms data (handles multi-part form for uploads)
    amount = float(request.form.get('amount', 0))
    t_type = request.form.get('type')
    date_val = request.form.get('date')
    category = request.form.get('category')
    account_id = int(request.form.get('account_id', 0))
    notes = request.form.get('notes', '')
    tags = request.form.get('tags', '')
    
    # Handle File upload
    receipt_path = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{ext}"
            save_path = os.path.join(RECEIPTS_DIR, unique_filename)
            file.save(save_path)
            receipt_path = unique_filename
            
    database.add_transaction(amount, date_val, t_type, category, account_id, None, notes, tags, receipt_path)
    return jsonify({"status": "success"})

@app.route('/api/transactions/transfer', methods=['POST'])
def add_transfer():
    data = request.json
    # Transfers create a transaction with type = 'transfer'
    database.add_transaction(
        amount=data['amount'],
        date=data['date'],
        t_type='transfer',
        category='Transfer',
        account_id=int(data['from_account_id']),
        to_account_id=int(data['to_account_id']),
        notes="Account transfer",
        tags="transfer"
    )
    return jsonify({"status": "success"})

@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
def delete_transaction(tx_id):
    database.delete_transaction(tx_id)
    return jsonify({"status": "success"})

@app.route('/api/transactions/query', methods=['POST'])
def query_transactions():
    filters = request.json.get('filters', {})
    txs = database.get_transactions(filters)
    
    # Calculate category sum breakdown for expenses
    cat_totals = {}
    for tx in txs:
        if tx['type'] == 'expense':
            cat = tx['category']
            cat_totals[cat] = cat_totals.get(cat, 0.0) + tx['amount']
            
    # Round category totals
    for cat in cat_totals:
        cat_totals[cat] = round(cat_totals[cat], 2)
        
    return jsonify({
        "transactions": txs,
        "category_totals": cat_totals
    })

@app.route('/api/transactions/export', methods=['GET'])
def export_transactions():
    # Construct filters from GET args
    filters = {}
    if request.args.get('search_text'): filters['search_text'] = request.args.get('search_text')
    if request.args.get('type'): filters['type'] = request.args.get('type')
    if request.args.get('account_id'): filters['account_id'] = int(request.args.get('account_id'))
    if request.args.get('amount_min'): filters['amount_min'] = float(request.args.get('amount_min'))
    if request.args.get('amount_max'): filters['amount_max'] = float(request.args.get('amount_max'))
    if request.args.get('date_start'): filters['date_start'] = request.args.get('date_start')
    if request.args.get('date_end'): filters['date_end'] = request.args.get('date_end')
    
    txs = database.get_transactions(filters)
    exp_format = request.args.get('format', 'csv')
    
    if exp_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Type', 'Category', 'Account', 'To Account (For Transfers)', 'Amount (₹)', 'Notes', 'Tags'])
        for tx in txs:
            writer.writerow([
                tx['date'], tx['type'].upper(), tx['category'],
                tx['account_name'] or '', tx['to_account_name'] or '',
                tx['amount'], tx['notes'] or '', tx['tags'] or ''
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=pennybook_statement.csv"}
        )
    else:
        # Export as a beautiful HTML ledger sheet (suitable for printing / saving as PDF)
        html = """
        <html>
        <head>
            <title>PennyBook Financial Statement</title>
            <style>
                body { font-family: sans-serif; color: #333; margin: 30px; }
                h1 { border-bottom: 2px solid #8a2be2; padding-bottom: 10px; color: #1e1335; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th { background-color: #8a2be2; color: white; padding: 10px; text-align: left; }
                td { padding: 10px; border-bottom: 1px solid #ddd; }
                .amount { font-weight: bold; }
                .income { color: green; }
                .expense { color: red; }
                .transfer { color: blue; }
                .meta { font-size: 12px; color: #666; margin-top: 5px; }
            </style>
        </head>
        <body onload="window.print()">
            <h1>PennyBook Financial Statement</h1>
            <p><strong>Generated On:</strong> """ + datetime.now().strftime("%B %d, %Y %I:%M %p") + """</p>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Category</th>
                        <th>Account Path</th>
                        <th>Amount (₹)</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
        """
        for tx in txs:
            sign = '+' if tx['type'] == 'income' else '-' if tx['type'] == 'expense' else ''
            acc = tx['account_name']
            if tx['type'] == 'transfer':
                acc = f"{tx['account_name']} &rarr; {tx['to_account_name']}"
            html += f"""
                <tr>
                    <td>{tx['date']}</td>
                    <td><span style="font-weight: bold;">{tx['type'].upper()}</span></td>
                    <td>{tx['category']}</td>
                    <td>{acc or ''}</td>
                    <td class="amount {tx['type']}"> {sign}₹{tx['amount']:.2f}</td>
                    <td>{tx['notes'] or ''}</td>
                </tr>
            """
        html += """
                </tbody>
            </table>
            <div class="meta">Total ledger matches: """ + str(len(txs)) + """</div>
        </body>
        </html>
        """
        return Response(html, mimetype="text/html")


@app.route('/api/sync/transactions', methods=['POST'])
def sync_transactions():
    data = request.json
    transactions = data.get('transactions', [])
    inserted_count = 0
    
    accounts = database.get_accounts()
    
    for tx in transactions:
        # Match or default account ID
        acc_id = None
        action = None
        
        if tx.get('type') == 'payback':
            acc_str = tx.get('account', 'NONE')
            if acc_str != 'NONE' and '_' in acc_str:
                action, acc_name = acc_str.split('_', 1)
                if action == 'sent': action = 'expense'
                elif action == 'received': action = 'income'
                for a in accounts:
                    if a['name'].lower() == acc_name.lower():
                        acc_id = a['id']
                        break
        else:
            for a in accounts:
                if a['name'].lower() == tx.get('account', '').lower():
                    acc_id = a['id']
                    break
            if not acc_id and accounts and tx.get('account') != 'NONE':
                acc_id = accounts[0]['id']
            
        try:
            if tx.get('type') == 'group_expense':
                database.add_group_expense(
                    group_id=int(tx.get('group_id')),
                    description=tx.get('notes') or tx.get('category'),
                    amount=float(tx.get('amount', 0)),
                    paid_by_member_id=int(tx.get('paid_by_id')),
                    date=tx.get('date'),
                    split_type=tx.get('split_type', 'equal'),
                    details_dict=tx.get('split_details', {}),
                    personal_account_id=acc_id
                )
            elif tx.get('type') == 'payback':
                database.add_group_payment(
                    group_id=int(tx.get('group_id')),
                    from_member_id=int(tx.get('from_member_id')),
                    to_member_id=int(tx.get('to_member_id')),
                    amount=float(tx.get('amount', 0)),
                    date=tx.get('date'),
                    personal_account_id=acc_id,
                    personal_action=action
                )
            else:
                database.add_transaction(
                    date=tx.get('date'),
                    t_type=tx.get('type', 'expense'),
                    category=tx.get('category', 'Uncategorized'),
                    amount=float(tx.get('amount', 0)),
                    notes=tx.get('notes', ''),
                    account_id=acc_id,
                    to_account_id=None
                )
            inserted_count += 1
        except Exception as e:
            print(f"Error syncing transaction {tx}: {e}")
            
    return jsonify({"status": "success", "inserted": inserted_count})

@app.route('/api/system/sync_status', methods=['GET'])
def system_sync_status():
    return jsonify({"last_sync_time": LAST_SYNC_TIME})

# ----------------- RECEIPT UPLOADS VIEWER -----------------
@app.route('/api/receipts/view')
def get_receipt():
    filename = request.args.get('path')
    safe_path = os.path.join(RECEIPTS_DIR, filename)
    if os.path.exists(safe_path) and os.path.commonpath([RECEIPTS_DIR]) == os.path.commonpath([RECEIPTS_DIR, safe_path]):
        return send_file(safe_path)
    return "Receipt File Not Found", 404


# ----------------- BUDGETS & SAVINGS APIs -----------------
@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    return jsonify(database.get_budgets())

@app.route('/api/budgets', methods=['POST'])
def add_budget():
    data = request.json
    database.add_budget(data['category'], data['amount'], data['period'])
    return jsonify({"status": "success"})

@app.route('/api/budgets/<int:b_id>', methods=['DELETE'])
def delete_budget(b_id):
    database.delete_budget(b_id)
    return jsonify({"status": "success"})

@app.route('/api/savings', methods=['GET'])
def get_savings():
    return jsonify(database.get_savings_goals())

@app.route('/api/savings', methods=['POST'])
def add_savings():
    data = request.json
    database.add_savings_goal(data['name'], data['target_amount'], data['saved_amount'], data['target_date'])
    return jsonify({"status": "success"})

@app.route('/api/savings/<int:sg_id>', methods=['PUT'])
def update_savings(sg_id):
    data = request.json
    database.update_savings_goal(sg_id, data['saved_amount'])
    return jsonify({"status": "success"})

@app.route('/api/savings/<int:sg_id>', methods=['DELETE'])
def delete_savings(sg_id):
    database.delete_savings_goal(sg_id)
    return jsonify({"status": "success"})


# ----------------- MONTHLY BUDGET PLANNER APIs -----------------
@app.route('/api/budget_plan', methods=['GET'])
def get_budget_plan():
    return jsonify(database.get_monthly_plan())

@app.route('/api/budget_plan', methods=['POST'])
def save_budget_plan():
    data = request.json
    database.save_monthly_plan(data)
    return jsonify({"status": "success"})


# ----------------- DEBTS & LOANS APIs -----------------
@app.route('/api/debts', methods=['GET'])
def get_debts():
    return jsonify(database.get_debts())

@app.route('/api/debts', methods=['POST'])
def add_debt():
    data = request.json
    database.add_debt(
        data['type'], data['person'], data['amount'], data['interest_rate'],
        data['compounding_period'], data['remaining_balance'], data['emi_amount'],
        data['start_date'], data['due_date'], data['notes']
    )
    return jsonify({"status": "success"})

@app.route('/api/debts/<int:debt_id>/repay', methods=['POST'])
def repay_debt(debt_id):
    data = request.json
    amount = float(data['amount'])
    account_id = int(data['account_id'])
    d_type = data['type']
    
    # 1. Deduct debt balance
    database.update_debt_balance(debt_id, amount)
    
    # 2. Add ledger entries (repayment is an expense if we borrowed, or income if we lent)
    t_type = 'expense' if d_type == 'borrowed' else 'income'
    category = 'Medical' if d_type == 'borrowed' else 'Other' # default categories or generic
    notes = f"Debt repayment to {d_type}"
    database.add_transaction(amount, datetime.now().strftime("%Y-%m-%d"), t_type, "Other", account_id, None, notes, "debt_repay")
    
    return jsonify({"status": "success"})

@app.route('/api/debts/<int:debt_id>', methods=['DELETE'])
def delete_debt(debt_id):
    database.delete_debt(debt_id)
    return jsonify({"status": "success"})


# ----------------- INVESTMENTS APIs -----------------
@app.route('/api/investments', methods=['GET'])
def get_investments():
    return jsonify(database.get_investments())

@app.route('/api/investments', methods=['POST'])
def add_investment():
    data = request.json
    database.add_investment(data['name'], data['type'], data['invested_amount'], data['current_value'], data['notes'])
    return jsonify({"status": "success"})

@app.route('/api/investments/<int:iv_id>', methods=['PUT'])
def update_investment(iv_id):
    data = request.json
    database.update_investment_value(iv_id, data['current_value'])
    return jsonify({"status": "success"})

@app.route('/api/investments/<int:iv_id>', methods=['DELETE'])
def delete_investment(iv_id):
    database.delete_investment(iv_id)
    return jsonify({"status": "success"})


# ----------------- SUBSCRIPTIONS & BILLS APIs -----------------
@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    return jsonify(database.get_subscriptions())

@app.route('/api/subscriptions', methods=['POST'])
def add_subscription():
    data = request.json
    database.add_subscription(data['name'], data['amount'], data['renewal_date'], data['billing_cycle'], data['account_id'])
    return jsonify({"status": "success"})

@app.route('/api/subscriptions/<int:sub_id>/renew', methods=['POST'])
def renew_subscription(sub_id):
    data = request.json
    new_renewal = data['renewal_date']
    
    # Add a ledger expense transaction for the subscription payment
    conn = database.get_db_connection()
    sub = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    if sub:
        database.add_transaction(
            amount=sub['amount'],
            date=datetime.now().strftime("%Y-%m-%d"),
            t_type='expense',
            category='Entertainment',
            account_id=sub['account_id'],
            notes=f"Renewal payment: {sub['name']}",
            tags="subscription"
        )
        database.update_subscription_renewal(sub_id, new_renewal)
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/subscriptions/<int:sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    database.delete_subscription(sub_id)
    return jsonify({"status": "success"})

@app.route('/api/bills', methods=['GET'])
def get_bills():
    return jsonify(database.get_bills())

@app.route('/api/bills', methods=['POST'])
def add_bill():
    data = request.json
    database.add_bill(data['name'], data['type'], data['amount'], data['due_date'], data['status'], data['account_id'])
    return jsonify({"status": "success"})

@app.route('/api/bills/<int:bill_id>/pay', methods=['POST'])
def pay_bill(bill_id):
    data = request.json
    database.pay_bill(bill_id, data['account_id'])
    return jsonify({"status": "success"})

@app.route('/api/bills/<int:bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    database.delete_bill(bill_id)
    return jsonify({"status": "success"})

@app.route('/api/recurring', methods=['GET'])
def get_recurring():
    return jsonify(database.get_recurring_transactions())

@app.route('/api/recurring', methods=['POST'])
def add_recurring():
    data = request.json
    database.add_recurring_transaction(
        data['name'], data['type'], data['amount'], data['category'],
        data['account_id'], data['frequency'], data['next_occurrence']
    )
    return jsonify({"status": "success"})

@app.route('/api/recurring/<int:rt_id>', methods=['DELETE'])
def delete_recurring(rt_id):
    database.delete_recurring_transaction(rt_id)
    return jsonify({"status": "success"})


# ----------------- SPLIT GROUP APIs -----------------
@app.route('/api/groups', methods=['GET'])
def get_groups():
    return jsonify(database.get_groups())

@app.route('/api/groups', methods=['POST'])
def add_group():
    data = request.json
    g_id = database.add_group(data['name'], data['description'], data['members'])
    return jsonify({"status": "success", "group_id": g_id})

@app.route('/api/groups/<int:g_id>', methods=['GET'])
def get_group_details(g_id):
    details = database.get_group_details(g_id)
    if details:
        return jsonify(details)
    return "Group Not Found", 404

@app.route('/api/groups/<int:g_id>', methods=['DELETE'])
def delete_group(g_id):
    database.delete_group(g_id)
    return jsonify({"status": "success"})

@app.route('/api/groups/<int:g_id>/expenses', methods=['POST'])
def add_group_expense(g_id):
    data = request.json
    database.add_group_expense(
        g_id, data['description'], data['amount'], data['paid_by_member_id'],
        data['date'], data['split_type'], data['details'],
        personal_account_id=data.get('personal_account_id')
    )
    return jsonify({"status": "success"})

@app.route('/api/groups/expenses/<int:exp_id>', methods=['DELETE'])
def delete_group_expense(exp_id):
    database.delete_group_expense(exp_id)
    return jsonify({"status": "success"})

@app.route('/api/groups/<int:g_id>/payments', methods=['POST'])
def add_group_payment(g_id):
    data = request.json
    database.add_group_payment(
        g_id, data['from_member_id'], data['to_member_id'], data['amount'], data['date'],
        personal_account_id=data.get('personal_account_id'),
        personal_action=data.get('personal_action')
    )
    return jsonify({"status": "success"})

@app.route('/api/groups/payments/<int:pay_id>', methods=['DELETE'])
def delete_group_payment(pay_id):
    database.delete_group_payment(pay_id)
    return jsonify({"status": "success"})

@app.route('/api/groups/<int:g_id>/balances', methods=['GET'])
def get_group_balances(g_id):
    return jsonify(database.calculate_group_balances(g_id))

@app.route('/api/groups/<int:g_id>/settlements', methods=['GET'])
def get_group_settlements(g_id):
    balances = database.calculate_group_balances(g_id)
    settlements = settlement.calculate_settlements(balances)
    return jsonify(settlements)


# ----------------- CALCULATORS APIs -----------------
@app.route('/api/calc/fire_excel', methods=['POST'])
def calc_fire_excel():
    data = request.json
    result = math_engine.calculate_fire_excel_model(
        int(data['current_age']),
        float(data['current_income']),
        float(data['salary_growth']),
        float(data['current_expense']),
        float(data['current_corpus']),
        int(data['target_age']),
        float(data['inflation']),
        float(data['expected_return'])
    )
    return jsonify(result)

@app.route('/api/calc/compound', methods=['POST'])
def calc_compound():
    data = request.json
    total, interest = math_engine.calculate_compound_interest(
        data['principal'], data['rate'], data['times_compounded_per_year'], data['years']
    )
    return jsonify({
        "total_amount": total,
        "interest_earned": interest
    })

@app.route('/api/calc/loan', methods=['POST'])
def calc_loan():
    data = request.json
    emi, total, interest = math_engine.calculate_loan_emi(
        data['principal'], data['rate'], data['tenure_months']
    )
    sched = math_engine.generate_amortization_schedule(
        data['principal'], data['rate'], data['tenure_months']
    )
    return jsonify({
        "emi": emi,
        "total_payment": total,
        "total_interest": interest,
        "schedule": sched
    })


# ----------------- FINANCIAL STATS & DASHBOARD APIs -----------------
@app.route('/api/stats/global', methods=['GET'])
def get_global_stats():
    # 1. Recalculate Net Worth
    # Net Worth = Sum(Accounts) + Sum(Investments) - Sum(Debts type borrowed)
    conn = database.get_db_connection()
    
    # Sum Accounts
    accs_sum = conn.execute("SELECT SUM(balance) FROM accounts").fetchone()[0] or 0.0
    
    # Sum Investments Current Value
    invests_sum = conn.execute("SELECT SUM(current_value) FROM investments").fetchone()[0] or 0.0
    
    # Sum Debts Remaining Borrowed
    debts_borrowed = conn.execute("SELECT SUM(remaining_balance) FROM debts WHERE type = 'borrowed'").fetchone()[0] or 0.0
    
    net_worth = accs_sum + invests_sum - debts_borrowed
    
    # 2. Monthly Income and Expenses (current month)
    today = date.today()
    start_of_month = today.strftime("%Y-%m-01")
    end_of_month = today.strftime(f"%Y-%m-{calendar.monthrange(today.year, today.month)[1]}")
    
    income_month = conn.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE type = 'income' AND date >= ? AND date <= ?
    """, (start_of_month, end_of_month)).fetchone()[0] or 0.0
    
    expense_month = conn.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE type = 'expense' AND date >= ? AND date <= ?
    """, (start_of_month, end_of_month)).fetchone()[0] or 0.0
    
    net_flow = income_month - expense_month
    savings_rate = math_engine.calculate_savings_rate(income_month, expense_month)
    
    conn.close()
    return jsonify({
        "net_worth": round(net_worth, 2),
        "savings_rate": savings_rate,
        "net_cash_flow": round(net_flow, 2)
    })

@app.route('/api/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    conn = database.get_db_connection()
    today = date.today()
    
    # Assets (positive accounts + investments)
    accs_pos = conn.execute("SELECT SUM(balance) FROM accounts WHERE balance > 0").fetchone()[0] or 0.0
    invests = conn.execute("SELECT SUM(current_value) FROM investments").fetchone()[0] or 0.0
    assets = accs_pos + invests
    
    # Liabilities (negative accounts + borrowed debts)
    accs_neg = abs(conn.execute("SELECT SUM(balance) FROM accounts WHERE balance < 0").fetchone()[0] or 0.0)
    debts = conn.execute("SELECT SUM(remaining_balance) FROM debts WHERE type = 'borrowed'").fetchone()[0] or 0.0
    liabilities = accs_neg + debts
    
    # Monthly burn rate
    start_of_month = today.strftime("%Y-%m-01")
    end_of_month = today.strftime(f"%Y-%m-{calendar.monthrange(today.year, today.month)[1]}")
    monthly_expenses = conn.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE type = 'expense' AND date >= ? AND date <= ?
    """, (start_of_month, end_of_month)).fetchone()[0] or 0.0
    
    days_elapsed = today.day
    burn_rate = math_engine.calculate_daily_burn_rate(monthly_expenses, days_elapsed)
    
    # Remaining Daily Budget
    # Budgets sum
    total_budget = conn.execute("SELECT SUM(amount) FROM budgets").fetchone()[0] or 0.0
    remaining_budget = total_budget - monthly_expenses
    
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day
    remaining_daily = math_engine.calculate_remaining_daily_budget(remaining_budget, days_left)
    
    conn.close()
    return jsonify({
        "assets": round(assets, 2),
        "liabilities": round(liabilities, 2),
        "burn_rate": burn_rate,
        "days_elapsed": days_elapsed,
        "remaining_daily": remaining_daily,
        "days_left": days_left
    })

@app.route('/api/stats/cashflow-trends', methods=['GET'])
def get_cashflow_trends():
    """
    Returns monthly income/expenses sums for the last 6 months.
    """
    conn = database.get_db_connection()
    today = date.today()
    
    labels = []
    income = []
    expense = []
    
    for i in range(5, -1, -1):
        # Subtract months
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
            
        start_date = f"{y:04d}-{m:02d}-01"
        end_date = f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]}"
        
        inc_sum = conn.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE type = 'income' AND date >= ? AND date <= ?
        """, (start_date, end_date)).fetchone()[0] or 0.0
        
        exp_sum = conn.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE type = 'expense' AND date >= ? AND date <= ?
        """, (start_date, end_date)).fetchone()[0] or 0.0
        
        month_name = calendar.month_name[m][:3]
        labels.append(f"{month_name} {y}")
        income.append(round(inc_sum, 2))
        expense.append(round(exp_sum, 2))
        
    conn.close()
    return jsonify({
        "labels": labels,
        "income": income,
        "expense": expense
    })

@app.route('/api/stats/category-spending', methods=['GET'])
def get_category_spending():
    category = request.args.get('category')
    today = date.today()
    start_of_month = today.strftime("%Y-%m-01")
    end_of_month = today.strftime(f"%Y-%m-{calendar.monthrange(today.year, today.month)[1]}")
    
    conn = database.get_db_connection()
    spent = conn.execute("""
        SELECT SUM(amount) FROM transactions 
        WHERE type = 'expense' AND category = ? AND date >= ? AND date <= ?
    """, (category, start_of_month, end_of_month)).fetchone()[0] or 0.0
    conn.close()
    
    return jsonify({"spent": round(spent, 2)})

@app.route('/api/stats/upcoming-dues', methods=['GET'])
def get_upcoming_dues():
    """
    Returns bills and subscriptions due in the next 30 days.
    """
    conn = database.get_db_connection()
    today = date.today()
    thirty_days_later = today + timedelta(days=30)
    
    today_str = today.strftime("%Y-%m-%d")
    later_str = thirty_days_later.strftime("%Y-%m-%d")
    
    dues = []
    
    # 1. Unpaid Bills
    bills = conn.execute("""
        SELECT name, amount, due_date, type FROM bills 
        WHERE status = 'unpaid' AND due_date >= ? AND due_date <= ?
    """, (today_str, later_str)).fetchall()
    
    for b in bills:
        dues.append({
            "name": b['name'],
            "amount": b['amount'],
            "due_date": b['due_date'],
            "source": b['type']
        })
        
    # 2. Subscriptions
    subs = conn.execute("""
        SELECT s.name, s.amount, s.renewal_date, a.name as acc_name FROM subscriptions s
        LEFT JOIN accounts a ON s.account_id = a.id
        WHERE s.renewal_date >= ? AND s.renewal_date <= ?
    """, (today_str, later_str)).fetchall()
    
    for s in subs:
        dues.append({
            "name": s['name'],
            "amount": s['amount'],
            "due_date": s['renewal_date'],
            "source": s['acc_name'] or 'Subscription'
        })
        
    dues.sort(key=lambda x: x['due_date'])
    conn.close()
    return jsonify(dues)


# ----------------- SERVER LAUNCHER -----------------
def run_flask_server():
    """
    Runs Flask server on localhost port 5000.
    """
    import socket
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    local_ip = get_local_ip()
    print("=" * 60)
    print("PennyBook is running!")
    print(f"Access on this PC: http://127.0.0.1:5000")
    print(f"Access on your phone (via WiFi): http://{local_ip}:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

if __name__ == '__main__':
    # Start Flask server in a daemon thread so it runs simultaneously
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Let server boot up
    time.sleep(1.5)
    
    class DesktopAPI:
        def __init__(self):
            self._window = None
        def minimize(self):
            if self._window: self._window.minimize()
        def toggle_maximize(self):
            if self._window: self._window.toggle_fullscreen()
        def close(self):
            if self._window: self._window.destroy()

    # Launch pywebview Native Window on the main thread
    try:
        print("Launching PennyBook Desktop Native Interface...")
        api = DesktopAPI()
        window = webview.create_window(
            title="PennyBook — Calculated Finance",
            url="http://127.0.0.1:5000",
            width=1280,
            height=800,
            min_size=(1024, 768),
            frameless=True,
            easy_drag=False,
            fullscreen=True,
            js_api=api
        )
        api._window = window
        
        # Suppress WinForms thread exception dialogs on close (specifically pywebview's BrowserProcessId NoneType error)
        try:
            import clr
            clr.AddReference('System.Windows.Forms')
            from System.Windows.Forms import Application, UnhandledExceptionMode
            
            def handle_thread_exception(sender, event_args):
                exc = event_args.Exception
                if exc and "BrowserProcessId" in str(exc):
                    # Suppress the pywebview browser close race condition error
                    return
                print(f"Ignored WinForms exception: {exc}")
                
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException)
            Application.ThreadException += handle_thread_exception
            print("Configured WinForms thread exception safety handler.")
        except Exception as handler_err:
            # Silently pass on non-Windows/non-CLR environments
            pass

        webview.start()
    except Exception as e:
        print(f"pywebview native UI engine did not start. Running in browser window instead. Error: {e}")
        try:
            webbrowser.open("http://127.0.0.1:5000")
        except Exception as wb_err:
            print(f"Failed to open fallback web browser: {wb_err}")
        # Hold the thread alive so the daemon thread continues to serve the browser
        while True:
            time.sleep(10)
