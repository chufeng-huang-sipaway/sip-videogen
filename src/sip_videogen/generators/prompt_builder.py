"""Shared helpers for building structured video generation prompts.

These utilities format prompts in a compact stack:
- Global style anchors (tone + visual style)
- Entity cards for the elements in the scene
- Per-shot micro prompts with camera, action, setting, and continuity notes

The goal is to keep prompts concise while preserving the key anchors that
models tend to drop when text is unstructured or overly long.
"""

from __future__ import annotations

import re
from typing import Iterable

from sip_videogen.models.script import ElementType, SceneAction, SharedElement, VideoScript

DEFAULT_MAX_PROMPT_CHARS = 2500


def _compact_text(text: str, max_phrases: int = 2, max_words: int = 12) -> str:
    """Condense freeform text into a few short phrases."""
    if not text:
        return ""

    clean = re.sub(r"\s+", " ", text.strip())
    if not clean:
        return ""

    # Split on common separators to find the most informative fragments
    fragments = re.split(r"[.;,\n]+", clean)
    phrases: list[str] = []

    for fragment in fragments:
        frag = fragment.strip()
        if not frag:
            continue
        words = frag.split()
        phrases.append(" ".join(words[:max_words]))
        if len(phrases) >= max_phrases:
            break

    if not phrases:
        return " ".join(clean.split()[:max_words])

    return "; ".join(phrases)


def _summarize_element(element: SharedElement, max_words: int = 12) -> str:
    """Build a concise one-line element card."""
    name = element.role_descriptor or element.name
    summary = _compact_text(element.visual_description, max_phrases=2, max_words=max_words)
    return f"{name}: {summary}" if summary else name


def _get_scene_elements(
    scene: SceneAction, script: VideoScript | None, max_elements: int = 5
) -> list[str]:
    """Return concise element cards for the scene."""
    if not script:
        return []

    elements: list[str] = []
    for element_id in scene.shared_element_ids:
        element = script.get_element_by_id(element_id)
        if not element:
            continue
        elements.append(_summarize_element(element))
        if len(elements) >= max_elements:
            break

    return elements


def _select_key_roles(
    scene: SceneAction, script: VideoScript | None, max_roles: int = 3
) -> list[str]:
    """Pick the most important role descriptors for per-shot anchors."""
    if not script:
        return []

    roles: list[str] = []
    # Prioritize characters and props, then environments
    for element_id in scene.shared_element_ids:
        element = script.get_element_by_id(element_id)
        if not element:
            continue
        if element.element_type in (ElementType.CHARACTER, ElementType.PROP):
            role = element.role_descriptor or element.name
            if role:
                roles.append(role)
        if len(roles) >= max_roles:
            break

    if len(roles) < max_roles:
        for element_id in scene.shared_element_ids:
            element = script.get_element_by_id(element_id)
            if not element:
                continue
            if element.element_type == ElementType.ENVIRONMENT:
                role = element.role_descriptor or element.name
                if role:
                    roles.append(role)
            if len(roles) >= max_roles:
                break

    return roles[:max_roles]


def _format_time(second: int) -> str:
    """Format seconds into MM:SS for timestamp prompts."""
    return f"00:{second:02d}"


def _build_shot_lines(
    scene: SceneAction,
    setting_anchor: str,
    roles: list[str],
    atmosphere: str,
) -> list[str]:
    """Create per-shot micro prompts."""
    lines: list[str] = []
    key_elements = ", ".join(roles) if roles else ""
    shared_tail = f"Setting: {setting_anchor}" if setting_anchor else ""
    if atmosphere:
        shared_tail = f"{shared_tail}; Atmosphere: {atmosphere}" if shared_tail else f"Atmosphere: {atmosphere}"
    if key_elements:
        shared_tail = f"{shared_tail}; Key elements: {key_elements}" if shared_tail else f"Key elements: {key_elements}"

    if scene.sub_shots:
        for sub_shot in scene.sub_shots:
            duration = sub_shot.end_second - sub_shot.start_second
            start_time = _format_time(sub_shot.start_second)
            end_time = _format_time(sub_shot.end_second)

            parts: list[str] = [
                f"[{start_time}-{end_time}] {duration}s {sub_shot.camera_direction}".strip()
            ]

            if sub_shot.action_description:
                parts.append(f"Action: {sub_shot.action_description}")
            if sub_shot.dialogue:
                dialogue_clean = sub_shot.dialogue.strip().strip('"').strip("'")
                if dialogue_clean:
                    parts.append(f'Dialogue: "{dialogue_clean}"')
            if shared_tail:
                parts.append(shared_tail)

            # Continuity note to avoid dead air
            parts.append("Flow: keep motion continuous, no pauses")

            lines.append("; ".join(parts))
    else:
        duration = scene.duration_seconds
        start_time = _format_time(0)
        end_time = _format_time(duration)
        camera = scene.camera_direction or "Shot"
        parts = [f"[{start_time}-{end_time}] {duration}s {camera}".strip()]
        if scene.action_description:
            parts.append(f"Action: {scene.action_description}")
        if scene.dialogue:
            dialogue_clean = scene.dialogue.strip().strip('"').strip("'")
            if dialogue_clean:
                parts.append(f'Dialogue: "{dialogue_clean}"')
        if shared_tail:
            parts.append(shared_tail)
        parts.append("Flow: keep motion continuous, no pauses")
        lines.append("; ".join(parts))

    return lines


def build_structured_scene_prompt(
    scene: SceneAction,
    script: VideoScript | None = None,
    flow_context: str | None = None,
    reference_context: str | None = None,
    audio_instruction: str | None = None,
    max_length: int | None = None,
) -> str:
    """Build a structured prompt string for a scene."""
    sections: list[str] = []

    # Global style anchors
    style_parts: list[str] = []
    if script and script.tone:
        style_parts.append(f"Tone: {_compact_text(script.tone, max_phrases=1, max_words=8)}")
    if script and script.visual_style:
        style_parts.append(f"Visual style: {_compact_text(script.visual_style, max_phrases=2, max_words=14)}")
    if style_parts:
        sections.append(" | ".join(style_parts))

    if reference_context:
        sections.append(reference_context)

    setting_anchor = _compact_text(scene.setting_description, max_phrases=2, max_words=18)
    if setting_anchor:
        sections.append(f"Setting: {setting_anchor}")

    # Entity cards (keep concise)
    element_cards = _get_scene_elements(scene, script)
    if element_cards:
        sections.append("Elements: " + " | ".join(element_cards))

    if flow_context:
        sections.append(f"Continuity: {flow_context}")

    roles = _select_key_roles(scene, script)
    atmosphere = _compact_text(scene.visual_notes, max_phrases=1, max_words=14)
    shot_lines = _build_shot_lines(scene, setting_anchor, roles, atmosphere)
    if shot_lines:
        sections.append("Shots:\n" + "\n".join(shot_lines))

    if audio_instruction:
        sections.append(audio_instruction)

    prompt = "\n".join(sections)

    if max_length and len(prompt) > max_length:
        prompt = prompt[: max_length - 3] + "..."

    return prompt
