"""File-based task list management for multi-step task execution.
Replaces in-memory todo state with persistent TASKS.md file as ground truth.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from agents import function_tool

from sip_studio.config.logging import get_logger
from sip_studio.utils.file_utils import write_atomically

from ._common import get_active_brand, get_brand_dir
from .todo_tools import get_tool_state

logger = get_logger(__name__)
TASKS_FILENAME = "TASKS.md"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _output_type_for_path(path: str) -> str:
    """Best-effort guess for output media type (used by UI)."""
    try:
        ext = Path(path).suffix.lower()
        return "image" if ext in _IMAGE_EXTS else "file"
    except Exception:
        return "file"


def _push_todo_list_from_task_data(data: dict) -> None:
    """Push the current TASKS.md state to the UI TodoList (best-effort).

    Frontend clears TodoList at the start of every send. If we only emit incremental
    updates (TodoUpdate), the UI may never re-hydrate the list. This method ensures
    the full list is re-sent whenever we read/update TASKS.md.
    """
    state = get_tool_state()
    if not state:
        return
    try:
        from sip_studio.studio.state import TodoItem, TodoList

        tasks = data.get("tasks", []) or []
        todo_items: list[TodoItem] = []
        for t in tasks:
            num = int(t.get("number", 0) or 0)
            desc = str(t.get("description", "") or "")
            done = bool(t.get("done", False))
            output = t.get("output")
            outputs = (
                [{"path": output, "type": _output_type_for_path(str(output))}] if output else []
            )
            todo_items.append(
                TodoItem(
                    id=f"task-{num}",
                    description=desc,
                    status="done" if done else "pending",
                    outputs=outputs,
                )
            )
        todo = TodoList(
            id="file-tasks",
            title=str(data.get("title") or "Tasks"),
            items=todo_items,
            created_at=str(data.get("created") or datetime.now(timezone.utc).isoformat()),
        )
        state.set_todo_list(todo)
    except Exception as e:
        logger.debug(f"[TASK_TOOLS] Failed to push todo list from TASKS.md: {e}")


def _get_tasks_path() -> Path | None:
    """Get path to TASKS.md in active brand directory."""
    slug = get_active_brand()
    if not slug:
        return None
    return get_brand_dir(slug) / TASKS_FILENAME


def _parse_tasks_file(content: str) -> dict:
    """Parse TASKS.md content into structured data."""
    result: dict = {
        "title": "",
        "state": "",
        "progress": 0,
        "total": 0,
        "created": "",
        "tasks": [],
        "context": "",
    }
    tasks_list: list[dict] = result["tasks"]  # type hint for mypy
    if not content.strip():
        return result
    lines = content.split("\n")
    in_tasks = False
    in_context = False
    for line in lines:
        if line.startswith("# "):
            result["title"] = line[2:].strip()
        elif "**Progress**:" in line:
            m = re.search(r"(\d+)/(\d+)", line)
            if m:
                result["progress"] = int(m.group(1))
                result["total"] = int(m.group(2))
        elif "**State**:" in line:
            result["state"] = line.split(":")[-1].strip()
        elif "**Created**:" in line:
            result["created"] = line.split("**Created**:")[-1].strip()
        elif line.strip() == "## Tasks":
            in_tasks = True
            in_context = False
        elif line.strip() == "## Context":
            in_tasks = False
            in_context = True
        elif in_tasks and line.strip().startswith("- ["):
            m = re.match(r"- \[(.)\] (\d+)\. (.+)", line.strip())
            if m:
                status_char, num, rest = m.groups()
                done = status_char == "x"
                parts = rest.split(" → ")
                desc = parts[0].strip()
                output = parts[1].strip() if len(parts) > 1 else None
                tasks_list.append(
                    {"number": int(num), "description": desc, "done": done, "output": output}
                )
        elif in_context and line.strip():
            result["context"] = str(result["context"]) + line + "\n"
    result["total"] = len(tasks_list)
    return result


def _build_tasks_file(
    title: str,
    tasks: list[dict],
    context: str | None = None,
    state: str = "IN_PROGRESS",
    created: str | None = None,
) -> str:
    """Generate TASKS.md content from structured data."""
    done_count = sum(1 for t in tasks if t.get("done"))
    total = len(tasks)
    created = created or datetime.now(timezone.utc).isoformat()
    lines = [
        f"# {title}",
        "",
        "## Status",
        f"- **Progress**: {done_count}/{total} complete",
        f"- **State**: {state}",
        f"- **Created**: {created}",
        "",
        "## Tasks",
    ]
    for t in tasks:
        num = t.get("number", 0)
        desc = t.get("description", "")
        done = t.get("done", False)
        output = t.get("output")
        char = "x" if done else " "
        line = f"- [{char}] {num}. {desc}"
        if output:
            line += f" → {output}"
        lines.append(line)
    if context:
        lines.extend(["", "## Context", context.strip()])
    return "\n".join(lines)


STALE_THRESHOLD_HOURS = 1


def _is_stale_task_file(path: Path, data: dict) -> bool:
    """Check if task file is stale (older than threshold or state is COMPLETE)."""
    if data.get("state") == "COMPLETE":
        return True
    created_str = data.get("created", "")
    if not created_str:
        return True
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        return age_hours > STALE_THRESHOLD_HOURS
    except Exception:
        return True


def _auto_archive_stale_file(path: Path, data: dict) -> str:
    """Archive a stale task file and return archive path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = path.parent / f"TASKS_{ts}.md"
    content = _build_tasks_file(
        data.get("title", "Untitled"),
        data.get("tasks", []),
        data.get("context"),
        "ARCHIVED_STALE",
        data.get("created"),
    )
    write_atomically(archive_path, content)
    path.unlink()
    return str(archive_path)


