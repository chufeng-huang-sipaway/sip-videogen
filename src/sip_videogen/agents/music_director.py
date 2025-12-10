"""Music Director agent for background music generation.

This agent analyzes a video script and produces a MusicBrief describing
the ideal background music style, mood, and generation prompt for Lyria 2.
"""

from pathlib import Path

from agents import Agent

from sip_videogen.models.music import MusicBrief

# Load the detailed prompt from the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MUSIC_DIRECTOR_PROMPT_PATH = _PROMPTS_DIR / "music_director.md"


def _load_prompt() -> str:
    """Load the music director prompt from the markdown file."""
    if _MUSIC_DIRECTOR_PROMPT_PATH.exists():
        return _MUSIC_DIRECTOR_PROMPT_PATH.read_text()
    # Fallback to inline prompt if file doesn't exist
    return """You are the Music Director for a video production. Your role is to analyze
the video script and determine the perfect background music style that enhances
the viewing experience.

Given a video script with scenes, characters, and narrative:
1. Analyze the overall tone, pacing, and emotional arc
2. Consider the setting, genre, and target audience
3. Design a cohesive music style that complements (not overpowers) the content

Output a MusicBrief with a detailed prompt for AI music generation.
"""


# Create the music director agent
music_director_agent = Agent(
    name="MusicDirector",
    instructions=_load_prompt(),
    output_type=MusicBrief,
)


async def analyze_script_for_music(script_summary: str) -> MusicBrief:
    """Analyze a video script and determine ideal background music.

    Args:
        script_summary: Summary of the video script including title, logline,
            tone, and scene descriptions.

    Returns:
        MusicBrief containing the music generation prompt and style metadata.
    """
    from agents import Runner

    prompt = f"""Analyze this video script and design the perfect background music:

{script_summary}

Requirements:
- Create a detailed prompt for AI music generation (50-100 words)
- Music should COMPLEMENT the video, not compete with dialogue or sound effects
- Consider that the music will loop if the video is longer than ~32 seconds
- Avoid overly complex or attention-grabbing music for narrative content
- Match energy levels to the video's pacing and emotional arc
- Background music must be INSTRUMENTAL only (no vocals)

Provide a MusicBrief with:
- prompt: Specific, detailed prompt for AI music generation
- negative_prompt: What to exclude (always include "vocals, singing, lyrics")
- mood: Primary emotional quality
- genre: Musical style
- tempo: Speed/energy level description
- instruments: 2-4 key instruments to feature
- rationale: Brief explanation of why this music fits
"""

    result = await Runner.run(music_director_agent, prompt)
    return result.final_output
