# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.3] — 2026-04-10

### Added
- **CC statement support** (`#28, #29, #31–#34`, PR #122) — full credit card pipeline for paid tier: `ExtractionResult.card_number`, `BankTemplate.column_aliases`, `CCGroupingService` grouping by last-4 card suffix, wired into `ServiceRegistry.group_by_card()`. `processor.run()` splits on `card_number is None` to route bank vs CC results.
- **`aib_credit_card.json` template** (`#129`, PR #138) — correct CC column boundaries (`Transaction Date 29–80`, `Posting Date 80–118`, `Transaction Details 118–370`, `Amount 370–430`) so `RefContinuationClassifier` and `RowMergerService` handle CC two-line transaction splits correctly without falling back to bank columns.
- **`PDFExtractorOptions` dataclass** (`#109`, PR #139) — groups 8 optional `PDFTableExtractor` constructor params into a single options object, reducing the constructor from 11 params to 3.
- **Pylint design gate in CI** (`#85`, PR #104) — Xenon complexity gate and Pylint design checks added to CI pipeline.

### Fixed
- **#129** — Non-transaction (empty/phantom) rows in CC CSV/JSON output eliminated. Root cause: missing CC template caused `Ref:` lines to be misclassified as transactions. Fixed by adding `aib_credit_card.json` (PR #138) and an earlier classifier fix (PR #133).
- **#131** — CC amounts ending in `CR` now populate the Credit column instead of Debit. `reroute_cr_suffix()` added to `currency.py`, wired via `RowPostProcessor._reroute_cr_amounts()` (PR #135).
- **#132** — CC transactions sorted incorrectly due to yearless dates. Year inferred from `Payment Due` date in statement; ordinal date suffixes added to `_PAYMENT_DUE_PATTERNS` (PR #133).
- **#134** — CC output dates now include the statement year (e.g. `4 Feb 2025`). `Transaction._enrich_date()` appends year via `to_dict()` (PR #137).
- **#125** — Unknown-IBAN group was producing output files instead of routing to `excluded_files.json` (PR #126).
- **#123** — Free-tier pipeline was producing CC grouped output files instead of routing to `excluded_files.json`. CC grouping now gated behind paid-tier entitlement check (PR #124).
- **#106** — Credit card PDFs were unconditionally skipped on the paid tier; now correctly processed (PR #108).
- **#110** — `data_retention_days` was not forwarded to `DataRetentionService` (PR #115).
- **#78** — `date_propagated` extraction warnings suppressed from JSON/CSV output (PR #93).
- **#90** — 214 logging f-string violations (G004) replaced with `%`-formatting (PR #100).
- **#98** — `_detect_text_based_table` decomposed to pass Xenon C complexity gate (PR #101).
- **#80** — Pre-existing unused imports (F401) removed from test files (PR #94).

### Changed
- **Service layer migrated to `list[Transaction]`** (`#71`, PR #79) — all services accept/return `list[Transaction]`; dict round-trips removed. Output boundary conversion via `transactions_to_dicts(currency_symbol="")`.
- **Currency-agnostic field names** (`#62–#64, #66`, PR #67) — `TransactionRow` fields renamed `_EUR → _AMT`; `strip_currency_symbols()` unified in `domain/currency.py`; `currency_symbol` defaults to `""` throughout.
- **`ruff` replaces `flake8`** (`#84, #89`, PR #91) — ruff lint config in both `pyproject.toml` files; pre-commit hook updated to `astral-sh/ruff-pre-commit v0.8.0`.
- **`pip-audit` replaces `safety`** (`#86`, PR #97) — dependency vulnerability scanning updated.
- **Hadolint + pinned `trivy-action`** added to CI (`#87`, PR #96).
- **`[skip downstream]` support** added to dispatch-downstream CI job (PR #82).
- **`#111, #112, #113`** — Dead fields removed from `ExtractionConfig` and `ExtractionScoringConfig`; dead `scoring_config` param removed from `PDFTableExtractor` (PRs #116, #117).
- **CONTRIBUTING.md** — Coverage threshold corrected to 91% to match `pyproject.toml` (PR #140).

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
