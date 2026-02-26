"""
pi0buzzer CLI — Command-line interface for standalone buzzer control.

Provides individual commands for scripting as well as an interactive
``buzzer-tool`` TUI for guided testing and configuration.

Usage::

    uv run pi0buzzer init 17
    uv run pi0buzzer beep 440 0.5
    uv run pi0buzzer play happy
    uv run pi0buzzer info --health-check
    uv run pi0buzzer buzzer-tool
"""

import json
import time

import click

from pi0buzzer.config.config_manager import BuzzerConfigManager
from pi0buzzer.notes import get_emotion_names


# -------------------------------------------------------------------
# Shared helpers
# -------------------------------------------------------------------


def _connect_pigpio():
    """Connect to pigpio daemon.

    Returns:
        pigpio.pi instance.

    Raises:
        click.ClickException: If pigpio is unavailable or daemon not running.
    """
    try:
        import pigpio
    except ImportError:
        raise click.ClickException(
            "pigpio is not installed. Install with:\n"
            "  Standalone: uv sync --extra pi\n"
            "  NinjaRobotV5: uv sync  (pigpio is a main dependency)\n"
            "  Manual: pip install pigpio"
        )

    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException(
            "Cannot connect to pigpiod. Start it with: sudo pigpiod"
        )
    return pi


def _create_buzzer(pi, config_path=None):
    """Create and initialize a MusicBuzzer from config.

    Args:
        pi: pigpio.pi instance.
        config_path: Optional path to buzzer.json.

    Returns:
        Initialized MusicBuzzer instance.
    """
    from pi0buzzer.core.music import MusicBuzzer

    cm = BuzzerConfigManager(config_path)
    cm.load()
    pin = cm.get_pin()
    volume = cm.get_volume()

    buzzer = MusicBuzzer(pin=pin, pi=pi, volume=volume)
    buzzer.initialize()
    return buzzer


# -------------------------------------------------------------------
# CLI group
# -------------------------------------------------------------------


@click.group(
    invoke_without_command=True,
    help="pi0buzzer — Passive buzzer driver for Raspberry Pi.",
)
@click.pass_context
@click.option(
    "--config-file", "-C",
    type=str, default=None,
    help="Path to config file (default: buzzer.json).",
)
def cli(ctx, config_file):
    """pi0buzzer CLI tool."""
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# -------------------------------------------------------------------
# init command
# -------------------------------------------------------------------


@cli.command()
@click.argument("pin", type=int)
@click.pass_context
def init(ctx, pin):
    """Initialize buzzer config with the given GPIO pin.

    Saves configuration to buzzer.json and plays a test beep.

    Example: uv run pi0buzzer init 17
    """
    cm = BuzzerConfigManager(ctx.obj.get("config_file"))

    try:
        cm.init_config(pin)
        click.echo(f"✓ Buzzer config saved to {cm.path}")
        click.echo(f"  Pin: GPIO {pin}")
    except ValueError as e:
        raise click.ClickException(str(e))

    # Test beep
    try:
        pi = _connect_pigpio()
        from pi0buzzer.core.driver import Buzzer

        buzzer = Buzzer(pin=pin, pi=pi)
        buzzer.initialize()
        click.echo("  Playing test beep...")
        buzzer.play_sound(440, 0.3)
        time.sleep(0.5)
        buzzer.off()
        pi.stop()
        click.echo("✓ Test beep successful!")
    except click.ClickException:
        click.echo("⚠ Could not test beep (pigpiod not running?).")
    except Exception as e:
        click.echo(f"⚠ Test beep failed: {e}")


# -------------------------------------------------------------------
# beep command
# -------------------------------------------------------------------


@cli.command()
@click.argument("frequency", type=float, default=440.0)
@click.argument("duration", type=float, default=0.5)
@click.pass_context
def beep(ctx, frequency, duration):
    """Play a single tone.

    Example: uv run pi0buzzer beep 440 0.5
    """
    pi = _connect_pigpio()
    try:
        buzzer = _create_buzzer(pi, ctx.obj.get("config_file"))
        click.echo(f"Playing {frequency} Hz for {duration}s...")
        buzzer.play_sound(int(frequency), duration)
        time.sleep(duration + 0.1)
        buzzer.off()
    finally:
        pi.stop()


