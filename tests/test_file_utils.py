"""Tests for file utility functions."""

import os
from pathlib import Path

import pytest

from sip_studio.utils.file_utils import write_atomically


class TestWriteAtomically:
    """Tests for write_atomically function."""

    def test_writes_text_content(self, tmp_path: Path):
        """Should write text content to file."""
        fp = tmp_path / "test.json"
        write_atomically(fp, '{"key":"value"}')
        assert fp.read_text() == '{"key":"value"}'

    def test_writes_bytes_content(self, tmp_path: Path):
        """Should write bytes content to file."""
        fp = tmp_path / "test.bin"
        write_atomically(fp, b"\x00\x01\x02\x03")
        assert fp.read_bytes() == b"\x00\x01\x02\x03"

    def test_creates_parent_directories(self, tmp_path: Path):
        """Should create parent dirs if they don't exist."""
        fp = tmp_path / "a" / "b" / "c" / "test.json"
        write_atomically(fp, '{"nested":true}')
        assert fp.exists()
        assert fp.read_text() == '{"nested":true}'

    def test_sets_file_mode(self, tmp_path: Path):
        """Should set file permissions when mode specified."""
        fp = tmp_path / "secret.json"
        write_atomically(fp, '{"api_key":"xxx"}', mode=0o600)
        assert fp.exists()
        assert (fp.stat().st_mode & 0o777) == 0o600

    def test_overwrites_existing_file(self, tmp_path: Path):
        """Should overwrite existing file atomically."""
        fp = tmp_path / "test.json"
        fp.write_text('{"old":"data"}')
        write_atomically(fp, '{"new":"data"}')
        assert fp.read_text() == '{"new":"data"}'

    def test_cleans_up_temp_on_failure(self, tmp_path: Path, monkeypatch):
        """Should remove temp file if write fails."""
        fp = tmp_path / "test.json"

        def fail_fsync(fd):
            raise OSError("fsync failed")

        monkeypatch.setattr(os, "fsync", fail_fsync)
        with pytest.raises(OSError):
            write_atomically(fp, "content")
        # Temp file should be cleaned up
        assert not (tmp_path / "test.json.tmp").exists()
        assert not fp.exists()

    def test_no_partial_writes(self, tmp_path: Path):
        """Should not leave partial content on atomic failure."""
        fp = tmp_path / "test.json"
        fp.write_text('{"original":"data"}')
        # Simulate failure by making temp file write fail
        tmp = fp.with_suffix(".json.tmp")
        tmp.mkdir()  # Make tmp a directory so write fails
        with pytest.raises((OSError, IsADirectoryError)):
            write_atomically(fp, '{"new":"data"}')
        # Original should be untouched
        assert fp.read_text() == '{"original":"data"}'
        tmp.rmdir()
