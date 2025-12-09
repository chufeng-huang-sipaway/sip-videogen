"""CLI interface for sip-videogen."""

import typer

app = typer.Typer(
    name="sip-videogen",
    help="Transform vague video ideas into complete videos using an AI agent team.",
    rich_markup_mode="rich",
)


@app.command()
def generate(
    idea: str = typer.Argument(..., help="Your video idea"),
    scenes: int = typer.Option(3, "--scenes", "-n", help="Number of scenes to generate"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Only generate script, no videos"),
) -> None:
    """Generate a video from your idea."""
    typer.echo(f"Generating video from idea: {idea}")
    typer.echo(f"Scenes: {scenes}, Dry run: {dry_run}")
    typer.echo("Not yet implemented - see Task 7.1")


@app.command()
def status() -> None:
    """Show configuration status."""
    typer.echo("Configuration status check")
    typer.echo("Not yet implemented - see Task 1.3")


@app.command()
def setup() -> None:
    """Interactive setup helper."""
    typer.echo("Interactive setup")
    typer.echo("Not yet implemented - see Task 1.3")


if __name__ == "__main__":
    app()
