"""Tests for BankStatementProcessorBuilder."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bankstatements_core.builders import BankStatementProcessorBuilder
from bankstatements_core.patterns.strategies import AllFieldsDuplicateStrategy, CSVOutputStrategy


class TestBankStatementProcessorBuilder:
    """Tests for BankStatementProcessorBuilder."""

    def test_builder_initialization(self):
        """Test builder initializes with correct defaults."""
        builder = BankStatementProcessorBuilder()

        # Required parameters should be None
        assert builder._input_dir is None
        assert builder._output_dir is None

        # Optional parameters should have sensible defaults
        assert builder._table_top_y == 300
        assert builder._table_bottom_y == 720
        assert builder._columns is None
        assert builder._enable_dynamic_boundary is False
        assert builder._sort_by_date is True
        assert builder._totals_columns is None
        assert builder._generate_monthly_summary is True
        assert builder._output_strategies is None
        assert builder._duplicate_strategy is None
        assert builder._repository is None

    def test_with_input_dir_returns_self(self):
        """Test with_input_dir returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_input_dir(Path("/tmp"))
        assert result is builder
        assert builder._input_dir == Path("/tmp")

    def test_with_output_dir_returns_self(self):
        """Test with_output_dir returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_output_dir(Path("/tmp/out"))
        assert result is builder
        assert builder._output_dir == Path("/tmp/out")

    def test_with_table_bounds_returns_self(self):
        """Test with_table_bounds returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_table_bounds(100, 500)
        assert result is builder
        assert builder._table_top_y == 100
        assert builder._table_bottom_y == 500

    def test_with_columns_returns_self(self):
        """Test with_columns returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        columns = {"Date": (0, 100), "Amount": (100, 200)}
        result = builder.with_columns(columns)
        assert result is builder
        assert builder._columns == columns

    def test_with_dynamic_boundary_returns_self(self):
        """Test with_dynamic_boundary returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_dynamic_boundary(True)
        assert result is builder
        assert builder._enable_dynamic_boundary is True

    def test_with_date_sorting_returns_self(self):
        """Test with_date_sorting returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_date_sorting(False)
        assert result is builder
        assert builder._sort_by_date is False

    def test_with_totals_returns_self(self):
        """Test with_totals returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        patterns = ["debit", "credit"]
        result = builder.with_totals(patterns)
        assert result is builder
        assert builder._totals_columns == patterns

    def test_with_monthly_summary_returns_self(self):
        """Test with_monthly_summary returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        result = builder.with_monthly_summary(False)
        assert result is builder
        assert builder._generate_monthly_summary is False

    def test_with_output_strategies_returns_self(self):
        """Test with_output_strategies returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        strategies = {"csv": CSVOutputStrategy()}
        result = builder.with_output_strategies(strategies)
        assert result is builder
        assert builder._output_strategies == strategies

    def test_with_duplicate_strategy_returns_self(self):
        """Test with_duplicate_strategy returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        strategy = AllFieldsDuplicateStrategy()
        result = builder.with_duplicate_strategy(strategy)
        assert result is builder
        assert builder._duplicate_strategy == strategy

    def test_with_repository_returns_self(self):
        """Test with_repository returns builder for chaining."""
        builder = BankStatementProcessorBuilder()
        from bankstatements_core.patterns.repositories import FileSystemTransactionRepository

        repo = FileSystemTransactionRepository()
        result = builder.with_repository(repo)
        assert result is builder
        assert builder._repository == repo

    def test_fluent_interface_chaining(self):
        """Test that multiple methods can be chained."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            builder = (
                BankStatementProcessorBuilder()
                .with_input_dir(input_dir)
                .with_output_dir(output_dir)
                .with_table_bounds(200, 600)
                .with_date_sorting(False)
                .with_monthly_summary(False)
            )

            assert builder._input_dir == input_dir
            assert builder._output_dir == output_dir
            assert builder._table_top_y == 200
            assert builder._table_bottom_y == 600
            assert builder._sort_by_date is False
            assert builder._generate_monthly_summary is False

    def test_build_with_minimal_config(self):
        """Test building processor with only required parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            processor = (
                BankStatementProcessorBuilder()
                .with_input_dir(input_dir)
                .with_output_dir(output_dir)
                .build()
            )

            assert processor.input_dir == input_dir
            assert processor.output_dir == output_dir
            # Defaults should be applied
            assert processor.table_top_y == 300
            assert processor.table_bottom_y == 720
            assert processor.sort_by_date is True
            assert processor.generate_monthly_summary is True

    def test_build_with_full_config(self):
        """Test building processor with all parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            columns = {"Date": (0, 100)}
            totals = ["debit", "credit"]
            strategies = {"csv": CSVOutputStrategy()}
            dup_strategy = AllFieldsDuplicateStrategy()

            processor = (
                BankStatementProcessorBuilder()
                .with_input_dir(input_dir)
                .with_output_dir(output_dir)
                .with_table_bounds(250, 650)
                .with_columns(columns)
                .with_dynamic_boundary(True)
                .with_date_sorting(False)
                .with_totals(totals)
                .with_monthly_summary(False)
                .with_output_strategies(strategies)
                .with_duplicate_strategy(dup_strategy)
                .build()
            )

            assert processor.input_dir == input_dir
            assert processor.output_dir == output_dir
            assert processor.table_top_y == 250
            assert processor.table_bottom_y == 650
            assert processor.columns == columns
            assert processor.enable_dynamic_boundary is True
            assert processor.sort_by_date is False
            assert processor.totals_columns == totals
            assert processor.generate_monthly_summary is False
            assert processor.output_strategies == strategies
            assert processor._duplicate_strategy == dup_strategy

    def test_build_without_input_dir_raises_error(self):
        """Test that build raises error if input_dir is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            builder = BankStatementProcessorBuilder().with_output_dir(output_dir)

            with pytest.raises(ValueError, match="Input directory is required"):
                builder.build()

    def test_build_without_output_dir_raises_error(self):
        """Test that build raises error if output_dir is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()

            builder = BankStatementProcessorBuilder().with_input_dir(input_dir)

            with pytest.raises(ValueError, match="Output directory is required"):
                builder.build()

    def test_build_without_required_params_raises_error(self):
        """Test that build raises error if no directories are set."""
        builder = BankStatementProcessorBuilder()

        with pytest.raises(ValueError, match="Input directory is required"):
            builder.build()

    def test_builder_is_reusable(self):
        """Test that builder can be reused to create multiple processors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir1 = Path(tmpdir) / "output1"
            output_dir2 = Path(tmpdir) / "output2"
            input_dir.mkdir()
            output_dir1.mkdir()
            output_dir2.mkdir()

            # Create base builder
            base_builder = BankStatementProcessorBuilder().with_input_dir(input_dir)

            # Create two processors with different output dirs
            processor1 = base_builder.with_output_dir(output_dir1).build()
            processor2 = base_builder.with_output_dir(output_dir2).build()

            assert processor1.output_dir == output_dir1
            assert processor2.output_dir == output_dir2
            # Both should share the same input dir
            assert processor1.input_dir == input_dir
            assert processor2.input_dir == input_dir
