# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.2] — 2026-03-25

### Fixed
- **#47** — `filter_service.apply_all_filters()` result was computed and logged but silently discarded. Filtered rows are now written back to `result.transactions` in `PDFProcessingOrchestrator.process_all_pdfs()`, so `filter_empty_rows`, `filter_header_rows`, and `filter_invalid_dates` are applied to every successfully extracted PDF.
- **#52** — `BankStatementProcessorBuilder.with_duplicate_strategy()` and `.with_date_sorting()` were inert: `build()` called `ServiceRegistry.from_config()` with no services, causing the registry to create its own defaults and silently ignore the configured strategy. The builder now constructs `DuplicateDetectionService` and `TransactionSortingService` from its configured values and passes them explicitly into `ServiceRegistry.from_config()`.
- **#55** — Credit card / no-IBAN PDFs excluded from the `pdfs_extracted` count in processing output. `process_all_pdfs()` now returns a 3-tuple `(results, pdf_count, pages_read)`.

### Changed (architecture cleanup — PRs #56, #57)
- **#49** — `ChronologicalSortingStrategy` sorts dicts directly via `DateParserService`, removing a redundant `Transaction` round-trip.
- **#48** — Deferred circular imports in `processor.py` removed; `service_registry`, `monthly_summary`, and `expense_analysis` import `ColumnAnalysisService`/`DateParserService` directly at module level.
- **#50** — `TransactionClassifier._looks_like_date` delegates to `RowAnalysisService.looks_like_date`, removing a duplicate regex and fixing a subtle 1-or-2-digit day matching bug.
- **#51** — `ProcessorFactory.create_from_config()` builds `ProcessorConfig` in one block via `BankStatementProcessorBuilder.with_processor_config()`; new config knobs now touch ≤2 files.

---

## [0.1.1] — 2026-03-25

### Added (v1.1 — Transaction Pipeline & Word Utils)
- **Transaction enrichment** (`source_page: int | None`, `confidence_score: float`, `extraction_warnings: list[str]`) — all three fields default correctly and survive `to_dict` / `from_dict` round-trips (#16 / Phase 21).
- **`ExtractionResult` dataclass** (`domain/models/extraction_result.py`) — typed extraction boundary with `transactions`, `page_count`, `iban`, `source_file`, and `warnings` fields. Architecture guard test enforces placement in `domain/models/` (#16 / Phase 22).
- **End-to-end `ExtractionResult` pipeline** — `PDFTableExtractor.extract()`, `ExtractionOrchestrator`, `PDFProcessingOrchestrator`, and `processor` all produce and consume `ExtractionResult`; zero tuple-index unpacking remains (#16 / Phase 23).
- **`extraction/word_utils.py`** — canonical module for `group_words_by_y`, `assign_words_to_columns` (with `strict_rightmost` flag), and `calculate_column_coverage`. Five callers migrated; four private duplicate methods deleted (#21 / Phase 24).

### Changed
- **ServiceRegistry** introduced (`feat/28`, PR #44) — `ServiceRegistry.from_config(ProcessorConfig, Entitlements)` wires all transaction-processing services. `TransactionProcessingOrchestrator` deleted (PR #46 / issue #45).
- **ClassifierRegistry** with explicit integer priorities added to `row_classifiers.py` (fix/29, PR #39).
- **`recursive_scan` default** changed `False → True` in `ProcessingConfig`, `AppConfig`, `ProcessorBuilder`, and `PDFDiscoveryService`; `RECURSIVE_SCAN` env var added to `docker-compose.yml` (fix/40, PR #41).
- **`ScoringConfig` injectable** via `BankStatementProcessorBuilder.with_scoring_config()` (feat/32, PR #36).

---

## [0.1.0] — 2026-03-24

### Added (v1.0 — Architecture RFC)
- **`extraction/word_utils.py`** foundation work — `RowClassifier` chain injected as shared dependency (issue #17, PR #22).
- **`PDFTableExtractor` decomposed** into `PageHeaderAnalyser`, `RowBuilder`, and `RowPostProcessor` (issue #18, PR #23).
- **Facade passthroughs deleted** — `content_analysis_facade.py`, `validation_facade.py`, `row_classification_facade.py` removed; service→shim circular import chain broken (issue #20, Phase 20).
- **`pdf_table_extractor.py` shim** rewired to module-level singletons; `pdf_extractor.py` cleaned of four lazy facade imports.
- Architecture guard test `test_facade_modules_deleted` added.

### Changed
- Credit card templates (`aib_credit_card.json`, `credit_card_default.json`) removed from open-source repo; credit card support is PAID tier only via `require_iban=False` in `Entitlements.paid_tier()`.
