# Background Music Generation - Implementation Plan

## Overview

Add consistent background music to sip-videogen using Google Vertex AI Lyria 2, while preserving VEO's dialogue and sound effects through prompt engineering.

**Approach**: Use VEO prompt engineering to generate video with ambient sounds/dialogue but NO background music, then overlay consistent Lyria 2 background music via FFmpeg.

---

## Technology Stack

### Google Vertex AI Lyria 2

| Aspect | Details |
|--------|---------|
| **Model** | `lyria-002` |
| **Pricing** | $0.06 per ~32.8-second clip |
| **Output** | WAV, 48kHz stereo |
| **Features** | Text-to-music, negative prompts, seed for reproducibility |
| **Commercial Use** | Yes - IP indemnification included |

### VEO 3.1 Audio Strategy

**Goal**: Keep dialogue + sound effects, remove background music via prompts.

```
Audio instruction format:
"Audio: [specific sounds], no background music, no soundtrack"

Example:
"A basketball game. Audio: dribbling, sneakers squeaking, crowd noise, player shouts. No background music."
```

---

## Architecture

### Current Flow
```
Showrunner → Images → VEO Clips (with VEO music) → FFmpeg Concat → Final Video
```

### New Flow
```
                                    ┌─────────────────────────────────────┐
                                    │  VEO Clips                          │
Showrunner ─┬─► Images ─────────────┤  (ambient audio, no background      │──┐
            │                       │   music via prompt engineering)     │  │
            │                       └─────────────────────────────────────┘  │
            │                                                                │
            │   ┌─────────────────────────────────────────────────────┐      │
            └──►│  Music Director Agent → Lyria 2                     │──────┼──► FFmpeg Mix ──► Final Video
                │  (analyzes script, generates consistent music)      │      │
                └─────────────────────────────────────────────────────┘      │
                                                                             │
                        Concatenate clips + overlay looped music ◄───────────┘
```

---

## Implementation Stages

### Stage 1: Music Data Models
**Goal**: Define data structures for music generation

**New File**: `src/sip_videogen/models/music.py`
```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class MusicMood(str, Enum):
    UPBEAT = "upbeat"
    CALM = "calm"
    DRAMATIC = "dramatic"
    SUSPENSEFUL = "suspenseful"
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    ENERGETIC = "energetic"
    PEACEFUL = "peaceful"

class MusicGenre(str, Enum):
    ORCHESTRAL = "orchestral"
    ELECTRONIC = "electronic"
    ACOUSTIC = "acoustic"
    AMBIENT = "ambient"
    CINEMATIC = "cinematic"
    POP = "pop"
    JAZZ = "jazz"
    CLASSICAL = "classical"

class MusicBrief(BaseModel):
    """Output from Music Director agent describing desired music."""
    prompt: str = Field(description="Detailed music generation prompt for Lyria 2")
    negative_prompt: Optional[str] = Field(default="vocals, singing, lyrics", description="Elements to exclude")
    mood: MusicMood = Field(description="Overall mood of the music")
    genre: MusicGenre = Field(description="Music genre/style")
    tempo: Optional[str] = Field(default=None, description="Tempo description (e.g., 'moderate 100 BPM')")
    instruments: Optional[list[str]] = Field(default=None, description="Key instruments to feature")
    rationale: str = Field(description="Why this music fits the video content")

class GeneratedMusic(BaseModel):
    """Represents generated music track."""
    file_path: str = Field(description="Local path to WAV file")
    duration_seconds: float = Field(description="Duration in seconds (~32.8s)")
    prompt_used: str = Field(description="Prompt used for generation")
    brief: MusicBrief = Field(description="Original music brief")
```

**Tests**: `tests/test_music_models.py`

---

### Stage 2: Music Director Agent
**Goal**: Create agent that analyzes script and outputs music brief

**New File**: `src/sip_videogen/agents/music_director.py`
```python
from agents import Agent
from ..models.music import MusicBrief
from ..config.settings import get_settings

def create_music_director_agent() -> Agent:
    """Create the Music Director agent."""
    settings = get_settings()

    return Agent(
        name="music_director",
        model=settings.openai_model,
        instructions=open("src/sip_videogen/agents/prompts/music_director.md").read(),
        output_type=MusicBrief,
    )
```

