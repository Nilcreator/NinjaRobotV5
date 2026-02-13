#
# (c) 2025 Yoichi Tanibayashi
#
import time

import click
import pigpio
from pathlib import Path

from ninja_utils.my_logger import get_logger
from .driver import VL53L0X
from .config_manager import get_default_config_filepath, save_config


@click.group(
    invoke_without_command=True,
    help="""
VL53L0X driver CLI
"""
)
@click.pass_context
@click.option(
    "--config-file", "-C", type=str,
    default=str(get_default_config_filepath()), show_default=True,
    help="Path to the configuration file"
)
@click.option("--debug", "-d", is_flag=True, help="debug mode")
def cli(ctx: click.Context, debug: bool, config_file: str) -> None:
    """VL53L0X距離センサーのPythonドライバー用CLIツール。"""
    cmd_name = ctx.info_name
    subcmd_name = ctx.invoked_subcommand

    __log = get_logger(str(cmd_name), debug)

    __log.debug("cmd_name=%a, subcmd_name=%a", cmd_name, subcmd_name)
    
    # Pass config_file to the context object for subcommands
    ctx.obj = {"config_file": Path(config_file), "debug": debug}

    if subcmd_name is None:
        print(f"{ctx.get_help()}")


@cli.command(
    help="""
get distance"""
)
@click.pass_context
@click.option(
    "--count", "-c", type=int, default=10, show_default=True, help="count"
)
@click.option(
    "--interval", "-i", type=float, default=1.0, show_default=True,
    help="interval seconds"
)
def get(
    ctx: click.Context, count: int, interval: float
) -> None:
    """基本的な例を実行します。"""
    debug = ctx.obj["debug"]
    __log = get_logger(__name__, debug)
    __log.debug("count=%s, interval=%s", count, interval)

    cmd_name = ctx.command.name
    __log.debug("cmd_name=%a", cmd_name)
    
    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("cannnto connect pigpiod")

    try:
        try:
            with VL53L0X(pi, debug=debug, config_file_path=ctx.obj["config_file"]) as sensor:
                for i in range(count):
                    distance: int = sensor.get_range()
                    if distance > 0:
                        click.echo(f"{i + 1}/{count}: {distance} mm")
                    else:
                        click.echo(f"{i + 1}/{count}: 無効なデータ。")
                    time.sleep(interval)
        except Exception as e:
            if debug:
                raise
            click.echo(f"Error: {e}")
    finally:
        pi.stop()


@cli.command()
@click.pass_context
@click.option(
    "--count", "-c", type=int, default=100, show_default=True, help="count"
)
def performance(ctx: click.Context, count: int) -> None:
    """VL53L0Xセンサーの測定パフォーマンスを評価します。"""
    debug = ctx.obj["debug"]
    __log = get_logger(__name__, debug)
    __log.debug("count=%s", count)

    cmd_name = ctx.command.name
    __log.debug("cmd_name=%a", cmd_name)
    
    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("cannnto connect pigpiod")

    try:
        try:
            with VL53L0X(pi, debug=debug, config_file_path=ctx.obj["config_file"]) as sensor:
                click.echo(f"{count}回の距離測定パフォーマンスを評価します...")
                start_time = time.perf_counter()
                for _ in range(count):
                    sensor.get_range()
                end_time = time.perf_counter()

                total_time = end_time - start_time
                avg_time_per_measurement = total_time / count
                measurements_per_second = count / total_time

                click.echo("---")
                click.echo(f"合計時間: {total_time:.4f} 秒")
                click.echo(f"1回あたりの平均時間: {avg_time_per_measurement * 1000:.4f} ms")
                click.echo(f"1秒あたりの測定回数: {measurements_per_second:.2f} 回/秒")
                click.echo("---")
        except Exception as e:
            if debug:
                raise
            click.echo(f"Error: {e}")
    finally:
        pi.stop()


@cli.command(help="""calibrate offset and save""" )
@click.pass_context
@click.option(
    "--distance", "-D", type=int, default=100, show_default=True,
    help="distance to target [mm]"
)
@click.option(
    "--count", "-c", type=int, default=10, show_default=True,
    help="count"
)
@click.option(
    "--output-file", "-o", type=str,
    default=str(get_default_config_filepath()), show_default=True,
    help="Path to save the calculated offset"
)
def calibrate(ctx: click.Context, distance: int, count: int, output_file: str) -> None:
    """オフセットをキャリブレーションします。"""
    debug = ctx.obj["debug"]
    __log = get_logger(__name__, debug)
    __log.debug("distance=%s, count=%s, output_file=%s", distance, count, output_file)

    output_file_path = Path(output_file)

    pi = pigpio.pi()
    if not pi.connected:
        raise click.ClickException("cannot connect to pigpiod")

    try:
        try:
            with VL53L0X(
                    pi, debug=debug, config_file_path=ctx.obj["config_file"]
            ) as sensor:
                click.echo(f"{distance}mmの距離にターゲットを置いてください。")
                click.echo("準備ができたらEnterキーを押してください...")
                input()

                offset = sensor.calibrate(distance, count)

                click.echo(f"測定結果から計算されたオフセット値: {offset} mm")
                click.echo("この値を set_offset() に設定して使用してください。")

                # オフセット値をファイルに保存
                config_data = {"offset_mm": offset}
                save_config(output_file_path, config_data)
                click.echo(f"オフセット値を {output_file_path} に保存しました。")
        except Exception as e:
            if debug:
                raise
            click.echo(f"Error: {e}")

    finally:
        pi.stop()