# -------------------------------------------------------------------
# play command
# -------------------------------------------------------------------


@cli.command()
@click.argument("emotion", type=str)
@click.pass_context
def play(ctx, emotion):
    """Play a predefined emotion sound.

    Available emotions: happy, sad, exciting, angry, confusing, cry,
    embarrassing, idle, laughing, scary, shy, sleepy, speaking, surprising

    Example: uv run pi0buzzer play happy
    """
    emotions = get_emotion_names()
    if emotion not in emotions:
        raise click.ClickException(
            f"Unknown emotion: '{emotion}'. "
            f"Available: {', '.join(emotions)}"
        )

    pi = _connect_pigpio()
    try:
        buzzer = _create_buzzer(pi, ctx.obj.get("config_file"))
        click.echo(f"Playing emotion: {emotion}")
        buzzer.play_emotion(emotion)
        # Wait for playback to complete
        time.sleep(2.0)
        buzzer.off()
    finally:
        pi.stop()


# -------------------------------------------------------------------
# info command
# -------------------------------------------------------------------


@cli.command()
@click.option(
    "--health-check", is_flag=True,
    help="Verify hardware connectivity.",
)
@click.pass_context
def info(ctx, health_check):
    """Show buzzer configuration and status.

    Example: uv run pi0buzzer info --health-check
    """
    cm = BuzzerConfigManager(ctx.obj.get("config_file"))
    cfg = cm.load()

    click.echo("pi0buzzer Status Report")
    click.echo(f"  Config file: {cm.path}")
    click.echo(f"  Pin:         GPIO {cfg.get('pin', 'N/A')}")
    click.echo(f"  Volume:      {cfg.get('volume', 'N/A')}/255")

    if health_check:
        click.echo("\nHealth Check:")
        try:
            pi = _connect_pigpio()
            click.echo("  ✓ pigpiod connection: OK")

            from pi0buzzer.core.driver import Buzzer

            buzzer = Buzzer(pin=cfg["pin"], pi=pi)
            buzzer.initialize()
            click.echo(f"  ✓ GPIO {cfg['pin']} mode set: OK")

            # Quick beep test
            buzzer.play_sound(440, 0.2)
            time.sleep(0.4)
            buzzer.off()
            click.echo("  ✓ Test beep: OK")

            pi.stop()
            click.echo("\n  Result: All checks passed ✓")
        except click.ClickException as e:
            click.echo(f"  ✗ {e.message}")
        except Exception as e:
            click.echo(f"  ✗ Health check failed: {e}")


# -------------------------------------------------------------------
# config subgroup
# -------------------------------------------------------------------


@cli.group()
def config():
    """Configuration management (show/export/import)."""


@config.command("show")
@click.pass_context
def config_show(ctx):
    """Show current buzzer configuration."""
    cm = BuzzerConfigManager(ctx.obj.get("config_file"))
    cfg = cm.load()
    click.echo(json.dumps(cfg, indent=2))
    click.echo(f"\nConfig file: {cm.path}")


@config.command("export")
@click.argument("path")
@click.pass_context
def config_export(ctx, path):
    """Export configuration to a file."""
    cm = BuzzerConfigManager(ctx.obj.get("config_file"))
    cm.load()
    cm.export_config(path)
    click.echo(f"✓ Config exported to {path}")


@config.command("import")
@click.argument("path")
@click.pass_context
def config_import(ctx, path):
    """Import configuration from a file."""
    cm = BuzzerConfigManager(ctx.obj.get("config_file"))
    try:
        cm.import_config(path)
        cm.save()
        click.echo(f"✓ Config imported from {path}")
    except FileNotFoundError:
        raise click.ClickException(f"File not found: {path}")


# -------------------------------------------------------------------
# buzzer-tool (interactive TUI)
# -------------------------------------------------------------------


@cli.command("buzzer-tool")
@click.pass_context
def buzzer_tool_cmd(ctx):
    """Launch the interactive buzzer tool (TUI)."""
    from pi0buzzer.cli.buzzer_tool import buzzer_tool

    buzzer_tool(ctx.obj.get("config_file"))


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------


if __name__ == "__main__":
    cli()
