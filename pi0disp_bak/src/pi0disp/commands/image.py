#
# (c) 2025 Yoichi Tanibayashi
#
"""Display image command."""
import time
import click
from PIL import Image

from ..disp.st7789v import ST7789V
from ..utils.image_processor import ImageProcessor

@click.command()
@click.argument('image_path', type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--duration', '-d', type=float, default=3.0, help='Duration to display each image in seconds.')
def image(image_path, duration):
    """Displays an image with optional gamma correction.

    IMAGE_PATH: Path to the image file to display.
    """
    try:
        source_image = Image.open(image_path)
    except FileNotFoundError:
        print(f"Error: Image file '{image_path}' not found.")
        exit(1)
    except Exception as e:
        print(f"Error opening image '{image_path}': {e}")
        exit(1)

    processor = ImageProcessor()

    try:
        with ST7789V() as lcd:
            print("Displaying original image resized to screen (contain mode)...")

            # Resize while maintaining aspect ratio
            resized_image = processor.resize_with_aspect_ratio(
                source_image, lcd.width, lcd.height, fit_mode="contain"
            )
            lcd.display(resized_image)
            time.sleep(duration)

            for gamma in (1.0, 1.5, 1.0, 0.5, 1.0):
                print(f"Applying gamma={gamma}")
                corrected_image = processor.apply_gamma(resized_image, gamma=gamma)
                lcd.display(corrected_image)
                time.sleep(duration)

    except RuntimeError as e:
        print(f"Error: {e}. Make sure pigpio daemon is running and SPI is enabled.")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during display processing: {e}")
        exit(1)
    finally:
        print("Image display finished.")
