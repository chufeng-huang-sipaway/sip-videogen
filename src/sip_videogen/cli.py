"""CLI interface for sip-videogen."""

# ruff: noqa: E402
# Load config from ~/.sip-videogen/.env first, then local .env
# This must happen BEFORE importing agents (openai-agents needs OPENAI_API_KEY in os.environ)
from .config.setup import load_env_to_os

load_env_to_os()

from dotenv import load_dotenv

load_dotenv()  # Also load local .env for backwards compatibility

import asyncio
import math
import platform
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import questionary
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from .agents import (
    AgentProgress,
    ScriptDevelopmentError,
    develop_script,
    develop_script_from_pitch,
    generate_directors_pitch,
)
from .agents.tools import ImageProductionManager
from .assembler import FFmpegAssembler, FFmpegError
from .config.costs import estimate_pre_generation_costs
from .config.logging import get_logger, setup_logging
from .config.settings import get_settings
from .config.setup import (
    ensure_configured,
    get_config_path,
    is_first_run,
    run_setup_wizard,
    show_current_config,
)
from .config.user_preferences import UserPreferences
from .generators import (
    MusicGenerationError,
    MusicGenerator,
    VideoGenerationError,
    VideoGeneratorFactory,
    VideoProvider,
)
from .models import (
    AssetType,
    DirectorsPitch,
    GeneratedAsset,
    GeneratedMusic,
    MusicBrief,
    MusicGenre,
    MusicMood,
    ProductionPackage,
    VideoScript,
)
from .storage import (
    GCSAuthenticationError,
    GCSBucketNotFoundError,
    GCSPermissionError,
    GCSStorage,
    GCSStorageError,
)
from .utils.updater import (
    check_for_update,
    get_current_version,
    prompt_for_update,
)

app = typer.Typer(
    name="sip-videogen",
    help="Transform vague video ideas into complete videos using an AI agent team.",
    rich_markup_mode="rich",
)

console = Console()

BANNER = """
[bold cyan]╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   [bold magenta]SIP VideoGen[/bold magenta]                                        ║
║   [dim]Transform ideas into videos with AI agents[/dim]             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝[/bold cyan]
"""


def _validate_idea(idea: str) -> str:
    """Validate and normalize the user's idea input.

    Args:
        idea: The raw idea string from user input.

    Returns:
        Normalized idea string.

    Raises:
        typer.BadParameter: If the idea is invalid.
    """
    if not idea or not idea.strip():
        raise typer.BadParameter("Idea cannot be empty")

    idea = idea.strip()

    if len(idea) < 5:
        raise typer.BadParameter("Idea is too short (minimum 5 characters)")

    if len(idea) > 2000:
        raise typer.BadParameter("Idea is too long (maximum 2000 characters)")

    return idea


