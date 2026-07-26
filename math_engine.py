import math
from datetime import datetime, date
import calendar

def calculate_savings_rate(income, expenses):
    """
    Savings Rate = ((Income - Expenses) / Income) * 100
    Returns 0.0 if income <= 0
    """
    if income <= 0:
        return 0.0
    rate = ((income - expenses) / income) * 100
    return round(rate, 2)

def calculate_daily_burn_rate(monthly_expenses, days_elapsed):
    """
    Daily Burn Rate = Monthly Expenses / Days Elapsed
    """
    if days_elapsed <= 0:
        days_elapsed = 1
    return round(monthly_expenses / days_elapsed, 2)

def calculate_projected_spending(daily_average, days_in_month):
    """
    Projected Spend = Daily Average * Days in Month
    """
    return round(daily_average * days_in_month, 2)

def calculate_remaining_daily_budget(remaining_budget, days_left):
    """
    Remaining Daily Budget = Remaining Budget / Days Left
    """
    if days_left <= 0:
        return round(remaining_budget, 2)
    return round(max(0.0, remaining_budget) / days_left, 2)

def calculate_net_worth(assets, liabilities):
    """
    Net Worth = Assets - Liabilities
    """
    return round(assets - liabilities, 2)

def calculate_compound_interest(principal, rate_percent, times_compounded_per_year, years):
    """
    A = P * (1 + r/n)**(n*t)
    Returns (Total Amount, Total Interest Earned)
    """
    P = float(principal)
    r = float(rate_percent) / 100.0
    n = int(times_compounded_per_year)
    t = float(years)
    
    if n <= 0 or t <= 0:
        return round(P, 2), 0.0
        
    total_amount = P * ((1 + r / n) ** (n * t))
    interest_earned = total_amount - P
    return round(total_amount, 2), round(interest_earned, 2)

def calculate_loan_emi(principal, annual_rate_percent, tenure_months):
    """
    Calculate EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r is monthly interest rate, n is tenure in months.
    Returns (EMI, Total Payment, Total Interest)
    """
    P = float(principal)
    annual_rate = float(annual_rate_percent)
    n = int(tenure_months)
    
    if P <= 0 or n <= 0:
        return 0.0, 0.0, 0.0
        
    if annual_rate <= 0:
        emi = P / n
        total_payment = P
        total_interest = 0.0
        return round(emi, 2), round(total_payment, 2), round(total_interest, 2)
        
    # Monthly interest rate
    r = (annual_rate / 12.0) / 100.0
    
    emi = P * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    total_payment = emi * n
    total_interest = total_payment - P
    
    return round(emi, 2), round(total_payment, 2), round(total_interest, 2)

def generate_amortization_schedule(principal, annual_rate_percent, tenure_months):
    """
    Generates a month-by-month amortization schedule.
    Returns list of dicts containing: month, emi, principal_paid, interest_paid, remaining_principal
    """
    P = float(principal)
    annual_rate = float(annual_rate_percent)
    n = int(tenure_months)
    
    emi, total_payment, total_interest = calculate_loan_emi(P, annual_rate, n)
    if emi <= 0:
        return []
        
    schedule = []
    remaining_principal = P
    r = (annual_rate / 12.0) / 100.0 if annual_rate > 0 else 0.0
    
    for month in range(1, n + 1):
        if r > 0:
            interest_paid = remaining_principal * r
            principal_paid = emi - interest_paid
        else:
            interest_paid = 0.0
            principal_paid = emi
            
        # Adjust for final month rounding errors
        if month == n or remaining_principal < principal_paid:
            principal_paid = remaining_principal
            emi_actual = principal_paid + interest_paid
        else:
            emi_actual = emi
            
        remaining_principal -= principal_paid
        if remaining_principal < 0.01:
            remaining_principal = 0.0
            
        schedule.append({
            "month": month,
            "emi": round(emi_actual, 2),
            "principal_paid": round(principal_paid, 2),
            "interest_paid": round(interest_paid, 2),
            "remaining_principal": round(remaining_principal, 2)
        })
        
        if remaining_principal <= 0:
            break
            
    return schedule

def calculate_emergency_fund_tracker(liquid_savings, average_monthly_expenses):
    """
    Returns the number of months the emergency fund covers.
    """
    if average_monthly_expenses <= 0:
        return 999.9  # Avoid division by zero, indicates effectively infinite coverage
    cover = liquid_savings / average_monthly_expenses
    return round(cover, 1)

def get_days_in_current_month():
    today = date.today()
    return calendar.monthrange(today.year, today.month)[1]

def get_days_elapsed_in_current_month():
    today = date.today()
    return today.day

def get_days_remaining_in_current_month():
    today = date.today()
    total_days = calendar.monthrange(today.year, today.month)[1]
    return total_days - today.day
