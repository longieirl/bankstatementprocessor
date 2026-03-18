# Transaction Domain Model

This document describes the Transaction domain model and how to use it in the bankstatements codebase.

## Overview

The `Transaction` class is a domain model that replaces plain dictionaries for representing bank transactions. It provides:

- **Type safety**: Compile-time type checking instead of runtime errors
- **Validation**: Business logic for checking transaction validity
- **Clarity**: Explicit fields instead of `dict[str, Any]`
- **IDE support**: Autocomplete and refactoring tools work better

## Basic Usage

### Creating Transactions

```python
from src.domain import Transaction

# Create directly
tx = Transaction(
    date="01/12/2023",
    details="TESCO STORES",
    debit="45.23",
    credit=None,
    balance="1234.56",
    filename="statement_20231201.pdf"
)

# Create from dictionary
data = {
    "Date": "01/12/2023",
    "Details": "TESCO STORES",
    "Debit €": "45.23",
    "Credit €": None,
    "Balance €": "1234.56",
    "Filename": "statement.pdf"
}
tx = Transaction.from_dict(data)
```

### Transaction Type Checking

```python
# Check if debit or credit
if tx.is_debit():
    print(f"Money out: {tx.debit}")
elif tx.is_credit():
    print(f"Money in: {tx.credit}")
```

### Getting Amounts as Decimals

```python
from decimal import Decimal

# Get transaction amount (negative for debits, positive for credits)
amount = tx.get_amount()  # Returns Decimal('-45.23')

# Get balance
balance = tx.get_balance()  # Returns Decimal('1234.56')

# Handles currency symbols and comma separators automatically
tx2 = Transaction(
    date="01/12/2023",
    details="Large purchase",
    debit="€1,234.56",  # With currency symbol and comma
    credit=None,
    balance="5,000.00",
    filename="statement.pdf"
)
amount = tx2.get_amount()  # Returns Decimal('-1234.56')
```

### Validation

```python
# Check if transaction has valid data
if tx.has_valid_date() and tx.has_valid_details():
    print("Transaction is valid")
```

### Converting Back to Dictionary

```python
# Convert Transaction back to dict (for output/serialization)
data = tx.to_dict()
# Returns:
# {
#     "Date": "01/12/2023",
#     "Details": "TESCO STORES",
#     "Debit €": "45.23",
#     "Credit €": None,
#     "Balance €": "1234.56",
#     "Filename": "statement.pdf"
# }
```

## Batch Conversions

For working with lists of transactions:

```python
from src.domain import dicts_to_transactions, transactions_to_dicts

# Convert list of dicts to list of Transactions
rows = [
    {"Date": "01/01/23", "Details": "Shop A", "Debit €": "50.00", ...},
    {"Date": "02/01/23", "Details": "Shop B", "Debit €": "30.00", ...},
]
transactions = dicts_to_transactions(rows)

# Convert back to dicts
rows_again = transactions_to_dicts(transactions)
```

## Working with Different Column Names

The Transaction model handles various column naming conventions:

```python
# AIB format
aib_data = {
    "Transaction Date": "01/12/2023",
    "Description": "Payment",
    "Debit": "50.00",
    "Credit": None,
    "Balance": "100.00",
    "Filename": "aib.pdf"
}
tx = Transaction.from_dict(aib_data)  # Works!

# Revolut format
revolut_data = {
    "date": "01/12/2023",
    "details": "Payment",
    "Debit_EUR": "50.00",
    "Credit_EUR": None,
    "Running Balance": "100.00",
    "source_pdf": "revolut.pdf"
}
tx = Transaction.from_dict(revolut_data)  # Also works!
```

## Additional Fields

For bank-specific custom columns:

```python
data = {
    "Date": "01/12/2023",
    "Details": "Purchase",
    "Debit €": "50.00",
    "Credit €": None,
    "Balance €": "100.00",
    "Filename": "statement.pdf",
    "Reference": "REF123",  # Bank-specific field
    "Category": "Shopping"  # Bank-specific field
}

tx = Transaction.from_dict(data)

# Access additional fields
print(tx.additional_fields["Reference"])  # "REF123"
print(tx.additional_fields["Category"])   # "Shopping"

# Additional fields are preserved in to_dict()
result = tx.to_dict()
print(result["Reference"])  # "REF123"
```

## Use Cases

### 1. Type-Safe Transaction Processing

```python
from decimal import Decimal
from src.domain import Transaction

def calculate_total_spending(transactions: list[Transaction]) -> Decimal:
    """Calculate total spending from transactions.

    Type checker ensures we're working with Transaction objects,
    not arbitrary dicts.
    """
    total = Decimal("0")
    for tx in transactions:
        if tx.is_debit():
            amount = tx.get_amount()
            if amount:
                total += abs(amount)  # Debits are negative, so abs()
    return total
```

### 2. Transaction Filtering with Type Safety

