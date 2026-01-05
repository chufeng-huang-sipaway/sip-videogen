"""Tests for the skills registry system."""

from pathlib import Path

import pytest

from sip_videogen.advisor.skills.registry import Skill, SkillsRegistry


class TestSkill:
    """Tests for Skill class."""

    def test_from_file_valid(self, tmp_path: Path) -> None:
        """Test loading a valid SKILL.md file."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
name: test-skill
description: A test skill for testing
triggers:
  - test
  - testing
tools_required:
  - tool1
  - tool2
---

# Test Skill

This is the skill instructions content.

## Section

More content here.
"""
        )

        skill = Skill.from_file(skill_file)

        assert skill.name == "test-skill"
        assert skill.description == "A test skill for testing"
        assert skill.triggers == ["test", "testing"]
        assert skill.tools_required == ["tool1", "tool2"]
        assert "# Test Skill" in skill.instructions
        assert "## Section" in skill.instructions
        assert skill.path == skill_file

    def test_from_file_missing_frontmatter(self, tmp_path: Path) -> None:
        """Test that missing frontmatter raises ValueError."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# Just content, no frontmatter")

        with pytest.raises(ValueError, match="missing frontmatter"):
            Skill.from_file(skill_file)

    def test_from_file_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises ValueError."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
name: test
description: [invalid yaml
---

Content
"""
        )

        with pytest.raises(ValueError, match="Invalid YAML"):
            Skill.from_file(skill_file)

    def test_from_file_defaults(self, tmp_path: Path) -> None:
        """Test that missing optional fields get defaults."""
        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            """---
description: Minimal skill
---

# Minimal Skill
"""
        )

        skill = Skill.from_file(skill_file)

        # Name defaults to parent directory name
        assert skill.name == "my_skill"
        assert skill.description == "Minimal skill"
        assert skill.triggers == []
        assert skill.tools_required == []

    def test_format_summary_with_triggers(self) -> None:
        """Test summary formatting with triggers."""
        skill = Skill(
            name="test-skill",
            description="A skill for testing",
            triggers=["trigger1", "trigger2", "trigger3", "trigger4"],
        )

        summary = skill.format_summary()

        assert "**test-skill**" in summary
        assert "A skill for testing" in summary
        # Only first 3 triggers
        assert "trigger1, trigger2, trigger3" in summary
        assert "trigger4" not in summary

    def test_format_summary_without_triggers(self) -> None:
        """Test summary formatting without triggers."""
        skill = Skill(
            name="simple-skill",
            description="No triggers here",
        )

        summary = skill.format_summary()

        assert "**simple-skill**" in summary
        assert "No triggers here" in summary
        assert "triggers:" not in summary


class TestSkillsRegistry:
    """Tests for SkillsRegistry class."""

    def test_load_skills(self, tmp_path: Path) -> None:
        """Test loading skills from a directory."""
        # Create two skill directories
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            """---
name: skill-one
description: First skill
triggers:
  - one
---

# Skill One
"""
        )

        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: skill-two
description: Second skill
triggers:
  - two
---

# Skill Two
"""
        )

        registry = SkillsRegistry(skills_dir=tmp_path)
        registry.load()

        assert len(registry.skills) == 2
        assert "skill-one" in registry.skills
        assert "skill-two" in registry.skills

    def test_load_skips_invalid(self, tmp_path: Path) -> None:
        """Test that invalid skills are skipped during load."""
        # Valid skill
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        (valid_dir / "SKILL.md").write_text(
            """---
name: valid
description: Valid skill
---

