#!/usr/bin/env python3
"""
IBAN Extraction Example

This script demonstrates how to extract IBANs from text and PDF files.
"""

from src.extraction.iban_extractor import IBANExtractor


def example_basic_extraction():
    """Example 1: Basic IBAN extraction from text."""
    print("=" * 60)
    print("Example 1: Basic IBAN Extraction")
    print("=" * 60)

    extractor = IBANExtractor()

    # Sample texts with IBANs
    texts = [
        "Your account IBAN: IE29 AIBK 9311 5212 3456 78",
        "Account: DE89370400440532013000",
        "Please transfer to GB29NWBK60161331926819",
        "IBAN: FR14 2004 1010 0505 0001 3M02 606",
    ]

    for text in texts:
        iban = extractor.extract_iban(text)
        if iban:
            masked = extractor._mask_iban(iban)
            print(f"✓ Found: {masked} (Full: {iban})")
        else:
            print(f"✗ No IBAN found in: {text}")

    print()


def example_validation():
    """Example 2: IBAN validation."""
    print("=" * 60)
    print("Example 2: IBAN Validation")
    print("=" * 60)

    extractor = IBANExtractor()

    # Test various IBANs
    test_ibans = [
        ("IE29AIBK93115212345678", True, "Valid Irish IBAN"),
        ("DE89370400440532013000", True, "Valid German IBAN"),
        ("XX29AIBK93115212345678", False, "Invalid country code"),
        ("IE29AIBK931152", False, "Too short"),
        ("IE29AIBK931152123456789012", False, "Too long"),
    ]

    for iban, expected, description in test_ibans:
        is_valid = extractor.is_valid_iban(iban)
        status = "✓" if is_valid == expected else "✗"
        print(f"{status} {description}: {iban} → {is_valid}")

    print()


def example_multiple_countries():
    """Example 3: IBANs from various countries."""
    print("=" * 60)
    print("Example 3: Multiple Country IBANs")
    print("=" * 60)

    extractor = IBANExtractor()

    # Sample IBANs from different countries
    ibans = {
        "Ireland": "IE29AIBK93115212345678",
        "Germany": "DE89370400440532013000",
        "UK": "GB29NWBK60161331926819",
        "France": "FR1420041010050500013M02606",
        "Spain": "ES9121000418450200051332",
        "Italy": "IT60X0542811101000000123456",
        "Netherlands": "NL91ABNA0417164300",
        "Belgium": "BE68539007547034",
    }

    for country, iban in ibans.items():
        is_valid = extractor.is_valid_iban(iban)
        length = len(iban)
        country_code = iban[:2]
        expected_length = extractor.IBAN_LENGTHS.get(country_code, "?")

        print(
            f"{country:15} {iban:35} "
            f"Length: {length}/{expected_length} "
            f"{'✓' if is_valid else '✗'}"
        )

    print()


def example_format_variations():
    """Example 4: Different IBAN formats."""
    print("=" * 60)
    print("Example 4: Format Variations")
    print("=" * 60)

    extractor = IBANExtractor()

    # Same IBAN in different formats
    formats = [
        "IE29AIBK93115212345678",  # No spaces
        "IE29 AIBK 9311 5212 3456 78",  # With spaces
        "IE29-AIBK-9311-5212-3456-78",  # With hyphens
        "ie29aibk93115212345678",  # Lowercase
        "Ie29AiBk93115212345678",  # Mixed case
    ]

    print("All formats should extract the same IBAN:")
    for fmt in formats:
        iban = extractor.extract_iban(fmt)
        print(f"  {fmt:40} → {iban}")

    print()


def example_text_context():
    """Example 5: IBANs in various text contexts."""
    print("=" * 60)
    print("Example 5: IBANs in Context")
    print("=" * 60)

    extractor = IBANExtractor()

    # IBANs embedded in different text contexts
    contexts = [
        "Account Number: IE29AIBK93115212345678",
        "IE29AIBK93115212345678 is your IBAN",
        "Transfer to IE29 AIBK 9311 5212 3456 78 today",
        """
        Bank Statement
        Account Holder: John Doe
        IBAN: IE29 AIBK 9311 5212 3456 78
        Statement Period: Jan 2024
        """,
        "Please use IBAN IE29-AIBK-9311-5212-3456-78 for payments",
    ]

    for context in contexts:
        iban = extractor.extract_iban(context)
        if iban:
            masked = extractor._mask_iban(iban)
            preview = context.replace("\n", " ").strip()[:50]
            print(f"✓ {masked} from: {preview}...")
        else:
            print(f"✗ No IBAN in: {context[:50]}...")

    print()


def example_edge_cases():
    """Example 6: Edge cases and error handling."""
    print("=" * 60)
    print("Example 6: Edge Cases")
    print("=" * 60)

    extractor = IBANExtractor()

    # Edge cases
    edge_cases = [
        ("", "Empty string"),
        (None, "None value"),
        ("No IBAN here", "Text without IBAN"),
        ("IE29AIBK93115212345678 and DE89370400440532013000", "Multiple IBANs"),
        ("IEXXAIBK93115212345678", "Non-numeric check digits"),
        ("IE29 AIBK 9311 5212 3456", "Incomplete IBAN"),
    ]

    for text, description in edge_cases:
        try:
            iban = extractor.extract_iban(text)
            if iban:
                print(f"✓ {description}: Found {iban}")
            else:
                print(f"○ {description}: No IBAN (expected)")
        except Exception as e:
            print(f"✗ {description}: Error - {e}")

    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "    IBAN Extraction Examples".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Run all examples
    example_basic_extraction()
    example_validation()
    example_multiple_countries()
    example_format_variations()
    example_text_context()
    example_edge_cases()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print()
    print("For more information, see docs/IBAN_EXTRACTION.md")
    print()


if __name__ == "__main__":
    main()
