from bankstatements_core.pdf_table_extractor import (
    DEFAULT_COLUMNS,
    parse_columns_from_env,
)


def test_parse_columns_from_env_logs_warning(monkeypatch, caplog):
    monkeypatch.setenv("TABLE_COLUMNS", "{bad json")
    with caplog.at_level("WARNING"):
        cols = parse_columns_from_env()

    assert cols == DEFAULT_COLUMNS
    assert any("Failed to parse TABLE_COLUMNS" in rec.message for rec in caplog.records)
