import unittest
import sys
import os

# Adjust path to find modules in parent dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from settlement import calculate_split, calculate_settlements

class TestSettlement(unittest.TestCase):
    
    def test_equal_split(self):
        members = ["John", "Alice", "Bob", "Myself"]
        shares = calculate_split(120.0, "equal", members, {"participants": ["John", "Alice", "Bob", "Myself"]})
        self.assertEqual(shares["John"], 30.0)
        self.assertEqual(shares["Alice"], 30.0)
        self.assertEqual(shares["Bob"], 30.0)
        self.assertEqual(shares["Myself"], 30.0)
        
        # Rounding adjustments
        shares = calculate_split(100.0, "equal", ["A", "B", "C"], {"participants": ["A", "B", "C"]})
        # 100 / 3 = 33.33 each. The remainder of 0.01 goes to the first participant (A).
        self.assertEqual(shares["A"], 33.34)
        self.assertEqual(shares["B"], 33.33)
        self.assertEqual(shares["C"], 33.33)
        self.assertEqual(sum(shares.values()), 100.00)
        
    def test_unequal_split(self):
        members = ["John", "Alice", "Bob", "Myself"]
        shares = calculate_split(120.0, "unequal", members, {
            "shares": {"John": 45.0, "Alice": 20.0, "Bob": 30.0, "Myself": 25.0}
        })
        self.assertEqual(shares["John"], 45.0)
        self.assertEqual(shares["Alice"], 20.0)
        self.assertEqual(shares["Bob"], 30.0)
        self.assertEqual(shares["Myself"], 25.0)
        self.assertEqual(sum(shares.values()), 120.00)
        
    def test_percentage_split(self):
        members = ["John", "Alice", "Bob", "Myself"]
        shares = calculate_split(100.0, "percentage", members, {
            "percentages": {"John": 40.0, "Alice": 30.0, "Bob": 20.0, "Myself": 10.0}
        })
        self.assertEqual(shares["John"], 40.0)
        self.assertEqual(shares["Alice"], 30.0)
        self.assertEqual(shares["Bob"], 20.0)
        self.assertEqual(shares["Myself"], 10.0)
        
        # Percentage rounding adjustment
        shares = calculate_split(10.00, "percentage", ["A", "B", "C"], {
            "percentages": {"A": 33.3, "B": 33.3, "C": 33.4}
        })
        # A: 3.33, B: 3.33, C: 3.34. Sum = 10.00
        self.assertEqual(shares["A"], 3.33)
        self.assertEqual(shares["B"], 3.33)
        self.assertEqual(shares["C"], 3.34)
        self.assertEqual(sum(shares.values()), 10.00)
        
    def test_quantity_split(self):
        members = ["John", "Alice", "Bob", "Myself"]
        shares = calculate_split(80.0, "quantity", members, {
            "quantities": {"John": 3, "Alice": 2, "Bob": 1, "Myself": 2}
        })
        # Total qty = 8. John = 80 * 3/8 = 30. Alice = 20. Bob = 10. Myself = 20.
        self.assertEqual(shares["John"], 30.0)
        self.assertEqual(shares["Alice"], 20.0)
        self.assertEqual(shares["Bob"], 10.0)
        self.assertEqual(shares["Myself"], 20.0)
        self.assertEqual(sum(shares.values()), 80.00)
        
    def test_item_split(self):
        members = ["John", "Alice", "Bob", "Myself"]
        shares = calculate_split(0.0, "item", members, {
            "items": [
                {"name": "Pizza", "price": 18.0, "consumers": ["John", "Myself"]},
                {"name": "Burger", "price": 12.0, "consumers": ["Myself"]},
                {"name": "Coke", "price": 4.0, "consumers": ["Alice"]},
                {"name": "Fries", "price": 4.0, "consumers": ["John", "Alice", "Bob", "Myself"]}
            ],
            "tax": 2.0,
            "tip": 4.0,
            "tax_tip_split": "proportional"
        })
        # Subtotals:
        # Pizza: $18 split between John, Myself. John = 9, Myself = 9
        # Burger: $12 to Myself
        # Coke: $4 to Alice
        # Fries: $4 split between 4. John = 1, Alice = 1, Bob = 1, Myself = 1
        # Net subtotals: John = 10, Myself = 22, Alice = 5, Bob = 1. Total sub = 38.0
        # Tax ($2) & Tip ($4) = $6 total. Proportional to subtotal:
        # Tax+Tip share = 6 * (subtotal / 38)
        # John: 10 + 6 * (10/38) = 10 + 1.58 = 11.58
        # Myself: 22 + 6 * (22/38) = 22 + 3.47 = 25.47
        # Alice: 5 + 6 * (5/38) = 5 + 0.79 = 5.79
        # Bob: 1 + 6 * (1/38) = 1 + 0.16 = 1.16
        # Sum = 11.58 + 25.47 + 5.79 + 1.16 = 44.00
        self.assertEqual(shares["John"], 11.58)
        self.assertEqual(shares["Myself"], 25.47)
        self.assertEqual(shares["Alice"], 5.79)
        self.assertEqual(shares["Bob"], 1.16)
        self.assertEqual(sum(shares.values()), 44.00)
        
    def test_settlements_greedy(self):
        # Suppose net balances are: John owes $166.67 (net balance -166.67), Bob owes $66.67 (-66.67), Alice is owed $233.34 (+233.34)
        # Alice net balance = +233.34, Bob = -66.67, John = -166.67
        balances = {
            "Alice": 233.34,
            "Bob": -66.67,
            "John": -166.67
        }
        payments = calculate_settlements(balances)
        
        # Expected transfers:
        # John -> Alice: 166.67
        # Bob -> Alice: 66.67
        self.assertEqual(len(payments), 2)
        
        # Settle check
        names_from = [p["from"] for p in payments]
        names_to = [p["to"] for p in payments]
        self.assertIn("John", names_from)
        self.assertIn("Bob", names_from)
        self.assertEqual(names_to, ["Alice", "Alice"])
        
        # Sum payments equals total debt
        total_transferred = sum(p["amount"] for p in payments)
        self.assertAlmostEqual(total_transferred, 233.34, places=2)

if __name__ == '__main__':
    unittest.main()