def _impl_archive_existing_tasks() -> str | None:
    """Archive any existing TASKS.md file at start of new chat turn.
    Called by ChatService to ensure each conversation starts fresh.
    Returns archive path if archived, None if no file existed."""
    path = _get_tasks_path()
    if not path or not path.exists():
        return None
    try:
        content = path.read_text()
        data = _parse_tasks_file(content)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_path = path.parent / f"TASKS_{ts}.md"
        archive_content = _build_tasks_file(
            data.get("title", "Untitled"),
            data.get("tasks", []),
            data.get("context"),
            "ARCHIVED_NEW_TURN",
            data.get("created"),
        )
        write_atomically(archive_path, archive_content)
        path.unlink()
        logger.info(f"[TASK_TOOLS] 🗄️ Archived previous task file: {archive_path}")
        # Clear todo list state in UI
        state = get_tool_state()
        if state:
            state.clear_todo_list()
        return str(archive_path)
    except Exception as e:
        logger.warning(f"[TASK_TOOLS] Failed to archive existing tasks: {e}")
        return None


def _impl_create_task_file(title: str, items: list[str], context: str | None = None) -> str:
    """Implementation of create_task_file for testing."""
    logger.info(f"[TASK_TOOLS] create_task_file called: title='{title}', items={len(items)}")
    path = _get_tasks_path()
    if not path:
        logger.warning("[TASK_TOOLS] create_task_file: No active brand selected")
        return "Error: No active brand selected"
    # Handle existing file: auto-archive if stale, else guide to use get_remaining_tasks
    if path.exists():
        try:
            existing_content = path.read_text()
            existing_data = _parse_tasks_file(existing_content)
            if _is_stale_task_file(path, existing_data):
                archive_path = _auto_archive_stale_file(path, existing_data)
                logger.info(f"[TASK_TOOLS] 🗄️ Auto-archived stale task file to: {archive_path}")
            else:
                # Active task file exists - check remaining tasks
                pending = [t for t in existing_data.get("tasks", []) if not t.get("done")]
                if pending:
                    logger.info(
                        f"[TASK_TOOLS] Active task file exists with {len(pending)} pending tasks"
                    )
                    _push_todo_list_from_task_data(existing_data)
                    return f"Active task file exists with {len(pending)} pending tasks. Call get_remaining_tasks() to see them and continue, or complete_task_file() to finish first."
                else:
                    # All done but not archived - archive it
                    archive_path = _auto_archive_stale_file(path, existing_data)
                    logger.info(
                        f"[TASK_TOOLS] 🗄️ Auto-archived completed task file to: {archive_path}"
                    )
        except Exception as e:
            logger.warning(f"[TASK_TOOLS] Failed to read existing file, overwriting: {e}")
            path.unlink()
    tasks = [
        {"number": i + 1, "description": item, "done": False, "output": None}
        for i, item in enumerate(items)
    ]
    content = _build_tasks_file(title, tasks, context)
    try:
        write_atomically(path, content)
        logger.info(f"[TASK_TOOLS] ✅ Created TASKS.md: {len(items)} tasks at {path}")
        state = get_tool_state()
        if state:
            from sip_studio.studio.state import TodoItem, TodoList

            todo_items = [
                TodoItem(id=f"task-{i+1}", description=item) for i, item in enumerate(items)
            ]
            todo = TodoList(
                id="file-tasks",
                title=title,
                items=todo_items,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            state.set_todo_list(todo)
        return f"Created task file '{title}' with {len(items)} tasks"
    except Exception as e:
        logger.error(f"Failed to create task file: {e}")
        return f"Error creating task file: {e}"


def _impl_get_remaining_tasks() -> str:
    """Implementation of get_remaining_tasks for testing."""
    logger.info("[TASK_TOOLS] get_remaining_tasks called (self-evaluation checkpoint)")
    path = _get_tasks_path()
    if not path:
        logger.warning("[TASK_TOOLS] get_remaining_tasks: No active brand")
        return "Error: No active brand selected"
    if not path.exists():
        logger.warning("[TASK_TOOLS] get_remaining_tasks: No TASKS.md file exists")
        return "No active task file. Use create_task_file() first."
    try:
        content = path.read_text()
        data = _parse_tasks_file(content)
        _push_todo_list_from_task_data(data)
        pending = [t for t in data["tasks"] if not t["done"]]
        done = [t for t in data["tasks"] if t["done"]]
        total = len(data["tasks"])
        logger.info(f"[TASK_TOOLS] 📊 Progress: {len(done)}/{total} done, {len(pending)} remaining")
        if not pending:
            logger.info(f"[TASK_TOOLS] ✅ ALL TASKS COMPLETE ({total}/{total})")
            return f"All {total} tasks complete. Call complete_task_file() to finish."
        lines = [f"Remaining: {len(pending)}/{total}"]
        for t in pending[:10]:
            lines.append(f"- [ ] {t['number']}. {t['description']}")
        if len(pending) > 10:
            lines.append(f"... and {len(pending)-10} more")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"[TASK_TOOLS] Failed to read task file: {e}")
        return f"Error reading task file: {e}"


