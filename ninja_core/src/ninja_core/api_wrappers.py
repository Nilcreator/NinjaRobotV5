import logging
import time
from pathlib import Path
from PIL import Image
from .robot_sound import RobotSoundPlayer
from .facial_expressions import AnimatedFaces

log = logging.getLogger(__name__)


class DistanceWrapper:
    def __init__(self, sensor):
        self._sensor = sensor

    def read(self):
        """Returns distance in mm from VL53L0X sensor.
        
        Returns:
            int: Distance in millimeters. Returns 9999 if sensor unavailable.
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
        """Play a predefined emotion sound by name.
        
        Valid names: happy, sad, exciting, angry, confusing, cry, 
                     embarrassing, idle, laughing, scary, shy, 
                     sleepy, speaking, surprising
        """
        self._player.play(sound_name)

    def tone(self, frequency, duration):
        """Play a specific frequency tone.
        
        Args:
            frequency: Frequency in Hz (100-2000).
            duration: Duration in seconds.
        """
        if self._hal.buzzer:
            self._hal.buzzer.execute({"frequency": frequency, "duration": duration})


class DisplayWrapper:
    def __init__(self, hal):
        self._hal = hal
        self._search_paths = [
            Path(__file__).parent / "static" / "assets" / "images",
        ]

    def image(self, name):
        """Display an image by name (e.g., 'star' -> 'star.png')."""
        if not self._hal.display:
            return

        image_path = None
        for path in self._search_paths:
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

    def clear(self):
        """Clear the display (fill with black)."""
        if self._hal.display:
            self._hal.display.execute({"clear": True})


class RobotWrapper:
    """
    High-level wrapper for the Robot HAL.
    Matches the API expected by the Blockly/Web IDE.
    
    Available API:
        robot.servo[n].angle = x   - Set servo n (0-7) to angle x
        robot.buzzer.tone(f, d)    - Play frequency f for d seconds
        robot.buzzer.play(name)    - Play emotion sound
        robot.display.clear()      - Clear display
        robot.expression(name)     - Show facial expression
        robot.distance.read()      - Read distance in mm
    """

    def __init__(self, hal):
        self._hal = hal
        self.buzzer = BuzzerWrapper(hal)
        self.display = DisplayWrapper(hal)
        self.distance = DistanceWrapper(hal.distance_sensor)
        
        # Servos: accessed via robot.servo[n].angle = x
        self.servo = hal.servos
        
        # Facial expressions engine
        self._faces = AnimatedFaces(hal)

    def expression(self, name: str, duration: float = 2.0):
        """Show an animated facial expression on the display.
        
        Args:
            name: Expression name. Valid options:
                  happy, sad, sleepy, surprising, angry, shy, confusing,
                  scary, exciting, cry, laughing, speaking, idle
            duration: How long to show the expression (default 2 seconds).
        """
        if self._faces:
            try:
                self._faces.show(name, duration=duration)
            except Exception as e:
                log.error(f"Failed to show expression '{name}': {e}")
        else:
            log.warning("AnimatedFaces not available.")
