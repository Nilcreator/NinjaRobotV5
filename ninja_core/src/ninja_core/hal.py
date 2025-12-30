"""
Hardware Abstraction Layer (HAL) for NinjaRobot V5.

This module provides a single, unified interface to all hardware components,
abstracting away the details of pin numbers and driver initialization. It is
responsible for initializing all hardware from a central configuration object
and providing a clean way to access and shut down the hardware.

V5 Changes:
- All drivers now implement Sensor/Actuator ABCs from ninja_utils.interfaces
- Added initialize_driver() for future dynamic loading support
- Buzzer now uses non-blocking threaded playback
"""

import importlib
import logging
from typing import Optional

import pigpio

from ninja_utils import Actuator, Sensor
from .config import NinjaConfig

# --- Driver Registry ---
# Maps component names to their module paths and class names.
# This enables future dynamic loading from config.json
DRIVER_REGISTRY = {
    "servos": {
        "module": "pi0servo.core.multi_servo",
        "class": "MultiServo",
    },
    "buzzer": {
        "module": "pi0buzzer.driver",
        "class": "MusicBuzzer",
    },
    "display": {
        "module": "pi0disp.disp.st7789v",
        "class": "ST7789V",
    },
    "distance_sensor": {
        "module": "pi0vl53l0x.driver",
        "class": "VL53L0X",
    },
}

log = logging.getLogger(__name__)


def load_driver_class(component_name: str) -> type:
    """Dynamically load a driver class from the registry.
    
    Args:
        component_name: The name of the component (e.g., "servos", "buzzer").
    
    Returns:
        The driver class.
    
    Raises:
        KeyError: If the component is not in the registry.
        ImportError: If the module cannot be imported.
    """
    if component_name not in DRIVER_REGISTRY:
        raise KeyError(f"Unknown component: {component_name}")
    
    registry_entry = DRIVER_REGISTRY[component_name]
    module = importlib.import_module(registry_entry["module"])
    driver_class = getattr(module, registry_entry["class"])
    
    log.debug(
        "Loaded driver class %s.%s for component '%s'",
        registry_entry["module"],
        registry_entry["class"],
        component_name,
    )
    return driver_class


