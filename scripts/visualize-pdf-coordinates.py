#!/usr/bin/env python3
"""Visualize PDF coordinates for template.json generation.

This script shows exact x,y coordinates of all detected regions to help
you manually tweak template.json settings.
"""

import argparse
import sys
from pathlib import Path

import pdfplumber
from PIL import ImageDraw, ImageFont

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.bbox_utils import BBox
from src.analysis.column_analyzer import ColumnAnalyzer
from src.analysis.iban_spatial_filter import IBANSpatialFilter
from src.analysis.table_detector import TableDetector


def visualize_pdf_coordinates(
    pdf_path: Path,
    output_path: Path,
    page_num: int = 1,
    output_format: str = "png",
) -> None:
    """Generate annotated visualization with coordinates.

    Args:
        pdf_path: Path to PDF file
        output_path: Path to save output file
        page_num: Page number to analyze (1-indexed)
        output_format: Output format ("png" or "pdf")
    """
    print(f"\n{'='*80}")
    print(f"PDF Coordinate Visualization: {pdf_path.name}")
    print(f"{'='*80}\n")

    with pdfplumber.open(pdf_path) as pdf:
        if page_num < 1 or page_num > len(pdf.pages):
            print(f"❌ Error: Page {page_num} not found (PDF has {len(pdf.pages)} pages)")
            return

        page = pdf.pages[page_num - 1]
        print(f"📄 Page {page_num}")
        print(f"   Dimensions: {page.width:.1f} x {page.height:.1f}\n")

        # Initialize analyzers
        table_detector = TableDetector()
        column_analyzer = ColumnAnalyzer()
        iban_filter = IBANSpatialFilter()

        # Create base image using pdfplumber's to_image
        im = page.to_image(resolution=200)

        # Get PIL image for text drawing (need to scale coordinates manually)
        resolution = 200
        scale = resolution / 72  # PDF points to pixels at this resolution
        pil_image = im.annotated.convert("RGB")
        draw = ImageDraw.Draw(pil_image)

        # Load font for text
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 12)
        except:
            font = ImageFont.load_default()
            font_bold = font

        # Store coordinates for template.json output
        template_data = {
            "page_width": page.width,
            "page_height": page.height,
        }

        # Track what we're drawing for legend
        has_pdfplumber_tables = False
        has_text_tables = False
        has_columns = False
        has_iban = False

        # 1. Detect tables using pdfplumber's find_tables with specific settings
        print("=" * 80)
        print("STEP 1: PDFPLUMBER TABLE DETECTION (with line-based settings)")
        print("=" * 80)

        # Table extraction settings
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "intersection_tolerance": 3,
        }

        print("Using table settings:")
        for key, value in table_settings.items():
            print(f"  {key}: {value}")
        print()

        # Extract tables using pdfplumber
        pdfplumber_tables = page.find_tables(table_settings=table_settings)

        if pdfplumber_tables:
            print(f"✓ pdfplumber found {len(pdfplumber_tables)} table(s)\n")
            has_pdfplumber_tables = True

            for i, table in enumerate(pdfplumber_tables, 1):
                bbox = table.bbox
                print(f"📊 pdfplumber Table {i} Coordinates:")
                print(f"   ┌─ Top-Left:     ({bbox[0]:.1f}, {bbox[1]:.1f})")
                print(f"   ├─ Top-Right:    ({bbox[2]:.1f}, {bbox[1]:.1f})")
                print(f"   ├─ Bottom-Left:  ({bbox[0]:.1f}, {bbox[3]:.1f})")
                print(f"   └─ Bottom-Right: ({bbox[2]:.1f}, {bbox[3]:.1f})")
                print(f"   Width:  {bbox[2] - bbox[0]:.1f}")
                print(f"   Height: {bbox[3] - bbox[1]:.1f}\n")

                # Draw using pdfplumber's drawing methods
                im.draw_rect(bbox, stroke="orange", stroke_width=3)

                # Add label
                label = f"PDFPLUMBER TABLE {i}"
                label_y = max(bbox[1] - 20, 10)
                im.draw_rect((bbox[0], label_y, bbox[0] + 200, label_y + 20),
                           fill="orange", stroke="black", stroke_width=1)

                # Add coordinate labels at corners
                im.draw_circle((bbox[0], bbox[1]), 5, fill="orange", stroke="black")
                im.draw_circle((bbox[2], bbox[1]), 5, fill="orange", stroke="black")
                im.draw_circle((bbox[0], bbox[3]), 5, fill="orange", stroke="black")
                im.draw_circle((bbox[2], bbox[3]), 5, fill="orange", stroke="black")
        else:
            print("✗ pdfplumber found no tables with line-based detection\n")

        # 2. Detect tables using our text-based fallback
        print("=" * 80)
        print("STEP 2: TEXT-BASED TABLE DETECTION (fallback)")
        print("=" * 80)
        table_result = table_detector.detect_tables(page)

        if table_result.tables:
            print(f"✓ Found {len(table_result.tables)} table(s)\n")
            has_text_tables = True

            for i, table_bbox in enumerate(table_result.tables, 1):
                print(f"📊 Table {i} Coordinates:")
                print(f"   ┌─ Top-Left:     ({table_bbox.x0:.1f}, {table_bbox.y0:.1f})")
                print(f"   ├─ Top-Right:    ({table_bbox.x1:.1f}, {table_bbox.y0:.1f})")
                print(f"   ├─ Bottom-Left:  ({table_bbox.x0:.1f}, {table_bbox.y1:.1f})")
                print(f"   └─ Bottom-Right: ({table_bbox.x1:.1f}, {table_bbox.y1:.1f})")
                print(f"   Width:  {table_bbox.width:.1f}")
                print(f"   Height: {table_bbox.height:.1f}\n")

                print(f"   📝 For template.json:")
                print(f"   \"table_top_y\": {int(table_bbox.y0)},")
                print(f"   \"table_bottom_y\": {int(table_bbox.y1)}\n")

                template_data["table_top_y"] = int(table_bbox.y0)
                template_data["table_bottom_y"] = int(table_bbox.y1)
                template_data["header_check_top_y"] = max(0, int(table_bbox.y0) - 10)

                # Draw using pdfplumber's drawing methods
                bbox_tuple = (table_bbox.x0, table_bbox.y0, table_bbox.x1, table_bbox.y1)
                im.draw_rect(bbox_tuple, stroke="red", stroke_width=4)

                # Add label
                label = f"TEXT-BASED TABLE {i}"
                label_y = max(table_bbox.y0 - 25, 10)
                im.draw_rect((table_bbox.x0, label_y, table_bbox.x0 + 200, label_y + 22),
                           fill="red", stroke="black", stroke_width=1)

                # Add coordinate labels at corners
                im.draw_circle((table_bbox.x0, table_bbox.y0), 6, fill="red", stroke="black")
                im.draw_circle((table_bbox.x1, table_bbox.y0), 6, fill="red", stroke="black")
                im.draw_circle((table_bbox.x0, table_bbox.y1), 6, fill="red", stroke="black")
                im.draw_circle((table_bbox.x1, table_bbox.y1), 6, fill="red", stroke="black")

                # Add coordinate text labels (scale to pixel coordinates)
                draw.text((int(table_bbox.x0 * scale) + 10, int(table_bbox.y0 * scale) - 15),
                         f"({int(table_bbox.x0)}, {int(table_bbox.y0)})",
                         fill="red", font=font)
                draw.text((int(table_bbox.x1 * scale) - 80, int(table_bbox.y0 * scale) - 15),
                         f"({int(table_bbox.x1)}, {int(table_bbox.y0)})",
                         fill="red", font=font)
                draw.text((int(table_bbox.x0 * scale) + 10, int(table_bbox.y1 * scale) + 5),
                         f"({int(table_bbox.x0)}, {int(table_bbox.y1)})",
                         fill="red", font=font)
                draw.text((int(table_bbox.x1 * scale) - 80, int(table_bbox.y1 * scale) + 5),
                         f"({int(table_bbox.x1)}, {int(table_bbox.y1)})",
                         fill="red", font=font)

            # Analyze columns
            largest_table = table_detector.get_largest_table(table_result)

            if largest_table:
                print("=" * 80)
                print("STEP 3: COLUMN DETECTION")
                print("=" * 80)
                columns = column_analyzer.analyze_columns(page, largest_table)

                if columns:
                    print(f"✓ Found {len(columns)} column(s)\n")
                    has_columns = True
                    template_data["columns"] = {}

                    # Color palette for columns
                    column_colors = [
                        "blue",
                        "purple",
                        "darkgreen",
                        "brown",
                        "navy",
                    ]

                    for idx, (col_name, (x_min, x_max)) in enumerate(columns.items()):
                        print(f"📋 Column: {col_name}")
                        print(f"   Left edge (x_min):  {x_min:.1f}")
                        print(f"   Right edge (x_max): {x_max:.1f}")
                        print(f"   Width: {x_max - x_min:.1f}\n")

                        template_data["columns"][col_name] = [int(x_min), int(x_max)]

                        col_color = column_colors[idx % len(column_colors)]

                        # Draw vertical lines for column boundaries
                        im.draw_line(((x_min, largest_table.y0), (x_min, largest_table.y1)),
                                   stroke=col_color, stroke_width=2)
                        im.draw_line(((x_max, largest_table.y0), (x_max, largest_table.y1)),
                                   stroke=col_color, stroke_width=2)

                        # Add labels at top (scale to pixel coordinates)
                        label_y = largest_table.y0 - 20
                        draw.text((int(x_min * scale), int(label_y * scale)),
                                f"{col_name}: x={int(x_min)}",
                                fill=col_color, font=font)
                        draw.text((int(x_max * scale) - 40, int(label_y * scale)),
                                f"x={int(x_max)}",
                                fill=col_color, font=font)

                    print("   📝 For template.json:")
                    print("   \"columns\": {")
                    for col_name, (x_min, x_max) in columns.items():
                        print(f"     \"{col_name}\": [{int(x_min)}, {int(x_max)}],")
                    print("   }\n")
                else:
                    print("✗ No columns detected\n")
        else:
            print("✗ No tables detected\n")

        # 3. Extract IBANs
        print("=" * 80)
        print("STEP 4: IBAN DETECTION")
        print("=" * 80)
        iban_candidates = iban_filter.extract_iban_candidates(page)

        if iban_candidates:
            print(f"✓ Found {len(iban_candidates)} IBAN candidate(s)\n")
            has_iban = True

            for i, candidate in enumerate(iban_candidates, 1):
                print(f"💳 IBAN {i}: {candidate.masked}")
                print(f"   ┌─ Top-Left:     ({candidate.bbox.x0:.1f}, {candidate.bbox.y0:.1f})")
                print(f"   ├─ Top-Right:    ({candidate.bbox.x1:.1f}, {candidate.bbox.y0:.1f})")
                print(f"   ├─ Bottom-Left:  ({candidate.bbox.x0:.1f}, {candidate.bbox.y1:.1f})")
                print(f"   └─ Bottom-Right: ({candidate.bbox.x1:.1f}, {candidate.bbox.y1:.1f})")
                print(f"   Width:  {candidate.bbox.width:.1f}")
                print(f"   Height: {candidate.bbox.height:.1f}\n")

                # Extract country code for template
                country_code = candidate.iban[:2]
                print(f"   📝 For template.json:")
                print(f"   \"iban_patterns\": [\"^{country_code}\\\\d{{2}}.*\"]\n")

                template_data["iban_pattern"] = f"^{country_code}\\\\d{{2}}.*"

                # Draw using pdfplumber's drawing methods
                bbox_tuple = (candidate.bbox.x0, candidate.bbox.y0,
                             candidate.bbox.x1, candidate.bbox.y1)
                im.draw_rect(bbox_tuple, stroke="green", stroke_width=3)

                # Add label
                label_y = max(candidate.bbox.y0 - 25, 10)
                label_width = 250
                im.draw_rect((candidate.bbox.x0, label_y,
                            candidate.bbox.x0 + label_width, label_y + 22),
                           fill="green", stroke="black", stroke_width=1)

                # Add coordinate labels
                im.draw_circle((candidate.bbox.x0, candidate.bbox.y0), 5,
                             fill="green", stroke="black")
                draw.text((int(candidate.bbox.x0 * scale) + 5, int(label_y * scale) + 5),
                         f"IBAN: {candidate.masked}",
                         fill="white", font=font)
        else:
            print("✗ No IBAN candidates found\n")

        # Add title at top
        title_text = f"PDF Coordinates - Page {page_num} - {pdf_path.name}"
        im.draw_rect((0, 0, page.width, 30), fill="black", stroke="black")

        # Add legend
        legend_x = page.width - 400
        legend_y = page.height - 130
        legend_width = 390
        legend_height = 120

        im.draw_rect((legend_x, legend_y, legend_x + legend_width, legend_y + legend_height),
                   fill="white", stroke="black", stroke_width=2)

        # Legend title (scale to pixel coordinates)
        draw.text((int(legend_x * scale) + 10, int(legend_y * scale) + 8),
                 "LEGEND", fill="black", font=font_bold)

        # Legend items
        legend_items = []
        if has_pdfplumber_tables:
            legend_items.append(("orange", "Orange: pdfplumber tables (line-based)"))
        if has_text_tables:
            legend_items.append(("red", "Red: Text-based tables (fallback)"))
        if has_columns:
            legend_items.append(("blue", "Blue: Column boundaries (x positions)"))
        if has_iban:
            legend_items.append(("green", "Green: IBAN location"))

        item_y = legend_y + 35
        for color, label in legend_items:
            # Draw color box
            im.draw_rect((legend_x + 10, item_y, legend_x + 28, item_y + 15),
                       fill=color, stroke="black", stroke_width=1)
            # Draw label (scale to pixel coordinates)
            draw.text((int(legend_x * scale) + 35, int(item_y * scale) + 2),
                     label, fill="black", font=font)
            item_y += 22

        # Save output
        print("=" * 80)
        print("OUTPUT")
        print("=" * 80)

        if output_format.lower() == "pdf":
            pil_image.save(output_path, format="PDF")
            print(f"✓ Saved annotated PDF: {output_path}")
        else:
            pil_image.save(output_path, format="PNG")
            print(f"✓ Saved annotated PNG: {output_path}")

        print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB\n")

        # Print template.json summary
        print("=" * 80)
        print("TEMPLATE.JSON SUMMARY")
        print("=" * 80)
        print("\nCopy these values to your template.json:\n")
        print("{")
        print("  \"extraction\": {")
        if "table_top_y" in template_data:
            print(f"    \"table_top_y\": {template_data['table_top_y']},")
            print(f"    \"table_bottom_y\": {template_data['table_bottom_y']},")
            print(f"    \"header_check_top_y\": {template_data['header_check_top_y']},")
        if "columns" in template_data:
            print("    \"columns\": {")
            for col_name, coords in template_data["columns"].items():
                print(f"      \"{col_name}\": {coords},")
            print("    }")
        print("  },")
        if "iban_pattern" in template_data:
            print("  \"detection\": {")
            print(f"    \"iban_patterns\": [\"{template_data['iban_pattern']}\"]")
            print("  }")
        print("}")
        print("\n" + "=" * 80)
        print("DETECTION NOTES")
        print("=" * 80)
        if pdfplumber_tables:
            print(f"✓ pdfplumber detected {len(pdfplumber_tables)} table(s) using line-based strategy")
            print("  This PDF has visible table borders - coordinates are precise")
        else:
            print("✗ pdfplumber found no tables (no visible borders)")
            print("✓ Used text-based fallback detection")
            print("  This PDF uses text alignment instead of borders")
            print("  Coordinates are estimated from text positions")
        print("\nTable extraction settings used:")
        for key, value in table_settings.items():
            print(f"  {key}: {value}")
        print("\n" + "=" * 80)
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize PDF coordinates for template.json generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate PNG with coordinates (default)
  python scripts/visualize-pdf-coordinates.py input/statement.pdf

  # Specify output file
  python scripts/visualize-pdf-coordinates.py input/statement.pdf -o output/coords.png

  # Generate PDF instead of PNG
  python scripts/visualize-pdf-coordinates.py input/statement.pdf -o output/coords.pdf --format pdf

  # Analyze specific page
  python scripts/visualize-pdf-coordinates.py input/statement.pdf --page 2
        """,
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to PDF file to analyze",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file path (default: {pdf_name}_coordinates.png)",
    )
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        default=1,
        help="Page number to analyze (default: 1)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["png", "pdf"],
        default="png",
        help="Output format (default: png)",
    )

    args = parser.parse_args()

    # Validate PDF path
    if not args.pdf_path.exists():
        print(f"❌ Error: PDF not found: {args.pdf_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.pdf_path.parent / f"{args.pdf_path.stem}_coordinates.{args.format}"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        visualize_pdf_coordinates(
            args.pdf_path,
            output_path,
            args.page,
            args.format,
        )
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
