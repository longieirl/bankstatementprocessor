#!/usr/bin/env python3
"""Debug script to analyze PDF structure and help diagnose table detection issues."""

import sys
from pathlib import Path

import pdfplumber


def analyze_pdf_structure(pdf_path: Path) -> None:
    """Analyze and print PDF structure details."""
    print(f"\n{'='*70}")
    print(f"PDF Structure Analysis: {pdf_path.name}")
    print(f"{'='*70}\n")

    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total Pages: {len(pdf.pages)}")
        print(f"\n{'─'*70}")

        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n📄 PAGE {page_num}")
            print(f"{'─'*70}")
            print(f"Dimensions: {page.width:.1f} x {page.height:.1f}")

            # Check for text
            text = page.extract_text()
            if text:
                lines = text.strip().split('\n')
                print(f"✓ Text found: {len(lines)} lines")
                print(f"  First 3 lines:")
                for line in lines[:3]:
                    print(f"    {line[:80]}")
            else:
                print("✗ No text found (might be scanned image)")

            # Check for tables using pdfplumber
            tables = page.find_tables()
            print(f"\nTables detected by pdfplumber: {len(tables)}")
            if tables:
                for i, table in enumerate(tables, 1):
                    bbox = table.bbox
                    print(f"  Table {i}: BBox({bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f})")

            # Check for words (individual text elements)
            words = page.extract_words()
            print(f"\nWords extracted: {len(words)}")
            if words:
                print(f"  Sample words (first 5):")
                for word in words[:5]:
                    print(f"    '{word['text']}' at x={word['x0']:.1f}, y={word['top']:.1f}")

            # Check for lines/curves (table borders)
            lines_h = page.lines
            curves = page.curves
            print(f"\nGraphical elements:")
            print(f"  Horizontal/Vertical lines: {len(lines_h)}")
            print(f"  Curves: {len(curves)}")

            # Check for images
            images = page.images
            print(f"  Images: {len(images)}")
            if images and not text:
                print("  ⚠️  WARNING: PDF contains images but no text (likely scanned)")

            print(f"\n{'─'*70}")

    print(f"\n{'='*70}")
    print("Analysis complete")
    print(f"{'='*70}\n")

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("─" * 70)

    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        words = first_page.extract_words()
        images = first_page.images

        if not text and images:
            print("✗ This is a SCANNED PDF (image-based)")
            print("  → OCR required - not supported by this tool")
            print("  → Use Adobe Acrobat or similar to convert to text-based PDF")

        elif not words:
            print("✗ No text elements found")
            print("  → PDF might be corrupted or encrypted")
            print("  → Try opening in a PDF viewer to verify")

        elif len(first_page.find_tables()) == 0:
            print("⚠️  Text found but no tables detected")
            print("  → PDF might not have clear table structure")
            print("  → Tables might use spaces instead of borders")
            print("  → Try manual template creation")
            print("\n  Next steps:")
            print("  1. Run with DEBUG logging:")
            print("     python -m src.commands.analyze_pdf input/statement.pdf \\")
            print("         --output output/template.json --log-level DEBUG")
            print("  2. Check if text is aligned in columns")
            print("  3. Consider manual template configuration")

        else:
            print("✓ Tables detected - analysis should work")
            print("  → Re-run analyze_pdf with DEBUG logging to see details")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/debug-pdf-structure.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    analyze_pdf_structure(pdf_path)
