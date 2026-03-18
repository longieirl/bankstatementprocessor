#!/usr/bin/env python3
"""Visualize PDF analysis results by drawing detected regions on PDF pages.

This script generates annotated images showing:
- Detected table boundaries
- Column boundaries
- IBAN locations
- Header areas
- Transaction rows
"""

import sys
from pathlib import Path
from typing import Optional

import pdfplumber
from PIL import ImageDraw, ImageFont

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.bbox_utils import BBox
from src.analysis.column_analyzer import ColumnAnalyzer
from src.analysis.iban_spatial_filter import IBANSpatialFilter
from src.analysis.table_detector import TableDetector
from src.extraction.iban_extractor import IBANExtractor


def draw_bbox(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color: str,
    label: Optional[str] = None,
    width: int = 2,
    fill_alpha: Optional[int] = None,
) -> None:
    """Draw a bounding box on the image with optional semi-transparent fill.

    Args:
        draw: ImageDraw object
        bbox: Bounding box to draw
        color: Outline color (name or RGB tuple)
        label: Optional text label
        width: Line width
        fill_alpha: Optional transparency (0-255) for fill color
    """
    # Draw outline
    draw.rectangle(
        [(bbox.x0, bbox.y0), (bbox.x1, bbox.y1)],
        outline=color,
        width=width,
    )

    # Draw semi-transparent fill if requested
    if fill_alpha is not None:
        # Create a new image for the fill with alpha channel
        fill_color = color if isinstance(color, tuple) else {
            "red": (255, 0, 0),
            "blue": (0, 0, 255),
            "green": (0, 255, 0),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
            "yellow": (255, 255, 0),
        }.get(color, (128, 128, 128))

        # Draw a semi-transparent rectangle
        overlay = draw._image.copy()
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(bbox.x0, bbox.y0), (bbox.x1, bbox.y1)],
            fill=fill_color + (fill_alpha,),
        )
        draw._image.paste(overlay, mask=overlay)

    if label:
        # Draw label background
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 14)
        except:
            font = ImageFont.load_default()
            font_bold = font

        # Get text size
        bbox_text = draw.textbbox((bbox.x0, bbox.y0 - 20), label, font=font_bold)
        text_width = bbox_text[2] - bbox_text[0]
        text_height = bbox_text[3] - bbox_text[1]

        # Draw background rectangle with padding
        padding = 6
        draw.rectangle(
            [
                (bbox.x0 - 2, bbox.y0 - text_height - padding - 2),
                (bbox.x0 + text_width + padding, bbox.y0 - 2)
            ],
            fill=color,
            outline="black",
            width=1,
        )

        # Draw text in white for better contrast
        draw.text(
            (bbox.x0 + padding // 2, bbox.y0 - text_height - padding // 2),
            label,
            fill="white",
            font=font_bold,
        )


def visualize_pdf_analysis(
    pdf_path: Path,
    output_dir: Path,
    page_num: int = 1,
) -> None:
    """Generate annotated images showing analysis results.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save output images
        page_num: Page number to analyze (1-indexed)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"PDF Visualization: {pdf_path.name}")
    print(f"{'='*70}\n")

    with pdfplumber.open(pdf_path) as pdf:
        if page_num < 1 or page_num > len(pdf.pages):
            print(f"Error: Page {page_num} not found (PDF has {len(pdf.pages)} pages)")
            return

        page = pdf.pages[page_num - 1]
        print(f"Analyzing Page {page_num}")
        print(f"Dimensions: {page.width:.1f} x {page.height:.1f}")
        print()

        # Initialize analyzers
        table_detector = TableDetector()
        column_analyzer = ColumnAnalyzer()
        iban_filter = IBANSpatialFilter()

        # Create base image with higher resolution for better quality
        im = page.to_image(resolution=200)

        # Convert to RGBA for transparency support
        base_image = im.original.convert("RGBA")
        draw = ImageDraw.Draw(base_image, mode="RGBA")

        # 1. Detect tables
        print("Step 1: Detecting tables...")
        table_result = table_detector.detect_tables(page)

        if table_result.tables:
            print(f"  ✓ Found {len(table_result.tables)} table(s)")
            for i, table_bbox in enumerate(table_result.tables, 1):
                print(f"    Table {i}: {table_bbox}")
                draw_bbox(
                    draw,
                    table_bbox,
                    color=(255, 0, 0),  # Red
                    label=f"📊 TABLE {i}",
                    width=4,
                    fill_alpha=20,  # Light red tint
                )

            # Use largest table for further analysis
            largest_table = table_detector.get_largest_table(table_result)

            # 2. Analyze columns
            if largest_table:
                print("\nStep 2: Analyzing columns...")
                columns = column_analyzer.analyze_columns(page, largest_table)

                if columns:
                    print(f"  ✓ Found {len(columns)} column(s)")
                    # Assign different colors to columns for better visibility
                    column_colors = [
                        (0, 100, 200),    # Dark blue
                        (100, 0, 200),    # Purple
                        (0, 150, 100),    # Teal
                        (200, 100, 0),    # Orange-brown
                        (150, 0, 150),    # Magenta
                    ]

                    for idx, (col_name, (x_min, x_max)) in enumerate(columns.items()):
                        print(f"    {col_name}: ({x_min:.1f}, {x_max:.1f})")

                        # Draw column boundaries with unique colors
                        col_bbox = BBox(
                            x0=x_min,
                            y0=largest_table.y0,
                            x1=x_max,
                            y1=largest_table.y1,
                        )
                        col_color = column_colors[idx % len(column_colors)]
                        draw_bbox(
                            draw,
                            col_bbox,
                            color=col_color,
                            label=f"📋 {col_name}",
                            width=2,
                            fill_alpha=15,  # Very light tint
                        )
                else:
                    print("  ✗ No columns detected")
        else:
            print("  ✗ No tables detected")
            largest_table = None

        # 3. Extract IBAN candidates
        print("\nStep 3: Extracting IBAN candidates...")
        iban_candidates = iban_filter.extract_iban_candidates(page)

        if iban_candidates:
            print(f"  ✓ Found {len(iban_candidates)} IBAN candidate(s)")
            for i, candidate in enumerate(iban_candidates, 1):
                print(f"    IBAN {i}: {candidate.masked} at {candidate.bbox}")
                draw_bbox(
                    draw,
                    candidate.bbox,
                    color=(0, 180, 0),  # Bright green
                    label=f"💳 IBAN: {candidate.masked}",
                    width=4,
                    fill_alpha=25,  # Light green tint
                )
        else:
            print("  ✗ No IBAN candidates found")

        # 4. Filter IBANs by table overlap
        if iban_candidates and largest_table:
            print("\nStep 4: Filtering IBANs by table overlap...")
            expanded_regions = table_detector.get_expanded_table_regions(
                table_result, margin=20.0
            )
            filtered_candidates = iban_filter.filter_by_table_overlap(
                iban_candidates, expanded_regions
            )

            print(f"  Filtered: {len(filtered_candidates)} accepted, "
                  f"{len(iban_candidates) - len(filtered_candidates)} rejected")

            # Draw expanded table regions with dashed lines (overlap detection zone)
            for expanded in expanded_regions:
                # Draw dashed rectangle by drawing line segments
                dash_color = (255, 140, 0)  # Dark orange
                for x in range(int(expanded.x0), int(expanded.x1), 15):
                    draw.line(
                        [(x, expanded.y0), (min(x + 8, expanded.x1), expanded.y0)],
                        fill=dash_color,
                        width=3,
                    )
                    draw.line(
                        [(x, expanded.y1), (min(x + 8, expanded.x1), expanded.y1)],
                        fill=dash_color,
                        width=3,
                    )
                for y in range(int(expanded.y0), int(expanded.y1), 15):
                    draw.line(
                        [(expanded.x0, y), (expanded.x0, min(y + 8, expanded.y1))],
                        fill=dash_color,
                        width=3,
                    )
                    draw.line(
                        [(expanded.x1, y), (expanded.x1, min(y + 8, expanded.y1))],
                        fill=dash_color,
                        width=3,
                    )

                # Add label for overlap zone
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 12)
                except:
                    font = ImageFont.load_default()

                label_text = "⚠️ OVERLAP ZONE (±20px)"
                label_x = expanded.x0 + 5
                label_y = expanded.y0 - 35

                # Draw label background
                bbox_text = draw.textbbox((label_x, label_y), label_text, font=font)
                draw.rectangle(
                    [(bbox_text[0] - 4, bbox_text[1] - 2), (bbox_text[2] + 4, bbox_text[3] + 2)],
                    fill=dash_color,
                    outline="black",
                    width=1,
                )
                draw.text((label_x, label_y), label_text, fill="white", font=font)

        # Add enhanced legend
        print("\nGenerating annotated image...")
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 16)
        except:
            font = ImageFont.load_default()
            font_bold = font

        # Legend items with emojis and better descriptions
        legend_items = [
            ((255, 0, 0), "📊 Table Boundary (detected transaction area)"),
            ((0, 100, 200), "📋 Column Boundaries (data columns)"),
            ((0, 180, 0), "💳 IBAN Location (account number)"),
            ((255, 140, 0), "⚠️ Overlap Zone (IBAN filtering region, dashed)"),
        ]

        # Draw legend background
        legend_x = 10
        legend_y = 10
        legend_width = 500
        legend_height = 20 + len(legend_items) * 28 + 10

        draw.rectangle(
            [(legend_x, legend_y), (legend_x + legend_width, legend_y + legend_height)],
            fill=(255, 255, 255, 230),  # Semi-transparent white
            outline="black",
            width=2,
        )

        # Draw legend title
        title_y = legend_y + 8
        draw.text((legend_x + 10, title_y), "LEGEND", fill="black", font=font_bold)

        # Draw legend items
        item_y = title_y + 25
        for color, label in legend_items:
            # Draw color box
            box_size = 18
            draw.rectangle(
                [(legend_x + 10, item_y), (legend_x + 10 + box_size, item_y + box_size)],
                fill=color,
                outline="black",
                width=2,
            )
            # Draw label
            draw.text((legend_x + 10 + box_size + 10, item_y + 2), label, fill="black", font=font)
            item_y += 28

        # Save annotated image
        output_path = output_dir / f"{pdf_path.stem}_page_{page_num}_annotated.png"
        base_image.save(output_path, "PNG")

        print(f"\n✓ Annotated image saved: {output_path}")
        print(f"\n{'='*70}\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/visualize-pdf-analysis.py <pdf-path> [output-dir] [page-num]")
        print("\nExample:")
        print("  python scripts/visualize-pdf-analysis.py input/statement.pdf")
        print("  python scripts/visualize-pdf-analysis.py input/statement.pdf output/visualizations")
        print("  python scripts/visualize-pdf-analysis.py input/statement.pdf output/visualizations 2")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output/visualizations")
    page_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    try:
        visualize_pdf_analysis(pdf_path, output_dir, page_num)
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
