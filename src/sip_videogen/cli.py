"""CLI interface for sip-videogen."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config.settings import get_settings

app = typer.Typer(
    name="sip-videogen",
    help="Transform vague video ideas into complete videos using an AI agent team.",
    rich_markup_mode="rich",
)

console = Console()


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
) -> None:
    """Generate a video from your idea.

    This command takes a creative idea and transforms it into a complete video
    using an AI agent team for scriptwriting and video generation.

    Examples:
        sip-videogen generate "A cat astronaut explores Mars"
        sip-videogen generate "A day in the life of a robot" --scenes 5
        sip-videogen generate "Underwater adventure" --dry-run
    """
    try:
        settings = get_settings()
    except Exception as e:
        console.print(
            f"[red]Configuration error:[/red] {e}\n"
            "Run [bold]sip-videogen status[/bold] to check your configuration."
        )
        raise typer.Exit(1)

    # Use default scenes from config if not specified
    num_scenes = scenes if scenes is not None else settings.sip_default_scenes

    console.print(
        Panel(
            f"[bold]Idea:[/bold] {idea}\n"
            f"[bold]Scenes:[/bold] {num_scenes}\n"
            f"[bold]Dry run:[/bold] {dry_run}",
            title="Video Generation Request",
            border_style="blue",
        )
    )

    if dry_run:
        console.print("[yellow]Dry run mode:[/yellow] Will only generate script, no videos.")

    # TODO: Implement full pipeline in Task 7.1
    console.print("\n[dim]Pipeline not yet implemented - see Task 7.1[/dim]")


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


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
