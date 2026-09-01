"""Interactive first-run setup tool for NinjaRobotV5."""

from __future__ import annotations

import json
from pathlib import Path

import click

from .config import (
    CONFIG_FILE_PATH,
    build_robot_profile,
    get_robot_type_options,
    import_and_update_config,
    load_config,
    set_gemini_configuration,
    set_robot_name,
    set_robot_type,
)
from .gemini_models import GeminiModelDiscoveryError, list_available_gemini_models
from .gemini_runtime import GeminiRuntimeError, validate_gemini_model
from .ngrok_config import has_ngrok_auth_token, set_ngrok_auth_token


MENU_OPTIONS = (
    ("1", "Set Gemini API Key and Model"),
    ("2", "Set ngrok Token"),
    ("3", "Rename the Ninja Robot"),
    ("4", "Select NinjaRobot Type"),
    ("5", "Import All Hardware Configuration"),
    ("6", "Show Existing Hardware Configuration"),
    ("7", "Start NinjaRobot Server"),
    ("8", "Exit"),
)


def configure_gemini_api_key(
    api_key: str,
    *,
    path: Path = CONFIG_FILE_PATH,
) -> str:
    """Discover, select, and persist a Gemini model for the supplied API key."""
    normalized_key = api_key.strip()
    if not normalized_key:
        raise ValueError("Gemini API key cannot be empty.")

    click.echo("Retrieving available Gemini models from Google...")
    models = list_available_gemini_models(normalized_key)
    current_model = load_config(path).gemini.model if path.exists() else None

    click.echo("Available Gemini models for NinjaRobot agent operations:")
    for index, model in enumerate(models, start=1):
        current_marker = " [current]" if model.model_id == current_model else ""
        click.echo(
            f"{index}. {model.display_name} ({model.model_id}){current_marker}"
        )
        if model.description:
            description = model.description
            if len(description) > 160:
                description = f"{description[:157]}..."
            click.echo(f"   {description}")

    choice = click.prompt(
        "Select a Gemini model",
        type=click.Choice([str(index) for index in range(1, len(models) + 1)]),
        show_choices=False,
    )
    selected = models[int(choice) - 1]
    click.echo(
        f"Validating Gemini model '{selected.model_id}' (this can take up to 60 seconds)..."
    )
    validate_gemini_model(normalized_key, selected.model_id)
    return set_gemini_configuration(normalized_key, selected.model_id, path=path)


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
    configure_gemini_api_key(key)


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
        except (
            GeminiModelDiscoveryError,
            GeminiRuntimeError,
            OSError,
            ValueError,
        ) as exc:
            click.echo(f"Error: {exc}", err=True)


__all__ = ["configure_gemini_api_key", "run_init_tool"]
