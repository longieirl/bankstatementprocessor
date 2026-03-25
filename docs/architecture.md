# Architecture

This document describes the structure of the `bankstatementprocessor` monorepo and how the premium distribution relates to the open-source packages.

---

## Two-Package Monorepo

```
bankstatementprocessor/
├── packages/
│   ├── parser-core/          PyPI: bankstatements-core (v0.1.2)
│   └── parser-free/          PyPI: bankstatements-free (v0.1.0)
├── templates/                shared IBAN-based bank templates
└── .github/workflows/
    ├── ci.yml                lint + test both packages
    ├── boundary-check.yml    enforce import boundaries
    └── release-core.yml      publish bankstatements-core to PyPI
```

### `bankstatements-core`

The shared parsing library. Contains:

- **`extraction/`** — PDF → rows pipeline (`pdf_extractor`, `boundary_detector`, `row_classifiers`, `word_utils`)
- **`services/`** — single-responsibility services (duplicate detection, sorting, filtering, monthly summary, GDPR audit log, etc.)
- **`builders/`** — `BankStatementProcessorBuilder` fluent builder
- **`templates/`** — template model, registry, detectors, and bundled IBAN-based bank templates
- **`domain/`** — domain models (`Transaction`, `ExtractionResult`), protocols, currency, converters, dataframe utilities
- **`config/`** — `AppConfig` dataclass validated from environment variables; `ProcessorConfig` for programmatic use
- **`patterns/`** — Strategy, Factory, Repository implementations
- **`facades/`** — `BankStatementProcessingFacade` (main orchestrator entry point)
- **`entitlements.py`** — `Entitlements` frozen dataclass (`free_tier()` and `paid_tier()`)
- **`processor.py`** — `BankStatementProcessor` (PDF extraction → filter → dedup → sort → output)

This package has no dependency on any licensing code. The `paid_tier()` entitlement is defined here because it describes a feature set (`require_iban=False`), not access control — activating it requires a valid signed license issued externally.

### `bankstatements-free`

A thin CLI wrapper. Contains a single `app.py` that:

1. Calls `Entitlements.free_tier()` (hardcoded — no license check)
2. Delegates entirely to `BankStatementProcessingFacade` from `bankstatements-core`

The free tier processes bank statements that include an IBAN pattern. Credit card and loan statements (which have no IBAN) require the premium distribution.

---

## Processing Pipeline

```
app.py / ProcessorFactory
  └── BankStatementProcessingFacade.process_with_error_handling()
        └── BankStatementProcessor.run()
              ├── PDFProcessingOrchestrator.process_all_pdfs()
              │     └── ExtractionOrchestrator.extract_from_pdf()
              │           └── BankStatementProcessingFacade.extract_tables_from_pdf()
              │                 └── PDFTableExtractor.extract()    → ExtractionResult
              │                       ├── BoundaryDetector         (word_utils)
              │                       ├── RowClassifiers           (chain of responsibility)
              │                       └── RowBuilder               (word_utils)
              │     └── TransactionFilterService.apply_all_filters()
              │           ├── filter_empty_rows
              │           ├── filter_header_rows
              │           └── filter_invalid_dates
              └── ServiceRegistry.process_transaction_group()
                    ├── EnrichmentService        (Filename, document_type, transaction_type)
                    ├── DuplicateDetectionService
                    ├── TransactionSortingService
                    └── OutputService            (CSV / JSON / Excel)
```

`ExtractionResult` is the typed boundary between the extraction layer and the service layer:
- Produced by `PDFTableExtractor.extract()` and propagated unchanged through `ExtractionOrchestrator` and `PDFProcessingOrchestrator`
- Fields: `transactions: list[Transaction]`, `page_count: int`, `iban: str | None`, `source_file: Path`, `warnings: list[str]`
- `processor.run()` converts `result.transactions` to `list[dict]` via `transactions_to_dicts()` before handing off to `ServiceRegistry`

