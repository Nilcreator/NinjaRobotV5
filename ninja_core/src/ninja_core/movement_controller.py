import time
from ninja_core.hal import HardwareAbstractionLayer
from ninja_core.config import NinjaConfig

from typing import Callable, Optional

class EmergencyStop(Exception):
    """Raised when a movement is aborted due to safety checks."""
    pass


class MovementController:
    """A controller to manage and execute complex, multi-servo movement sequences."""

    def __init__(self, hal: HardwareAbstractionLayer, config: NinjaConfig):
        """
        Initializes the MovementController.

        Args:
            hal: The HardwareAbstractionLayer instance.
            config: The NinjaConfig instance for loading settings.
        """
        self.servos = hal.servos
        self.servo_definitions = config.servos.calibration
        self.movements = config.movements

    def move_servos(
        self,
        movements: dict[int, float],
        speed: str = "M",
        per_servo_speeds: dict[int, str] | None = None,
        abort_check: Optional[Callable[[], bool]] = None,
    ):
        """
        Executes a set of servo movements with per-servo velocity control.

        Uses pi0servo's move_all_sync which handles:
        - Per-servo speed limits from calibration
        - Per-servo duration calculation
        - Easing curves for smooth motion

        Args:
            movements: A dictionary of {pin: angle}.
            speed: Global speed mode ('S'low, 'M'edium, 'F'ast).
            per_servo_speeds: Optional {pin: speed} for per-servo override.
            abort_check: Optional function that returns True to abort.
        """
        if not self.servos:
            return

        # Build ordered list of target angles and speed modes
        ordered_pins = self.servos.pins
        target_angles: list[float | None] = []
        speed_modes: list[str] = []

        per_servo_speeds = per_servo_speeds or {}

        for pin in ordered_pins:
            if pin in movements:
                target_angles.append(movements[pin])
                # Use per-servo speed if specified, otherwise global
                servo_speed = per_servo_speeds.get(pin, speed)
                speed_modes.append(servo_speed)
            else:
                # Hold current position (don't move this servo)
                target_angles.append(None)
                speed_modes.append(speed)

        # Use pi0servo's move_all_sync with per-servo speed modes
        # This handles velocity calculation, easing, and abort internally
        completed = self.servos.move_all_sync(
            target_angles,
            speed_mode=speed_modes,
            easing="ease_in_out_cubic",
            force=True,  # Prevent skipped PWM updates causing limpness
        )

        if not completed and abort_check:
            print("! EMERGENCY STOP TRIGGERED !")
            self.center_all_servos()
            raise EmergencyStop("Movement aborted by safety check.")

    def get_current_angles(self) -> dict[int, float]:
        """
        Returns a dictionary of {pin: current_angle} by mapping the list
        from the driver to its corresponding pins.
        """
        if not self.servos:
            # Return 0 for all known pins if driver is missing
            return {int(pin): 0.0 for pin in self.servo_definitions.keys()}

        angle_list = self.servos.get_all_angles()
        pin_list = self.servos.pins
        return {pin_list[i]: angle_list[i] for i in range(len(pin_list))}

    def center_all_servos(self):
        """Moves all servos to their center position."""
        print("Centering all servos...")
        center_angles = {int(pin): 0 for pin in self.servo_definitions.keys()}
        # We don't pass abort_check here to ensure centering always happens
        self.move_servos(center_angles, speed="F") 
        time.sleep(0.5)

    def execute_movement(
        self, movement_name: str, abort_check: Optional[Callable[[], bool]] = None
    ):
        """
        Executes a pre-defined movement sequence by name.

        Args:
            movement_name: The name of the movement to execute.
            abort_check: An optional function that returns True if the movement should stop.
        """
        if movement_name not in self.movements:
            print(f"Error: Movement '{movement_name}' not found.")
            return

        print(f"Executing movement: '{movement_name}'...")
        sequence = self.movements[movement_name]
        for step in sequence:
            # The keys in 'moves' from JSON will be strings, convert them to int
            moves = {int(k): v for k, v in step["moves"].items()}
            # Extract per-servo speeds if stored (int keys from JSON strings)
            per_servo = None
            if "per_servo_speeds" in step:
                per_servo = {int(k): v for k, v in step["per_servo_speeds"].items()}
            self.move_servos(moves, step["speed"], per_servo, abort_check)
        print(f"Movement '{movement_name}' finished.")