**New File**: `src/sip_videogen/agents/prompts/music_director.md`
```markdown
# Music Director

You are the Music Director for a video production. Your role is to analyze the video script
and determine the perfect background music style that enhances the viewing experience.

## Your Task

Given a video script with scenes, characters, and narrative:
1. Analyze the overall tone, pacing, and emotional arc
2. Consider the setting, genre, and target audience
3. Design a cohesive music style that complements (not overpowers) the content

## Output Requirements

Provide a detailed MusicBrief with:
- **prompt**: Specific, detailed prompt for AI music generation (50-100 words)
  - Include: genre, mood, tempo, key instruments, style references
  - Example: "Upbeat electronic music with synthesizers and light percussion,
    energetic and positive mood, 120 BPM, suitable for tech product showcase"
- **negative_prompt**: What to exclude (always include "vocals, singing, lyrics" for background music)
- **mood**: Primary emotional quality
- **genre**: Musical style
- **tempo**: Speed/energy level
- **instruments**: 2-4 key instruments that should feature
- **rationale**: Brief explanation of why this music fits

## Guidelines

- Background music should COMPLEMENT, not compete with dialogue/sound effects
- Consider the video length - music should work when looped
- Avoid overly complex or attention-grabbing music for narrative content
- Match energy levels to the video's pacing
- Instrumental only - no vocals for background music
```

**Modify**: `src/sip_videogen/agents/showrunner.py`
- Add `music_director` as a tool the Showrunner can call
- Call music director after script is finalized

**Tests**: `tests/test_music_director.py`

---

### Stage 3: Lyria 2 Music Generator
**Goal**: Integrate Lyria 2 API for music generation

**New File**: `src/sip_videogen/generators/music.py`
```python
import base64
from pathlib import Path
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

from ..config.settings import get_settings
from ..models.music import MusicBrief, GeneratedMusic

class MusicGenerator:
    """Generates background music using Google Vertex AI Lyria 2."""

    def __init__(self):
        self.settings = get_settings()
        self.client = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": f"{self.settings.google_cloud_location}-aiplatform.googleapis.com"}
        )
        self.endpoint = (
            f"projects/{self.settings.google_cloud_project}"
            f"/locations/{self.settings.google_cloud_location}"
            f"/publishers/google/models/lyria-002"
        )

    async def generate(self, brief: MusicBrief, output_dir: Path) -> GeneratedMusic:
        """Generate music from a MusicBrief."""
        instance = {"prompt": brief.prompt}
        if brief.negative_prompt:
            instance["negative_prompt"] = brief.negative_prompt

        instances = [json_format.ParseDict(instance, Value())]
        response = self.client.predict(
            endpoint=self.endpoint,
            instances=instances,
            parameters=json_format.ParseDict({}, Value())
        )

        # Decode and save audio
        audio_content = response.predictions[0]["audioContent"]
        audio_bytes = base64.b64decode(audio_content)

        output_path = output_dir / "background_music.wav"
        output_path.write_bytes(audio_bytes)

        return GeneratedMusic(
            file_path=str(output_path),
            duration_seconds=32.8,  # Lyria fixed duration
            prompt_used=brief.prompt,
            brief=brief
        )
```

**Modify**: `src/sip_videogen/config/settings.py`
- Add `enable_background_music: bool = True` setting
- Add `music_volume: float = 0.2` setting (0.0 to 1.0)

**Tests**: `tests/test_music_generator.py`

---

### Stage 4: VEO Prompt Engineering
**Goal**: Modify VEO prompts to exclude background music

**Modify**: `src/sip_videogen/generators/video.py`

