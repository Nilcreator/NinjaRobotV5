import logging
import time
from pathlib import Path
from PIL import Image
from .robot_sound import RobotSoundPlayer

log = logging.getLogger(__name__)

class DistanceWrapper:
    def __init__(self, sensor):
        self._sensor = sensor

    def read(self):
        """Returns distance in cm (standard for education) or mm?
        Blockly usually expects cm. Let's return mm for precision, or check spec.
        Given code: `if robot.distance.read() < 100:` (10cm).
        VL53L0X returns mm. 100mm = 10cm. So mm seems consistent.
        """
        if self._sensor:
            data = self._sensor.get_data()
            return data.get("distance_mm", 9999)
        return 9999

class BuzzerWrapper:
    def __init__(self, hal):
        self._hal = hal
        self._player = RobotSoundPlayer(hal)

    def play(self, sound_name):
        """Play a predefined sound by name."""
        self._player.play(sound_name)

    def tone(self, frequency, duration):
        """Play a specific frequency."""
        if self._hal.buzzer:
            self._hal.buzzer.execute({"frequency": frequency, "duration": duration})

class DisplayWrapper:
    def __init__(self, hal):
        self._hal = hal
        # Define asset lookup or path
        self._search_paths = [
            Path(__file__).parent / "static" / "assets" / "images",
            # Add more paths if needed
        ]

    def image(self, name):
        """Display an image by name (e.g., 'star' -> 'star.png')."""
        if not self._hal.display:
            return

        # Find image file
        image_path = None
        for path in self._search_paths:
            # Try png, jpg
            for ext in [".png", ".jpg", ".bmp"]:
                candidate = path / f"{name}{ext}"
                if candidate.exists():
                    image_path = candidate
                    break
            if image_path:
                break
        
        if image_path:
            try:
                img = Image.open(image_path)
                self._hal.display.execute({"image": img})
            except Exception as e:
                log.error(f"Failed to load/display image {name}: {e}")
        else:
            log.warning(f"Image '{name}' not found in assets.")
            # Optional: Show text or placeholder?

    def clear(self):
        if self._hal.display:
            self._hal.display.execute({"clear": True})

class RobotWrapper:
    """
    High-level wrapper for the Robot HAL.
    Matches the API expected by the Blockly/Web IDE.
    """
    def __init__(self, hal):
        self._hal = hal
        self.buzzer = BuzzerWrapper(hal)
        self.display = DisplayWrapper(hal)
        self.distance = DistanceWrapper(hal.distance_sensor)
        
        # Servos are usually accessed directly or via wrapper
        # Assuming HAL exposes servos directly for now, or we wrap them if needed.
        # Code: `robot.servo[7].angle = 45`
        # HAL has self.servos which is MultiServo.
        # MultiServo should support list-like access.
        self.servo = hal.servos