def _impl_update_task(task_number: int, done: bool = False, output_path: str | None = None) -> str:
    """Implementation of update_task for testing."""
    status_str = "done" if done else "pending"
    logger.info(
        f"[TASK_TOOLS] update_task called: task #{task_number} -> {status_str}, output={output_path}"
    )
    path = _get_tasks_path()
    if not path:
        logger.warning("[TASK_TOOLS] update_task: No active brand")
        return "Error: No active brand selected"
    if not path.exists():
        logger.warning("[TASK_TOOLS] update_task: No TASKS.md file")
        return "Error: No active task file. Use create_task_file() first."
    try:
        content = path.read_text()
        data = _parse_tasks_file(content)
        task = next((t for t in data["tasks"] if t["number"] == task_number), None)
        if not task:
            logger.error(f"[TASK_TOOLS] update_task: Task #{task_number} not found")
            return f"Error: Task {task_number} not found"
        old_status = "done" if task["done"] else "pending"
        task["done"] = done
        if output_path:
            task["output"] = output_path
        new_content = _build_tasks_file(
            data["title"], data["tasks"], data.get("context"), data["state"], data["created"]
        )
        write_atomically(path, new_content)
        logger.info(f"[TASK_TOOLS] ✅ Task #{task_number}: {old_status} -> {status_str}")
        # Re-push full todo list to keep UI hydrated across turns.
        # (TodoUpdate deltas are dropped if frontend cleared its local todoList state.)
        _push_todo_list_from_task_data(data)
        return f"Task {task_number} marked as {status_str}"
    except Exception as e:
        logger.error(f"[TASK_TOOLS] Failed to update task: {e}")
        return f"Error updating task: {e}"


