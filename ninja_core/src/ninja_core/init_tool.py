"""Interactive first-run setup tool for NinjaRobotV5."""

from __future__ import annotations

import json

import click

from .config import (
    build_robot_profile,
    get_robot_type_options,
    import_and_update_config,
    load_config,
    set_api_key,
    set_robot_name,
    set_robot_type,
)
from .ngrok_config import has_ngrok_auth_token, set_ngrok_auth_token


MENU_OPTIONS = (
    ("1", "Set Gemini API Key"),
    ("2", "Set ngrok Token"),
    ("3", "Rename the Ninja Robot"),
    ("4", "Select NinjaRobot Type"),
    ("5", "Import All Hardware Configuration"),
    ("6", "Show Existing Hardware Configuration"),
    ("7", "Start NinjaRobot Server"),
    ("8", "Exit"),
)


def _print_menu():
    click.echo()
    click.echo("=== NinjaRobotV5 Initialization Tool ===")
    click.echo("Use this tool to configure the robot before connecting Code IDE.")
    click.echo("Hardware display/edit steps do not move servos or start motors.")
    click.echo()
    for value, label in MENU_OPTIONS:
        click.echo(f"{value}. {label}")


def _prompt_menu_choice() -> str:
    valid_choices = [value for value, _ in MENU_OPTIONS]
    return click.prompt(
        "Select an option",
        type=click.Choice(valid_choices),
        show_choices=False,
    )


def _set_gemini_api_key():
    key = click.prompt("Gemini API key", hide_input=True).strip()
    if not key:
        click.echo("Gemini API key was not changed.")
        return
    set_api_key("gemini", key)


def _set_ngrok_token():
    if has_ngrok_auth_token():
        click.echo("Existing ngrok token found.")
    token = click.prompt("ngrok token", hide_input=True).strip()
    if set_ngrok_auth_token(token):
        click.echo("ngrok token saved.")
    else:
        click.echo("ngrok token was not changed.")


def _rename_robot():
    name = click.prompt("New NinjaRobot name").strip()
    set_robot_name(name)


def _select_robot_type():
    click.echo("Supported NinjaRobot types:")
    options = get_robot_type_options()
    for index, (_, label) in enumerate(options, start=1):
        click.echo(f"{index}. {label}")

    choice = click.prompt(
        "Select robot type",
        type=click.Choice([str(index) for index in range(1, len(options) + 1)]),
        show_choices=False,
    )
    robot_type, _ = options[int(choice) - 1]
    set_robot_type(robot_type)


def _import_hardware_configuration():
    click.echo("Importing servo, buzzer, and display configuration.")
    click.echo("This reads config files only; it does not move servos.")
    import_and_update_config()


def _show_hardware_configuration():
    profile = build_robot_profile(load_config())
    click.echo(json.dumps(profile, indent=2, sort_keys=True))


def _start_server():
    click.echo("Starting NinjaRobot server. This initializes robot hardware.")
    from .web_server import run_server

    run_server(autostart=False)


def run_init_tool():
    """Run the interactive initialization menu until the user exits."""
    handlers = {
        "1": _set_gemini_api_key,
        "2": _set_ngrok_token,
        "3": _rename_robot,
        "4": _select_robot_type,
        "5": _import_hardware_configuration,
        "6": _show_hardware_configuration,
        "7": _start_server,
    }

    while True:
        _print_menu()
        choice = _prompt_menu_choice()
        if choice == "8":
            click.echo("Exiting NinjaRobotV5 initialization tool.")
            return

        try:
            handlers[choice]()
        except (OSError, ValueError) as exc:
            click.echo(f"Error: {exc}", err=True)


__all__ = ["run_init_tool"]
