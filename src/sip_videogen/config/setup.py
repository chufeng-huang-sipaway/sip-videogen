"""First-run setup and configuration management.

Handles:
- First-run detection
- Parsing pasted config blocks (entire .env content)
- Interactive individual key input
- Saving config to ~/.sip-videogen/.env
"""

import os
import re
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Config directory in user's home
CONFIG_DIR = Path.home() / ".sip-videogen"
CONFIG_FILE = CONFIG_DIR / ".env"

# Required keys and their descriptions
REQUIRED_KEYS = {
    "OPENAI_API_KEY": {
        "description": "OpenAI API key for agent orchestration",
        "hint": "Get from https://platform.openai.com/api-keys",
        "placeholder": "sk-...",
    },
    "GEMINI_API_KEY": {
        "description": "Google Gemini API key for image generation",
        "hint": "Get from https://aistudio.google.com/apikey",
        "placeholder": "AIza...",
    },
    "GOOGLE_CLOUD_PROJECT": {
        "description": "Google Cloud Project ID",
        "hint": "Create at https://console.cloud.google.com",
        "placeholder": "my-project-id",
    },
    "SIP_GCS_BUCKET_NAME": {
        "description": "GCS bucket name for video storage",
        "hint": "Create with: gsutil mb -l us-central1 gs://your-bucket",
        "placeholder": "my-sip-bucket",
    },
}

# Optional keys
OPTIONAL_KEYS = {
    "KLING_ACCESS_KEY": {
        "description": "Kling API access key (optional)",
        "hint": "Get from https://app.klingai.com/global/dev/api-key",
        "placeholder": "",
    },
    "KLING_SECRET_KEY": {
        "description": "Kling API secret key (optional)",
        "hint": "Required if using Kling video generation",
        "placeholder": "",
    },
    "GOOGLE_CLOUD_LOCATION": {
        "description": "Google Cloud region",
        "hint": "Default: us-central1",
        "placeholder": "us-central1",
    },
    "SIP_OUTPUT_DIR": {
        "description": "Local output directory",
        "hint": "Default: ./output",
        "placeholder": "./output",
    },
    "SIP_DEFAULT_SCENES": {
        "description": "Default number of scenes",
        "hint": "Default: 3",
        "placeholder": "3",
    },
}

# Defaults for optional keys
DEFAULTS = {
    "GOOGLE_CLOUD_LOCATION": "us-central1",
    "GOOGLE_GENAI_USE_VERTEXAI": "True",
    "SIP_OUTPUT_DIR": "./output",
    "SIP_DEFAULT_SCENES": "3",
    "SIP_VIDEO_DURATION": "6",
    "SIP_ENABLE_BACKGROUND_MUSIC": "True",
    "SIP_MUSIC_VOLUME": "0.2",
}


def get_config_path() -> Path:
    """Get the path to the user's config file."""
    return CONFIG_FILE


def config_exists() -> bool:
    """Check if config file exists and has content."""
    if not CONFIG_FILE.exists():
        return False
    content = CONFIG_FILE.read_text().strip()
    return bool(content)


def is_first_run() -> bool:
    """Check if this is the first run (no config file or empty)."""
    return not config_exists()


