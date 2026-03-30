"""Tests for init command."""

from __future__ import annotations

from pathlib import Path

from bankstatements_core.commands.init import init_directories


class TestInitDirectories:
    """Tests for directory initialization command."""

    def test_init_creates_default_directories(self, tmp_path: Path):
        """Test that init creates all required directories."""
        result = init_directories(base_dir=tmp_path, verbose=False)

        assert result == 0
        assert (tmp_path / "input").exists()
        assert (tmp_path / "output").exists()
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "custom_templates").exists()

    def test_init_with_existing_directories(self, tmp_path: Path):
        """Test that init handles existing directories gracefully."""
        # Create directories first
        (tmp_path / "input").mkdir()
        (tmp_path / "output").mkdir()

        result = init_directories(base_dir=tmp_path, verbose=False)

        assert result == 0
        assert (tmp_path / "input").exists()
        assert (tmp_path / "output").exists()
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "custom_templates").exists()

    def test_init_creates_sample_files(self, tmp_path: Path):
        """Test that init creates sample files when requested."""
        result = init_directories(base_dir=tmp_path, create_samples=True, verbose=False)

        assert result == 0
        assert (tmp_path / ".env").exists()
        assert (tmp_path / "input" / "README.md").exists()

        # Check .env content
        env_content = (tmp_path / ".env").read_text()
        assert "Bank Statement Processor Configuration" in env_content
        assert "LOG_LEVEL" in env_content

        # Check README content
        readme_content = (tmp_path / "input" / "README.md").read_text()
        assert "Input Directory" in readme_content
        assert "PDF bank statements" in readme_content

    def test_init_does_not_overwrite_existing_env(self, tmp_path: Path):
        """Test that init does not overwrite existing .env file."""
        # Create .env with custom content
        env_file = tmp_path / ".env"
        env_file.write_text("CUSTOM_CONTENT=true\n")

        result = init_directories(base_dir=tmp_path, create_samples=True, verbose=False)

        assert result == 0
        # Verify .env was not overwritten
        assert env_file.read_text() == "CUSTOM_CONTENT=true\n"

    def test_init_uses_current_directory_by_default(self, tmp_path: Path, monkeypatch):
        """Test that init uses current working directory when base_dir not specified."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        result = init_directories(base_dir=None, verbose=False)

        assert result == 0
        assert (tmp_path / "input").exists()
        assert (tmp_path / "output").exists()

    def test_init_with_permission_error(self, tmp_path: Path, monkeypatch):
        """Test that init handles permission errors gracefully."""

        # Create a function that raises PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")

        # Patch Path.mkdir to raise PermissionError
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        result = init_directories(base_dir=tmp_path, verbose=False)

        assert result == 1  # Should fail

    def test_init_verbose_output(self, tmp_path: Path, capsys):
        """Test that verbose mode produces output."""
        result = init_directories(base_dir=tmp_path, verbose=True)

        assert result == 0

        # Check output contains expected messages
        captured = capsys.readouterr()
        assert "Initializing directory structure" in captured.out
        assert "✓ Created:" in captured.out or "✓ Already exists:" in captured.out
        assert "Next steps:" in captured.out

    def test_init_quiet_mode(self, tmp_path: Path, capsys):
        """Test that quiet mode suppresses output."""
        result = init_directories(base_dir=tmp_path, verbose=False)

        assert result == 0

        # Check no output in quiet mode
        captured = capsys.readouterr()
        assert captured.out == ""
