# Configuration Reference

All settings are environment variables. Pass them via `docker-compose.yml`, a `.env` file, or `docker run -e`.

---

## Common settings

These are exposed in `docker-compose.yml` and cover most use cases.

| Variable | Default | Description |
|---|---|---|
| `OUTPUT_FORMATS` | `csv,json` | Comma-separated output formats: `csv`, `json`, `excel` |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `EXIT_AFTER_PROCESSING` | `true` | Exit container after processing. Set `false` for interactive use. |
| `RECURSIVE_SCAN` | `true` | Scan subdirectories of `./input` recursively |
| `SORT_BY_DATE` | `true` | Sort transactions by date in output |

---

## Advanced settings

Override by adding to the `environment` block in `docker-compose.yml` or passing `-e` to `docker run`.

| Variable | Default | Description |
|---|---|---|
| `ENABLE_DYNAMIC_BOUNDARY` | `false` | Auto-detect table boundaries instead of using `TABLE_TOP_Y`/`TABLE_BOTTOM_Y` |
| `TABLE_TOP_Y` | `250` | Top Y-coordinate of the transaction table (pixels from top of page) |
| `TABLE_BOTTOM_Y` | `720` | Bottom Y-coordinate of the transaction table |
| `TOTALS_COLUMNS` | `debit,credit` | Columns to sum in expense analysis output |
| `GENERATE_EXPENSE_ANALYSIS` | `true` | Generate expense analysis report |
| `GENERATE_MONTHLY_SUMMARY` | `true` | Generate monthly summary |
| `DATA_RETENTION_DAYS` | `0` | Delete output files older than N days. `0` = disabled. |
| `AUTO_CLEANUP_ON_EXIT` | `false` | Delete input PDFs after processing |
| `LOGS_DIR` | `logs` | Directory for processing activity logs |

---

## Privacy / telemetry

These are set in the `Dockerfile` and apply to all runs without configuration.

| Variable | Value | Purpose |
|---|---|---|
| `DO_NOT_TRACK` | `1` | Global telemetry opt-out |
| `TELEMETRY_DISABLED` | `true` | Secondary telemetry opt-out |
| `ANALYTICS_DISABLED` | `true` | Analytics opt-out |
| `NO_ANALYTICS` | `1` | Analytics opt-out |
| `PANDAS_TELEMETRY_ENABLED` | `false` | Disable pandas telemetry |
| `SENTRY_DSN` | _(empty)_ | Sentry error reporting — disabled |
| `SEGMENT_WRITE_KEY` | _(empty)_ | Segment analytics — disabled |