`ServiceRegistry` is the wiring point for all post-extraction services. It is constructed by `BankStatementProcessorBuilder.build()` via `ServiceRegistry.from_config()`, which accepts optional injected services to override defaults — enabling custom duplicate strategies and sort orders.

`AppConfig` (from environment variables) is the single source of truth for runtime configuration via Docker/CLI. Use `get_config_singleton()` to access it. For programmatic use, `ProcessorConfig` is constructed directly by the builder.

---

## Template System

Templates are JSON files that describe how to extract a table from a specific bank's PDF format. The registry chains detectors (filename, header, column header, IBAN) to match incoming PDFs to known templates.

**Bundled templates** (IBAN-based, ship inside the `bankstatements-core` package):

| Template | Bank |
|---|---|
| `aib_ireland.json` | AIB Ireland |
| `revolut.json` | Revolut |
| `default.json` | Generic fallback |

**Custom templates** can be placed in a directory pointed to by `CUSTOM_TEMPLATES_DIR`. These are loaded in addition to (and with higher priority than) the bundled templates.

Template resolution at runtime:

```
BANK_TEMPLATES_DIR   → unset: resolved from the installed bankstatements-core package
                     → set: use that directory instead
CUSTOM_TEMPLATES_DIR → unset: no custom templates
                     → set: load from that directory (overrides bundled templates of same name)
```

---

## Entitlements

`Entitlements` is a frozen dataclass checked at feature boundaries inside `bankstatements-core`:

```python
@dataclass(frozen=True)
class Entitlements:
    require_iban: bool   # True → only process PDFs with IBAN; False → process all

    @classmethod
    def free_tier(cls) -> "Entitlements":
        return cls(require_iban=True)

    @classmethod
    def paid_tier(cls) -> "Entitlements":
        return cls(require_iban=False)
```

The free-tier CLI always calls `free_tier()`. The premium distribution validates a signed license file and calls `paid_tier()` when the license is valid.

---

## ServiceRegistry

`ServiceRegistry` centralises all transaction-processing service wiring. It is the single construction point for `DuplicateDetectionService`, `TransactionSortingService`, and `IBANGroupingService`.

```python
# Default construction (services built from config)
registry = ServiceRegistry.from_config(config, entitlements=entitlements)

# Custom strategy injection (builder passes these in)
registry = ServiceRegistry.from_config(
    config,
    entitlements=entitlements,
    duplicate_detector=DuplicateDetectionService(my_strategy),
    sorting_service=TransactionSortingService(my_sort_strategy),
)
```

`BankStatementProcessorBuilder` constructs services from its configured strategies before calling `from_config()`, so `.with_duplicate_strategy()` and `.with_date_sorting()` are guaranteed to be honoured.

---

## Premium Distribution

A separate premium distribution extends the open-source packages with:

- Additional bank templates (credit card, loan statements) not present in this repository
- Support for processing statements without IBAN patterns
- License-gated access to `paid_tier()` entitlements

The premium distribution is not part of this repository. For premium access, contact the maintainer via a GitHub issue with label `license-inquiry`.

---

## Boundary Enforcement

CI enforces that `parser-free` never imports code from outside `bankstatements-core`. A dedicated `boundary-check.yml` workflow scans `packages/parser-free/src/` on every PR and fails if any prohibited imports are found.

This ensures the structural boundary between the free and premium tiers is maintained automatically on every PR.

---

## Versioning

| Package | Source | Tag convention |
|---|---|---|
| `bankstatements-core` | `packages/parser-core/pyproject.toml` | `core-v0.1.0` |
| `bankstatements-free` | `packages/parser-free/pyproject.toml` | `free-v0.1.0` |

Core and free versions are independent. A core release does not require a free release and vice versa.

`bankstatements-premium` follows a separate versioning scheme (`v1.x.x`) and is not published to PyPI.
