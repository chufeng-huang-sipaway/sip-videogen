"""Tests for CLI commands in sip-videogen."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from sip_videogen.cli import _validate_idea, app

runner = CliRunner()


class TestValidateIdea:
    """Tests for _validate_idea function."""

    def test_valid_idea(self) -> None:
        """Test valid idea passes validation."""
        result = _validate_idea("A cat astronaut explores Mars")
        assert result == "A cat astronaut explores Mars"

    def test_idea_gets_stripped(self) -> None:
        """Test whitespace is stripped from idea."""
        result = _validate_idea("  A cat astronaut  ")
        assert result == "A cat astronaut"

    def test_empty_idea_raises_error(self) -> None:
        """Test empty idea raises BadParameter."""
        import typer

        with pytest.raises(typer.BadParameter) as exc_info:
            _validate_idea("")
        assert "empty" in str(exc_info.value)

    def test_whitespace_only_idea_raises_error(self) -> None:
        """Test whitespace-only idea raises BadParameter."""
        import typer

        with pytest.raises(typer.BadParameter):
            _validate_idea("   ")

    def test_too_short_idea_raises_error(self) -> None:
        """Test too short idea raises BadParameter."""
        import typer

        with pytest.raises(typer.BadParameter) as exc_info:
            _validate_idea("Cat")
        assert "too short" in str(exc_info.value)

    def test_too_long_idea_raises_error(self) -> None:
        """Test too long idea raises BadParameter."""
        import typer

        long_idea = "A" * 2001
        with pytest.raises(typer.BadParameter) as exc_info:
            _validate_idea(long_idea)
        assert "too long" in str(exc_info.value)

    def test_minimum_length_idea(self) -> None:
        """Test minimum length idea (5 chars) is valid."""
        result = _validate_idea("Hello")
        assert result == "Hello"

    def test_maximum_length_idea(self) -> None:
        """Test maximum length idea (2000 chars) is valid."""
        long_idea = "A" * 2000
        result = _validate_idea(long_idea)
        assert len(result) == 2000


class TestStatusCommand:
    """Tests for 'sip-videogen status' command."""

    def test_status_all_configured(self) -> None:
        """Test status command when all settings are configured."""
        result = runner.invoke(app, ["status"])
        # Should show configured status (using mocked env vars from conftest)
        assert result.exit_code == 0
        assert "OPENAI_API_KEY" in result.output
        assert "GEMINI_API_KEY" in result.output

    def test_status_shows_current_settings(self) -> None:
        """Test status shows current configuration values."""
        result = runner.invoke(app, ["status"])
        assert "us-central1" in result.output  # Default location
        assert "Output Directory" in result.output

    def test_status_missing_config(self) -> None:
        """Test status command when configuration is missing."""
        import os

        # Remove required env vars
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""},
            clear=False,
        ):
            from sip_videogen.config.settings import get_settings

            get_settings.cache_clear()

            result = runner.invoke(app, ["status"])
            # Should still run but show not set status
            assert "Not set" in result.output or result.exit_code == 1


class TestSetupCommand:
    """Tests for 'sip-videogen setup' command."""

    @patch("sip_videogen.cli.run_setup_wizard")
    def test_setup_runs_wizard(self, mock_wizard: MagicMock) -> None:
        """Test setup command runs the interactive wizard."""
        mock_wizard.return_value = True
        result = runner.invoke(app, ["setup"])
        assert result.exit_code == 0
        mock_wizard.assert_called_once()


class TestConfigCommand:
    """Tests for 'sip-videogen config' command."""

    @patch("sip_videogen.cli.show_current_config")
    @patch("sip_videogen.cli.get_config_path")
    def test_config_show(
        self, mock_path: MagicMock, mock_show: MagicMock
    ) -> None:
        """Test config --show displays current configuration."""
        mock_path.return_value = "/home/user/.sip-videogen/.env"
        result = runner.invoke(app, ["config", "--show"])
        assert result.exit_code == 0
        mock_show.assert_called_once()

    @patch("sip_videogen.cli.run_setup_wizard")
    def test_config_interactive(self, mock_wizard: MagicMock) -> None:
        """Test config command runs interactive wizard."""
        mock_wizard.return_value = True
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        mock_wizard.assert_called_once_with(reset=False)

    @patch("sip_videogen.cli.run_setup_wizard")
    def test_config_reset(self, mock_wizard: MagicMock) -> None:
        """Test config --reset runs wizard in reset mode."""
        mock_wizard.return_value = True
        result = runner.invoke(app, ["config", "--reset"])
        assert result.exit_code == 0
        mock_wizard.assert_called_once_with(reset=True)


class TestUpdateCommand:
    """Tests for 'sip-videogen update' command."""

    @patch("sip_videogen.cli.check_for_update")
    @patch("sip_videogen.cli.get_current_version")
    def test_update_check_only_no_update(
        self, mock_version: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test update --check when no update is available."""
        mock_version.return_value = "1.0.0"
        mock_check.return_value = (False, "1.0.0", "1.0.0")
        result = runner.invoke(app, ["update", "--check"])
        assert result.exit_code == 0
        assert "latest version" in result.output.lower()

    @patch("sip_videogen.cli.check_for_update")
    @patch("sip_videogen.cli.get_current_version")
    def test_update_check_only_with_update(
        self, mock_version: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test update --check when update is available."""
        mock_version.return_value = "1.0.0"
        mock_check.return_value = (True, "1.1.0", "1.0.0")
        result = runner.invoke(app, ["update", "--check"])
        assert result.exit_code == 0
        assert "1.1.0" in result.output


class TestGenerateCommand:
    """Tests for 'sip-videogen generate' command."""

    def test_generate_help(self) -> None:
        """Test generate command help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--scenes" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output

    def test_generate_missing_idea(self) -> None:
        """Test generate command requires idea argument."""
        result = runner.invoke(app, ["generate"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    def test_generate_invalid_scenes_count(self) -> None:
        """Test generate validates scenes count."""
        result = runner.invoke(
            app, ["generate", "Test idea here", "--scenes", "15"]
        )
        assert result.exit_code != 0
        # Should fail validation (max 10)

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_dry_run(self, mock_asyncio_run: MagicMock) -> None:
        """Test generate with --dry-run flag."""
        # Mock the async pipeline
        mock_asyncio_run.return_value = None

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut explores Mars", "--dry-run"],
            input="y\n",  # Accept cost confirmation
        )

        # With dry-run, should show dry run mode message
        assert "Dry run mode" in result.output

    def test_generate_empty_idea_rejected(self) -> None:
        """Test generate rejects empty idea."""
        result = runner.invoke(app, ["generate", ""])
        assert result.exit_code != 0
        assert "Invalid idea" in result.output or "empty" in result.output.lower()

    def test_generate_short_idea_rejected(self) -> None:
        """Test generate rejects too short idea."""
        result = runner.invoke(app, ["generate", "Cat"])
        assert result.exit_code != 0

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_shows_cost_estimate(self, mock_asyncio_run: MagicMock) -> None:
        """Test generate shows cost estimate before proceeding."""
        mock_asyncio_run.return_value = None

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut explores Mars"],
            input="n\n",  # Decline at cost confirmation
        )

        assert "Estimated Cost" in result.output or "Cost Estimate" in result.output
        assert "cancelled" in result.output.lower()

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_yes_flag_skips_confirmation(
        self, mock_asyncio_run: MagicMock
    ) -> None:
        """Test --yes flag skips cost confirmation."""
        mock_asyncio_run.return_value = None

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut explores Mars", "--dry-run", "--yes"],
        )

        # Should proceed without asking for confirmation
        assert result.exit_code == 0 or "Dry run" in result.output


