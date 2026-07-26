import unittest
import sys
import os

# Adjust path to find modules in parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from math_engine import (
    calculate_savings_rate,
    calculate_daily_burn_rate,
    calculate_projected_spending,
    calculate_remaining_daily_budget,
    calculate_compound_interest,
    calculate_loan_emi,
    generate_amortization_schedule
)

class TestMathEngine(unittest.TestCase):
    
    def test_savings_rate(self):
        self.assertEqual(calculate_savings_rate(5000, 3000), 40.0)
        self.assertEqual(calculate_savings_rate(0, 100), 0.0)
        self.assertEqual(calculate_savings_rate(1000, 1200), -20.0)
        self.assertEqual(calculate_savings_rate(-500, 100), 0.0)
        
    def test_daily_burn_rate(self):
        self.assertEqual(calculate_daily_burn_rate(1500, 15), 100.0)
        self.assertEqual(calculate_daily_burn_rate(300, 0), 300.0) # falls back to 1 day
        self.assertEqual(calculate_daily_burn_rate(100, -5), 100.0)
        
    def test_projected_spending(self):
        self.assertEqual(calculate_projected_spending(30.0, 31), 930.0)
        self.assertEqual(calculate_projected_spending(0, 30), 0.0)
        
    def test_remaining_daily_budget(self):
        self.assertEqual(calculate_remaining_daily_budget(450, 15), 30.0)
        self.assertEqual(calculate_remaining_daily_budget(-50, 5), 0.0)
        self.assertEqual(calculate_remaining_daily_budget(100, 0), 100.0) # falls back to raw budget
        
    def test_compound_interest(self):
        # P = 1000, r = 5%, n = 12 (monthly), t = 2 years
        total, interest = calculate_compound_interest(1000, 5.0, 12, 2)
        # Expected: A = 1000 * (1 + 0.05/12)**24 = 1104.94
        self.assertAlmostEqual(total, 1104.94, places=1)
        self.assertAlmostEqual(interest, 104.94, places=1)
        
    def test_loan_emi(self):
        # P = 10000, r = 12% annual, n = 12 months (1 year)
        # Monthly interest rate r = 12% / 12 / 100 = 0.01
        # EMI = 10000 * 0.01 * (1.01)**12 / ((1.01)**12 - 1) = 888.49
        emi, total, interest = calculate_loan_emi(10000, 12.0, 12)
        self.assertEqual(emi, 888.49)
        self.assertEqual(total, 10661.85)
        self.assertEqual(interest, 661.85)
        
    def test_amortization_schedule(self):
        schedule = generate_amortization_schedule(10000, 12.0, 12)
        self.assertEqual(len(schedule), 12)
        self.assertEqual(schedule[0]["month"], 1)
        self.assertEqual(schedule[11]["month"], 12)
        self.assertEqual(schedule[11]["remaining_principal"], 0.0)

if __name__ == '__main__':
    unittest.main()
