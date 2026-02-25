"""Demo command — Bouncing ball animation demo."""

import random
import time

import click
from PIL import Image, ImageDraw


@click.command()
@click.option("--num-balls", default=3, type=int, help="Number of balls.")
@click.option("--fps", default=30, type=int, help="Target frames per second.")
@click.option("--duration", default=10.0, type=float, help="Duration in seconds.")
def demo(num_balls, fps, duration):
    """Run a bouncing ball animation demo.

    A physics-based demo to verify display performance and SPI throughput.
    """
    try:
        import pigpio

        from ..config.config_manager import ConfigManager
        from ..core.driver import ST7789V

        cm = ConfigManager()
        cfg = cm.load()
        pi = pigpio.pi()
        if not pi.connected:
            click.echo("Error: Could not connect to pigpio daemon.")
            return

        lcd = ST7789V(
            pi=pi,
            dc_pin=cfg.get("dc_pin", 14),
            rst_pin=cfg.get("rst_pin", 15),
            backlight_pin=cfg.get("backlight_pin", 16),
            width=cfg.get("width", 240),
            height=cfg.get("height", 320),
            rotation=cfg.get("rotation", 0),
        )

        click.echo(
            f"Running demo: {num_balls} balls, {fps} FPS, {duration}s "
            f"(Ctrl+C to stop)"
        )

        _run_ball_demo(lcd, num_balls, fps, duration)

        lcd.clear()
        lcd.close()
        click.echo("Demo complete.")
    except ImportError as e:
        click.echo(f"Error: Missing dependency — {e}")
        click.echo("  Hint: Run 'sudo apt install python3-pigpio && sudo pigpiod' on Raspberry Pi.")
    except KeyboardInterrupt:
        click.echo("\nDemo stopped.")
    except Exception as e:
        click.echo(f"Error: {e}")


def _run_ball_demo(lcd, num_balls: int, fps: int, duration: float) -> None:
    """Run the bouncing ball animation loop.

    Args:
        lcd: The display driver.
        num_balls: Number of bouncing balls.
        fps: Target frames per second.
        duration: Animation duration in seconds.
    """
    w, h = lcd.width, lcd.height
    frame_time = 1.0 / fps

    # Initialize balls with random positions, velocities, and colors
    balls = []
    for _ in range(num_balls):
        radius = random.randint(8, 20)
        balls.append({
            "x": random.uniform(radius, w - radius),
            "y": random.uniform(radius, h - radius),
            "vx": random.uniform(-3, 3),
            "vy": random.uniform(-3, 3),
            "radius": radius,
            "color": (
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255),
            ),
        })

    gravity = 0.15
    damping = 0.98
    start_time = time.monotonic()
    frame_count = 0

    while time.monotonic() - start_time < duration:
        frame_start = time.monotonic()

        # Create frame
        image = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Update and draw each ball
        for ball in balls:
            # Apply gravity
            ball["vy"] += gravity

            # Apply damping
            ball["vx"] *= damping
            ball["vy"] *= damping

            # Move
            ball["x"] += ball["vx"]
            ball["y"] += ball["vy"]

            r = ball["radius"]

            # Bounce off walls
            if ball["x"] - r < 0:
                ball["x"] = r
                ball["vx"] = abs(ball["vx"])
            elif ball["x"] + r > w:
                ball["x"] = w - r
                ball["vx"] = -abs(ball["vx"])

            if ball["y"] - r < 0:
                ball["y"] = r
                ball["vy"] = abs(ball["vy"])
            elif ball["y"] + r > h:
                ball["y"] = h - r
                ball["vy"] = -abs(ball["vy"]) * 0.85  # Bounce energy loss

            # Draw ball
            x, y = int(ball["x"]), int(ball["y"])
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=ball["color"],
            )

        lcd.display(image)
        frame_count += 1

        # Frame rate control
        elapsed = time.monotonic() - frame_start
        sleep_time = frame_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Print stats
    total_time = time.monotonic() - start_time
    actual_fps = frame_count / total_time if total_time > 0 else 0
    click.echo(f"  Rendered {frame_count} frames in {total_time:.1f}s ({actual_fps:.1f} FPS)")