Add audio instruction suffix to scene prompts:
```python
def _build_scene_prompt(self, scene: SceneAction, script: VideoScript) -> str:
    """Build VEO prompt for a scene with audio instructions."""
    base_prompt = self._build_visual_prompt(scene, script)

    # Add audio instruction to keep SFX/dialogue but no music
    audio_instruction = self._build_audio_instruction(scene)

    return f"{base_prompt}\n\n{audio_instruction}"

def _build_audio_instruction(self, scene: SceneAction) -> str:
    """Build audio instruction based on scene content."""
    # Analyze scene for relevant sounds
    sounds = []

    if scene.dialogue:
        sounds.append("character dialogue")
    if scene.setting:
        sounds.extend(self._infer_ambient_sounds(scene.setting))
    if scene.action:
        sounds.extend(self._infer_action_sounds(scene.action))

    if sounds:
        sound_list = ", ".join(sounds)
        return f"Audio: {sound_list}. No background music, no soundtrack, no musical score."
    else:
        return "Audio: ambient environmental sounds only. No background music, no soundtrack."

def _infer_ambient_sounds(self, setting: str) -> list[str]:
    """Infer ambient sounds from setting description."""
    setting_lower = setting.lower()
    sounds = []

    # Environment mappings
    if any(word in setting_lower for word in ["beach", "ocean", "sea"]):
        sounds.extend(["waves", "seagulls"])
    elif any(word in setting_lower for word in ["forest", "woods", "jungle"]):
        sounds.extend(["birds", "rustling leaves", "wind"])
    elif any(word in setting_lower for word in ["city", "street", "urban"]):
        sounds.extend(["traffic", "city ambience"])
    elif any(word in setting_lower for word in ["office", "room", "indoor"]):
        sounds.extend(["room tone", "subtle ambience"])
    elif any(word in setting_lower for word in ["gym", "basketball", "sports"]):
        sounds.extend(["sneakers squeaking", "ball bouncing", "crowd"])
    # ... more mappings

    return sounds

def _infer_action_sounds(self, action: str) -> list[str]:
    """Infer sounds from action description."""
    action_lower = action.lower()
    sounds = []

    if "walk" in action_lower:
        sounds.append("footsteps")
    if "run" in action_lower:
        sounds.append("running footsteps")
    if "door" in action_lower:
        sounds.append("door sounds")
    if "car" in action_lower or "drive" in action_lower:
        sounds.append("engine sounds")
    # ... more mappings

    return sounds
```

**Tests**: `tests/test_video_generator_audio.py`

---

### Stage 5: FFmpeg Audio Mixing
**Goal**: Mix Lyria music with VEO video clips

**Modify**: `src/sip_videogen/assemblers/ffmpeg.py`

```python
import subprocess
from pathlib import Path
from ..models.music import GeneratedMusic

class FFmpegAssembler:
    # ... existing code ...

    async def assemble_with_music(
        self,
        video_clips: list[Path],
        music: GeneratedMusic,
        output_path: Path,
        music_volume: float = 0.2,
        fade_duration: float = 2.0
    ) -> Path:
        """Assemble video clips and overlay background music."""

        # Step 1: Concatenate video clips (existing logic)
        concat_path = output_path.parent / "concat_temp.mp4"
        await self._concatenate_clips(video_clips, concat_path)

        # Step 2: Get video duration for fade calculation
        duration = await self._get_duration(concat_path)
        fade_out_start = max(0, duration - fade_duration)

        # Step 3: Mix in background music
        filter_complex = (
            f"[1:a]"
            f"afade=t=in:st=0:d={fade_duration},"
            f"afade=t=out:st={fade_out_start}:d={fade_duration},"
            f"volume={music_volume}[music];"
            f"[0:a]volume={1.0 - music_volume * 0.5}[video];"  # Slightly lower video audio
            f"[video][music]amix=inputs=2:duration=first[audio]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(concat_path),
            "-stream_loop", "-1",
            "-i", music.file_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[audio]",
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac",
            str(output_path)
        ]

        await self._run_ffmpeg(cmd)

        # Cleanup temp file
        concat_path.unlink(missing_ok=True)

        return output_path

    async def _get_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
```

**Tests**: `tests/test_ffmpeg_music.py`

---

### Stage 6: CLI Integration
**Goal**: Wire everything together in the CLI

