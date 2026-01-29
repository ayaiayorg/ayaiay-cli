"""Command-line interface for AyAiAy."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ayaiay import __version__
from ayaiay.client import AyAiAyClient, AyAiAyError
from ayaiay.config import Config
from ayaiay.installer import Installer, PackReference
from ayaiay.models import PackVersion
from ayaiay.package_manager import PackageManager
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


def handle_api_connection_error(config: Config, exception: httpx.RequestError) -> None:
    """Handle API connection errors with informative message and exit.

    Args:
        config: Configuration object containing API URL.
        exception: The httpx.RequestError that was raised.
    """
    error_msg = (
        "Unable to connect to the API. This could be due to:\n"
        "  • No internet connection\n"
        "  • API service is not available or unreachable\n"
        f"  • Invalid API URL: {config.api_base_url}\n\n"
        "Try:\n"
        "  • Check your internet connection\n"
        "  • Verify the API URL with 'ayaiay info'\n"
        "  • Set a custom API URL with --api-url or AYAIAY_API_URL\n"
        f"  • See documentation at: https://github.com/ayaiayorg/ayaiay-cli#readme"
    )
    print_error(error_msg)
    sys.exit(1)


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
@click.option(
    "--type", "-t", "pack_type", type=click.Choice(["agent", "instruction", "prompt"])
)
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
        except httpx.RequestError as e:
            handle_api_connection_error(config, e)
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
            pack.pack_type.value if pack.pack_type else "-",
            pack.latest_version or "-",
            (
                (pack.description or "")[:50] + "..."
                if pack.description and len(pack.description) > 50
                else pack.description or "-"
            ),
            str(pack.downloads),
        )

    console.print(table)

    if result.has_more:
        console.print(
            f"\n[dim]Showing page {result.page}. "
            f"Use --page {result.page + 1} for more.[/dim]"
        )


@main.command()
@click.argument("reference")
@click.option(
    "--force", "-f", is_flag=True, help="Force reinstall if already installed"
)
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
        pm = PackageManager(config=config)
        if pm.lock_file_path.exists() and isinstance(result.version, PackVersion):
            updated, message = pm.record_installation(reference, result)
            if updated:
                console.print(f"[dim]{message}[/dim]")
            else:
                print_warning(message)
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
        pm = PackageManager(config=config)
        if pm.lock_file_path.exists():
            updated, message = pm.record_uninstall(reference)
            if updated:
                console.print(f"[dim]{message}[/dim]")
            else:
                print_warning(message)
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
                if result.manifest.skills:
                    counts.append(f"{len(result.manifest.skills)} skills")

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
        except httpx.RequestError as e:
            handle_api_connection_error(config, e)
        except AyAiAyError as e:
            print_error(str(e))
            sys.exit(1)

    # Pack info panel
    info = Text()
    info.append("Name: ", style="dim")
    info.append(f"{pack.full_name}\n", style="cyan bold")
    info.append("Type: ", style="dim")
    info.append(
        f"{pack.pack_type.value if pack.pack_type else 'N/A'}\n",
        style="magenta",
    )

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


@main.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(path_type=Path),
    help="Path to ayaiay.json (default: current directory)",
)
@click.pass_context
def init(ctx: click.Context, path: Path | None) -> None:
    """Initialize a new ayaiay.json file for package management.

    This creates a lock file that tracks all installed packs with their versions,
    similar to composer.json in PHP or package.json in Node.js.

    Example:
        ayaiay init
        ayaiay init --path /path/to/project
    """
    lock_file_path = (path / "ayaiay.json") if path else None
    pm = PackageManager(lock_file_path=lock_file_path)

    if pm.init():
        print_success(f"Created {pm.lock_file_path}")
        console.print(
            "[dim]Use 'ayaiay add <package>' to add packages to your project.[/dim]"
        )
    else:
        print_error(f"Lock file already exists: {pm.lock_file_path}")
        sys.exit(1)


@main.command()
@click.argument("reference")
@click.option(
    "--force", "-f", is_flag=True, help="Force reinstall if already installed"
)
@click.option(
    "--path",
    "-p",
    type=click.Path(path_type=Path),
    help="Path to ayaiay.json directory",
)
@click.pass_context
def add(ctx: click.Context, reference: str, force: bool, path: Path | None) -> None:
    """Add a package to ayaiay.json and install it.

    REFERENCE format: publisher/pack-name[@version]

    The package will be added to ayaiay.json and installed to the local directory.
    This allows you to track all dependencies in one file.

    Examples:
        ayaiay add acme/code-reviewer
        ayaiay add acme/code-reviewer@1.0.0
        ayaiay add acme/code-reviewer --force
    """
    config: Config = ctx.obj["config"]
    lock_file_path = (path / "ayaiay.json") if path else None
    pm = PackageManager(config=config, lock_file_path=lock_file_path)

    console.print(f"[dim]Adding {reference} to {pm.lock_file_path}...[/dim]")

    success, message, result = pm.add_package(reference, force=force)

    if success:
        print_success(message)
        if result.install_path:
            console.print(f"[dim]Location: {result.install_path}[/dim]")
    else:
        print_error(message)
        sys.exit(1)


@main.command()
@click.argument("reference")
@click.option(
    "--path",
    "-p",
    type=click.Path(path_type=Path),
    help="Path to ayaiay.json directory",
)
@click.pass_context
def remove(ctx: click.Context, reference: str, path: Path | None) -> None:
    """Remove a package from ayaiay.json and uninstall it.

    REFERENCE format: publisher/pack-name

    Examples:
        ayaiay remove acme/code-reviewer
    """
    config: Config = ctx.obj["config"]
    lock_file_path = (path / "ayaiay.json") if path else None
    pm = PackageManager(config=config, lock_file_path=lock_file_path)

    success, message = pm.remove_package(reference)

    if success:
        print_success(message)
    else:
        print_error(message)
        sys.exit(1)


@main.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(path_type=Path),
    help="Path to ayaiay.json directory",
)
@click.pass_context
def sync(ctx: click.Context, path: Path | None) -> None:
    """Sync installed packages with ayaiay.json.

    Installs all packages listed in ayaiay.json that aren't currently installed.
    Useful after cloning a project or checking out a different branch.

    Example:
        ayaiay sync
    """
    config: Config = ctx.obj["config"]
    lock_file_path = (path / "ayaiay.json") if path else None
    pm = PackageManager(config=config, lock_file_path=lock_file_path)

    if not pm.lock_file_path.exists():
        print_error(f"No lock file found: {pm.lock_file_path}")
        console.print("[dim]Use 'ayaiay init' to create one.[/dim]")
        sys.exit(1)

    console.print(f"[dim]Syncing packages from {pm.lock_file_path}...[/dim]")
    results = pm.sync()

    if not results:
        console.print("[dim]No packages to sync.[/dim]")
        return

    table = Table(title="Sync Results")
    table.add_column("Package", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")

    for package_name, success, message in results:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(package_name, status, message)

    console.print(table)

    failed = [r for r in results if not r[1]]
    if failed:
        sys.exit(1)


@main.command()
@click.argument("package_name", required=False)
@click.option(
    "--path",
    "-p",
    type=click.Path(path_type=Path),
    help="Path to ayaiay.json directory",
)
@click.pass_context
def update(ctx: click.Context, package_name: str | None, path: Path | None) -> None:
    """Update packages to their latest versions.

    Updates packages listed in ayaiay.json to their latest available versions.
    If no package name is provided, updates all packages.

    Examples:
        ayaiay update                    # Update all packages
        ayaiay update acme/code-reviewer # Update specific package
    """
    config: Config = ctx.obj["config"]
    lock_file_path = (path / "ayaiay.json") if path else None
    pm = PackageManager(config=config, lock_file_path=lock_file_path)

    if not pm.lock_file_path.exists():
        print_error(f"No lock file found: {pm.lock_file_path}")
        console.print("[dim]Use 'ayaiay init' to create one.[/dim]")
        sys.exit(1)

    target = package_name or "all packages"
    console.print(f"[dim]Updating {target}...[/dim]")

    results = pm.update(package_name=package_name)

    if not results:
        console.print("[dim]No packages to update.[/dim]")
        return

    table = Table(title="Update Results")
    table.add_column("Package", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")

    for pkg_name, success, message in results:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(pkg_name, status, message)

    console.print(table)

    failed = [r for r in results if not r[1]]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
