# AI Coding Instructions for Bank Statement Processor

## Project Overview
A containerized Python application that **extracts transaction data from bank statement PDFs and converts them to structured CSV format**. The pipeline uses coordinate-based table extraction with pdfplumber and configurable column definitions to parse structured transaction tables.

**Key Flow**: PDFs in `/app/input/` → Extract words with coordinates → Map to configurable columns → Validate/dedup → CSV to `/app/output/`

## Architecture & Data Flow

### Core Components
1. **`BankStatementProcessor`** (`processor.py`): Main orchestrator that coordinates PDF processing, duplicate detection, and output generation
2. **Coordinate-Based Extraction** (`pdf_table_extractor.py`): Uses pdfplumber to extract words with X,Y coordinates and maps them to configurable column boundaries
3. **Configurable Columns**: Column names and X-coordinate boundaries can be customized via environment variables or programmatic configuration
4. **Default Schema**: `{"Date": (26, 78), "Details": (78, 255), "Debit €": (255, 313), "Credit €": (313, 369), "Balance €": (369, 450)}`
5. **Automatic Filename Tracking**: "Filename" column automatically added to track source PDFs

### Docker Environment
- **Host OS**: macOS
- **Container**: Python 3.11-slim + pdfplumber, pandas, tesseract
- **Mounts**: `./input/` ↔ `/app/input/`, `./output/` ↔ `/app/output/`
- **Memory**: 8GB limit + 2GB shared memory (for processing large PDFs)
- **Entrypoint**: Runs `python -m src.app`, keeps container alive for debugging

## Critical Workflows

### Processing New PDFs
```bash
# Development (local execution)
python -m src.app

# Production (Docker)
docker-compose up --build

# Custom column configuration
TABLE_COLUMNS='{"Date": [20, 80], "Details": [80, 250]}' python -m src.app
```

### Coordinate-Based Extraction
- PDFs are processed page-by-page using pdfplumber to extract words with precise X,Y coordinates
- Words are grouped by Y-position (rounded to nearest pixel) to form table rows
- Each word is assigned to a column based on its X-coordinate falling within column boundaries
- Date propagation: Empty date cells inherit the date from the previous row

### Configurable Columns
- **Environment Variable**: `TABLE_COLUMNS='{"Date": [20, 80], "Description": [80, 250]}'`
- **Programmatic**: Pass `columns` parameter to `BankStatementProcessor` constructor
- **Fallback**: Uses default column configuration if parsing fails or not specified

### CSV Output
- Column order matches the configured column definitions
- Automatic "Filename" column added for source tracking
- Duplicate detection based on transaction details across all configured columns
- Index dropped, no row numbers in output

## Project-Specific Patterns

### Coordinate-Based Extraction (Structure-First)
The parser relies on **PDF table structure and precise coordinate mapping**, not regex or ML analysis:
```python
# Default column boundaries (X-coordinates in pixels)
DEFAULT_COLUMNS = {
    "Date": (26, 78),
    "Details": (78, 255),
    "Debit €": (255, 313),
    "Credit €": (313, 369),
    "Balance €": (369, 450),
}

# Table vertical bounds
TABLE_TOP_Y = 300      # Start of table area
TABLE_BOTTOM_Y = 720   # End of table area
```
**When adding new bank statements**: Use coordinate finder tools to identify optimal column boundaries and table bounds for the specific PDF layout.

### Data Classes Over Dictionaries
Use `@dataclass` for structured data (`StatementMetadata`, `Transaction` in `models.py`). Includes `.dict()` method for serialization.

### Logging Strategy
- **Structured logs**: `logger.info("✓ Extracted %d transactions...", len(df))`
- **Error propagation**: `raise RuntimeError()` if extraction fails (no silent failures)
- **Debug level**: Available via `LOG_LEVEL` env var in docker-compose.yml

## Dependencies & Integration Points
- **pdfplumber 0.10.3**: Extract text from PDFs (main workhorse)
- **pandas 2.1.4**: DataFrames for transaction tables
- **requests**: HTTP client for API calls

## Common Maintenance Tasks

### Adding Support for a New Bank Format
1. **Analyze PDF Structure**: Place sample PDF in `/input/` and run extraction
2. **Find Column Boundaries**: Use coordinate finder to identify X-boundaries for each column
3. **Configure Custom Columns**: Set `TABLE_COLUMNS` environment variable with discovered boundaries
4. **Adjust Table Bounds**: Modify `TABLE_TOP_Y` and `TABLE_BOTTOM_Y` if needed for different PDF layouts
5. **Test and Validate**: Run processing and verify correct column assignment and data extraction

### Debugging Failed PDFs
- **Check Logs**: Look for word extraction counts and column assignment statistics
- **Inspect Coordinates**: Add temporary logging to show word positions and column assignments
- **Test Column Boundaries**: Use the test script to verify column configuration works
- **Visualize Table Area**: Crop PDF to table bounds and verify the extraction area is correct

### Column Configuration Troubleshooting
- **Invalid JSON**: Ensure proper JSON format in `TABLE_COLUMNS` environment variable
- **Overlapping Columns**: Make sure column boundaries don't overlap (x_max of col1 <= x_min of col2)
- **Missing Data**: Check if words fall outside defined column boundaries
- **Empty Extraction**: Verify table bounds include the actual table area in the PDF

## File Purpose Reference
- **`src/app.py`**: Entry point—configures columns from environment, orchestrates processing, outputs CSV/JSON
- **`src/processor.py`**: `BankStatementProcessor` class—manages PDF processing, duplicate detection, and output generation
- **`src/pdf_table_extractor.py`**: Core coordinate-based extraction—maps PDF words to configurable columns using X,Y coordinates
- **`src/models.py`**: Type definitions and data models for transaction processing
- **`test_configurable_columns.py`**: Comprehensive test suite for configurable columns functionality
- **`docker-compose.yml`**: Production orchestration with volume mounts
- **`entrypoint.sh`**: Container startup script

## When You're Stuck
- **"No words extracted"** → Check PDF structure, ensure table bounds are correct
- **"Empty columns in output"** → Verify column boundaries align with actual PDF table layout
- **"Transaction key errors"** → Column names changed but duplicate detection logic not updated
- **"JSON parsing error"** → Invalid `TABLE_COLUMNS` format, check JSON syntax and structure
- **"Missing transactions"** → Words falling outside defined column boundaries or table bounds
