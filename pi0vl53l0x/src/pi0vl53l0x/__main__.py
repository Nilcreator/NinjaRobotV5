"""Entry point for `python -m pi0vl53l0x` and `pi0vl53l0x` command."""

from pi0vl53l0x.cli.sensor_tool import cli, main
from pi0vl53l0x.cli.vl53l0x_tool import vl53l0x_tool

cli.add_command(vl53l0x_tool)

if __name__ == "__main__":
    main()