```python
from src.domain import Transaction

def filter_large_transactions(
    transactions: list[Transaction],
    threshold: Decimal
) -> list[Transaction]:
    """Filter transactions above threshold amount."""
    return [
        tx for tx in transactions
        if tx.get_amount() and abs(tx.get_amount()) > threshold
    ]
```

### 3. Business Rules Validation

```python
from src.domain import Transaction

def validate_transaction(tx: Transaction) -> bool:
    """Validate transaction meets business rules."""
    # Must have valid date
    if not tx.has_valid_date():
        return False

    # Must have valid details
    if not tx.has_valid_details():
        return False

    # Must be either debit or credit (not both, not neither)
    if not (tx.is_debit() or tx.is_credit()):
        return False

    # Must have valid amount
    if tx.get_amount() is None:
        return False

    return True
```

## Migration Guide

### Current State (dict-based)

```python
# Old way - using dicts
rows = extract_transactions()  # Returns list[dict]

# No type safety
for row in rows:
    if row.get("Debit €"):  # Prone to typos
        amount = float(row["Debit €"].replace(",", ""))  # Manual parsing
```

### Future State (Transaction-based)

```python
# New way - using Transaction
from src.domain import dicts_to_transactions

rows = extract_transactions()
transactions = dicts_to_transactions(rows)

# Type safety!
for tx in transactions:
    if tx.is_debit():
        amount = tx.get_amount()  # Returns Decimal, handles parsing
```

### Gradual Migration

The Transaction model can be adopted gradually:

1. **Extraction layer**: Keep returning dicts (existing code)
2. **Service layer**: Convert to Transaction where type safety helps
3. **Output layer**: Convert back to dicts for DataFrame/JSON/Excel

```python
# Extraction (unchanged)
rows = pdf_extractor.extract(pdf_path)  # list[dict]

# Service layer (use Transaction)
from src.domain import dicts_to_transactions, transactions_to_dicts

transactions = dicts_to_transactions(rows)
filtered = filter_transactions(transactions)  # Type-safe processing
sorted_txs = sort_transactions(filtered)

# Output (convert back to dicts)
output_rows = transactions_to_dicts(sorted_txs)
df = pd.DataFrame(output_rows)
```

## Benefits

### 1. Type Safety

```python
# Dict approach - typo not caught until runtime
row["Detials"]  # KeyError at runtime!

# Transaction approach - typo caught by type checker
tx.detials  # Error: 'Transaction' object has no attribute 'detials'
```

### 2. IDE Support

```python
# Dict approach - no autocomplete
row["D..."]  # IDE can't help

# Transaction approach - full autocomplete
tx.de  # IDE suggests: details, debit, ...
```

### 3. Refactoring

```python
# Dict approach - rename requires manual find/replace
# If you rename "Debit €" to "Debit Amount", you must find all string literals

# Transaction approach - IDE can refactor
# Rename tx.debit field, IDE updates all references automatically
```

### 4. Business Logic Encapsulation

```python
# Dict approach - business logic scattered
if row.get("Debit €"):
    amount_str = row["Debit €"].replace("€", "").replace(",", "")
    amount = -float(amount_str)

# Transaction approach - logic in one place
amount = tx.get_amount()  # Handles all parsing/conversion
```

## Testing

Testing with Transaction objects:

```python
from src.domain import Transaction

def test_calculate_spending():
    """Test spending calculation with Transaction objects."""
    transactions = [
        Transaction(
            date="01/01/23",
            details="Shop A",
            debit="50.00",
            credit=None,
            balance="100.00",
            filename="test.pdf"
        ),
        Transaction(
            date="02/01/23",
            details="Shop B",
            debit="30.00",
            credit=None,
            balance="70.00",
            filename="test.pdf"
        ),
    ]

    total = calculate_total_spending(transactions)
    assert total == Decimal("80.00")
```

## Best Practices

1. **Use Transaction for business logic**: Type-safe processing is most valuable in business logic
2. **Keep I/O boundaries as dicts**: External interfaces (DB, JSON) work with dicts
3. **Convert at boundaries**: Convert dict → Transaction at input, Transaction → dict at output
4. **Validate early**: Use Transaction validation methods as soon as data enters system
5. **Leverage type hints**: Add `-> list[Transaction]` return types for type safety

## Future Enhancements

Potential improvements to Transaction model:

1. **Parsed date field**: Add `parsed_date: datetime | None` field
2. **Currency support**: Add `currency: str` field for multi-currency statements
3. **Transaction categories**: Add `category: TransactionCategory` enum
4. **Immutability**: Make Transaction frozen dataclass for safety
5. **Rich comparison**: Add `__lt__`, `__eq__` for sorting without external functions

## See Also

- **src/domain/models/transaction.py** - Transaction model implementation
- **src/domain/converters.py** - Conversion utilities
- **tests/domain/test_transaction.py** - Comprehensive test suite (29 tests)
- **docs/ERROR_HANDLING.md** - Error handling patterns
