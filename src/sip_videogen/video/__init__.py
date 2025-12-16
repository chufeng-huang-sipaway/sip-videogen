"""Video generation pipeline API.

This module provides a non-interactive, programmatic API for video generation.
It extracts the core orchestration logic from the CLI into a reusable library.

The main entry points are:
- VideoPipeline: Full control over the generation process
- generate_video: Simple convenience function

Example usage:
    from sip_videogen.video import generate_video

    result = await generate_video(
        idea="A cat playing piano in a jazz club",
        num_scenes=3,
    )
    print(f"Video created: {result.final_video_path}")

For more control:
    from sip_videogen.video import VideoPipeline, PipelineConfig

    config = PipelineConfig(
        idea="A day in the life of a robot",
        num_scenes=5,
        enable_music=True,
    )
    pipeline = VideoPipeline(config)
    pipeline.on_progress = lambda stage, msg: print(f"[{stage}] {msg}")
    result = await pipeline.run()
"""

from sip_videogen.video.pipeline import (
    PipelineConfig,
    PipelineError,
    PipelineResult,
    VideoPipeline,
    generate_video,
)

__all__ = [
    "PipelineConfig",
    "PipelineError",
    "PipelineResult",
    "VideoPipeline",
    "generate_video",
]
