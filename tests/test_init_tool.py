from __future__ import annotations

from click.testing import CliRunner

from ninja_core.__main__ import main
from ninja_core.config import load_config


def test_init_tool_exits_cleanly():
    runner = CliRunner()

    result = runner.invoke(main, ["init-tool"], input="8\n")

    assert result.exit_code == 0
    assert "Initialization Tool" in result.output
    assert "Exiting NinjaRobotV5 initialization tool." in result.output


def test_init_tool_selects_robot_type():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init-tool"], input="4\n2\n8\n")

        assert result.exit_code == 0
        assert load_config().robot_type == "humanoid"


def test_init_tool_shows_sanitized_hardware_configuration():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            ["init-tool"],
            input="1\nsuper-secret-key\n6\n8\n",
        )

        assert result.exit_code == 0
        assert "hardware_configuration" in result.output
        assert "super-secret-key" not in result.output
        assert "api_keys" not in result.output
