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
            "Debit_EUR": "100.00",
            "Credit_EUR": None,
            "Balance_EUR": "500.00",
            "Filename": "test.pdf",
        }

        # Verify all required keys are present
        expected_keys = {
            "Date",
            "Details",
            "Debit_EUR",
            "Credit_EUR",
            "Balance_EUR",
            "Filename",
        }
        self.assertEqual(set(transaction.keys()), expected_keys)

        # Verify types
        self.assertIsInstance(transaction["Date"], str)
        self.assertIsInstance(transaction["Details"], str)
        self.assertIsInstance(transaction["Filename"], str)

        # Verify optional fields can be None
        self.assertIsNone(transaction["Credit_EUR"])

        # Verify optional fields can be strings
        transaction_with_credit: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Salary Payment",
            "Debit_EUR": None,
            "Credit_EUR": "3000.00",
            "Balance_EUR": "3500.00",
            "Filename": "salary.pdf",
        }

        self.assertIsNone(transaction_with_credit["Debit_EUR"])
        self.assertEqual(transaction_with_credit["Credit_EUR"], "3000.00")

    def test_transaction_row_optional_fields(self):
        """Test that monetary fields can be None or string values"""
        # Test all monetary fields as None
        transaction: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Test",
            "Debit_EUR": None,
            "Credit_EUR": None,
            "Balance_EUR": None,
            "Filename": "test.pdf",
        }

        self.assertIsNone(transaction["Debit_EUR"])
        self.assertIsNone(transaction["Credit_EUR"])
        self.assertIsNone(transaction["Balance_EUR"])

        # Test all monetary fields as strings
        transaction2: TransactionRow = {
            "Date": "01 Jan 2024",
            "Details": "Test",
            "Debit_EUR": "50.00",
            "Credit_EUR": "100.00",
            "Balance_EUR": "150.00",
            "Filename": "test.pdf",
        }

        self.assertEqual(transaction2["Debit_EUR"], "50.00")
        self.assertEqual(transaction2["Credit_EUR"], "100.00")
        self.assertEqual(transaction2["Balance_EUR"], "150.00")


if __name__ == "__main__":
    unittest.main()
