"""CLI interface for sip-videogen."""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from .agents import AgentProgress, ScriptDevelopmentError, develop_script
from .assembler import FFmpegAssembler, FFmpegError
from .config.costs import estimate_costs, estimate_pre_generation_costs
from .config.logging import get_logger, setup_logging
from .config.settings import get_settings
from .generators import ImageGenerationError, ImageGenerator, VideoGenerationError, VideoGenerator
from .models import GeneratedAsset, ProductionPackage, VideoScript
from .storage import (
    GCSAuthenticationError,
    GCSBucketNotFoundError,
    GCSPermissionError,
    GCSStorage,
    GCSStorageError,
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
) -> None:
    """Generate a video from your idea.

    This command takes a creative idea and transforms it into a complete video
    using an AI agent team for scriptwriting and video generation.

    Examples:
        sip-videogen generate "A cat astronaut explores Mars"
        sip-videogen generate "A day in the life of a robot" --scenes 5
        sip-videogen generate "Underwater adventure" --dry-run
        sip-videogen generate "Epic space battle" --yes  # Skip cost confirmation
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
                f"[red]Missing configuration:[/red]\n\n"
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

    logger.info("Starting video generation for idea: %s", idea[:50] + "..." if len(idea) > 50 else idea)
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

    # Run the async pipeline
    try:
        asyncio.run(_run_pipeline(idea, num_scenes, dry_run, settings, logger))
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
) -> None:
    """Run the full video generation pipeline.

    Flow:
    1. Run Showrunner to develop script
    2. Generate reference images for shared elements (dry-run stops here)
    3. Upload reference images to GCS
    4. Generate video clips (parallel)
    5. Download video clips from GCS
    6. Concatenate clips with FFmpeg
    7. Display final video path
    """
    # Create unique project ID for this run
    project_id = f"sip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Ensure output directory exists
    output_dir = settings.ensure_output_dir()
    project_dir = output_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize production package
    package = ProductionPackage(
        script=VideoScript(
            title="",
            logline="",
            tone="",
            shared_elements=[],
            scenes=[],
        )
    )

    # ========== STAGE 1: Develop Script ==========
    console.print("\n[bold cyan]Stage 1/6:[/bold cyan] Developing script...")
    console.print("[dim]Agent team is collaborating on your video script...[/dim]\n")

    # Create a live display for agent progress
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text

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

    # ========== STAGE 2: Generate Reference Images ==========
    console.print("\n[bold cyan]Stage 2/6:[/bold cyan] Generating reference images...")

    if not script.shared_elements:
        console.print("[yellow]No shared elements found - skipping reference images.[/yellow]")
    else:
        images_dir = project_dir / "reference_images"
        images_dir.mkdir(exist_ok=True)

        image_generator = ImageGenerator(api_key=settings.gemini_api_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Generating images...",
                total=len(script.shared_elements),
            )

            for element in script.shared_elements:
                try:
                    asset = await image_generator.generate_reference_image(
                        element=element,
                        output_dir=images_dir,
                    )
                    package.reference_images.append(asset)
                    progress.update(
                        task,
                        advance=1,
                        description=f"[green]Generated: {element.name}",
                    )
                except ImageGenerationError as e:
                    logger.warning(f"Failed to generate image for {element.name}: {e}")
                    progress.update(
                        task,
                        advance=1,
                        description=f"[red]Failed: {element.name}",
                    )

        console.print(
            f"[green]Generated {len(package.reference_images)}/{len(script.shared_elements)} "
            "reference images.[/green]"
        )

    # ========== STAGE 3: Upload Reference Images to GCS ==========
    console.print("\n[bold cyan]Stage 3/6:[/bold cyan] Uploading images to GCS...")

    gcs_storage = GCSStorage(bucket_name=settings.sip_gcs_bucket_name)
    gcs_prefix = f"sip-videogen/{project_id}"

    if package.reference_images:
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
    console.print("\n[bold cyan]Stage 4/6:[/bold cyan] Generating video clips...")

    video_generator = VideoGenerator(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )

    output_gcs_prefix = f"gs://{settings.sip_gcs_bucket_name}/{gcs_prefix}/videos"

    try:
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
    except VideoGenerationError as e:
        logger.error(f"Video generation failed: {e}")
        console.print(f"[red]Video generation failed:[/red] {e}")
        raise

    # ========== STAGE 5: Download Video Clips ==========
    console.print("\n[bold cyan]Stage 5/6:[/bold cyan] Downloading video clips...")

    videos_dir = project_dir / "clips"
    videos_dir.mkdir(exist_ok=True)

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
                # Determine local filename from GCS URI
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

    if not downloaded_clips:
        console.print("[red]No clips available for concatenation.[/red]")
        raise typer.Exit(1)

    # ========== STAGE 6: Concatenate Clips ==========
    console.print("\n[bold cyan]Stage 6/6:[/bold cyan] Assembling final video...")

    try:
        assembler = FFmpegAssembler()
    except FFmpegError as e:
        console.print(f"[red]FFmpeg error:[/red] {e}")
        raise typer.Exit(1)

    # Sort clips by scene number
    clip_paths = sorted(
        [Path(c.local_path) for c in downloaded_clips if c.local_path],
        key=lambda p: int(p.stem.split("_")[-1]),
    )

    final_video_path = project_dir / f"{script.title.replace(' ', '_').lower()[:50]}_final.mp4"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Concatenating clips...", total=None)
        try:
            assembler.concatenate_clips(clip_paths, final_video_path)
            package.final_video_path = str(final_video_path)
            progress.update(task, description="[green]Video assembled ✓")
        except FFmpegError as e:
            progress.update(task, description=f"[red]Assembly failed: {e}")
            raise

    # ========== FINAL SUMMARY ==========
    _display_final_summary(package, project_dir)


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


def _display_final_summary(package: ProductionPackage, project_dir: Path) -> None:
    """Display the final generation summary."""
    # Get video info if available
    duration_info = ""
    if package.final_video_path:
        try:
            assembler = FFmpegAssembler()
            duration = assembler.get_video_duration(Path(package.final_video_path))
            duration_info = f"\n[bold]Duration:[/bold] {duration:.1f}s"
        except FFmpegError:
            pass

    console.print(
        Panel(
            "[bold green]Video generation complete![/bold green]\n\n"
            f"[bold]Final Video:[/bold] {package.final_video_path}{duration_info}\n"
            f"[bold]Project Folder:[/bold] {project_dir}\n"
            f"[bold]Reference Images:[/bold] {len(package.reference_images)}\n"
            f"[bold]Video Clips:[/bold] {len(package.video_clips)}",
            title="Generation Complete",
            border_style="green",
        )
    )


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
        console.print("Run [bold]sip-videogen generate \"your idea\"[/bold] to create a video.")
    else:
        console.print("\n[red]✗ Missing required configuration[/red]")
        console.print(
            "Copy [bold].env.example[/bold] to [bold].env[/bold] and fill in missing values."
        )
        raise typer.Exit(1)


@app.command()
def setup() -> None:
    """Interactive setup helper.

    Guides you through setting up the required configuration for sip-videogen.
    """
    console.print(
        Panel(
            "[bold]sip-videogen Setup[/bold]\n\n"
            "This command will help you configure sip-videogen.",
            border_style="blue",
        )
    )

    console.print("\n[bold]Required Setup Steps:[/bold]\n")

    steps = [
        (
            "1. OpenAI API Key",
            "Get from https://platform.openai.com/api-keys",
        ),
        (
            "2. Gemini API Key",
            "Get from https://aistudio.google.com/apikey",
        ),
        (
            "3. Google Cloud Project",
            "Create at https://console.cloud.google.com",
        ),
        (
            "4. GCS Bucket",
            "Create with: gsutil mb -l us-central1 gs://your-bucket-name",
        ),
        (
            "5. Application Default Credentials",
            "Run: gcloud auth application-default login",
        ),
    ]

    for step, details in steps:
        console.print(f"[cyan]{step}[/cyan]")
        console.print(f"   {details}\n")

    console.print(
        "[yellow]After completing these steps:[/yellow]\n"
        "1. Copy .env.example to .env\n"
        "2. Fill in your API keys and project details\n"
        "3. Run [bold]sip-videogen status[/bold] to verify configuration"
    )

    # TODO: Could add interactive prompts here in the future


def _show_menu() -> str:
    """Display the main menu and get user choice."""
    console.print(BANNER)
    console.print()

    menu_options = [
        ("1", "Generate Video", "Create a new video from your idea"),
        ("2", "Script Only (Dry Run)", "Generate script without creating video"),
        ("3", "Check Status", "View configuration status"),
        ("4", "Help", "Show usage information"),
        ("5", "Exit", "Quit the application"),
    ]

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold yellow", width=4)
    table.add_column("Option", style="bold white", width=25)
    table.add_column("Description", style="dim")

    for key, option, desc in menu_options:
        table.add_row(f"[{key}]", option, desc)

    console.print(Panel(table, title="[bold]Main Menu[/bold]", border_style="cyan"))
    console.print()

    return Prompt.ask(
        "[bold yellow]Select an option[/bold yellow]",
        choices=["1", "2", "3", "4", "5"],
        default="1"
    )


def _get_video_idea() -> tuple[str, int]:
    """Prompt user for video idea and number of scenes."""
    console.print()
    console.print("[bold cyan]Let's create your video![/bold cyan]")
    console.print()

    idea = Prompt.ask("[bold]Enter your video idea[/bold]")
    while not idea.strip() or len(idea.strip()) < 5:
        console.print("[red]Please enter a valid idea (at least 5 characters)[/red]")
        idea = Prompt.ask("[bold]Enter your video idea[/bold]")

    scenes = IntPrompt.ask(
        "[bold]Number of scenes[/bold]",
        default=3,
    )
    scenes = max(1, min(scenes, 10))  # Clamp between 1-10

    return idea.strip(), scenes


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

            if choice == "1":
                idea, scenes = _get_video_idea()
                # Call the actual generate function
                generate(idea=idea, scenes=scenes, dry_run=False, yes=False)
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "2":
                idea, scenes = _get_video_idea()
                generate(idea=idea, scenes=scenes, dry_run=True, yes=False)
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "3":
                status()
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "4":
                _show_help()
                Prompt.ask("\n[dim]Press Enter to continue...[/dim]")

            elif choice == "5":
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