**Modify**: `src/sip_videogen/cli.py`

```python
# Add to imports
from .generators.music import MusicGenerator
from .models.music import MusicBrief

# Add CLI flags
@click.option("--no-music", is_flag=True, help="Disable background music generation")
@click.option("--music-volume", default=0.2, help="Background music volume (0.0-1.0)")

# In generate command, after script generation:
async def generate(idea: str, dry_run: bool, no_music: bool, music_volume: float):
    # ... existing script generation ...

    # Generate music brief via Music Director (part of Showrunner flow)
    music_brief: MusicBrief = script.music_brief  # Added to VideoScript model

    if not dry_run and not no_music and music_brief:
        # Generate background music
        click.echo("Generating background music...")
        music_generator = MusicGenerator()
        generated_music = await music_generator.generate(music_brief, output_dir)
        click.echo(f"Music generated: {generated_music.file_path}")

    # ... existing video generation ...

    # Final assembly with music
    if not no_music and generated_music:
        click.echo("Assembling video with background music...")
        final_video = await assembler.assemble_with_music(
            video_clips,
            generated_music,
            output_path,
            music_volume=music_volume
        )
    else:
        final_video = await assembler.assemble(video_clips, output_path)
```

**Modify**: `src/sip_videogen/models/script.py`
- Add `music_brief: Optional[MusicBrief] = None` to `VideoScript` model

---

## Files Summary

### New Files (6)
| File | Purpose |
|------|---------|
| `src/sip_videogen/models/music.py` | Music data models |
| `src/sip_videogen/agents/music_director.py` | Music Director agent |
| `src/sip_videogen/agents/prompts/music_director.md` | Agent prompt |
| `src/sip_videogen/generators/music.py` | Lyria 2 integration |
| `tests/test_music_models.py` | Model tests |
| `tests/test_music_generator.py` | Generator tests |

### Modified Files (6)
| File | Changes |
|------|---------|
| `src/sip_videogen/agents/showrunner.py` | Add music_director tool |
| `src/sip_videogen/generators/video.py` | Add audio prompt engineering |
| `src/sip_videogen/assemblers/ffmpeg.py` | Add music mixing |
| `src/sip_videogen/cli.py` | Add music flags and generation step |
| `src/sip_videogen/config/settings.py` | Add music settings |
| `src/sip_videogen/models/script.py` | Add music_brief field |

---

## Testing Strategy

### Unit Tests
- `test_music_models.py` - Model validation
- `test_music_generator.py` - Lyria API mocking
- `test_video_generator_audio.py` - Audio prompt generation
- `test_ffmpeg_music.py` - FFmpeg command building

### Integration Tests
- Generate script with music brief
- Mock Lyria API response
- Verify FFmpeg command construction

### Manual Testing
1. Generate video with `--dry-run` to verify music brief
2. Generate short test video with music
3. Compare video quality with/without music
4. Test `--no-music` flag
5. Test different `--music-volume` levels

---

## Cost Analysis

| Video Length | Music Clips | Music Cost | Notes |
|--------------|-------------|------------|-------|
| 32 seconds | 1 | $0.06 | Single clip, no looping needed |
| 2 minutes | 1 | $0.06 | Loop single clip |
| 10 minutes | 1 | $0.06 | Loop single clip |
| 20 minutes | 1 | $0.06 | Loop single clip |

**Note**: Since we loop the music, we only need ONE Lyria generation per video regardless of length.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| VEO ignores "no background music" prompt | Test extensively; fallback to `generateAudio=False` + music-only |
| Lyria music doesn't match video mood | Music Director agent provides detailed prompts; iterate on prompt |
| Music loop sounds repetitive | Generate longer videos may need multiple distinct clips |
| FFmpeg mixing issues | Extensive testing; fallback volume levels |

---

## Future Enhancements

1. **Multiple music sections** - Different music for different parts of video
2. **Music-to-video sync** - Align music beats with scene transitions
3. **User music upload** - Allow custom background music instead of Lyria
4. **Audio ducking** - Automatically lower music during dialogue