Content
"""
        )

        # Invalid skill (no frontmatter)
        invalid_dir = tmp_path / "invalid"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text("No frontmatter here")

        # Directory without SKILL.md
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Regular file (not directory)
        (tmp_path / "not_a_dir.txt").write_text("ignore me")

        registry = SkillsRegistry(skills_dir=tmp_path)
        registry.load()

        assert len(registry.skills) == 1
        assert "valid" in registry.skills

    def test_get_skill(self, tmp_path: Path) -> None:
        """Test getting a skill by name."""
        skill_dir = tmp_path / "test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: Test
---

Content
"""
        )

        registry = SkillsRegistry(skills_dir=tmp_path)

        skill = registry.get("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"

        missing = registry.get("nonexistent")
        assert missing is None

    def test_format_for_prompt(self, tmp_path: Path) -> None:
        """Test formatting skills for system prompt."""
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            """---
name: alpha-skill
description: First skill
triggers:
  - alpha
---

Content
"""
        )

        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: beta-skill
description: Second skill
triggers:
  - beta
---

Content
"""
        )

        registry = SkillsRegistry(skills_dir=tmp_path)

        prompt = registry.format_for_prompt()

        assert "## Available Skills" in prompt
        assert "**alpha-skill**" in prompt
        assert "**beta-skill**" in prompt
        # Should be sorted by name
        assert prompt.index("alpha-skill") < prompt.index("beta-skill")

    def test_format_for_prompt_empty(self, tmp_path: Path) -> None:
        """Test formatting when no skills are available."""
        registry = SkillsRegistry(skills_dir=tmp_path)

        prompt = registry.format_for_prompt()

        assert "No skills available" in prompt

    def test_find_relevant_skills(self, tmp_path: Path) -> None:
        """Test finding skills relevant to a user message."""
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text(
            """---
name: mascot-skill
description: Create mascots
triggers:
  - mascot
  - character
---

Content
"""
        )

        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text(
            """---
name: logo-skill
description: Create logos
triggers:
  - logo
  - brand mark
---

Content
"""
        )

        registry = SkillsRegistry(skills_dir=tmp_path)

        # Message about mascot
        relevant = registry.find_relevant_skills("I want to create a mascot")
        assert len(relevant) == 1
        assert relevant[0].name == "mascot-skill"

        # Message about logo
        relevant = registry.find_relevant_skills("Design a new logo for me")
        assert len(relevant) == 1
        assert relevant[0].name == "logo-skill"

        # Message about neither
        relevant = registry.find_relevant_skills("Hello, how are you?")
        assert len(relevant) == 0

        # Case insensitive
        relevant = registry.find_relevant_skills("I need a MASCOT")
        assert len(relevant) == 1

    def test_lazy_loading(self, tmp_path: Path) -> None:
        """Test that skills are loaded lazily on first access."""
        skill_dir = tmp_path / "lazy"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: lazy
description: Lazy skill
---

Content
"""
        )

        registry = SkillsRegistry(skills_dir=tmp_path)

        # Not loaded yet
        assert registry._loaded is False

        # Accessing skills triggers load
        _ = registry.skills

        assert registry._loaded is True
        assert "lazy" in registry.skills


class TestBundledSkills:
    """Tests for the bundled skills in the package."""

    def test_bundled_skills_load(self) -> None:
        """Test that bundled skills load correctly."""
        from sip_videogen.advisor.skills.registry import get_skills_registry

        registry = get_skills_registry()

        # Should have bundled skills
        assert len(registry.skills) >= 5  # We created 6 skills

        # Check expected skills exist
        expected_skills = [
            "brand-identity",
            "mascot-generation",
            "logo-design",
            "image-composer",
            "image-prompt-engineering",
            "brand-evolution",
        ]

        for skill_name in expected_skills:
            skill = registry.get(skill_name)
            assert skill is not None, f"Missing bundled skill: {skill_name}"
            assert skill.description, f"Skill {skill_name} missing description"
            assert skill.instructions, f"Skill {skill_name} missing instructions"

    def test_bundled_skills_format(self) -> None:
        """Test that bundled skills format correctly for prompt."""
        from sip_videogen.advisor.skills.registry import get_skills_registry

        registry = get_skills_registry()
        prompt = registry.format_for_prompt()

        assert "## Available Skills" in prompt
        assert "brand-identity" in prompt
        assert "mascot" in prompt.lower()
        assert "logo" in prompt.lower()