class TestGenerateCommandErrors:
    """Tests for error handling in generate command."""

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_script_development_error(
        self, mock_asyncio_run: MagicMock
    ) -> None:
        """Test handling of script development errors."""
        from sip_videogen.agents import ScriptDevelopmentError

        mock_asyncio_run.side_effect = ScriptDevelopmentError("API rate limit")

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut", "--yes"],
        )

        assert result.exit_code == 1
        assert "Script" in result.output or "failed" in result.output.lower()

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_gcs_authentication_error(
        self, mock_asyncio_run: MagicMock
    ) -> None:
        """Test handling of GCS authentication errors."""
        from sip_videogen.storage import GCSAuthenticationError

        mock_asyncio_run.side_effect = GCSAuthenticationError(
            "Invalid credentials"
        )

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut", "--yes"],
        )

        assert result.exit_code == 1
        assert "authentication" in result.output.lower()

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_gcs_bucket_not_found_error(
        self, mock_asyncio_run: MagicMock
    ) -> None:
        """Test handling of GCS bucket not found errors."""
        from sip_videogen.storage import GCSBucketNotFoundError

        mock_asyncio_run.side_effect = GCSBucketNotFoundError(
            "Bucket does not exist"
        )

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut", "--yes"],
        )

        assert result.exit_code == 1
        assert "bucket" in result.output.lower()

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_ffmpeg_error(self, mock_asyncio_run: MagicMock) -> None:
        """Test handling of FFmpeg errors."""
        from sip_videogen.assembler import FFmpegError

        mock_asyncio_run.side_effect = FFmpegError("FFmpeg not found")

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut", "--yes"],
        )

        assert result.exit_code == 1
        assert "FFmpeg" in result.output

    @patch("sip_videogen.cli.asyncio.run")
    def test_generate_keyboard_interrupt(
        self, mock_asyncio_run: MagicMock
    ) -> None:
        """Test handling of keyboard interrupt."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        result = runner.invoke(
            app,
            ["generate", "A cat astronaut", "--yes"],
        )

        assert result.exit_code == 130
        assert "cancelled" in result.output.lower()


class TestAppMetadata:
    """Tests for CLI app metadata."""

    def test_app_name(self) -> None:
        """Test app name is correct."""
        assert app.info.name == "sip-videogen"

    def test_app_has_help(self) -> None:
        """Test app has help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "video" in result.output.lower()
        assert "AI" in result.output

    def test_all_commands_available(self) -> None:
        """Test all expected commands are available."""
        result = runner.invoke(app, ["--help"])
        assert "generate" in result.output
        assert "status" in result.output
        assert "setup" in result.output
        assert "config" in result.output
        assert "update" in result.output
