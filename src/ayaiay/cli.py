"""Command-line interface for AyAiAy."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ayaiay import __version__
from ayaiay.client import AyAiAyClient, AyAiAyError
from ayaiay.config import Config
from ayaiay.installer import Installer, PackReference
from ayaiay.validator import validate_manifest

console = Console()
error_console = Console(stderr=True)


def print_error(message: str) -> None:
    """Print an error message."""
    error_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


@click.group()
@click.version_option(version=__version__, prog_name="ayaiay")
@click.option(
    "--api-url",
    envvar="AYAIAY_API_URL",
    help="API base URL (default: https://api.ayaiay.org)",
)
@click.pass_context
def main(ctx: click.Context, api_url: str | None) -> None:
    """AyAiAy CLI - Marketplace for AI Agent Profiles, Instructions, and Prompts.

    Discover, install, and manage AI packs from the AyAiAy marketplace.
    """
    ctx.ensure_object(dict)
    config = Config.load()
    if api_url:
        config.api_base_url = api_url
    ctx.obj["config"] = config


@main.command()
@click.argument("query", required=False)
@click.option("--type", "-t", "pack_type", type=click.Choice(["agent", "instruction", "prompt"]))
@click.option("--tag", "-g", "tags", multiple=True, help="Filter by tag")
@click.option("--limit", "-l", default=20, help="Number of results")
@click.option("--page", "-p", default=1, help="Page number")
@click.pass_context
def search(
    ctx: click.Context,
    query: str | None,
    pack_type: str | None,
    tags: tuple[str, ...],
    limit: int,
    page: int,
) -> None:
    """Search for packs in the marketplace.

    Examples:
        ayaiay search "code review"
        ayaiay search --type agent
        ayaiay search --tag python --tag testing
    """
    config: Config = ctx.obj["config"]

    with AyAiAyClient(config=config) as client:
        try:
            result = client.search_packs(
                query=query,
                pack_type=pack_type,
                tags=list(tags) if tags else None,
                page=page,
                per_page=limit,
            )
        except AyAiAyError as e:
            print_error(str(e))
            sys.exit(1)

    if not result.packs:
        console.print("[dim]No packs found.[/dim]")
        return

    table = Table(title=f"Search Results ({result.total} total)")
    table.add_column("Pack", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Description")
    table.add_column("Downloads", justify="right")

    for pack in result.packs:
        table.add_row(
            pack.full_name,
            pack.pack_type.value,
            pack.latest_version or "-",
            (pack.description or "")[:50] + "..." if pack.description and len(pack.description) > 50 else pack.description or "-",
            str(pack.downloads),
        )

    console.print(table)

    if result.has_more:
        console.print(f"\n[dim]Showing page {result.page}. Use --page {result.page + 1} for more.[/dim]")


@main.command()
@click.argument("reference")
@click.option("--force", "-f", is_flag=True, help="Force reinstall if already installed")
@click.pass_context
def install(ctx: click.Context, reference: str, force: bool) -> None:
    """Install a pack from the marketplace.

    REFERENCE format: publisher/pack-name[@version]

    Examples:
        ayaiay install acme/code-reviewer
        ayaiay install acme/code-reviewer@1.0.0
        ayaiay install acme/code-reviewer@latest
    """
    config: Config = ctx.obj["config"]
    installer = Installer(config=config)

    console.print(f"[dim]Installing {reference}...[/dim]")

    result = installer.install(reference, force=force)

    if result.success:
        print_success(result.message)
        if result.install_path:
            console.print(f"[dim]Location: {result.install_path}[/dim]")
    else:
        print_error(result.message)
        sys.exit(1)


@main.command()
@click.argument("reference")
@click.pass_context
def uninstall(ctx: click.Context, reference: str) -> None:
    """Uninstall a pack.

    REFERENCE format: publisher/pack-name

    Examples:
        ayaiay uninstall acme/code-reviewer
    """
    config: Config = ctx.obj["config"]
    installer = Installer(config=config)

    result = installer.uninstall(reference)

    if result.success:
        print_success(result.message)
    else:
        print_error(result.message)
        sys.exit(1)


@main.command("list")
@click.pass_context
def list_packs(ctx: click.Context) -> None:
    """List installed packs."""
    config: Config = ctx.obj["config"]
    installer = Installer(config=config)

    installed = installer.list_installed()

    if not installed:
        console.print("[dim]No packs installed.[/dim]")
        return

    table = Table(title="Installed Packs")
    table.add_column("Pack", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Location", style="dim")

    for full_name, version, path in installed:
        table.add_row(full_name, version, str(path))

    console.print(table)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--quiet", "-q", is_flag=True, help="Only output errors")
def validate(path: Path, quiet: bool) -> None:
    """Validate an ayaiay.yaml manifest file.

    Examples:
        ayaiay validate ayaiay.yaml
        ayaiay validate ./my-pack/ayaiay.yaml
    """
    result = validate_manifest(path)

    if result.is_valid:
        if not quiet:
            print_success(f"Manifest is valid: {path}")

            if result.manifest:
                info = Text()
                info.append("Name: ", style="dim")
                info.append(f"{result.manifest.name}\n", style="cyan")

                if result.manifest.description:
                    info.append("Description: ", style="dim")
                    info.append(f"{result.manifest.description}\n")

                counts = []
                if result.manifest.agents:
                    counts.append(f"{len(result.manifest.agents)} agents")
                if result.manifest.instructions:
                    counts.append(f"{len(result.manifest.instructions)} instructions")
                if result.manifest.prompts:
                    counts.append(f"{len(result.manifest.prompts)} prompts")

                if counts:
                    info.append("Contents: ", style="dim")
                    info.append(", ".join(counts))

                console.print(Panel(info, title="Manifest Info", border_style="green"))

        for warning in result.warnings:
            print_warning(warning)
    else:
        print_error(f"Manifest validation failed: {path}")
        for error in result.errors:
            console.print(f"  [red]•[/red] {error}")
        sys.exit(1)


@main.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show CLI configuration and status."""
    config: Config = ctx.obj["config"]

    table = Table(title="AyAiAy CLI Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("API URL", config.api_base_url)
    table.add_row("Registry URL", config.registry_url)
    table.add_row("Install Directory", str(config.install_dir))
    table.add_row("Cache Directory", str(config.cache_dir))
    table.add_row("Timeout", f"{config.timeout}s")
    table.add_row("Authenticated", "Yes" if config.token else "No")

    console.print(table)

    # Check API health
    with AyAiAyClient(config=config) as client:
        healthy = client.health_check()
        status = "[green]Connected[/green]" if healthy else "[red]Unreachable[/red]"
        console.print(f"\nAPI Status: {status}")


@main.command()
@click.argument("reference")
@click.pass_context
def show(ctx: click.Context, reference: str) -> None:
    """Show details for a specific pack.

    REFERENCE format: publisher/pack-name

    Examples:
        ayaiay show acme/code-reviewer
    """
    config: Config = ctx.obj["config"]

    try:
        pack_ref = PackReference.parse(reference)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)

    with AyAiAyClient(config=config) as client:
        try:
            pack = client.get_pack(pack_ref.full_name)
            versions = client.get_pack_versions(pack_ref.full_name)
        except AyAiAyError as e:
            print_error(str(e))
            sys.exit(1)

    # Pack info panel
    info = Text()
    info.append("Name: ", style="dim")
    info.append(f"{pack.full_name}\n", style="cyan bold")
    info.append("Type: ", style="dim")
    info.append(f"{pack.pack_type.value}\n", style="magenta")

    if pack.description:
        info.append("Description: ", style="dim")
        info.append(f"{pack.description}\n")

    info.append("Latest Version: ", style="dim")
    info.append(f"{pack.latest_version or 'N/A'}\n", style="green")

    info.append("Downloads: ", style="dim")
    info.append(f"{pack.downloads}\n")

    if pack.tags:
        info.append("Tags: ", style="dim")
        info.append(", ".join(pack.tags) + "\n")

    if pack.repository_url:
        info.append("Repository: ", style="dim")
        info.append(f"{pack.repository_url}\n", style="blue underline")

    console.print(Panel(info, title="Pack Details", border_style="cyan"))

    # Versions table
    if versions:
        version_table = Table(title="Available Versions")
        version_table.add_column("Version", style="green")
        version_table.add_column("Published", style="dim")
        version_table.add_column("Downloads", justify="right")

        for v in versions[:10]:  # Show latest 10
            published = v.published_at.strftime("%Y-%m-%d") if v.published_at else "-"
            version_table.add_row(v.version, published, str(v.downloads))

        console.print(version_table)

        if len(versions) > 10:
            console.print(f"[dim]... and {len(versions) - 10} more versions[/dim]")


if __name__ == "__main__":
    main()