def _impl_complete_task_file(summary: str | None = None) -> str:
    """Implementation of complete_task_file for testing."""
    logger.info(f"[TASK_TOOLS] complete_task_file called, summary={summary}")
    path = _get_tasks_path()
    if not path:
        logger.warning("[TASK_TOOLS] complete_task_file: No active brand")
        return "Error: No active brand selected"
    if not path.exists():
        logger.warning("[TASK_TOOLS] complete_task_file: No TASKS.md file")
        return "No active task file"
    try:
        content = path.read_text()
        data = _parse_tasks_file(content)
        done_count = sum(1 for t in data["tasks"] if t["done"])
        total = len(data["tasks"])
        logger.info(f"[TASK_TOOLS] 📋 Final status: {done_count}/{total} tasks completed")
        new_content = _build_tasks_file(
            data["title"], data["tasks"], data.get("context"), "COMPLETE", data["created"]
        )
        # Archive to TASKS_{timestamp}.md
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_path = path.parent / f"TASKS_{ts}.md"
        write_atomically(archive_path, new_content)
        path.unlink()
        logger.info(f"[TASK_TOOLS] ✅ TASK FILE ARCHIVED: {archive_path}")
        state = get_tool_state()
        if state:
            todo = state.get_todo_list()
            if todo:
                state._push_todo_completed(todo)
        result = (
            f"Task file complete: {done_count}/{total} tasks finished. Archived to TASKS_{ts}.md"
        )
        if summary:
            result += f" {summary}"
        return result
    except Exception as e:
        logger.error(f"[TASK_TOOLS] Failed to complete task file: {e}")
        return f"Error completing task file: {e}"


@function_tool
def create_task_file(title: str, items: list[str], context: str | None = None) -> str:
    """Create TASKS.md file for tracking multi-step tasks.
    Use this when user requests 3+ items (e.g., "generate 10 images").
    Args:
        title: Brief description of the overall task (e.g., "10 Product Images")
        items: List of task descriptions (each becomes a checkbox item)
        context: Optional context string (product info, style notes, etc.)
    Returns:
        Confirmation message with task count
    """
    return _impl_create_task_file(title, items, context)


@function_tool
def get_remaining_tasks() -> str:
    """Read TASKS.md and return pending tasks. CRITICAL for self-evaluation.
    Call this after completing each task to check what's left.
    Continue working until this returns "All tasks complete".
    Returns:
        Count and list of pending tasks, or "All tasks complete (N/N)"
    """
    return _impl_get_remaining_tasks()


@function_tool
def update_task(task_number: int, status: str, output_path: str | None = None) -> str:
    """Update a task's status in TASKS.md.
    Call with 'in_progress' before starting, 'done' after completing.
    Args:
        task_number: The task number (1-indexed)
        status: New status - 'pending', 'in_progress', 'done', 'error'
        output_path: Optional path to generated output (e.g., "generated/hero_001.png")
    Returns:
        Confirmation message
    """
    done = status == "done"
    return _impl_update_task(task_number, done=done, output_path=output_path)


@function_tool
def complete_task_file(summary: str | None = None) -> str:
    """Mark TASKS.md as complete. Call when all tasks are done.
    Args:
        summary: Optional summary of what was accomplished
    Returns:
        Completion message with final counts
    """
    return _impl_complete_task_file(summary)
