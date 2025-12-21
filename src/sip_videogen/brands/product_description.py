"""Helpers for storing product attributes inside the description text."""

from __future__ import annotations

from sip_videogen.brands.models import ProductAttribute

_ATTRIBUTES_HEADER = "Attributes:"


def _is_attributes_header(line: str) -> bool:
    return line.strip().lower() == _ATTRIBUTES_HEADER.lower()


def _find_attributes_block(lines: list[str]) -> int | None:
    """Find the start index of a trailing Attributes block, if present."""
    for idx, line in enumerate(lines):
        if not _is_attributes_header(line):
            continue

        tail = lines[idx + 1 :]
        if all(not tail_line.strip() or tail_line.lstrip().startswith("-") for tail_line in tail):
            return idx
    return None


def has_attributes_block(description: str) -> bool:
    """Return True if the description contains a trailing Attributes block."""
    if not description:
        return False
    return _find_attributes_block(description.splitlines()) is not None


def format_attributes_block(attributes: list[ProductAttribute]) -> str:
    """Format attributes into a human-editable block appended to descriptions."""
    lines: list[str] = []
    for attr in attributes:
        key = attr.key.strip()
        value = attr.value.strip()
        if not key or not value:
            continue

        category = (attr.category or "").strip()
        if category and category.lower() != "general":
            lines.append(f"- [{category}] {key}: {value}")
        else:
            lines.append(f"- {key}: {value}")

    if not lines:
        return ""

    return "\n".join([_ATTRIBUTES_HEADER, *lines])


def extract_attributes_from_description(description: str) -> tuple[str, list[ProductAttribute]]:
    """Extract attributes from a trailing Attributes block in a description."""
    if not description:
        return "", []

    lines = description.splitlines()
    header_idx = _find_attributes_block(lines)
    if header_idx is None:
        return description.strip(), []

    base_description = "\n".join(lines[:header_idx]).rstrip()
    attributes: list[ProductAttribute] = []

    for line in lines[header_idx + 1 :]:
        trimmed = line.strip()
        if not trimmed or not trimmed.startswith("-"):
            continue

        content = trimmed[1:].strip()
        category = "general"
        if content.startswith("["):
            closing = content.find("]")
            if closing != -1:
                category = content[1:closing].strip() or "general"
                content = content[closing + 1 :].strip()

        if ":" not in content:
            continue

        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue

        attributes.append(ProductAttribute(key=key, value=value, category=category))

    return base_description, attributes


def merge_attributes_into_description(description: str, attributes: list[ProductAttribute]) -> str:
    """Ensure description ends with a formatted Attributes block (or none)."""
    base_description, _ = extract_attributes_from_description(description or "")
    block = format_attributes_block(attributes)
    if not block:
        return base_description

    if base_description:
        return f"{base_description.rstrip()}\n\n{block}"
    return block
