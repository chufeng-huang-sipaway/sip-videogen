"""Skills registry for loading and managing SKILL.md files.

Skills are markdown files with YAML frontmatter that provide specialized
instructions for specific tasks. The registry loads skill metadata for
the system prompt and full instructions on demand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from sip_videogen.config.logging import get_logger

logger = get_logger(__name__)

# Default skills directory (bundled with package)
SKILLS_DIR = Path(__file__).parent


@dataclass
class Skill:
    """A loaded skill with metadata and instructions."""

    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    tools_required: List[str] = field(default_factory=list)
    instructions: str = ""
    path: Path | None = None

    @classmethod
    def from_file(cls, path: Path) -> "Skill":
        """Load a skill from a SKILL.md file.

        Args:
            path: Path to the SKILL.md file.

        Returns:
            Loaded Skill instance.

        Raises:
            ValueError: If the file format is invalid.
        """
        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError(f"Invalid SKILL.md format (missing frontmatter): {path}")

        frontmatter_str = frontmatter_match.group(1)
        instructions = content[frontmatter_match.end() :].strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {path}: {e}") from e

        if not isinstance(frontmatter, dict):
            raise ValueError(f"Frontmatter must be a dictionary in {path}")

        return cls(
            name=frontmatter.get("name", path.parent.name),
            description=frontmatter.get("description", ""),
            triggers=frontmatter.get("triggers", []),
            tools_required=frontmatter.get("tools_required", []),
            instructions=instructions,
            path=path,
        )

    def format_summary(self) -> str:
        """Format skill as a short summary for the system prompt.

        Returns:
            One-line skill summary with name and description.
        """
        triggers_str = ", ".join(self.triggers[:3]) if self.triggers else ""
        if triggers_str:
            return f"- **{self.name}**: {self.description} (triggers: {triggers_str})"
        return f"- **{self.name}**: {self.description}"


class SkillsRegistry:
    """Registry that loads and manages available skills."""

    def __init__(self, skills_dir: Path | None = None):
        """Initialize the registry.

        Args:
            skills_dir: Directory containing skill folders. Defaults to bundled skills.
        """
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: dict[str, Skill] = {}
        self._loaded = False

    def load(self) -> None:
        """Load all skills from the skills directory."""
        if self._loaded:
            return

        if not self.skills_dir.is_dir():
            logger.warning("Skills directory not found: %s", self.skills_dir)
            self._loaded = True
            return

        for skill_folder in self.skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue

            skill_file = skill_folder / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                skill = Skill.from_file(skill_file)
                self._skills[skill.name] = skill
                logger.debug("Loaded skill: %s", skill.name)
            except ValueError as e:
                logger.warning("Failed to load skill from %s: %s", skill_file, e)

        self._loaded = True
        logger.info("Loaded %d skills from %s", len(self._skills), self.skills_dir)

    @property
    def skills(self) -> dict[str, Skill]:
        """Get all loaded skills."""
        self.load()
        return self._skills

    def get(self, name: str) -> Skill | None:
        """Get a skill by name.

        Args:
            name: Skill name.

        Returns:
            Skill instance or None if not found.
        """
        self.load()
        return self._skills.get(name)

    def format_for_prompt(self) -> str:
        """Format all skills as a summary for the system prompt.

        Returns:
            Markdown list of available skills.
        """
        self.load()

        if not self._skills:
            return "No skills available."

        lines = ["## Available Skills", ""]
        lines.append(
            "You have access to the following specialized skills. "
            "When a user request matches a skill's domain, load and follow "
            "its instructions for best results."
        )
        lines.append("")

        for skill in sorted(self._skills.values(), key=lambda s: s.name):
            lines.append(skill.format_summary())

        lines.append("")
        lines.append(
            "To use a skill, internally reference its instructions when "
            "handling relevant tasks. Skills provide domain-specific guidelines, "
            "prompt templates, and quality checks."
        )

        return "\n".join(lines)

    def find_relevant_skills(self, user_message: str) -> List[Skill]:
        """Find skills that might be relevant to a user message.

        This is a simple keyword-based match. The LLM ultimately decides
        which skills to apply.

        Args:
            user_message: The user's message text.

        Returns:
            List of potentially relevant skills.
        """
        self.load()
        message_lower = user_message.lower()
        relevant = []

        for skill in self._skills.values():
            # Check if any triggers match
            for trigger in skill.triggers:
                if trigger.lower() in message_lower:
                    relevant.append(skill)
                    break

        return relevant


# Global registry instance
_registry: SkillsRegistry | None = None


def get_skills_registry() -> SkillsRegistry:
    """Get the global skills registry instance."""
    global _registry
    if _registry is None:
        _registry = SkillsRegistry()
    return _registry