class HardwareAbstractionLayer:
    """A class to initialize, manage, and access all robot hardware.
    
    All hardware drivers now implement the Sensor or Actuator ABC from
    ninja_utils.interfaces, providing a consistent interface for:
    - Sensors: initialize(), get_data(), close()
    - Actuators: initialize(), execute(command), off()
    """

    def __init__(self, config: NinjaConfig):
        """
        Initializes the HAL with the robot's configuration.

        Note: This only stores the config. Hardware is not initialized until
        the `initialize()` method is called.

        Args:
            config: The NinjaConfig object with all hardware settings.
        """
        self.config = config
        self.pi: Optional[pigpio.pi] = None
        
        # Actuators (implement Actuator ABC)
        self.servos: Optional[Actuator] = None
        self.buzzer: Optional[Actuator] = None
        self.display: Optional[Actuator] = None
        
        # Sensors (implement Sensor ABC)
        self.distance_sensor: Optional[Sensor] = None
        
        log.info("Hardware Abstraction Layer created.")

    def initialize(self, components: Optional[list[str]] = None):
        """
        Connects to the pigpio daemon and initializes all hardware components
        based on the provided configuration.

        Args:
            components: A list of component names to initialize. 
                        Options: "servos", "buzzer", "display", "sensors".
                        If None, all components are initialized.
        """
        log.info("Initializing hardware components...")
        try:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise ConnectionError("Could not connect to the pigpiod daemon.")
            log.info("Successfully connected to pigpiod.")
        except Exception as e:
            log.error(f"Failed to connect to pigpio daemon: {e}")
            log.error("Please ensure the pigpio daemon is running (`sudo pigpiod`).")
            raise

        # --- Filter components if specified ---
        if components is None:
            components = ["servos", "buzzer", "display", "sensors"]

        # --- Initialize Servos ---
        if "servos" in components:
            self._init_servos()

        # --- Initialize Buzzer ---
        if "buzzer" in components:
            self._init_buzzer()

        # --- Initialize Display ---
        if "display" in components:
            self._init_display()

        # --- Initialize Distance Sensor ---
        if "sensors" in components:
            self._init_distance_sensor()

        log.info("Hardware initialization process complete.")

    def _init_servos(self) -> None:
        """Initialize the servo controller."""
        # Debug: Show what config values we're checking
        has_servos_config = bool(self.config.servos)
        has_calibration = bool(self.config.servos.calibration) if has_servos_config else False
        log.debug(f"Servo config check: servos={has_servos_config}, calibration={has_calibration}")
        
        if not self.config.servos or not self.config.servos.calibration:
            log.info("No servo calibration data found. Skipping servo initialization.")
            log.info("Tip: Run 'uv run ninja_core config import' to import servo.json")
            return

        try:
            pin_list = [int(pin_str) for pin_str in self.config.servos.calibration.keys()]
            if not pin_list:
                log.info("No servo pins found in config. Skipping.")
                return

            log.info(f"Initializing MultiServo with pins {pin_list}...")
            MultiServo = load_driver_class("servos")
            self.servos = MultiServo(
                pi=self.pi,
                pins=pin_list,
                conf_file="servo.json",
            )
            log.info("MultiServo controller initialized.")
        except Exception as e:
            log.error(f"Failed to initialize Servos: {e}")
            log.warning("Continuing without Servos.")
            self.servos = None

    def _init_buzzer(self) -> None:
        """Initialize the buzzer (non-blocking threaded driver)."""
        # Debug: Show what config values we're checking
        has_buzzer_config = bool(self.config.buzzer)
        buzzer_pin = self.config.buzzer.pin if has_buzzer_config else None
        log.debug(f"Buzzer config check: buzzer={has_buzzer_config}, pin={buzzer_pin}")
        
        if not self.config.buzzer or not self.config.buzzer.pin:
            log.info("No buzzer pin configured. Skipping.")
            log.info("Tip: Run 'uv run ninja_core config import' to import buzzer.json")
            return

        try:
            MusicBuzzer = load_driver_class("buzzer")
            self.buzzer = MusicBuzzer(pin=self.config.buzzer.pin, pi=self.pi)
            # V5: Call initialize() to start the background worker thread
            self.buzzer.initialize()
            log.info(f"Buzzer initialized on pin {self.config.buzzer.pin} (non-blocking mode).")
        except Exception as e:
            log.error(f"Failed to initialize Buzzer: {e}")
            log.warning("Continuing without Buzzer.")
            self.buzzer = None

    def _init_display(self) -> None:
        """Initialize the display."""
        if not self.config.display or self.config.display.dc is None:
            log.info("No display pins configured. Skipping.")
            return

        try:
            log.info("Initializing display...")
            ST7789V = load_driver_class("display")
            self.display = ST7789V(
                pi=self.pi,
                channel=0,
                dc_pin=self.config.display.dc,
                rst_pin=self.config.display.rst,
                backlight_pin=self.config.display.blk,
            )
            log.info("Display initialized.")
        except Exception as e:
            log.error(f"Failed to initialize Display: {e}")
            log.warning("Continuing without Display.")
            self.display = None

    def _init_distance_sensor(self) -> None:
        """Initialize the distance sensor."""
        if not self.config.sensors:
            log.info("No sensor config found. Skipping distance sensor.")
            return

        try:
            log.info("Initializing distance sensor...")
            VL53L0X = load_driver_class("distance_sensor")
            self.distance_sensor = VL53L0X(pi=self.pi)
            log.info("Distance sensor initialized.")
        except Exception as e:
            log.error(f"Failed to initialize distance sensor: {e}")
            log.warning("Continuing without distance sensor. Obstacle avoidance will be disabled.")
            self.distance_sensor = None

    def shutdown(self):
        """
        Safely shuts down all initialized hardware components and disconnects
        from the pigpio daemon.
        """
        log.info("Shutting down hardware components...")

        # Use ABC off() method for actuators
        if self.servos:
            self.servos.off()
            log.info("All servos turned off.")

        if self.buzzer:
            self.buzzer.off()
            log.info("Buzzer turned off.")

        if self.display:
            self.display.off()  # Uses ABC method
            self.display.close()
            log.info("Display closed.")

        # Use ABC close() method for sensors
        if self.distance_sensor:
            self.distance_sensor.close()
            log.info("Distance sensor closed.")

        if self.pi and self.pi.connected:
            self.pi.stop()
            log.info("Disconnected from pigpiod.")
