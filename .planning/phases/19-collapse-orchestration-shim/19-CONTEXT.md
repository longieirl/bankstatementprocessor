# Phase 19: Collapse Redundant Orchestration Layers / Retire pdf_table_extractor Shim - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure refactoring of the processing pipeline: remove duplicate logic from `BankStatementProcessor`, inline a 3-line passthrough method in `PDFProcessingOrchestrator`, and move the two named production files off the backward-compat shim. No behaviour change, no new features. Tracked as GitHub Issue #19.

</domain>

<decisions>
## Implementation Decisions

### Shim cleanup scope
- Fix **only the two files explicitly named in the RFC**: `extraction_orchestrator.py` and `pdf_extractor.py`
- The 4 additional production files that also import from the shim (`processing_facade.py`, `content_density.py`, `page_validation.py`, `row_merger.py`) are **out of scope** for this phase — left for RFC #20/#21
- Do not delete the shim — external callers may depend on it

### CSV writing methods
- `_write_csv_with_totals` and `_append_totals_to_csv` are considered **dead code** and must be removed from `BankStatementProcessor`
- `OutputOrchestrator.write_output_files()` at line 703 already handles this; no verification step needed

### Shim deprecation annotation
- Add a **runtime `DeprecationWarning`** at module import time in `pdf_table_extractor.py`
- External callers will receive a warning; no silent failure
- Style: `warnings.warn("...", DeprecationWarning, stacklevel=2)` at module level

### CI guard for shim imports
- Add a **pytest test** in the existing test suite that greps `packages/*/src/` for imports from `bankstatements_core.pdf_table_extractor` and fails if any are found
- This enforces the "shim is external-use-only" contract going forward

### Claude's Discretion
- Exact placement of the pytest shim-import guard (which test file, fixture structure)
- Wording of the DeprecationWarning message
- Whether `_filter_rows` (the private helper used by the three filter methods) is moved to `TransactionFilterService` or simply deleted along with its callers

</decisions>

<specifics>
## Specific Ideas

No specific requirements beyond what the RFC prescribes — open to standard approaches for test structure and warning format.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TransactionFilterService` (`services/transaction_filter.py`): already has `filter_empty_rows`, `filter_header_rows`, `filter_invalid_dates` — the RFC's proposed additions (`filter_invalid_date_rows`, `has_valid_transaction_date`) may already exist under slightly different names; verify before adding duplicates
- `extraction_facade.py`: already exports `extract_tables_from_pdf` and `detect_table_end_boundary_smart` — direct import targets for `extraction_orchestrator.py`
- `validation_facade.py`: already exports `validate_page_structure`, `detect_table_headers`, `merge_continuation_lines` — direct import targets for `pdf_extractor.py`

### Established Patterns
- Shim imports in `pdf_extractor.py` are **inline local imports** (inside method bodies), not top-level — must replace them as local imports or hoist to top-level consistently
- The project uses `pytest` for all testing; no separate lint tooling needed for the shim guard

### Integration Points
- `BankStatementProcessor.run()` at lines 609 and 685: the duplicate IBAN grouping — remove the processor's private call, keep only the orchestrator call at 685
- `PDFProcessingOrchestrator` line 126: the `_process_single_pdf` call site to inline

</code_context>

<deferred>
## Deferred Ideas

- Move remaining 4 production shim importers (`processing_facade.py`, `content_density.py`, `page_validation.py`, `row_merger.py`) — RFC #20
- Remove `enrich_with_document_type` defensive re-enrichment — explicitly deferred until RFC #16 (`ExtractionResult` boundary) is implemented (noted in RFC #19 as Issue D)

</deferred>

---

*Phase: 19-collapse-orchestration-shim*
*Context gathered: 2026-03-24*
