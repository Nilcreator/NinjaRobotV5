#
# (c) 2025 Nil
#
"""__main__.py"""
import click
import pigpio

from .command import cmd_calib, cmd_servo
from ninja_utils.my_logger import get_logger


@click.group(help="A command-line tool for controlling servo motors.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx, debug):
    """Main CLI group."""
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["PI"] = pigpio.pi()
    log = get_logger(__name__, debug)
    
    if not ctx.obj["PI"].connected:
        log.error("pigpio daemon not connected. Please run 'sudo pigpiod'.")
        raise click.Abort()

@cli.result_callback()
@click.pass_context
def cleanup(ctx, result, *args, **kwargs):
    """Cleanup resources."""
    log = get_logger(__name__, ctx.obj["DEBUG"])
    log.debug("Cleaning up pigpio connection.")
    if "PI" in ctx.obj and ctx.obj["PI"].connected:
        ctx.obj["PI"].stop()

# Add commands from other modules
cli.add_command(cmd_calib.main, "calib")
cli.add_command(cmd_servo.main, "servo")

if __name__ == "__main__":
    cli()
