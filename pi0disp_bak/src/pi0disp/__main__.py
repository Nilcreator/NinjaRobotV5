#
# (c) 2025 Yoichi Tanibayashi
#
import click

from .commands.ball_anime import ball_anime
from .commands.image import image

@click.group()
def cli():
    """
    A CLI tool for the ST7789V Display Driver.
    """
    pass

cli.add_command(ball_anime)
cli.add_command(image)


if __name__ == "__main__":
    cli()
