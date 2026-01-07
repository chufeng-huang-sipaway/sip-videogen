"""File system tools for brand directory operations."""

from __future__ import annotations

from pathlib import Path

from agents import function_tool

from sip_studio.config.constants import Limits
from sip_studio.config.logging import get_logger
from sip_studio.utils.file_utils import write_atomically

from . import _common

logger = get_logger(__name__)


def _resolve_brand_path(relative_path: str) -> Path | None:
    """Resolve a relative path within the active brand directory."""
    brand_slug = _common.get_active_brand()
    if not brand_slug:
        return None
    brand_dir = _common.get_brand_dir(brand_slug)
    resolved = brand_dir / relative_path
    try:
        resolved.resolve().relative_to(brand_dir.resolve())
    except ValueError:
        logger.warning(f"Path escapes brand directory: {relative_path}")
        return None
    return resolved


def _impl_read_file(path: str, chunk: int = 0, chunk_size: int = 2000) -> str:
    """Implementation of read_file tool with chunking support."""
    if chunk < 0:
        return f"Error: chunk must be >= 0, got {chunk}"
    if chunk_size < Limits.CHUNK_SIZE_FILE_MIN:
        chunk_size = Limits.CHUNK_SIZE_FILE_MIN
    if chunk_size > Limits.CHUNK_SIZE_FILE_MAX:
        chunk_size = Limits.CHUNK_SIZE_FILE_MAX
    resolved = _resolve_brand_path(path)
    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."
    if not resolved.exists():
        return f"Error: File not found: {path}"
    if not resolved.is_file():
        return f"Error: {path} is a directory, not a file. Use list_files() to browse."
    text_extensions = {".json", ".md", ".txt", ".yaml", ".yml", ".csv"}
    if resolved.suffix.lower() in text_extensions:
        try:
            content = resolved.read_text(encoding="utf-8")
            if len(content) <= chunk_size:
                return content
            total_chunks = (len(content) + chunk_size - 1) // chunk_size
            if chunk >= total_chunks:
                return f"Error: chunk {chunk} does not exist. File has {total_chunks} chunks (0-{total_chunks - 1})."
            start = chunk * chunk_size
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]
            total_len = len(content)
            header = (
                f"[Chunk {chunk + 1}/{total_chunks}] (chars {start + 1}-{end} of {total_len})\n\n"
            )
            footer = ""
            if chunk < total_chunks - 1:
                footer = f'\n\n---\nUse read_file("{path}", chunk={chunk + 1}) for next chunk.'
            return header + chunk_content + footer
        except Exception as e:
            return f"Error reading file: {e}"
    else:
        size = resolved.stat().st_size
        return f"Binary file exists: {path} ({size} bytes)"


def _impl_write_file(path: str, content: str) -> str:
    """Implementation of write_file tool."""
    resolved = _resolve_brand_path(path)
    if resolved is None:
        return "Error: No active brand selected. Use load_brand() first."
    try:
        write_atomically(resolved, content)
        logger.info(f"Wrote file: {resolved}")
        return f"Successfully wrote to: {path}"
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return f"Error writing file: {e}"


def _impl_list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """Implementation of list_files tool with pagination support."""
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0
    resolved = _resolve_brand_path(path) if path else None
    if resolved is None and path:
        return "Error: No active brand selected. Use load_brand() first."
    if resolved is None:
        brand_slug = _common.get_active_brand()
        if not brand_slug:
            return "Error: No active brand selected. Use load_brand() first."
        resolved = _common.get_brand_dir(brand_slug)
    if not resolved.exists():
        return f"Error: Directory not found: {path or '/'}"
    if not resolved.is_dir():
        return f"Error: {path} is a file, not a directory. Use read_file() to read it."
    try:
        items = sorted(resolved.iterdir())
        total_count = len(items)
        if offset >= total_count and total_count > 0:
            return f"Error: offset {offset} is past end of directory ({total_count} items). Use offset 0-{total_count - 1}."
        paginated_items = items[offset : offset + limit]
        lines = []
        for item in paginated_items:
            if item.is_dir():
                count = len(list(item.iterdir()))
                lines.append(f"  {item.name}/ ({count} items)")
            else:
                size = item.stat().st_size
                lines.append(f"  {item.name} ({size} bytes)")
        if not lines and total_count == 0:
            return f"Directory is empty: {path or '/'}"
        start_idx = offset + 1
        end_idx = min(offset + limit, total_count)
        display_path = path or "/"
        if total_count <= limit and offset == 0:
            header = f"Contents of {display_path}:\n"
        else:
            header = (
                f"Contents of {display_path} (showing {start_idx}-{end_idx} of {total_count}):\n"
            )
        result = header + "\n".join(lines)
        if offset + limit < total_count:
            next_offset = offset + limit
            if path:
                hint = f'\n\nUse list_files("{path}", offset={next_offset}) to see more.'
            else:
                hint = f"\n\nUse list_files(offset={next_offset}) to see more."
            result += hint
        return result
    except Exception as e:
        logger.error(f"Failed to list directory: {e}")
        return f"Error listing directory: {e}"


@function_tool
def read_file(path: str, chunk: int = 0, chunk_size: int = 2000) -> str:
    """Read a file from the brand directory.
    Args:
        path: Relative path within the brand directory.
        chunk: Chunk number to read (0-indexed, default 0).
        chunk_size: Characters per chunk (100-10000, default 2000).
    Returns:
        File contents as string (for text files), or confirmation for binary files.
    """
    return _impl_read_file(path, chunk, chunk_size)


@function_tool
def write_file(path: str, content: str) -> str:
    """Write content to a file in the brand directory.
    Args:
        path: Relative path within the brand directory.
        content: Content to write.
    Returns:
        Confirmation message or error.
    """
    return _impl_write_file(path, content)


@function_tool
def list_files(path: str = "", limit: int = 20, offset: int = 0) -> str:
    """List files and directories in the brand directory.
    Args:
        path: Relative path within brand directory. Empty string for root.
        limit: Maximum number of items to return (1-100, default 20).
        offset: Number of items to skip for pagination (default 0).
    Returns:
        Formatted list of files and directories with pagination info.
    """
    return _impl_list_files(path, limit, offset)
