"""Tests for the updater module."""

from unittest.mock import MagicMock, patch

import pytest

from sip_videogen.utils.updater import (
    check_for_update,
    get_current_version,
    get_latest_version,
)


class TestGetCurrentVersion:
    """Tests for get_current_version function."""

    @patch("sip_videogen.utils.updater.get_installed_version")
    def test_returns_installed_version(self, mock_get: MagicMock) -> None:
        """Test that installed version is returned."""
        mock_get.return_value = "1.2.3"
        result = get_current_version()
        assert result == "1.2.3"

    @patch("sip_videogen.utils.updater.get_installed_version")
    def test_fallback_on_error(self, mock_get: MagicMock) -> None:
        """Test fallback when installed version fails."""
        mock_get.side_effect = Exception("Not installed")
        # Should return some version, not raise
        result = get_current_version()
        assert isinstance(result, str)


class TestGetLatestVersion:
    """Tests for get_latest_version function."""

    @patch("sip_videogen.utils.updater.httpx.get")
    def test_returns_latest_from_pypi(self, mock_get: MagicMock) -> None:
        """Test fetching latest version from PyPI."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "2.0.0"}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = get_latest_version()
        assert result == "2.0.0"

    @patch("sip_videogen.utils.updater.httpx.get")
    def test_returns_none_on_network_error(self, mock_get: MagicMock) -> None:
        """Test returns None when PyPI is unreachable."""
        mock_get.side_effect = Exception("Network error")
        result = get_latest_version()
        assert result is None

    @patch("sip_videogen.utils.updater.httpx.get")
    def test_returns_none_on_timeout(self, mock_get: MagicMock) -> None:
        """Test returns None on timeout."""
        import httpx

        mock_get.side_effect = httpx.TimeoutException("Timeout")
        result = get_latest_version()
        assert result is None


class TestCheckForUpdate:
    """Tests for check_for_update function."""

    @patch("sip_videogen.utils.updater.get_latest_version")
    @patch("sip_videogen.utils.updater.get_current_version")
    def test_update_available(
        self, mock_current: MagicMock, mock_latest: MagicMock
    ) -> None:
        """Test detection when update is available."""
        mock_current.return_value = "1.0.0"
        mock_latest.return_value = "2.0.0"

        update_available, latest, current = check_for_update()

        assert update_available is True
        assert latest == "2.0.0"
        assert current == "1.0.0"

    @patch("sip_videogen.utils.updater.get_latest_version")
    @patch("sip_videogen.utils.updater.get_current_version")
    def test_no_update_available(
        self, mock_current: MagicMock, mock_latest: MagicMock
    ) -> None:
        """Test detection when no update is available."""
        mock_current.return_value = "2.0.0"
        mock_latest.return_value = "2.0.0"

        update_available, latest, current = check_for_update()

        assert update_available is False
        assert latest == "2.0.0"
        assert current == "2.0.0"

    @patch("sip_videogen.utils.updater.get_latest_version")
    @patch("sip_videogen.utils.updater.get_current_version")
    def test_current_newer_than_latest(
        self, mock_current: MagicMock, mock_latest: MagicMock
    ) -> None:
        """Test when current version is newer (dev version)."""
        mock_current.return_value = "2.1.0"
        mock_latest.return_value = "2.0.0"

        update_available, latest, current = check_for_update()

        assert update_available is False

    @patch("sip_videogen.utils.updater.get_latest_version")
    @patch("sip_videogen.utils.updater.get_current_version")
    def test_pypi_unreachable(
        self, mock_current: MagicMock, mock_latest: MagicMock
    ) -> None:
        """Test behavior when PyPI is unreachable."""
        mock_current.return_value = "1.0.0"
        mock_latest.return_value = None

        update_available, latest, current = check_for_update()

        assert update_available is False
        assert latest is None
        assert current == "1.0.0"
