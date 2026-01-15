"""Tests for sip_studio.advisor.tools.task_tools module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sip_studio.advisor.tools.task_tools import (
    _build_tasks_file,
    _get_tasks_path,
    _impl_complete_task_file,
    _impl_create_task_file,
    _impl_get_remaining_tasks,
    _impl_update_task,
    _parse_tasks_file,
)

# =========================================================================
# _parse_tasks_file Tests
# =========================================================================
SAMPLE_TASKS_CONTENT = """# Campaign Images

## Status
- **Progress**: 2/5 complete
- **State**: IN_PROGRESS
- **Created**: 2024-01-15T10:30:00Z

## Tasks
- [x] 1. Hero shot on white → /images/hero.png
- [x] 2. Lifestyle kitchen scene → /images/lifestyle.png
- [ ] 3. Product detail close-up
- [ ] 4. In-use demonstration
- [ ] 5. Social media format

## Context
Create images for coffee brand launch
"""


def test_parse_tasks_file_full():
    result = _parse_tasks_file(SAMPLE_TASKS_CONTENT)
    assert result["title"] == "Campaign Images"
    assert result["progress"] == 2
    assert result["total"] == 5
    assert result["state"] == "IN_PROGRESS"
    assert result["created"] == "2024-01-15T10:30:00Z"
    assert len(result["tasks"]) == 5
    assert result["tasks"][0]["number"] == 1
    assert result["tasks"][0]["description"] == "Hero shot on white"
    assert result["tasks"][0]["done"] is True
    assert result["tasks"][0]["output"] == "/images/hero.png"
    assert result["tasks"][2]["done"] is False
    assert result["tasks"][2]["output"] is None
    assert "coffee brand launch" in result["context"]


def test_parse_tasks_file_empty():
    result = _parse_tasks_file("")
    assert result["title"] == ""
    assert result["total"] == 0
    assert result["tasks"] == []


def test_parse_tasks_file_minimal():
    content = "# Simple Task\n\n## Tasks\n- [ ] 1. Do thing\n"
    result = _parse_tasks_file(content)
    assert result["title"] == "Simple Task"
    assert len(result["tasks"]) == 1
    assert result["tasks"][0]["number"] == 1
    assert result["tasks"][0]["done"] is False


# =========================================================================
# _build_tasks_file Tests
# =========================================================================
def test_build_tasks_file_basic():
    tasks = [
        {"number": 1, "description": "Task A", "done": False, "output": None},
        {"number": 2, "description": "Task B", "done": True, "output": "/out.png"},
    ]
    content = _build_tasks_file(
        "Test Title", tasks, context="Some context", created="2024-01-01T00:00:00Z"
    )
    assert "# Test Title" in content
    assert "**Progress**: 1/2 complete" in content
    assert "**State**: IN_PROGRESS" in content
    assert "**Created**: 2024-01-01T00:00:00Z" in content
    assert "- [ ] 1. Task A" in content
    assert "- [x] 2. Task B → /out.png" in content
    assert "## Context" in content
    assert "Some context" in content


def test_build_tasks_file_no_context():
    tasks = [{"number": 1, "description": "Only task", "done": False}]
    content = _build_tasks_file("No Context", tasks)
    assert "## Context" not in content


def test_build_tasks_file_complete_state():
    tasks = [{"number": 1, "description": "Done", "done": True}]
    content = _build_tasks_file("Complete", tasks, state="COMPLETE")
    assert "**State**: COMPLETE" in content


# =========================================================================
# _get_tasks_path Tests
# =========================================================================
def test_get_tasks_path_no_brand():
    with patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value=None):
        result = _get_tasks_path()
        assert result is None


def test_get_tasks_path_with_brand(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _get_tasks_path()
        assert result == brand_dir / "TASKS.md"


# =========================================================================
# _impl_create_task_file Tests
# =========================================================================
def test_create_task_file_success(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_create_task_file(
            "Test Tasks", ["Item 1", "Item 2", "Item 3"], "Context here"
        )
        assert "Created task file 'Test Tasks'" in result
        assert "3 tasks" in result
        task_path = brand_dir / "TASKS.md"
        assert task_path.exists()
        content = task_path.read_text()
        assert "# Test Tasks" in content
        assert "- [ ] 1. Item 1" in content
        assert "- [ ] 2. Item 2" in content
        assert "- [ ] 3. Item 3" in content
        assert "Context here" in content


def test_create_task_file_no_brand():
    with patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value=None):
        result = _impl_create_task_file("Test", ["Item"])
        assert "Error: No active brand" in result


def test_create_task_file_stale_gets_archived(tmp_path: Path):
    """Stale task files (>1 hour old or no timestamp) get auto-archived."""
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    # Create stale file with no valid timestamp (will be treated as stale)
    (brand_dir / "TASKS.md").write_text("# Old Task\n\n## Status\n- **State**: IN_PROGRESS\n")
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_create_task_file("New", ["Item"])
        assert "Created task file" in result
        # Verify stale file was archived
        archives = list(brand_dir.glob("TASKS_*.md"))
        assert len(archives) == 1
        assert "ARCHIVED_STALE" in archives[0].read_text()


def test_create_task_file_recent_with_pending(tmp_path: Path):
    """Recent task files with pending tasks return helpful message."""
    from datetime import datetime, timezone

    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    # Create recent file with pending tasks
    now = datetime.now(timezone.utc).isoformat()
    content = (
        f"# Active Task\n\n## Status\n- **Progress**: 0/2 complete\n"
        f"- **State**: IN_PROGRESS\n- **Created**: {now}\n\n"
        "## Tasks\n- [ ] 1. Task A\n- [ ] 2. Task B\n"
    )
    (brand_dir / "TASKS.md").write_text(content)
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_create_task_file("New", ["Item"])
        assert "Active task file exists" in result
        assert "2 pending tasks" in result
        assert "get_remaining_tasks()" in result


# =========================================================================
# _impl_get_remaining_tasks Tests
# =========================================================================
def test_get_remaining_tasks_all_pending(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [
        {"number": 1, "description": "A", "done": False},
        {"number": 2, "description": "B", "done": False},
    ]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_get_remaining_tasks()
        assert "Remaining: 2/2" in result
        assert "- [ ] 1. A" in result
        assert "- [ ] 2. B" in result


def test_get_remaining_tasks_some_done(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [
        {"number": 1, "description": "Done", "done": True},
        {"number": 2, "description": "Pending", "done": False},
    ]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_get_remaining_tasks()
        assert "Remaining: 1/2" in result
        assert "- [ ] 2. Pending" in result
        assert "Done" not in result


def test_get_remaining_tasks_all_complete(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [
        {"number": 1, "description": "A", "done": True},
        {"number": 2, "description": "B", "done": True},
    ]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_get_remaining_tasks()
        assert "All 2 tasks complete" in result
        assert "complete_task_file" in result


def test_get_remaining_tasks_no_file(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_get_remaining_tasks()
        assert "No active task file" in result


def test_get_remaining_tasks_no_brand():
    with patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value=None):
        result = _impl_get_remaining_tasks()
        assert "Error: No active brand" in result


# =========================================================================
# _impl_update_task Tests
# =========================================================================
def test_update_task_mark_done(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [{"number": 1, "description": "Task A", "done": False}]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_update_task(1, done=True)
        assert "Task 1 marked as done" in result
        content = (brand_dir / "TASKS.md").read_text()
        assert "- [x] 1. Task A" in content


def test_update_task_with_output(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [{"number": 1, "description": "Generate image", "done": False}]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_update_task(1, done=True, output_path="/images/out.png")
        assert "Task 1 marked as done" in result
        content = (brand_dir / "TASKS.md").read_text()
        assert "- [x] 1. Generate image → /images/out.png" in content


def test_update_task_mark_pending(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [{"number": 1, "description": "Task", "done": True}]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_update_task(1, done=False)
        assert "Task 1 marked as pending" in result
        content = (brand_dir / "TASKS.md").read_text()
        assert "- [ ] 1. Task" in content


def test_update_task_not_found(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [{"number": 1, "description": "Task", "done": False}]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_update_task(99, done=True)
        assert "Error: Task 99 not found" in result


def test_update_task_no_file(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_update_task(1, done=True)
        assert "Error: No active task file" in result


def test_update_task_no_brand():
    with patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value=None):
        result = _impl_update_task(1, done=True)
        assert "Error: No active brand" in result


# =========================================================================
# _impl_complete_task_file Tests
# =========================================================================
def test_complete_task_file_success(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [
        {"number": 1, "description": "A", "done": True},
        {"number": 2, "description": "B", "done": True},
    ]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_complete_task_file("Great work!")
        assert "2/2 tasks finished" in result
        assert "Great work!" in result
        assert "Archived to TASKS_" in result
        # Original file should be gone
        assert not (brand_dir / "TASKS.md").exists()
        # Archive file should exist
        archive_files = list(brand_dir.glob("TASKS_*.md"))
        assert len(archive_files) == 1
        content = archive_files[0].read_text()
        assert "**State**: COMPLETE" in content


def test_complete_task_file_partial(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    tasks = [
        {"number": 1, "description": "A", "done": True},
        {"number": 2, "description": "B", "done": False},
    ]
    (brand_dir / "TASKS.md").write_text(_build_tasks_file("Test", tasks))
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_complete_task_file()
        assert "1/2 tasks finished" in result


def test_complete_task_file_no_file(tmp_path: Path):
    brand_dir = tmp_path / "test-brand"
    brand_dir.mkdir()
    with (
        patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value="test-brand"),
        patch("sip_studio.advisor.tools.task_tools.get_brand_dir", return_value=brand_dir),
    ):
        result = _impl_complete_task_file()
        assert "No active task file" in result


def test_complete_task_file_no_brand():
    with patch("sip_studio.advisor.tools.task_tools.get_active_brand", return_value=None):
        result = _impl_complete_task_file()
        assert "Error: No active brand" in result