def parse_env_block(text: str) -> dict[str, str]:
    """Parse a block of text containing environment variables.

    Supports formats:
    - KEY=value
    - KEY="value"
    - KEY='value'
    - export KEY=value
    - # comments (ignored)
    - Empty lines (ignored)

    Args:
        text: Block of text containing env vars

    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Remove 'export ' prefix if present
        if line.startswith("export "):
            line = line[7:]

        # Parse KEY=VALUE
        match = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line, re.IGNORECASE)
        if match:
            key = match.group(1).upper()
            value = match.group(2)

            # Remove surrounding quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            result[key] = value

    return result


def validate_config(config: dict[str, str]) -> tuple[list[str], list[str]]:
    """Validate config and return missing required keys and warnings.

    Args:
        config: Dictionary of config values

    Returns:
        Tuple of (missing_required_keys, warnings)
    """
    missing = []
    warnings = []

    for key in REQUIRED_KEYS:
        value = config.get(key, "")
        if not value or value in ("sk-...", "...", "your-project-id", "your-bucket-name"):
            missing.append(key)

    # Check for placeholder values
    openai_key = config.get("OPENAI_API_KEY", "")
    if openai_key.startswith("sk-") and len(openai_key) < 20:
        warnings.append("OPENAI_API_KEY looks like a placeholder")

    return missing, warnings


def save_config(config: dict[str, str]) -> None:
    """Save config to ~/.sip-videogen/.env.

    Args:
        config: Dictionary of config values
    """
    # Ensure directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Build env file content with nice formatting
    lines = [
        "# SIP VideoGen Configuration",
        "# Generated by sipvid config",
        "",
        "# OpenAI (for agent orchestration)",
    ]

    if "OPENAI_API_KEY" in config:
        lines.append(f"OPENAI_API_KEY={config['OPENAI_API_KEY']}")

    lines.extend([
        "",
        "# Google Gemini (for image generation)",
    ])
    if "GEMINI_API_KEY" in config:
        lines.append(f"GEMINI_API_KEY={config['GEMINI_API_KEY']}")

    lines.extend([
        "",
        "# Google Cloud (for VEO video generation)",
    ])
    gcp_keys = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "SIP_GCS_BUCKET_NAME",
        "GOOGLE_GENAI_USE_VERTEXAI",
    ]
    for key in gcp_keys:
        if key in config:
            lines.append(f"{key}={config[key]}")

    # Add Kling keys if present
    if config.get("KLING_ACCESS_KEY") or config.get("KLING_SECRET_KEY"):
        lines.extend([
            "",
            "# Kling AI (optional, alternative video generation)",
        ])
        if config.get("KLING_ACCESS_KEY"):
            lines.append(f"KLING_ACCESS_KEY={config['KLING_ACCESS_KEY']}")
        if config.get("KLING_SECRET_KEY"):
            lines.append(f"KLING_SECRET_KEY={config['KLING_SECRET_KEY']}")

    lines.extend([
        "",
        "# Application settings",
    ])
    app_keys = [
        "SIP_OUTPUT_DIR",
        "SIP_DEFAULT_SCENES",
        "SIP_VIDEO_DURATION",
        "SIP_ENABLE_BACKGROUND_MUSIC",
        "SIP_MUSIC_VOLUME",
    ]
    for key in app_keys:
        if key in config:
            lines.append(f"{key}={config[key]}")

    content = "\n".join(lines) + "\n"
    CONFIG_FILE.write_text(content)


def load_config() -> dict[str, str]:
    """Load config from ~/.sip-videogen/.env.

    Returns:
        Dictionary of config values
    """
    if not CONFIG_FILE.exists():
        return {}

    return parse_env_block(CONFIG_FILE.read_text())


def run_setup_wizard(reset: bool = False) -> bool:
    """Run the interactive setup wizard.

    Args:
        reset: If True, allows replacing existing config

    Returns:
        True if setup completed successfully
    """
    console.print()
    console.print(Panel(
        "[bold cyan]SIP VideoGen Setup[/bold cyan]\n\n"
        "Let's configure your environment. You can either:\n"
        "  [bold]1.[/bold] Paste your entire config block (recommended)\n"
        "  [bold]2.[/bold] Enter each key individually",
        border_style="cyan",
    ))

    # Check if config exists
    existing_config = load_config()
    if existing_config and not reset:
        console.print("\n[yellow]Existing configuration found.[/yellow]")
        missing, _ = validate_config(existing_config)
        if not missing:
            console.print("[green]All required keys are set.[/green]")
            modify = questionary.confirm(
                "Do you want to modify the configuration?",
                default=False,
            ).ask()
            if not modify:
                return True

    # Ask for input method
    console.print()
    method = questionary.select(
        "How would you like to enter your configuration?",
        choices=[
            questionary.Choice(
                title="Paste config block (paste all keys at once)",
                value="paste",
            ),
            questionary.Choice(
                title="Enter keys individually",
                value="individual",
            ),
            questionary.Choice(
                title="Cancel",
                value="cancel",
            ),
        ],
        style=questionary.Style([
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ]),
    ).ask()

    if method == "cancel" or method is None:
        console.print("[yellow]Setup cancelled.[/yellow]")
        return False

    config = dict(existing_config) if existing_config else {}

    if method == "paste":
        config = _setup_via_paste(config)
    else:
        config = _setup_via_individual(config)

    if not config:
        return False

    # Add defaults for missing optional keys
    for key, default in DEFAULTS.items():
        if key not in config:
            config[key] = default

    # Validate
    missing, warnings = validate_config(config)

    if warnings:
        for warning in warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")

    if missing:
        console.print(f"\n[yellow]Missing required keys:[/yellow] {', '.join(missing)}")
        proceed = questionary.confirm(
            "Save anyway? (You can add missing keys later with 'sipvid config')",
            default=True,
        ).ask()
        if not proceed:
            return False

    # Save
    save_config(config)
    console.print(f"\n[green]Configuration saved to:[/green] {CONFIG_FILE}")

    # Show summary
    _display_config_summary(config)

    return True


def _setup_via_paste(existing_config: dict[str, str]) -> dict[str, str] | None:
    """Setup by pasting a block of env vars.

    Args:
        existing_config: Existing config to merge with

    Returns:
        Merged config dict or None if cancelled
    """
    console.print()
    console.print(Panel(
        "[bold]Paste your configuration below[/bold]\n\n"
        "Paste the entire config block, then press [bold]Enter twice[/bold] to finish.\n"
        "Supported formats: KEY=value, KEY=\"value\", export KEY=value",
        border_style="blue",
    ))

    # Collect multi-line input
    lines = []
    console.print("[dim]Paste config (Enter twice when done):[/dim]")

    empty_count = 0
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append(line)
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return None

    text = "\n".join(lines)
    parsed = parse_env_block(text)

    if not parsed:
        console.print("[yellow]No valid configuration found in pasted text.[/yellow]")
        return None

    # Merge with existing
    config = dict(existing_config)
    config.update(parsed)

    console.print(f"\n[green]Found {len(parsed)} configuration values[/green]")

    # Show what was parsed
    table = Table(show_header=True, header_style="bold")
    table.add_column("Key", style="cyan")
    table.add_column("Status")

    for key in list(REQUIRED_KEYS.keys()) + list(OPTIONAL_KEYS.keys()):
        if key in parsed:
            # Mask sensitive values
            value = parsed[key]
            if "KEY" in key or "SECRET" in key:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value[:30] + "..." if len(value) > 30 else value
            table.add_row(key, f"[green]Set[/green] ({display_value})")
        elif key in config:
            table.add_row(key, "[dim]Existing[/dim]")
        elif key in REQUIRED_KEYS:
            table.add_row(key, "[red]Missing (required)[/red]")

    console.print(table)

    return config


def _setup_via_individual(existing_config: dict[str, str]) -> dict[str, str] | None:
    """Setup by entering each key individually.

    Args:
        existing_config: Existing config to merge with

    Returns:
        Config dict or None if cancelled
    """
    config = dict(existing_config)

    console.print()
    console.print("[bold]Enter your configuration values[/bold]")
    console.print("[dim]Press Enter to keep existing value, or enter new value[/dim]")
    console.print()

    # Required keys
    console.print("[bold cyan]Required Keys:[/bold cyan]")
    for key, info in REQUIRED_KEYS.items():
        existing = config.get(key, "")
        existing_display = ""
        if existing:
            if "KEY" in key or "SECRET" in key:
                existing_display = existing[:8] + "..." if len(existing) > 8 else "***"
            else:
                existing_display = existing

        prompt = f"{key}"
        if existing_display:
            prompt += f" [{existing_display}]"

        console.print(f"  [dim]{info['description']}[/dim]")
        console.print(f"  [dim]{info['hint']}[/dim]")

        try:
            value = questionary.text(
                prompt,
                default="",
            ).ask()
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return None

        if value is None:
            return None
        if value:
            config[key] = value
        console.print()

    # Ask about optional keys
    configure_optional = questionary.confirm(
        "Configure optional keys (Kling API, etc.)?",
        default=False,
    ).ask()

    if configure_optional:
        console.print()
        console.print("[bold cyan]Optional Keys:[/bold cyan]")
        for key, info in OPTIONAL_KEYS.items():
            existing = config.get(key, info.get("placeholder", ""))

            console.print(f"  [dim]{info['description']}[/dim]")
            console.print(f"  [dim]{info['hint']}[/dim]")

            try:
                value = questionary.text(
                    key,
                    default=existing,
                ).ask()
            except KeyboardInterrupt:
                break

            if value:
                config[key] = value
            console.print()

    return config


def _display_config_summary(config: dict[str, str]) -> None:
    """Display a summary of the configuration."""
    console.print()
    console.print("[bold]Configuration Summary:[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Status")

    missing, _ = validate_config(config)

    for key in REQUIRED_KEYS:
        if key in missing:
            table.add_row(key, "[red]Not set[/red]")
        else:
            table.add_row(key, "[green]Set[/green]")

    # Optional keys
    if config.get("KLING_ACCESS_KEY") and config.get("KLING_SECRET_KEY"):
        table.add_row("Kling API", "[green]Configured[/green]")
    else:
        table.add_row("Kling API", "[dim]Not configured[/dim]")

    console.print(table)


def edit_single_key(key: str, value: str) -> bool:
    """Edit a single configuration key.

    Args:
        key: The key to edit
        value: The new value

    Returns:
        True if saved successfully
    """
    config = load_config()
    config[key] = value
    save_config(config)
    return True


def show_current_config() -> None:
    """Display the current configuration."""
    config = load_config()

    if not config:
        console.print("[yellow]No configuration found.[/yellow]")
        console.print("Run [bold]sipvid config[/bold] to set up.")
        return

    console.print(Panel(
        f"[bold]Configuration Location:[/bold] {CONFIG_FILE}",
        border_style="blue",
    ))

    _display_config_summary(config)


def ensure_configured() -> bool:
    """Ensure the app is configured, running setup if needed.

    Returns:
        True if configured, False if user cancelled setup
    """
    if is_first_run():
        console.print()
        console.print(Panel(
            "[bold yellow]Welcome to SIP VideoGen![/bold yellow]\n\n"
            "No configuration found. Let's set up your environment.",
            border_style="yellow",
        ))
        return run_setup_wizard()

    # Check if required keys are set
    config = load_config()
    missing, _ = validate_config(config)

    if missing:
        console.print()
        console.print(Panel(
            f"[bold yellow]Missing configuration[/bold yellow]\n\n"
            f"Required keys not set: {', '.join(missing)}\n"
            "Run setup to configure.",
            border_style="yellow",
        ))
        return run_setup_wizard()

    return True


def load_env_to_os() -> None:
    """Load config from ~/.sip-videogen/.env into os.environ.

    This should be called before any modules that read from os.environ.
    """
    config = load_config()
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value
