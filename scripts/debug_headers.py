#!/usr/bin/env python3
"""
Diagnostic script to show what text is in the first 10 rows of each page.
This helps diagnose why header detection is failing.

Usage:
    python debug_headers.py input/your_statement.pdf
"""

import sys
from pathlib import Path

import pdfplumber


def debug_page_headers(pdf_path: Path, table_top_y: int = 300):
    """Show the first 10 rows of each page to diagnose header detection."""

    print(f"\n{'='*80}")
    print(f"Analyzing: {pdf_path.name}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{'─'*80}")
            print(f"PAGE {page_num} of {len(pdf.pages)}")
            print(f"{'─'*80}")

            # Extract words from table area
            table_area = page.crop((0, table_top_y, page.width, page.height))
            words = table_area.extract_words(use_text_flow=True)

            if not words:
                print("⚠️  NO WORDS FOUND IN TABLE AREA")
                continue

            # Group by Y coordinate
            lines = {}
            for w in words:
                y_key = round(w["top"], 0)
                lines.setdefault(y_key, []).append(w)

            # Show first 10 rows
            sorted_y_coords = sorted(lines.keys())[:10]

            print(f"\nFirst {len(sorted_y_coords)} rows in table area:")
            print()

            for i, y_coord in enumerate(sorted_y_coords, 1):
                row_text = " ".join([w["text"] for w in lines[y_coord]])

                # Check for header keywords
                header_keywords = ["date", "details", "description", "amount",
                                 "debit", "credit", "balance", "transaction",
                                 "reference", "memo"]

                row_lower = row_text.lower()
                found_keywords = [kw for kw in header_keywords if kw in row_lower]

                # Highlight rows with header keywords
                marker = "🔍" if found_keywords else "  "
                keyword_info = f" [{len(found_keywords)} keywords: {', '.join(found_keywords)}]" if found_keywords else ""

                print(f"{marker} Row {i:2d} (Y={y_coord:4.0f}): {row_text[:100]}{keyword_info}")

            print()

            # Show header detection result
            header_keywords_by_row = []
            for y_coord in sorted_y_coords[:5]:  # Check first 5 like the detector does
                row_text = " ".join([w["text"] for w in lines[y_coord]]).lower()
                matches = sum(1 for kw in header_keywords if kw in row_text)
                if matches >= 2:
                    header_keywords_by_row.append((y_coord, matches))

            if header_keywords_by_row:
                print("✅ HEADERS DETECTED - This page would be processed")
                for y, count in header_keywords_by_row:
                    print(f"   Row at Y={y}: {count} header keywords found")
            else:
                print("❌ NO HEADERS DETECTED - This page would be SKIPPED")
                print("   (Need at least 2 header keywords in a single row within first 5 rows)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_headers.py <pdf_file>")
        print("\nExample:")
        print("  python debug_headers.py input/statement.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    if pdf_path.is_dir():
        # Process all PDFs in directory
        pdf_files = sorted(pdf_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {pdf_path}")
            sys.exit(1)

        for pdf_file in pdf_files:
            debug_page_headers(pdf_file)
    else:
        # Process single file
        debug_page_headers(pdf_path)

    print(f"\n{'='*80}")
    print("Analysis complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
