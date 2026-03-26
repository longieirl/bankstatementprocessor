from __future__ import annotations

import unittest

from bankstatements_core.models import TransactionRow


class TestModels(unittest.TestCase):
    def test_transaction_row_structure(self):
        """Test TransactionRow TypedDict structure and typing"""
        # Create a valid transaction row
        transaction: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Test Transaction",
            "Debit_AMT": "100.00",
            "Credit_AMT": None,
            "Balance_AMT": "500.00",
            "Filename": "test.pdf",
        }

        # Verify all required keys are present
        expected_keys = {
            "Date",
            "Details",
            "Debit_AMT",
            "Credit_AMT",
            "Balance_AMT",
            "Filename",
        }
        self.assertEqual(set(transaction.keys()), expected_keys)

        # Verify types
        self.assertIsInstance(transaction["Date"], str)
        self.assertIsInstance(transaction["Details"], str)
        self.assertIsInstance(transaction["Filename"], str)

        # Verify optional fields can be None
        self.assertIsNone(transaction["Credit_AMT"])

        # Verify optional fields can be strings
        transaction_with_credit: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Salary Payment",
            "Debit_AMT": None,
            "Credit_AMT": "3000.00",
            "Balance_AMT": "3500.00",
            "Filename": "salary.pdf",
        }

        self.assertIsNone(transaction_with_credit["Debit_AMT"])
        self.assertEqual(transaction_with_credit["Credit_AMT"], "3000.00")

    def test_transaction_row_optional_fields(self):
        """Test that monetary fields can be None or string values"""
        # Test all monetary fields as None
        transaction: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Test",
            "Debit_AMT": None,
            "Credit_AMT": None,
            "Balance_AMT": None,
            "Filename": "test.pdf",
        }

        self.assertIsNone(transaction["Debit_AMT"])
        self.assertIsNone(transaction["Credit_AMT"])
        self.assertIsNone(transaction["Balance_AMT"])

        # Test all monetary fields as strings
        transaction2: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Test",
            "Debit_AMT": "50.00",
            "Credit_AMT": "100.00",
            "Balance_AMT": "150.00",
            "Filename": "test.pdf",
        }

        self.assertEqual(transaction2["Debit_AMT"], "50.00")
        self.assertEqual(transaction2["Credit_AMT"], "100.00")
        self.assertEqual(transaction2["Balance_AMT"], "150.00")


if __name__ == "__main__":
    unittest.main()
