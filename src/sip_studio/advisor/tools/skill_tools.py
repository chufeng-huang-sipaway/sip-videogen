"""Skill activation tools for progressive disclosure architecture.
This module provides tools for on-demand skill loading and workflow tracking.
Skills are loaded lazily to reduce context pollution.
Uses contextvars for thread-safe per-session state access.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field

from agents import function_tool

from sip_studio.advisor.skills.registry import get_skills_registry
from sip_studio.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SkillWorkflowState:
    """Tracks skill activation and workflow compliance per turn."""

    activated_skills: list[str] = field(default_factory=list)
    composition_brief_produced: bool = False
    prompt_crafted: bool = False


# Thread-safe per-turn state using contextvars (NOT module globals)
_workflow_state_var: ContextVar[SkillWorkflowState | None] = ContextVar(
    "skill_workflow_state", default=None
)


def get_workflow_state() -> SkillWorkflowState:
    """Get current workflow state (creates new if none)."""
    state = _workflow_state_var.get()
    if state is None:
        state = SkillWorkflowState()
        _workflow_state_var.set(state)
    return state


def reset_workflow_state() -> None:
    """Reset workflow state for new turn."""
    _workflow_state_var.set(SkillWorkflowState())
    logger.info("[SKILL_WORKFLOW] State reset for new turn")


def mark_skill_activated(skill_name: str) -> None:
    """Mark a skill as activated."""
    state = get_workflow_state()
    if skill_name not in state.activated_skills:
        state.activated_skills.append(skill_name)
        logger.info("[SKILL_WORKFLOW] Activated: %s", skill_name)


def mark_composition_brief_produced() -> None:
    """Mark that a composition brief has been produced."""
    state = get_workflow_state()
    state.composition_brief_produced = True
    logger.info("[SKILL_WORKFLOW] Composition brief produced")


def mark_prompt_crafted() -> None:
    """Mark that a prompt has been crafted."""
    state = get_workflow_state()
    state.prompt_crafted = True
    logger.info("[SKILL_WORKFLOW] Prompt crafted")


def check_image_workflow_compliance() -> tuple[bool, str]:
    """Check if workflow requirements are met for generate_image.
    Validates both image-composer and image-prompt-engineering were activated.
    Returns:
        Tuple of (is_compliant, error_message)
    """
    state = get_workflow_state()
    required = ["image-composer", "image-prompt-engineering"]
    missing = [s for s in required if s not in state.activated_skills]
    if missing:
        return False, (
            f"Workflow violation: Missing skill activation: {missing}\n\n"
            "Required workflow:\n"
            "1. activate_skill('image-composer') -> read composition guidelines\n"
            "2. Produce a structured visual brief\n"
            "3. activate_skill('image-prompt-engineering') -> read prompt guidelines\n"
            "4. Craft your prompt following the 5-point formula\n"
            "5. Call generate_image with your crafted prompt"
        )
    return True, ""


def _impl_activate_skill(skill_name: str) -> str:
    """Implementation of activate_skill tool."""
    registry = get_skills_registry()
    skill = registry.get(skill_name)
    if skill is None:
        available = [s.name for s in registry.skills.values()]
        return f"Error: Skill '{skill_name}' not found. Available: {available}"
    mark_skill_activated(skill_name)
    logger.info(
        "[SKILL_ACTIVATE] Loading full instructions for: %s (%d chars)",
        skill_name,
        len(skill.instructions),
    )
    return f"## {skill.name} - Full Instructions\n\n{skill.instructions}"


@function_tool
def activate_skill(skill_name: str) -> str:
    """Load full instructions for a skill on-demand.
    Call this to get detailed guidelines before performing skill-specific tasks.
    For image generation, you MUST activate both skills in order:
    1. activate_skill("image-composer") - Design your visual brief
    2. activate_skill("image-prompt-engineering") - Craft your prompt
    Args:
        skill_name: Name of the skill to activate (e.g., "image-composer")
    Returns:
        Full skill instructions to follow.
    """
    return _impl_activate_skill(skill_name)


@function_tool
def mark_brief_complete() -> str:
    """Mark that you have completed your visual composition brief.
    Call this AFTER producing your structured visual brief and BEFORE crafting the final prompt.
    Returns:
        Confirmation message.
    """
    mark_composition_brief_produced()
    return "Visual brief marked complete. Now activate 'image-prompt-engineering' to craft your prompt."


def get_workflow_summary() -> str:
    """Get current workflow state summary for debugging."""
    state = get_workflow_state()
    return (
        f"Activated skills: {state.activated_skills}\n"
        f"Brief produced: {state.composition_brief_produced}\n"
        f"Prompt crafted: {state.prompt_crafted}"
    )
