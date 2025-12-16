"""AI agents for script development and creative direction.

This module contains the agent team that collaborates to transform
vague video ideas into structured video scripts.
"""

from sip_videogen.agents.continuity_supervisor import (
    continuity_supervisor_agent,
    validate_and_optimize,
)
from sip_videogen.agents.image_reviewer import (
    image_reviewer_agent,
    review_image,
)
from sip_videogen.agents.production_designer import (
    identify_shared_elements,
    production_designer_agent,
)
from sip_videogen.agents.screenwriter import develop_scenes, screenwriter_agent
from sip_videogen.agents.showrunner import (
    AgentProgress,
    ProgressCallback,
    ProgressTrackingHooks,
    ScriptDevelopmentError,
    develop_script,
    develop_script_from_pitch,
    generate_directors_pitch,
    pitch_agent,
    showrunner_agent,
)
from sip_videogen.agents.tools import (
    ImageProductionManager,
    generate_reference_images_with_review,
)

__all__ = [
    # Screenwriter
    "screenwriter_agent",
    "develop_scenes",
    # Production Designer
    "production_designer_agent",
    "identify_shared_elements",
    # Continuity Supervisor
    "continuity_supervisor_agent",
    "validate_and_optimize",
    # Image Reviewer
    "image_reviewer_agent",
    "review_image",
    # Showrunner
    "showrunner_agent",
    "pitch_agent",
    "develop_script",
    "generate_directors_pitch",
    "develop_script_from_pitch",
    "ScriptDevelopmentError",
    "AgentProgress",
    "ProgressCallback",
    "ProgressTrackingHooks",
    # Image Production Tools
    "ImageProductionManager",
    "generate_reference_images_with_review",
]