@app.command()
def generate(
    idea: str = typer.Argument(..., help="Your video idea (e.g., 'A cat astronaut explores Mars')"),
    scenes: int = typer.Option(
        None,
        "--scenes",
        "-n",
        help="Number of scenes to generate (default from config)",
        min=1,
        max=10,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only generate script, skip video generation",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip cost confirmation prompt",
    ),
    no_music: bool = typer.Option(
        False,
        "--no-music",
        help="Disable background music generation",
    ),
    music_volume: float = typer.Option(
        None,
        "--music-volume",
        help="Background music volume (0.0-1.0, default from config)",
        min=0.0,
        max=1.0,
    ),
) -> None:
    """Generate a video from your idea.

    This command takes a creative idea and transforms it into a complete video
    using an AI agent team for scriptwriting and video generation.

    Examples:
        sip-videogen generate "A cat astronaut explores Mars"
        sip-videogen generate "A day in the life of a robot" --scenes 5
        sip-videogen generate "Underwater adventure" --dry-run
        sip-videogen generate "Epic space battle" --yes  # Skip cost confirmation
        sip-videogen generate "Cooking show" --no-music  # No background music
        sip-videogen generate "Action scene" --music-volume 0.3  # Louder music
    """
    logger = get_logger(__name__)

    # Validate idea input
    try:
        idea = _validate_idea(idea)
    except typer.BadParameter as e:
        console.print(f"[red]Invalid idea:[/red] {e}")
        raise typer.Exit(1)

    # Load and validate configuration
    try:
        settings = get_settings()
    except ValidationError as e:
        logger.error("Configuration validation error: %s", e)
        console.print(
            "[red]Configuration error:[/red] Invalid configuration values.\n"
            "Check your .env file for correct format.\n"
            f"Details: {e}"
        )
        raise typer.Exit(1)
    except Exception as e:
        logger.error("Configuration error: %s", e)
        console.print(
            f"[red]Configuration error:[/red] {e}\n"
            "Run [bold]sip-videogen status[/bold] to check your configuration."
        )
        raise typer.Exit(1)

    # Validate configuration
    config_status = settings.is_configured()
    if not all(config_status.values()):
        missing = [k for k, v in config_status.items() if not v]
        console.print(
            Panel(
                "[red]Missing configuration:[/red]\n\n"
                + "\n".join(f"  • {m}" for m in missing)
                + "\n\n"
                "Run [bold]sip-videogen setup[/bold] for setup instructions.",
                title="Configuration Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Use default scenes from config if not specified
    num_scenes = scenes if scenes is not None else settings.sip_default_scenes

    logger.info(
        "Starting video generation for idea: %s", idea[:50] + "..." if len(idea) > 50 else idea
    )
    logger.debug("Configuration: scenes=%d, dry_run=%s", num_scenes, dry_run)

    console.print(
        Panel(
            f"[bold]Idea:[/bold] {idea}\n"
            f"[bold]Scenes:[/bold] {num_scenes}\n"
            f"[bold]Dry run:[/bold] {dry_run}",
            title="Video Generation Request",
            border_style="blue",
        )
    )

    # Show cost estimation if not dry-run
    if not dry_run:
        # Estimate costs before generation
        # With reference images, VEO forces 8-second duration
        cost_estimate = estimate_pre_generation_costs(
            num_scenes=num_scenes,
            estimated_shared_elements=3,  # Typical number of shared elements
            video_duration_per_scene=8,  # VEO forces 8s with reference images
        )

        console.print(
            Panel(
                f"[bold yellow]Estimated Cost[/bold yellow]\n\n"
                f"Image Generation ({cost_estimate.image_count} images): ~${cost_estimate.image_total:.2f}\n"
                f"Video Generation ({cost_estimate.video_count} clips, ~{cost_estimate.video_duration_seconds}s): ~${cost_estimate.video_total:.2f}\n"
                f"\n[bold]Total: ${cost_estimate.total_min:.2f} - ${cost_estimate.total_max:.2f}[/bold]\n"
                f"\n[dim]Note: Actual costs depend on final script. VEO pricing may vary.[/dim]",
                title="Cost Estimate",
                border_style="yellow",
            )
        )

        # Ask for confirmation unless --yes flag is provided
        if not yes:
            proceed = typer.confirm("Do you want to proceed with video generation?")
            if not proceed:
                console.print("[yellow]Generation cancelled.[/yellow]")
                raise typer.Exit(0)

    if dry_run:
        console.print("[yellow]Dry run mode:[/yellow] Will only generate script, no videos.")
        logger.info("Dry run mode enabled - will only generate script")

    # Determine music settings
    enable_music = settings.sip_enable_background_music and not no_music
    actual_music_volume = music_volume if music_volume is not None else settings.sip_music_volume

    # Run the async pipeline
    try:
        asyncio.run(
            _run_pipeline(
                idea,
                num_scenes,
                dry_run,
                settings,
                logger,
                enable_music=enable_music,
                music_volume=actual_music_volume,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Generation cancelled by user.[/yellow]")
        raise typer.Exit(130)
    except ScriptDevelopmentError as e:
        logger.error("Script development failed: %s", e)
        console.print(
            Panel(
                f"[red]Script development failed[/red]\n\n{e}\n\n"
                "This may be due to:\n"
                "  • Invalid OpenAI API key\n"
                "  • API rate limits exceeded\n"
                "  • Network connectivity issues",
                title="Script Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except GCSAuthenticationError as e:
        logger.error("GCS authentication failed: %s", e)
        console.print(
            Panel(
                f"[red]Google Cloud authentication failed[/red]\n\n{e}",
                title="Authentication Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except GCSBucketNotFoundError as e:
        logger.error("GCS bucket not found: %s", e)
        console.print(
            Panel(
                f"[red]GCS bucket error[/red]\n\n{e}",
                title="Storage Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except GCSPermissionError as e:
        logger.error("GCS permission denied: %s", e)
        console.print(
            Panel(
                f"[red]GCS permission denied[/red]\n\n{e}",
                title="Permission Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except FFmpegError as e:
        logger.error("FFmpeg error: %s", e)
        console.print(
            Panel(
                f"[red]FFmpeg error[/red]\n\n{e}",
                title="Video Assembly Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except MusicGenerationError as e:
        logger.error("Music generation error: %s", e)
        console.print(
            Panel(
                f"[red]Music generation failed[/red]\n\n{e}\n\n"
                "The video will be generated without background music.",
                title="Music Error",
                border_style="yellow",
            )
        )
        # Don't exit - continue without music
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        console.print(
            Panel(
                f"[red]Generation failed unexpectedly[/red]\n\n{e}\n\n"
                "Check the logs for more details.",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


async def _run_pipeline(
    idea: str,
    num_scenes: int,
    dry_run: bool,
    settings,
    logger,
    enable_music: bool = True,
    music_volume: float = 0.2,
    existing_script: VideoScript | None = None,
) -> None:
    """Run the full video generation pipeline.

    Flow:
    1. Run Showrunner to develop script (skipped if existing_script provided)
    2. Generate reference images for shared elements (dry-run stops here)
    3. Upload reference images to GCS
    4. Generate video clips (parallel)
    5. Download video clips from GCS
    6. Generate background music (if enabled)
    7. Assemble clips with FFmpeg (with music overlay if enabled)
    8. Display final video path

    Args:
        idea: The user's video idea.
        num_scenes: Target number of scenes.
        dry_run: If True, only generate script without video.
        settings: Application settings.
        logger: Logger instance.
        enable_music: Whether to generate background music.
        music_volume: Music volume level (0.0-1.0).
        existing_script: Pre-existing script to use (skips step 1 if provided).
    """
    # Create unique project ID for this run
    project_id = f"sip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Ensure output directory exists
    output_dir = settings.ensure_output_dir()
    project_dir = output_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize production package with placeholder script
    # (will be replaced by develop_script output)
    placeholder_music_brief = MusicBrief(
        prompt="placeholder",
        mood=MusicMood.CALM,
        genre=MusicGenre.AMBIENT,
        rationale="placeholder",
    )
    package = ProductionPackage(
        script=VideoScript(
            title="",
            logline="",
            tone="",
            shared_elements=[],
            scenes=[],
            music_brief=placeholder_music_brief,
        )
    )

    # Track generated music (if enabled)
    generated_music: GeneratedMusic | None = None

    # Determine total stages based on music setting and whether script exists
    if existing_script:
        # Skip stage 1 if script is pre-existing
        total_stages = 6 if enable_music else 5
    else:
        total_stages = 7 if enable_music else 6

    # ========== STAGE 1: Develop Script (skipped if existing_script provided) ==========
    if existing_script:
        # Use pre-existing script
        script = existing_script
        package = ProductionPackage(script=script)
        console.print(f"\n[green]✓ Using pre-approved script: {script.title}[/green]")
    else:
        console.print(f"\n[bold cyan]Stage 1/{total_stages}:[/bold cyan] Developing script...")
        console.print("[dim]Agent team is collaborating on your video script...[/dim]\n")

        # Create a live display for agent progress
        from rich.live import Live

        # Track agent activities
        agent_activities: list[str] = []
        current_status = ["[cyan]Initializing agent team...[/cyan]"]

        def on_agent_progress(progress: AgentProgress) -> None:
            """Callback to update display with agent progress."""
            # Format the message based on event type
            if progress.event_type == "agent_start":
                icon = "[bold blue]►[/bold blue]"
                msg = f"{icon} {progress.message}"
            elif progress.event_type == "agent_end":
                icon = "[bold green]✓[/bold green]"
                msg = f"{icon} {progress.message}"
            elif progress.event_type == "tool_start":
                icon = "[bold yellow]→[/bold yellow]"
                msg = f"{icon} {progress.message}"
                if progress.detail:
                    msg += f"\n    [dim]{progress.detail}[/dim]"
            elif progress.event_type == "tool_end":
                icon = "[bold green]←[/bold green]"
                msg = f"{icon} {progress.message}"
            elif progress.event_type == "thinking":
                icon = "[bold magenta]⋯[/bold magenta]"
                msg = f"{icon} {progress.message}"
            else:
                msg = f"  {progress.message}"

            agent_activities.append(msg)
            # Keep only last 8 activities
            if len(agent_activities) > 8:
                agent_activities.pop(0)
            current_status[0] = msg

        def build_progress_display() -> Panel:
            """Build the progress display panel."""
            lines = []
            for activity in agent_activities:
                lines.append(activity)
            if not lines:
                lines.append("[dim]Starting...[/dim]")
            content = "\n".join(lines)
            return Panel(
                content,
                title="[bold]Agent Team Activity[/bold]",
                border_style="cyan",
                padding=(0, 1),
            )

        try:
            with Live(build_progress_display(), console=console, refresh_per_second=4) as live:

                async def run_with_updates():
                    # Run the script development with progress callback
                    return await develop_script(
                        idea,
                        num_scenes,
                        progress_callback=on_agent_progress,
                    )

                # Create a task that updates the display
                import asyncio

                async def update_display():
                    while True:
                        live.update(build_progress_display())
                        await asyncio.sleep(0.25)

                # Run both concurrently
                update_task = asyncio.create_task(update_display())
                try:
                    script = await run_with_updates()
                finally:
                    update_task.cancel()
                    try:
                        await update_task
                    except asyncio.CancelledError:
                        pass

                # Final update
                agent_activities.append("[bold green]✓ Script development complete![/bold green]")
                live.update(build_progress_display())

            package = ProductionPackage(script=script)
            console.print("[green]✓ Script developed successfully[/green]")

        except Exception as e:
            console.print(f"[red]✗ Script development failed: {e}[/red]")
            raise

    # Display script summary
    _display_script_summary(script)

    # Save script to JSON
    script_path = project_dir / "script.json"
    script_path.write_text(script.model_dump_json(indent=2))
    console.print(f"\n[dim]Script saved to: {script_path}[/dim]")

    if dry_run:
        console.print(
            Panel(
                "[green]Dry run complete![/green]\n\n"
                f"Script saved to: {script_path}\n"
                "Run without --dry-run to generate video.",
                title="Dry Run Summary",
                border_style="green",
            )
        )
        return

    # ========== STAGE 2: Generate Reference Images with Quality Review ==========
    console.print(
        "\n[bold cyan]Stage 2/{total_stages}:[/bold cyan] "
        "Generating reference images with quality review..."
    )

    if not script.shared_elements:
        console.print("[yellow]No shared elements found - skipping reference images.[/yellow]")
    else:
        images_dir = project_dir / "reference_images"
        images_dir.mkdir(exist_ok=True)

        # Use ImageProductionManager for generation with AI quality review
        image_production = ImageProductionManager(
            gemini_api_key=settings.gemini_api_key,
            output_dir=images_dir,
            max_retries=2,  # 3 total attempts per image
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Generating and reviewing images...",
                total=len(script.shared_elements),
            )

            for element in script.shared_elements:
                try:
                    # Generate with review loop
                    result = await image_production.generate_with_review(element)

                    if result.status in ("success", "fallback"):
                        # Create GeneratedAsset from successful or fallback result
                        asset = GeneratedAsset(
                            asset_type=AssetType.REFERENCE_IMAGE,
                            element_id=element.id,
                            local_path=result.local_path,
                        )
                        package.reference_images.append(asset)

                        attempts_info = f"({result.total_attempts} attempt{'s' if result.total_attempts > 1 else ''})"
                        if result.status == "success":
                            progress.update(
                                task,
                                advance=1,
                                description=f"[green]Generated: {element.name} {attempts_info}",
                            )
                        else:
                            # Fallback - image kept despite not being ideal
                            progress.update(
                                task,
                                advance=1,
                                description=f"[yellow]Fallback: {element.name} {attempts_info}",
                            )
                    else:
                        # Complete failure - no image generated at all
                        logger.warning(
                            f"Failed to generate any image for {element.name} "
                            f"after {result.total_attempts} attempts"
                        )
                        progress.update(
                            task,
                            advance=1,
                            description=f"[red]Failed: {element.name} (no image generated)",
                        )
                except Exception as e:
                    logger.warning(f"Error generating image for {element.name}: {e}")
                    progress.update(
                        task,
                        advance=1,
                        description=f"[red]Error: {element.name}",
                    )

        console.print(
            f"[green]Generated {len(package.reference_images)}/{len(script.shared_elements)} "
            "reference images with quality review.[/green]"
        )

    # ========== STAGE 3: Upload Reference Images to GCS ==========
    console.print("\n[bold cyan]Stage 3/{total_stages}:[/bold cyan] Uploading images to GCS...")

    # Try to initialize GCS storage - needed for both VEO (direct URIs) and KLING (signed URLs)
    gcs_storage: GCSStorage | None = None
    gcs_prefix = f"sip-videogen/{project_id}"

    try:
        if settings.sip_gcs_bucket_name:
            gcs_storage = GCSStorage(bucket_name=settings.sip_gcs_bucket_name)
        else:
            raise GCSStorageError("GCS bucket not configured")
    except (GCSStorageError, GCSAuthenticationError, GCSBucketNotFoundError) as e:
        if package.reference_images:
            console.print(
                f"[yellow]Warning: GCS not available ({e})[/yellow]\n"
                "[yellow]Reference images will not be used for video generation.[/yellow]\n"
                "[dim]To enable reference images, configure SIP_GCS_BUCKET_NAME and run:[/dim]\n"
                "[dim]  gcloud auth application-default login[/dim]"
            )
            # Clear GCS URIs since we can't upload
            for asset in package.reference_images:
                asset.gcs_uri = None
        else:
            console.print("[dim]GCS not configured (not needed without reference images)[/dim]")

    if package.reference_images and gcs_storage:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Uploading to GCS...",
                total=len(package.reference_images),
            )

            for asset in package.reference_images:
                try:
                    local_path = Path(asset.local_path)
                    remote_path = gcs_storage.generate_remote_path(
                        f"{gcs_prefix}/reference_images",
                        local_path.name,
                    )
                    gcs_uri = gcs_storage.upload_file(local_path, remote_path)
                    asset.gcs_uri = gcs_uri
                    progress.update(
                        task,
                        advance=1,
                        description=f"[green]Uploaded: {local_path.name}",
                    )
                except GCSStorageError as e:
                    logger.warning(f"Failed to upload {asset.local_path}: {e}")
                    progress.update(
                        task,
                        advance=1,
                        description=f"[red]Failed: {local_path.name}",
                    )

        console.print(
            f"[green]Uploaded {sum(1 for a in package.reference_images if a.gcs_uri)} images to GCS.[/green]"
        )
    else:
        console.print("[yellow]No images to upload.[/yellow]")

    # ========== STAGE 4: Generate Video Clips ==========
    console.print("\n[bold cyan]Stage 4/{total_stages}:[/bold cyan] Generating video clips...")

    # Get user's preferred video provider
    prefs = UserPreferences.load()
    provider = prefs.default_video_provider

    console.print(f"[dim]Using {provider.value.upper()} video generator[/dim]")

    try:
        video_generator = VideoGeneratorFactory.create(provider)
    except ValueError as e:
        console.print(f"[red]Failed to create video generator:[/red] {e}")
        raise typer.Exit(1)

    videos_dir = project_dir / "clips"
    videos_dir.mkdir(exist_ok=True)

    try:
        if provider == VideoProvider.VEO:
            # VEO requires GCS for video storage
            if not gcs_storage:
                console.print(
                    "[red]Error: VEO requires Google Cloud Storage.[/red]\n"
                    "[dim]Configure SIP_GCS_BUCKET_NAME in your .env file and run:[/dim]\n"
                    "[dim]  gcloud auth application-default login[/dim]"
                )
                raise typer.Exit(1)

            # VEO: Generate to GCS, then download
            output_gcs_prefix = f"gs://{settings.sip_gcs_bucket_name}/{gcs_prefix}/videos"

            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_gcs_prefix=output_gcs_prefix,
                reference_images=package.reference_images,
                show_progress=True,
            )
            package.video_clips = video_clips

            if not video_clips:
                console.print("[red]No video clips were generated.[/red]")
                raise typer.Exit(1)

            console.print(
                f"[green]Generated {len(video_clips)}/{len(script.scenes)} video clips.[/green]"
            )

            # Download VEO clips from GCS
            console.print("\n[bold cyan]Stage 5/{total_stages}:[/bold cyan] Downloading video clips...")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Downloading from GCS...",
                    total=len(package.video_clips),
                )

                for clip in package.video_clips:
                    if not clip.gcs_uri:
                        progress.update(task, advance=1)
                        continue

                    try:
                        filename = f"scene_{clip.scene_number:03d}.mp4"
                        local_path = videos_dir / filename

                        gcs_storage.download_file(clip.gcs_uri, local_path)
                        clip.local_path = str(local_path)
                        progress.update(
                            task,
                            advance=1,
                            description=f"[green]Downloaded: {filename}",
                        )
                    except GCSStorageError as e:
                        logger.warning(f"Failed to download {clip.gcs_uri}: {e}")
                        progress.update(
                            task,
                            advance=1,
                            description=f"[red]Failed: scene {clip.scene_number}",
                        )

            downloaded_clips = [c for c in package.video_clips if c.local_path]
            console.print(
                f"[green]Downloaded {len(downloaded_clips)}/{len(package.video_clips)} clips.[/green]"
            )

        else:
            # Kling: Generate directly to local directory
            # Create signed URL generator for reference images (requires GCS)
            signed_url_generator = None
            if gcs_storage:
                def signed_url_generator(gcs_uri: str) -> str:
                    return gcs_storage.generate_signed_url(gcs_uri, expiration_minutes=120)

            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_path=str(videos_dir),
                reference_images=package.reference_images if gcs_storage else None,
                show_progress=True,
                signed_url_generator=signed_url_generator,
            )
            package.video_clips = video_clips

            if not video_clips:
                console.print("[red]No video clips were generated.[/red]")
                raise typer.Exit(1)

            console.print(
                f"[green]Generated {len(video_clips)}/{len(script.scenes)} video clips.[/green]"
            )

            # Kling clips are already local, no download needed
            downloaded_clips = [c for c in package.video_clips if c.local_path]

    except VideoGenerationError as e:
        logger.error(f"Video generation failed: {e}")
        console.print(f"[red]Video generation failed:[/red] {e}")
        raise

    if not downloaded_clips:
        console.print("[red]No clips available for concatenation.[/red]")
        raise typer.Exit(1)

    # ========== Prepare Clips for Assembly ==========
    try:
        assembler = FFmpegAssembler()
    except FFmpegError as e:
        console.print(f"[red]FFmpeg error:[/red] {e}")
        raise typer.Exit(1)

    # Use clips directly - they're already in the right format
    # Just update local_path references if needed for consistency
    clips_ready = [c for c in downloaded_clips if c.local_path]
    console.print(f"[green]{len(clips_ready)} clips ready for assembly.[/green]")

    # ========== STAGE 6: Generate Background Music (if enabled) ==========
    if enable_music and script.music_brief:
        console.print(
            f"\n[bold cyan]Stage 6/{total_stages}:[/bold cyan] Generating background music..."
        )

        music_dir = project_dir / "music"
        music_dir.mkdir(exist_ok=True)

        try:
            music_generator = MusicGenerator(
                project_id=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                mood = script.music_brief.mood.value
                genre = script.music_brief.genre.value
                task = progress.add_task(
                    f"[cyan]Generating {mood} {genre} music...",
                    total=None,
                )
                generated_music = await music_generator.generate(
                    brief=script.music_brief,
                    output_dir=music_dir,
                )
                progress.update(task, description="[green]Music generated ✓")

            console.print(
                f"[green]Generated background music:[/green] {script.music_brief.mood.value} "
                f"{script.music_brief.genre.value} (~{generated_music.duration_seconds:.0f}s)"
            )
        except MusicGenerationError as e:
            logger.warning(f"Music generation failed: {e}")
            console.print(
                f"[yellow]Music generation failed:[/yellow] {e}\n"
                "[dim]Continuing without background music...[/dim]"
            )
            generated_music = None
    elif enable_music and not script.music_brief:
        console.print(
            "[yellow]No music brief in script - skipping music generation.[/yellow]\n"
            "[dim]The Music Director agent may not have been called.[/dim]"
        )

    # ========== STAGE 6 (or 5): Assemble Final Video ==========
    assembly_stage = 6 if enable_music else 5
    console.print(
        f"\n[bold cyan]Stage {assembly_stage}/{total_stages}:[/bold cyan] Assembling final video..."
    )

    # Sort clips by scene number
    clip_paths = sorted(
        [Path(c.local_path) for c in clips_ready],
        key=lambda p: int(p.stem.split("_")[-1]),
    )

    final_video_path = project_dir / f"{script.title.replace(' ', '_').lower()[:50]}_final.mp4"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        if generated_music:
            task = progress.add_task("[cyan]Assembling video with background music...", total=None)
            try:
                assembler.assemble_with_music(
                    clip_paths=clip_paths,
                    music=generated_music,
                    output_path=final_video_path,
                    music_volume=music_volume,
                )
                package.final_video_path = str(final_video_path)
                progress.update(task, description="[green]Video with music assembled ✓")
            except FFmpegError as e:
                progress.update(task, description=f"[red]Assembly failed: {e}")
                raise
        else:
            task = progress.add_task("[cyan]Concatenating clips...", total=None)
            try:
                assembler.concatenate_clips(clip_paths, final_video_path)
                package.final_video_path = str(final_video_path)
                progress.update(task, description="[green]Video assembled ✓")
            except FFmpegError as e:
                progress.update(task, description=f"[red]Assembly failed: {e}")
                raise

    # ========== FINAL SUMMARY ==========
    _display_final_summary(package, project_dir, generated_music)


def _display_script_summary(script: VideoScript) -> None:
    """Display a summary of the generated script."""
    console.print(
        Panel(
            f"[bold]Title:[/bold] {script.title}\n"
            f"[bold]Logline:[/bold] {script.logline}\n"
            f"[bold]Tone:[/bold] {script.tone}\n"
            f"[bold]Scenes:[/bold] {len(script.scenes)}\n"
            f"[bold]Shared Elements:[/bold] {len(script.shared_elements)}\n"
            f"[bold]Total Duration:[/bold] ~{script.total_duration}s",
            title="Script Summary",
            border_style="green",
        )
    )

    # List scenes
    console.print("\n[bold]Scenes:[/bold]")
    for scene in script.scenes:
        console.print(
            f"  [cyan]Scene {scene.scene_number}[/cyan] ({scene.duration_seconds}s): "
            f"{scene.action_description[:60]}..."
            if len(scene.action_description) > 60
            else f"  [cyan]Scene {scene.scene_number}[/cyan] ({scene.duration_seconds}s): "
            f"{scene.action_description}"
        )

    # List shared elements
    if script.shared_elements:
        console.print("\n[bold]Shared Elements:[/bold]")
        for element in script.shared_elements:
            console.print(
                f"  [magenta]{element.element_type.value}:[/magenta] {element.name} "
                f"(appears in scenes: {element.appears_in_scenes})"
            )


def _display_final_summary(
    package: ProductionPackage,
    project_dir: Path,
    generated_music: GeneratedMusic | None = None,
) -> None:
    """Display the final generation summary and offer to open folder."""
    # Get video info if available
    duration_info = ""
    if package.final_video_path:
        try:
            assembler = FFmpegAssembler()
            duration = assembler.get_video_duration(Path(package.final_video_path))
            duration_info = f"\n[bold]Duration:[/bold] {duration:.1f}s"
        except FFmpegError:
            pass

    # Build music info if available
    music_info = ""
    if generated_music:
        music_info = (
            f"\n[bold]Background Music:[/bold] {generated_music.brief.mood.value} "
            f"{generated_music.brief.genre.value}"
        )

    console.print(
        Panel(
            "[bold green]Video generation complete![/bold green]\n\n"
            f"[bold]Final Video:[/bold] {package.final_video_path}{duration_info}{music_info}\n"
            f"[bold]Project Folder:[/bold] {project_dir}\n"
            f"[bold]Reference Images:[/bold] {len(package.reference_images)}\n"
            f"[bold]Video Clips:[/bold] {len(package.video_clips)}",
            title="Generation Complete",
            border_style="green",
        )
    )

    # Offer to open the project folder
    console.print()
    choice = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice(title="Open project folder", value="open"),
            questionary.Choice(title="Return to menu", value="menu"),
        ],
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if choice == "open":
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", str(project_dir)])
            console.print(f"[green]Opened folder:[/green] {project_dir}")
        elif system == "Linux":
            subprocess.run(["xdg-open", str(project_dir)])
            console.print(f"[green]Opened folder:[/green] {project_dir}")
        else:
            console.print(f"[cyan]Project folder:[/cyan] {project_dir}")


@app.command()
def resume(
    run_path: Path | None = typer.Argument(
        None,
        help="Path to an existing run directory containing script.json and reference_images",
    ),
    provider: VideoProvider | None = typer.Option(
        None,
        "--provider",
        help="Override the default video provider (veo or kling)",
        case_sensitive=False,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt",
    ),
) -> None:
    """Regenerate videos from a previous run's script and reference images."""
    run_dir = run_path

    if run_dir is None:
        run_dir = _select_previous_run()
        if run_dir is None:
            raise typer.Exit(1)
    else:
        run_dir = run_dir.expanduser()

    try:
        asyncio.run(
            _resume_video_generation(
                run_dir,
                provider_override=provider,
                skip_confirmation=yes,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Resume cancelled by user.[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Resume failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show configuration status.

    Validates that all required environment variables are set and displays
    the current configuration state.
    """
    console.print(Panel("[bold]Configuration Status[/bold]", border_style="blue"))

    try:
        settings = get_settings()
        config_status = settings.is_configured()
    except Exception as e:
        console.print(f"[red]Failed to load configuration:[/red] {e}")
        console.print(
            "\n[yellow]Tip:[/yellow] Make sure you have a .env file with required settings.\n"
            "Copy .env.example to .env and fill in your API keys."
        )
        raise typer.Exit(1)

    # Create status table
    table = Table(title="Environment Variables", show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Status")
    table.add_column("Notes", style="dim")

    # Check each configuration
    status_items = [
        (
            "OPENAI_API_KEY",
            config_status["openai_api_key"],
            "For agent orchestration",
        ),
        (
            "GEMINI_API_KEY",
            config_status["gemini_api_key"],
            "For image generation",
        ),
        (
            "GOOGLE_CLOUD_PROJECT",
            config_status["google_cloud_project"],
            "GCP project ID",
        ),
        (
            "SIP_GCS_BUCKET_NAME",
            config_status["sip_gcs_bucket_name"],
            "For VEO video storage",
        ),
    ]

    all_configured = True
    for name, is_set, notes in status_items:
        if is_set:
            table.add_row(name, "[green]✓ Set[/green]", notes)
        else:
            table.add_row(name, "[red]✗ Not set[/red]", notes)
            all_configured = False

    console.print(table)

    # Additional configuration details
    console.print("\n[bold]Current Settings:[/bold]")
    details_table = Table(show_header=False, box=None)
    details_table.add_column("Setting", style="cyan")
    details_table.add_column("Value")

    details_table.add_row("Google Cloud Location", settings.google_cloud_location)
    details_table.add_row("Output Directory", str(settings.sip_output_dir))
    details_table.add_row("Default Scenes", str(settings.sip_default_scenes))
    details_table.add_row("Video Duration", f"{settings.sip_video_duration}s")
    details_table.add_row("Log Level", settings.sip_log_level)

    console.print(details_table)

    # Summary
    if all_configured:
        console.print("\n[green]✓ All required settings are configured![/green]")
        console.print('Run [bold]sip-videogen generate "your idea"[/bold] to create a video.')
    else:
        console.print("\n[red]✗ Missing required configuration[/red]")
        console.print(
            "Copy [bold].env.example[/bold] to [bold].env[/bold] and fill in missing values."
        )
        raise typer.Exit(1)


@app.command()
def setup() -> None:
    """Interactive setup wizard.

    Guides you through setting up the required configuration for sip-videogen.
    Supports pasting an entire config block or entering keys individually.
    """
    run_setup_wizard()


@app.command()
def config(
    reset: bool = typer.Option(
        False,
        "--reset",
        "-r",
        help="Reset configuration by pasting a new config block",
    ),
    show: bool = typer.Option(
        False,
        "--show",
        "-s",
        help="Show current configuration",
    ),
) -> None:
    """Manage configuration.

    Run without options to interactively edit configuration.
    Use --reset to replace all configuration with a new config block.
    Use --show to display current configuration status.

    Examples:
        sipvid config          # Interactive config editor
        sipvid config --reset  # Paste new config block
        sipvid config --show   # Show current config
    """
    if show:
        show_current_config()
        console.print(f"\n[dim]Config file: {get_config_path()}[/dim]")
        return

    run_setup_wizard(reset=reset)


@app.command(name="setup-credentials")
def setup_credentials() -> None:
    """Set up Google Cloud credentials for GCS access.

    This command helps you configure Google Cloud credentials by dragging
    and dropping a service account JSON key file. The credentials are saved
    securely and the .env file is updated automatically.

    Examples:
        sipvid setup-credentials
    """
    import json

    console.print(
        Panel(
            "[bold]Google Cloud Credentials Setup[/bold]\n\n"
            "This will configure GCS credentials for uploading reference images.\n"
            "You'll need a service account JSON key from Google Cloud Console.",
            border_style="cyan",
        )
    )

    console.print("\n[bold]Instructions:[/bold]")
    console.print("1. Go to Google Cloud Console → IAM & Admin → Service Accounts")
    console.print("2. Create or select a service account")
    console.print("3. Go to Keys → Add Key → Create new key → JSON")
    console.print("4. A JSON file will be downloaded to your computer")
    console.print()

    console.print("[bold cyan]Drag and drop the JSON file here, then press Enter:[/bold cyan]")
    console.print("[dim](You can drag the file directly from Finder into this terminal)[/dim]")
    console.print()

    # Get file path from drag-and-drop
    try:
        file_path_input = input().strip()
    except EOFError:
        console.print("[red]No input provided. Aborting.[/red]")
        raise typer.Exit(1)

    if not file_path_input:
        console.print("[red]No file path provided. Aborting.[/red]")
        raise typer.Exit(1)

    # Clean up the path - remove quotes and escape characters from drag-and-drop
    # macOS terminal may add quotes around paths with spaces
    # or escape spaces with backslashes
    file_path_str = file_path_input.strip("'\"")
    file_path_str = file_path_str.replace("\\ ", " ")  # Unescape spaces

    file_path = Path(file_path_str)

    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    if not file_path.is_file():
        console.print(f"[red]Not a file: {file_path}[/red]")
        raise typer.Exit(1)

    # Read the JSON file
    try:
        json_content = file_path.read_text()
    except Exception as e:
        console.print(f"[red]Failed to read file: {e}[/red]")
        raise typer.Exit(1)

    # Validate JSON
    try:
        creds_data = json.loads(json_content)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in file: {e}[/red]")
        raise typer.Exit(1)

    # Check for required fields
    required_fields = ["type", "project_id", "private_key", "client_email"]
    missing_fields = [f for f in required_fields if f not in creds_data]
    if missing_fields:
        console.print(f"[red]Missing required fields: {', '.join(missing_fields)}[/red]")
        console.print("[dim]Make sure you're pasting a service account JSON key.[/dim]")
        raise typer.Exit(1)

    if creds_data.get("type") != "service_account":
        console.print("[red]Invalid credential type. Expected 'service_account'.[/red]")
        raise typer.Exit(1)

    # Save to file
    config_dir = Path.home() / ".sip-videogen"
    config_dir.mkdir(parents=True, exist_ok=True)
    creds_file = config_dir / "service-account.json"

    try:
        creds_file.write_text(json_content)
        console.print(f"\n[green]✓[/green] Saved credentials to: {creds_file}")
    except Exception as e:
        console.print(f"[red]Failed to save credentials: {e}[/red]")
        raise typer.Exit(1)

    # Update .env file
    env_file = config_dir / ".env"
    env_line = f"GOOGLE_APPLICATION_CREDENTIALS={creds_file}"

    if env_file.exists():
        env_content = env_file.read_text()
        if "GOOGLE_APPLICATION_CREDENTIALS" in env_content:
            # Replace existing line
            import re
            env_content = re.sub(
                r"GOOGLE_APPLICATION_CREDENTIALS=.*",
                env_line,
                env_content,
            )
        else:
            # Append new line
            if not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f"\n# Google Cloud credentials\n{env_line}\n"
        env_file.write_text(env_content)
    else:
        # Create new .env with this line
        env_file.write_text(f"# Google Cloud credentials\n{env_line}\n")

    console.print(f"[green]✓[/green] Updated config: {env_file}")

    console.print(
        Panel(
            "[bold green]Setup complete![/bold green]\n\n"
            f"Service account: [cyan]{creds_data.get('client_email', 'unknown')}[/cyan]\n"
            f"Project: [cyan]{creds_data.get('project_id', 'unknown')}[/cyan]\n\n"
            "You can now run [bold]sipvid[/bold] to generate videos.",
            border_style="green",
        )
    )


@app.command()
def update(
    check_only: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Only check for updates, don't install",
    ),
) -> None:
    """Check for and install updates.

    Checks PyPI for the latest version and offers to update if available.

    Examples:
        sipvid update         # Update to latest version
        sipvid update --check # Only check, don't install
    """
    console.print(f"[dim]Current version: {get_current_version()}[/dim]")
    console.print("[dim]Checking for updates...[/dim]")

    update_available, latest, current = check_for_update()

    if not update_available:
        if latest:
            console.print(f"\n[green]You're on the latest version ({current})[/green]")
        else:
            console.print("\n[yellow]Could not check for updates (PyPI unreachable)[/yellow]")
        return

    if check_only:
        console.print(f"\n[yellow]Update available:[/yellow] {current} → {latest}")
        console.print("Run [bold]sipvid update[/bold] to install")
        return

    # Prompt and run update
    prompt_for_update(latest, current)


def _open_output_folder() -> None:
    """Open the output directory in the system file browser."""
    settings = get_settings()
    output_dir = settings.ensure_output_dir()

    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(output_dir)])
        console.print(f"[green]Opened output folder:[/green] {output_dir}")
    elif system == "Linux":
        subprocess.run(["xdg-open", str(output_dir)])
        console.print(f"[green]Opened output folder:[/green] {output_dir}")
    else:
        # Fallback: just print the path
        console.print(f"[cyan]Output folder:[/cyan] {output_dir}")


def _get_run_info(run_dir: Path) -> dict | None:
    """Extract run information for history display.

    Args:
        run_dir: Path to a previous run directory.

    Returns:
        Dictionary with run info or None if invalid.
    """
    script_path = run_dir / "script.json"
    if not script_path.exists():
        return None

    try:
        script = _load_script_from_run(run_dir)
    except Exception:
        return None

    # Check for final video
    final_videos = list(run_dir.glob("*_final.mp4"))
    has_final = len(final_videos) > 0

    # Calculate estimated duration from scenes
    estimated_duration = sum(scene.duration_seconds for scene in script.scenes)

    return {
        "title": script.title,
        "clip_count": len(script.scenes),
        "estimated_duration": estimated_duration,
        "is_complete": has_final,
        "run_dir": run_dir,
    }


def _show_history() -> None:
    """Display history of previous video generations with resume option."""
    runs = _list_previous_runs()

    if not runs:
        console.print("[yellow]No previous generations found.[/yellow]")
        console.print(f"[dim]Output directory: {get_settings().sip_output_dir}[/dim]")
        return

    # Build table with run info
    table = Table(
        title="Video Generation History",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Date", style="dim")
    table.add_column("Title", style="white")
    table.add_column("Duration", justify="right")
    table.add_column("Clips", justify="center")
    table.add_column("Status", justify="center")

    # Collect run info for display (limit to 15)
    run_infos = []
    for run_dir in runs[:15]:
        info = _get_run_info(run_dir)
        if info:
            run_infos.append(info)

    for idx, info in enumerate(run_infos, 1):
        # Parse date from folder name (sip_YYYYMMDD_HHMMSS_uuid)
        parts = info["run_dir"].name.split("_")
        if len(parts) >= 3:
            date_str = f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:]}"
            time_str = f"{parts[2][:2]}:{parts[2][2:4]}"
            datetime_str = f"{date_str} {time_str}"
        else:
            datetime_str = "Unknown"

        duration = f"~{info['estimated_duration']}s"
        status = "[green]Complete[/green]" if info["is_complete"] else "[yellow]Partial[/yellow]"

        # Truncate title if too long
        title = info["title"][:35] + "..." if len(info["title"]) > 38 else info["title"]

        table.add_row(
            str(idx),
            datetime_str,
            title,
            duration,
            str(info["clip_count"]),
            status,
        )

    console.print()
    console.print(table)
    console.print()

    if not run_infos:
        console.print("[yellow]No valid runs found.[/yellow]")
        return

    # Build selection choices
    choices = [
        questionary.Choice(
            title=f"{idx}. {info['title'][:40]}",
            value=str(idx),
        )
        for idx, info in enumerate(run_infos, 1)
    ]
    choices.append(questionary.Choice(title="Back to menu", value="back"))

    selection = questionary.select(
        "Select a run to view options:",
        choices=choices,
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if selection == "back" or selection is None:
        return

    # Get selected run
    selected_idx = int(selection) - 1
    selected_info = run_infos[selected_idx]
    selected_dir = selected_info["run_dir"]

    # Show action options for selected run
    console.print()
    console.print(f"[bold cyan]Selected:[/bold cyan] {selected_info['title']}")
    console.print(f"[dim]Path: {selected_dir}[/dim]")
    console.print()

    action_choices = [
        questionary.Choice(title="Resume/regenerate videos from this script", value="resume"),
        questionary.Choice(title="Open this run's folder", value="open"),
        questionary.Choice(title="Back to history", value="back"),
    ]

    action = questionary.select(
        "What would you like to do?",
        choices=action_choices,
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if action == "resume":
        # Trigger resume flow for this run
        _resume_video_generation(selected_dir)
    elif action == "open":
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", str(selected_dir)])
        elif system == "Linux":
            subprocess.run(["xdg-open", str(selected_dir)])
        console.print(f"[green]Opened folder:[/green] {selected_dir}")
    # If "back", just return to history (but we're in a function so it returns to menu)


def _show_menu() -> str:
    """Display the simplified main menu with primary actions."""
    console.print(BANNER)

    # Show version
    version = get_current_version()
    console.print(f"[dim]v{version}[/dim]")
    console.print()

    choices = [
        questionary.Choice(
            title="Generate Video     Create a new video from your idea",
            value="generate",
        ),
        questionary.Choice(
            title="View History       See previous generations",
            value="history",
        ),
        questionary.Choice(
            title="More Options...    Settings, resume, and other tools",
            value="more",
        ),
        questionary.Choice(
            title="Exit",
            value="exit",
        ),
    ]

    result = questionary.select(
        "Use arrow keys to navigate, Enter to select:",
        choices=choices,
        style=questionary.Style([
            ("qmark", "fg:cyan bold"),
            ("question", "fg:white bold"),
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
            ("selected", "fg:green"),
        ]),
    ).ask()

    return result or "exit"  # Default to exit if None (Ctrl+C)


def _show_more_options_menu() -> str:
    """Display the 'More Options' submenu."""
    console.print("\n[bold cyan]More Options[/bold cyan]\n")

    choices = [
        questionary.Choice(
            title="Resume Video            Regenerate from a previous run",
            value="resume",
        ),
        questionary.Choice(
            title="Script Only (Dry Run)   Generate script without video",
            value="dry_run",
        ),
        questionary.Choice(
            title="Open Output Folder      Open output directory",
            value="open_folder",
        ),
        questionary.Choice(
            title="Settings                Video generation preferences",
            value="settings",
        ),
        questionary.Choice(
            title="Configuration           API keys and credentials",
            value="config",
        ),
        questionary.Choice(
            title="Check Status            View current configuration",
            value="status",
        ),
        questionary.Choice(
            title="Check for Updates       Update to latest version",
            value="update",
        ),
        questionary.Choice(
            title="Help                    Usage information",
            value="help",
        ),
        questionary.Choice(
            title="Back to Main Menu",
            value="back",
        ),
    ]

    result = questionary.select(
        "Select an option:",
        choices=choices,
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    return result or "back"


# Duration options for video generation (seconds, display label)
DURATION_OPTIONS = [
    (15, "15 seconds"),
    (30, "30 seconds"),
    (45, "45 seconds"),
    (60, "60 seconds"),
]


def _calculate_scenes_from_duration(duration_seconds: int) -> int:
    """Calculate optimal scene count from target duration.

    VEO generates 8-second clips by default, so:
    ceil(duration / 8) gives the scene count.
    Minimum of 2 scenes to ensure a narrative arc.

    Args:
        duration_seconds: Target video duration in seconds.

    Returns:
        Number of scenes to generate.
    """
    return max(2, math.ceil(duration_seconds / 8))


def _get_video_idea() -> tuple[str, int, int]:
    """Prompt user for video idea and target duration.

    Returns:
        Tuple of (idea, target_duration_seconds, calculated_scenes)
    """
    console.print()
    console.print("[bold cyan]Let's create your video![/bold cyan]")
    console.print()

    idea = Prompt.ask("[bold]Enter your video idea[/bold]")
    while not idea.strip() or len(idea.strip()) < 5:
        console.print("[red]Please enter a valid idea (at least 5 characters)[/red]")
        idea = Prompt.ask("[bold]Enter your video idea[/bold]")

    # Build duration choices
    duration_choices = [
        questionary.Choice(title=label, value=duration)
        for duration, label in DURATION_OPTIONS
    ]

    console.print()
    target_duration = questionary.select(
        "Select target video duration:",
        choices=duration_choices,
        default=duration_choices[1],  # 30 seconds default
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    # Handle None (Ctrl+C)
    if target_duration is None:
        target_duration = 30

    num_scenes = _calculate_scenes_from_duration(target_duration)

    return idea.strip(), target_duration, num_scenes


def _display_directors_pitch(pitch: DirectorsPitch) -> None:
    """Display the Director's Pitch proposal to the user.

    Args:
        pitch: The DirectorsPitch to display.
    """
    # Format key elements as a bullet list
    elements_str = "\n".join(f"  - {elem}" for elem in pitch.key_elements)

    content = (
        f"[bold cyan]Title:[/bold cyan] {pitch.title}\n\n"
        f"[bold cyan]Logline:[/bold cyan] {pitch.logline}\n\n"
        f"[bold cyan]Tone:[/bold cyan] {pitch.tone}\n\n"
        f"[bold cyan]Description:[/bold cyan]\n{pitch.brief_description}\n\n"
        f"[bold cyan]Key Elements:[/bold cyan]\n{elements_str}\n\n"
        f"[dim]Planned: {pitch.scene_count} scenes, ~{pitch.estimated_duration}s total[/dim]"
    )

    console.print()
    console.print(
        Panel(
            content,
            title="[bold magenta]Director's Pitch[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
    )
    console.print()


def _interactive_pitch_flow(
    idea: str,
    target_duration: int,
    progress_callback=None,
) -> tuple[VideoScript | None, bool]:
    """Run the interactive Director's Pitch flow with feedback loop.

    This function generates a pitch, shows it to the user, and allows them
    to provide feedback for revision or accept the pitch to proceed.

    Note: This is a synchronous function that calls asyncio.run() internally
    for async operations. This avoids event loop conflicts with questionary.

    Args:
        idea: The user's video idea.
        target_duration: Target duration in seconds.
        progress_callback: Optional callback for agent progress updates.

    Returns:
        Tuple of (VideoScript or None, accepted boolean).
        If accepted is True, VideoScript is the full script.
        If accepted is False, VideoScript is None (user cancelled).
    """
    num_scenes = _calculate_scenes_from_duration(target_duration)
    feedback_history: list[str] = []

    while True:
        # Show progress indicator for pitch generation
        console.print("[dim]Generating pitch...[/dim]")

        try:
            # Run async pitch generation in its own event loop
            pitch = asyncio.run(
                generate_directors_pitch(
                    idea=idea,
                    target_duration=target_duration,
                    num_scenes=num_scenes,
                    previous_feedback=feedback_history if feedback_history else None,
                    progress_callback=progress_callback,
                )
            )
        except ScriptDevelopmentError as e:
            console.print(f"[red]Failed to generate pitch: {e}[/red]")
            return None, False

        # Display the pitch
        _display_directors_pitch(pitch)

        # Get user decision (sync - runs outside event loop)
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice(
                    title="Accept and generate video",
                    value="accept",
                ),
                questionary.Choice(
                    title="Provide feedback for revision",
                    value="feedback",
                ),
                questionary.Choice(
                    title="Cancel and return to menu",
                    value="cancel",
                ),
            ],
            style=questionary.Style([
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
            ]),
        ).ask()

        if choice == "accept":
            # User accepted - develop full script from pitch
            console.print()
            console.print("[bold cyan]Developing full script from approved pitch...[/bold cyan]")
            console.print()

            try:
                # Run async script development in its own event loop
                script = asyncio.run(
                    develop_script_from_pitch(
                        idea=idea,
                        pitch=pitch,
                        progress_callback=progress_callback,
                    )
                )
                return script, True
            except ScriptDevelopmentError as e:
                console.print(f"[red]Failed to develop script: {e}[/red]")
                return None, False

        elif choice == "feedback":
            # User wants to provide feedback
            console.print()
            feedback = Prompt.ask("[bold]Enter your feedback[/bold]")
            if feedback and feedback.strip():
                feedback_history.append(feedback.strip())
                console.print(
                    "[green]Feedback recorded. Generating revised pitch...[/green]"
                )
            # Loop continues with new pitch

        else:
            # User cancelled or Ctrl+C
            console.print("[yellow]Cancelled.[/yellow]")
            return None, False


def _show_settings_menu() -> None:
    """Display and handle settings menu."""
    prefs = UserPreferences.load()
    settings = get_settings()

    while True:
        console.print("\n[bold cyan]Settings[/bold cyan]\n")

        # Show current settings in a table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Setting", style="cyan")
        table.add_column("Current Value", style="green")

        # Default video provider
        table.add_row(
            "Default Video Provider",
            prefs.default_video_provider.value.upper(),
        )

        # Kling settings
        table.add_row("Kling Model Version", prefs.kling.model_version)
        table.add_row("Kling Mode", prefs.kling.mode.upper())

        # API status
        config_status = settings.is_configured()
        veo_status = "[green]Configured[/green]" if (
            config_status.get("google_cloud_project") and
            config_status.get("sip_gcs_bucket_name")
        ) else "[red]Not configured[/red]"
        kling_status = "[green]Configured[/green]" if config_status.get("kling_api") else "[red]Not configured[/red]"

        table.add_row("VEO (Google) Status", veo_status)
        table.add_row("Kling API Status", kling_status)

        console.print(table)
        console.print()

        # Settings menu options
        choices = [
            questionary.Choice(
                title="Change default video provider",
                value="provider",
            ),
            questionary.Choice(
                title="Configure Kling settings",
                value="kling",
            ),
            questionary.Choice(
                title="Back to main menu",
                value="back",
            ),
        ]

        choice = questionary.select(
            "Select option:",
            choices=choices,
            style=questionary.Style([
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
            ]),
        ).ask()

        if choice == "provider":
            _change_video_provider(prefs, settings)
        elif choice == "kling":
            _configure_kling_settings(prefs)
        elif choice == "back" or choice is None:
            break


def _change_video_provider(prefs: UserPreferences, settings) -> None:
    """Change default video provider."""
    console.print("\n[bold]Select Default Video Provider[/bold]\n")

    config_status = settings.is_configured()
    choices = []

    # VEO option (always show, but indicate if not configured)
    veo_available = config_status.get("google_cloud_project") and config_status.get("sip_gcs_bucket_name")
    veo_title = "VEO (Google Vertex AI)"
    if not veo_available:
        veo_title += " [dim][Not configured][/dim]"
    choices.append(questionary.Choice(title=veo_title, value=VideoProvider.VEO.value))

    # Kling option
    kling_available = config_status.get("kling_api")
    kling_title = "Kling AI"
    if not kling_available:
        kling_title += " [dim][Not configured - set KLING_ACCESS_KEY and KLING_SECRET_KEY][/dim]"
    choices.append(questionary.Choice(title=kling_title, value=VideoProvider.KLING.value))

    result = questionary.select(
        "Choose provider:",
        choices=choices,
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if result:
        new_provider = VideoProvider(result)

        # Warn if provider is not configured
        if new_provider == VideoProvider.VEO and not veo_available:
            console.print("[yellow]Warning: VEO is not fully configured. Video generation may fail.[/yellow]")
        elif new_provider == VideoProvider.KLING and not kling_available:
            console.print("[yellow]Warning: Kling is not configured. Set KLING_ACCESS_KEY and KLING_SECRET_KEY in .env[/yellow]")

        prefs.default_video_provider = new_provider
        prefs.save()
        console.print(f"\n[green]Default provider set to {new_provider.value.upper()}[/green]")


def _configure_kling_settings(prefs: UserPreferences) -> None:
    """Configure Kling-specific settings."""
    console.print("\n[bold]Configure Kling Settings[/bold]\n")

    # Model version selection
    # Note: versions are stored without "v" prefix (e.g., "1.6" not "v1.6")
    model_choices = [
        questionary.Choice(title="v2.6 (Audio-capable)", value="2.6"),
        questionary.Choice(title="v2.5 Turbo", value="2.5-turbo"),
        questionary.Choice(title="v1.6 (Stable)", value="1.6"),
        questionary.Choice(title="v1.5", value="1.5"),
        questionary.Choice(title="v2.0", value="2.0"),
        questionary.Choice(title="v2.1", value="2.1"),
    ]

    # Find current selection index
    current_version = prefs.kling.model_version
    default_idx = next(
        (
            i
            for i, c in enumerate(model_choices)
            if c.value == current_version
            or (current_version in {"2.5", "v2.5"} and c.value == "2.5-turbo")
        ),
        0
    )

    model = questionary.select(
        "Select Kling model version:",
        choices=model_choices,
        default=model_choices[default_idx],
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if model:
        prefs.kling.model_version = model

    # Mode selection
    mode_choices = [
        questionary.Choice(
            title="Standard (Faster, default)",
            value="std",
        ),
        questionary.Choice(
            title="Pro (Higher quality, slower)",
            value="pro",
        ),
    ]

    current_mode_idx = 0 if prefs.kling.mode == "std" else 1

    mode = questionary.select(
        "Select Kling mode:",
        choices=mode_choices,
        default=mode_choices[current_mode_idx],
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if mode:
        prefs.kling.mode = mode

    prefs.save()
    console.print("\n[green]Kling settings saved![/green]")


def _list_previous_runs() -> list[Path]:
    """List all previous runs from the output directory.

    Returns:
        List of run directories sorted by modification time (newest first).
    """
    settings = get_settings()
    output_dir = Path(settings.sip_output_dir)

    if not output_dir.exists():
        return []

    runs = []
    for item in output_dir.iterdir():
        if item.is_dir() and item.name.startswith("sip_"):
            # Check if it has a script.json file
            script_file = item / "script.json"
            if script_file.exists():
                runs.append(item)

    # Sort by modification time (newest first)
    runs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return runs


def _load_script_from_run(run_dir: Path) -> VideoScript:
    """Load a VideoScript from a previous run's script.json.

    Args:
        run_dir: Path to the run directory.

    Returns:
        Loaded VideoScript.

    Raises:
        FileNotFoundError: If script.json doesn't exist.
        ValidationError: If the JSON is invalid.
    """
    import json

    script_file = run_dir / "script.json"
    if not script_file.exists():
        raise FileNotFoundError(f"No script.json found in {run_dir}")

    with open(script_file) as f:
        data = json.load(f)

    return VideoScript.model_validate(data)


def _load_reference_images_from_run(run_dir: Path) -> list[GeneratedAsset]:
    """Load reference images from a previous run.

    Args:
        run_dir: Path to the run directory.

    Returns:
        List of GeneratedAsset objects for each reference image.
    """
    images_dir = run_dir / "reference_images"
    if not images_dir.exists():
        return []

    assets = []
    for img_file in images_dir.iterdir():
        if img_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            # Extract element_id from filename (e.g., "char_knight.png" -> "char_knight")
            element_id = img_file.stem

            asset = GeneratedAsset(
                asset_type=AssetType.REFERENCE_IMAGE,
                local_path=str(img_file),
                element_id=element_id,
            )
            assets.append(asset)

    return assets


def _load_music_from_run(run_dir: Path, brief: MusicBrief | None) -> GeneratedMusic | None:
    """Load previously generated background music if present."""
    music_dir = run_dir / "music"
    if not music_dir.exists() or not brief:
        return None

    candidates = list(music_dir.glob("background_music.*"))
    if not candidates:
        # Fallback: any audio file in the directory
        candidates = [
            p
            for p in music_dir.iterdir()
            if p.suffix.lower() in (".wav", ".mp3", ".m4a", ".aac")
        ]
    if not candidates:
        return None

    audio_path = candidates[0]

    try:
        assembler = FFmpegAssembler()
        duration = assembler.get_video_duration(audio_path)
    except Exception:
        duration = 0.0

    return GeneratedMusic(
        file_path=str(audio_path),
        duration_seconds=duration or 0.0,
        prompt_used=brief.prompt if brief else "",
        brief=brief,
    )


def _prepare_clips_for_assembly(
    video_clips: list[GeneratedAsset],
    output_dir: Path,
) -> tuple[list[GeneratedAsset], int]:
    """Copy clips to output directory for assembly."""
    logger = get_logger(__name__)
    output_dir.mkdir(parents=True, exist_ok=True)

    prepared_clips: list[GeneratedAsset] = []
    copied = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Preparing clips...",
            total=len(video_clips),
        )

        for clip in video_clips:
            if not clip.local_path:
                progress.update(task, advance=1)
                continue

            input_path = Path(clip.local_path)
            output_path = output_dir / f"scene_{clip.scene_number:03d}.mp4"

            try:
                shutil.copy(input_path, output_path)
                copied += 1
                clip.local_path = str(output_path)
                prepared_clips.append(clip)
                progress.update(
                    task,
                    advance=1,
                    description=f"[green]Copied scene {clip.scene_number}",
                )
            except (OSError, shutil.Error) as e:
                logger.warning("Failed to copy scene %s: %s", clip.scene_number, e)
                progress.update(
                    task,
                    advance=1,
                    description=f"[red]Failed: scene {clip.scene_number}",
                )

    return prepared_clips, copied


def _select_previous_run() -> Path | None:
    """Show a menu to select a previous run.

    Returns:
        Selected run directory, or None if cancelled.
    """
    runs = _list_previous_runs()

    if not runs:
        console.print("[yellow]No previous runs found in output directory.[/yellow]")
        return None

    # Build choices with run info
    choices = []
    for run_dir in runs[:15]:  # Limit to 15 most recent
        # Parse timestamp from directory name (sip_YYYYMMDD_HHMMSS_uuid)
        parts = run_dir.name.split("_")
        if len(parts) >= 3:
            date_str = parts[1]  # YYYYMMDD
            time_str = parts[2]  # HHMMSS
            try:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
                display_date = f"{formatted_date} {formatted_time}"
            except (IndexError, ValueError):
                display_date = run_dir.name
        else:
            display_date = run_dir.name

        # Try to get script title
        try:
            script = _load_script_from_run(run_dir)
            title = script.title[:40] + "..." if len(script.title) > 40 else script.title
            label = f"{display_date} | {title}"
        except Exception:
            label = f"{display_date} | (script unavailable)"

        choices.append(questionary.Choice(title=label, value=str(run_dir)))

    choices.append(questionary.Choice(title="← Back to main menu", value="back"))

    result = questionary.select(
        "Select a previous run:",
        choices=choices,
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if result == "back" or result is None:
        return None

    return Path(result)


async def _resume_video_generation(
    run_dir: Path,
    provider_override: VideoProvider | None = None,
    skip_confirmation: bool = False,
) -> None:
    """Resume video generation from an existing run folder."""
    logger = get_logger(__name__)

    if not run_dir.exists():
        console.print(f"[red]Run directory not found:[/red] {run_dir}")
        return

    console.print(f"\n[bold cyan]Resuming from:[/bold cyan] {run_dir}\n")

    # Load script
    try:
        script = _load_script_from_run(run_dir)
        console.print(f"[green]✓[/green] Loaded script: {script.title}")
        console.print(f"  Scenes: {len(script.scenes)}")
    except Exception as e:
        console.print(f"[red]Failed to load script:[/red] {e}")
        return

    # Load reference images
    reference_images = _load_reference_images_from_run(run_dir)
    console.print(f"[green]✓[/green] Loaded {len(reference_images)} reference images")

    # Choose provider
    prefs = UserPreferences.load()
    provider = provider_override or prefs.default_video_provider
    console.print(f"[green]✓[/green] Using video provider: {provider.value.upper()}")

    if not skip_confirmation:
        console.print()
        try:
            proceed = await questionary.confirm(
                "Proceed with video generation?",
                default=True,
            ).ask_async()
        except AttributeError:
            # Fallback for older questionary versions
            proceed = questionary.confirm(
                "Proceed with video generation?",
                default=True,
            ).ask()

        if not proceed:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    try:
        settings = get_settings()
    except Exception as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        return

    # Set up output directories
    videos_dir = run_dir / "clips"
    videos_dir.mkdir(parents=True, exist_ok=True)

    processed_dir = run_dir / "clips_processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    try:
        video_generator = VideoGeneratorFactory.create(provider)
    except ValueError as e:
        console.print(f"[red]Failed to create video generator:[/red] {e}")
        return

    console.print("\n[bold cyan]Generating video clips...[/bold cyan]")
    console.print(f"Using {provider.value.upper()} video generator")

    video_clips: list[GeneratedAsset] = []

    try:
        if provider == VideoProvider.VEO:
            gcs_storage = GCSStorage(bucket_name=settings.sip_gcs_bucket_name)
            gcs_prefix = f"sip-videogen/{run_dir.name}"

            # Upload reference images to GCS if needed
            if reference_images:
                console.print("\n[bold cyan]Uploading reference images to GCS...[/bold cyan]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        "[cyan]Uploading images...",
                        total=len(reference_images),
                    )

                    for asset in reference_images:
                        local_path = Path(asset.local_path)
                        if asset.gcs_uri:
                            progress.update(
                                task,
                                advance=1,
                                description=f"[dim]Using existing upload: {local_path.name}[/dim]",
                            )
                            continue

                        remote_path = gcs_storage.generate_remote_path(
                            f"{gcs_prefix}/reference_images",
                            local_path.name,
                        )
                        try:
                            asset.gcs_uri = gcs_storage.upload_file(local_path, remote_path)
                            progress.update(
                                task,
                                advance=1,
                                description=f"[green]Uploaded: {local_path.name}",
                            )
                        except GCSStorageError as e:
                            logger.warning("Failed to upload %s: %s", local_path, e)
                            progress.update(
                                task,
                                advance=1,
                                description=f"[red]Failed: {local_path.name}",
                            )

            output_gcs_prefix = (
                f"gs://{settings.sip_gcs_bucket_name}/{gcs_prefix}/videos"
            )

            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_gcs_prefix=output_gcs_prefix,
                reference_images=reference_images,
                show_progress=True,
            )

            if not video_clips:
                console.print("[red]No video clips were generated.[/red]")
                return

            console.print(
                f"[green]✓[/green] Generated {len(video_clips)}/{len(script.scenes)} video clips"
            )

            # Download clips from GCS
            console.print("\n[bold cyan]Downloading video clips from GCS...[/bold cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Downloading clips...",
                    total=len(video_clips),
                )

                for clip in video_clips:
                    if not clip.gcs_uri:
                        progress.update(task, advance=1)
                        continue

                    try:
                        local_path = videos_dir / f"scene_{clip.scene_number:03d}.mp4"
                        gcs_storage.download_file(clip.gcs_uri, local_path)
                        clip.local_path = str(local_path)
                        progress.update(
                            task,
                            advance=1,
                            description=f"[green]Downloaded: {local_path.name}",
                        )
                    except GCSStorageError as e:
                        logger.warning("Failed to download %s: %s", clip.gcs_uri, e)
                        progress.update(
                            task,
                            advance=1,
                            description=f"[red]Failed: scene {clip.scene_number}",
                        )

        else:
            # Kling generates directly to local path
            signed_url_generator = None
            kling_gcs_storage = None
            try:
                if settings.sip_gcs_bucket_name:
                    kling_gcs_storage = GCSStorage(bucket_name=settings.sip_gcs_bucket_name)
                    signed_url_generator = lambda uri: kling_gcs_storage.generate_signed_url(
                        uri,
                        expiration_minutes=120,
                    )
            except Exception:
                logger.debug("Signed URL generation unavailable; continuing without it")

            # Only pass reference images if GCS is available (needed for signed URLs)
            kling_refs = reference_images if kling_gcs_storage else None
            if reference_images and not kling_gcs_storage:
                console.print(
                    "[yellow]Note: Reference images will not be used (GCS not configured)[/yellow]"
                )

            video_clips = await video_generator.generate_all_video_clips(
                script=script,
                output_path=str(videos_dir),
                reference_images=kling_refs,
                max_concurrent=3,
                show_progress=True,
                signed_url_generator=signed_url_generator,
            )

            if not video_clips:
                console.print("[red]No video clips were generated.[/red]")
                return

            console.print(
                f"[green]✓[/green] Generated {len(video_clips)}/{len(script.scenes)} video clips"
            )

    except (VideoGenerationError, GCSStorageError) as e:
        console.print(f"[red]Video generation failed:[/red] {e}")
        return

    # Prepare clips for assembly
    console.print("\n[bold cyan]Preparing clips for assembly...[/bold cyan]")
    prepared_clips, copied_count = _prepare_clips_for_assembly(video_clips, processed_dir)

    if not prepared_clips:
        console.print("[red]No clips available for assembly.[/red]")
        return

    console.print(f"[green]Prepared {copied_count} clips for assembly.[/green]")

    # Background music handling
    generated_music: GeneratedMusic | None = None
    enable_music = settings.sip_enable_background_music and script.music_brief is not None

    if enable_music:
        console.print("\n[bold cyan]Loading or generating background music...[/bold cyan]")
        generated_music = _load_music_from_run(run_dir, script.music_brief)

        if generated_music:
            console.print(f"[green]✓[/green] Found existing music: {Path(generated_music.file_path).name}")
        else:
            music_dir = run_dir / "music"
            music_dir.mkdir(parents=True, exist_ok=True)
            try:
                music_generator = MusicGenerator(
                    project_id=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                )
                generated_music = await music_generator.generate(
                    brief=script.music_brief,
                    output_dir=music_dir,
                )
                console.print(f"[green]✓[/green] Generated new background music ({generated_music.duration_seconds:.0f}s)")
            except MusicGenerationError as e:
                console.print(
                    f"[yellow]Music generation failed:[/yellow] {e}\n"
                    "[dim]Continuing without background music...[/dim]"
                )
                generated_music = None
    else:
        console.print("[yellow]Background music disabled or not available in script.[/yellow]")

    # Assemble final video
    console.print("\n[bold cyan]Assembling final video...[/bold cyan]")
    slug = script.title.replace(" ", "_").lower() if script.title else "video"
    final_output = run_dir / f"{slug[:50]}_final.mp4"

    clip_paths = sorted(
        (Path(c.local_path) for c in prepared_clips if c.local_path),
        key=lambda p: int(p.stem.split("_")[-1]),
    )

    if not clip_paths:
        console.print("[red]No clips available for assembly.[/red]")
        return

    try:
        assembler = FFmpegAssembler()
        if generated_music:
            assembler.assemble_with_music(
                clip_paths=clip_paths,
                music=generated_music,
                output_path=final_output,
                music_volume=settings.sip_music_volume,
            )
        else:
            assembler.concatenate_clips(
                clip_paths=clip_paths,
                output_path=final_output,
            )

        package = ProductionPackage(
            script=script,
            reference_images=reference_images,
            video_clips=prepared_clips,
            final_video_path=str(final_output),
        )
        _display_final_summary(package, run_dir, generated_music)
    except FFmpegError as e:
        console.print(f"[red]Failed to assemble video:[/red] {e}")


def _show_resume_menu() -> None:
    """Show the resume from previous run menu."""
    console.print("\n[bold]Resume Video Generation[/bold]")
    console.print("[dim]Regenerate videos from a previous run's script and images[/dim]\n")

    run_dir = _select_previous_run()
    if run_dir is None:
        return

    # Run the async function
    asyncio.run(_resume_video_generation(run_dir))


def _show_help() -> None:
    """Show help information."""
    console.print()
    help_text = """
[bold cyan]SIP VideoGen[/bold cyan] transforms your video ideas into complete videos using AI agents.

[bold]How it works:[/bold]
  1. You provide a video idea (e.g., "A cat astronaut explores Mars")
  2. AI agents collaborate to write a script with scenes
  3. Reference images are generated for visual consistency
  4. Video clips are generated for each scene
  5. Clips are assembled into a final video

[bold]Commands:[/bold]
  [yellow]./start.sh[/yellow]              Launch interactive menu
  [yellow]./start.sh generate "idea"[/yellow]  Generate video directly
  [yellow]./start.sh resume [run_dir][/yellow] Resume video generation from a saved script/images folder
  [yellow]./start.sh status[/yellow]       Check configuration

[bold]Requirements:[/bold]
  - OpenAI API key (for AI agents)
  - Google Gemini API key (for image generation)
  - Google Cloud project with Vertex AI enabled (for video generation)
  - FFmpeg installed (for video assembly)

[bold]More info:[/bold]
  See TASKS.md for implementation details
  See IMPLEMENTATION_PLAN.md for architecture overview
"""
    console.print(Panel(help_text, title="[bold]Help[/bold]", border_style="cyan"))
    console.print()


@app.command()
def menu() -> None:
    """Launch interactive menu."""
    while True:
        try:
            choice = _show_menu()

            if choice == "generate":
                idea, target_duration, scenes = _get_video_idea()
                # Run interactive pitch flow for user approval
                try:
                    # Note: _interactive_pitch_flow is now synchronous
                    # (handles asyncio.run internally for async operations)
                    script, accepted = _interactive_pitch_flow(idea, target_duration)

                    if accepted and script:
                        # User approved the pitch - run full generation
                        settings = get_settings()
                        logger = get_logger(__name__)
                        asyncio.run(
                            _run_pipeline(
                                idea=idea,
                                num_scenes=scenes,
                                dry_run=False,
                                settings=settings,
                                logger=logger,
                                enable_music=settings.sip_enable_background_music,
                                music_volume=settings.sip_music_volume,
                                existing_script=script,
                            )
                        )
                    else:
                        console.print("[yellow]Generation cancelled.[/yellow]")
                except KeyboardInterrupt:
                    console.print("\n[yellow]Generation cancelled.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "history":
                _show_history()
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "more":
                # Show submenu and handle selection
                sub_choice = _show_more_options_menu()

                if sub_choice == "resume":
                    _show_resume_menu()
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "dry_run":
                    idea, target_duration, scenes = _get_video_idea()
                    generate(
                        idea=idea,
                        scenes=scenes,
                        dry_run=True,
                        yes=False,
                        no_music=False,
                        music_volume=None,
                    )
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "open_folder":
                    _open_output_folder()
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "settings":
                    _show_settings_menu()

                elif sub_choice == "config":
                    run_setup_wizard()
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "status":
                    status()
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "update":
                    update(check_only=False)
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                elif sub_choice == "help":
                    _show_help()
                    Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

                # "back" just returns to main menu

            elif choice == "exit":
                console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
                sys.exit(0)

        except typer.Exit:
            # Allow typer exits to propagate in menu context
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]")
        except KeyboardInterrupt:
            console.print("\n\n[bold cyan]Goodbye![/bold cyan]\n")
            sys.exit(0)


@app.callback(invoke_without_command=True)
def _default_command(ctx: typer.Context) -> None:
    """Default to interactive menu when no command is specified."""
    if ctx.invoked_subcommand is None:
        # First-run setup check
        if is_first_run():
            if not ensure_configured():
                console.print(
                    "[yellow]Setup cancelled. "
                    "Run 'sipvid config' to configure later.[/yellow]"
                )
                raise typer.Exit(0)

        # Check for updates (non-blocking, fast timeout)
        update_available, latest, current = check_for_update()
        if update_available and latest:
            from .utils.updater import show_update_banner
            show_update_banner(latest, current)

        menu()


def main() -> None:
    """Entry point for the CLI."""
    # Initialize logging with settings
    try:
        settings = get_settings()
        log_level = settings.sip_log_level
    except Exception:
        # Use default log level if settings fail to load
        log_level = "INFO"

    setup_logging(level=log_level)
    app()


if __name__ == "__main__":
    main()
