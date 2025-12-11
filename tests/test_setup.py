"""Tests for config setup module."""

import pytest

from sip_videogen.config.setup import parse_env_block, validate_config


class TestParseEnvBlock:
    """Tests for parse_env_block function."""

    def test_parse_simple_key_value(self) -> None:
        """Test parsing simple KEY=value pairs."""
        text = "OPENAI_API_KEY=sk-test123"
        result = parse_env_block(text)
        assert result == {"OPENAI_API_KEY": "sk-test123"}

    def test_parse_multiple_keys(self) -> None:
        """Test parsing multiple keys."""
        text = """
OPENAI_API_KEY=sk-test123
GEMINI_API_KEY=AIza456
GOOGLE_CLOUD_PROJECT=my-project
"""
        result = parse_env_block(text)
        assert result == {
            "OPENAI_API_KEY": "sk-test123",
            "GEMINI_API_KEY": "AIza456",
            "GOOGLE_CLOUD_PROJECT": "my-project",
        }

    def test_parse_quoted_values(self) -> None:
        """Test parsing values with quotes."""
        text = '''
OPENAI_API_KEY="sk-test123"
GEMINI_API_KEY='AIza456'
'''
        result = parse_env_block(text)
        assert result["OPENAI_API_KEY"] == "sk-test123"
        assert result["GEMINI_API_KEY"] == "AIza456"

    def test_parse_export_prefix(self) -> None:
        """Test parsing lines with export prefix."""
        text = "export OPENAI_API_KEY=sk-test123"
        result = parse_env_block(text)
        assert result == {"OPENAI_API_KEY": "sk-test123"}

    def test_ignore_comments(self) -> None:
        """Test that comments are ignored."""
        text = """
# This is a comment
OPENAI_API_KEY=sk-test123
# Another comment
"""
        result = parse_env_block(text)
        assert result == {"OPENAI_API_KEY": "sk-test123"}

    def test_ignore_empty_lines(self) -> None:
        """Test that empty lines are ignored."""
        text = """

OPENAI_API_KEY=sk-test123


GEMINI_API_KEY=AIza456

"""
        result = parse_env_block(text)
        assert len(result) == 2

    def test_case_insensitive_keys(self) -> None:
        """Test that keys are converted to uppercase."""
        text = "openai_api_key=sk-test123"
        result = parse_env_block(text)
        assert "OPENAI_API_KEY" in result

    def test_empty_text_returns_empty_dict(self) -> None:
        """Test empty text returns empty dict."""
        result = parse_env_block("")
        assert result == {}

    def test_parse_value_with_equals_sign(self) -> None:
        """Test parsing values containing equals signs."""
        text = "SECRET_KEY=abc=def=ghi"
        result = parse_env_block(text)
        assert result["SECRET_KEY"] == "abc=def=ghi"


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_all_required_keys_present(self) -> None:
        """Test validation passes with all required keys."""
        config = {
            "OPENAI_API_KEY": "sk-validkey123456789",
            "GEMINI_API_KEY": "AIzaValid",
            "GOOGLE_CLOUD_PROJECT": "my-project",
            "SIP_GCS_BUCKET_NAME": "my-bucket",
        }
        missing, warnings = validate_config(config)
        assert missing == []

    def test_missing_required_keys(self) -> None:
        """Test validation reports missing keys."""
        config = {
            "OPENAI_API_KEY": "sk-validkey123456789",
        }
        missing, warnings = validate_config(config)
        assert "GEMINI_API_KEY" in missing
        assert "GOOGLE_CLOUD_PROJECT" in missing
        assert "SIP_GCS_BUCKET_NAME" in missing

    def test_placeholder_values_are_invalid(self) -> None:
        """Test that placeholder values are treated as missing."""
        config = {
            "OPENAI_API_KEY": "sk-...",
            "GEMINI_API_KEY": "...",
            "GOOGLE_CLOUD_PROJECT": "your-project-id",
            "SIP_GCS_BUCKET_NAME": "your-bucket-name",
        }
        missing, warnings = validate_config(config)
        assert len(missing) == 4

    def test_empty_values_are_invalid(self) -> None:
        """Test that empty values are treated as missing."""
        config = {
            "OPENAI_API_KEY": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_CLOUD_PROJECT": "",
            "SIP_GCS_BUCKET_NAME": "",
        }
        missing, warnings = validate_config(config)
        assert len(missing) == 4
