"""pi0servo - Servo control library for Raspberry Pi.

A unified API for controlling multiple servos with:
- Velocity-based movement control
- Abort mechanism for safe interruption
- Movement-tool command format
- Per-servo calibration with speed limits
- CLI tools for testing and configuration

Usage:
    from pi0servo import Servo, ServoGroup, ConfigManager

    # Single servo
    import pigpio
    pi = pigpio.pi()
    servo = Servo(pi, pin=20)
    servo.set_angle(45)

    # Multi-servo with commands
    group = ServoGroup(pi, pins=[20, 21, 22, 23])
    group.execute_command("F_20:45/21:-30")
"""

__version__ = "1.0.0"

# Core classes
# Configuration
from .config import (
    ConfigManager,
    get_default_config_path,
)
from .core import (
    PULSE_CENTER,
    PULSE_MAX,
    PULSE_MIN,
    Servo,
    ServoCalibration,
    ServoGroup,
)

# Motion utilities
from .motion import (
    EASING_FUNCTIONS,
    FMS_MULTIPLIERS,
    calculate_duration,
    calculate_step_count,
    ease_in,
    ease_in_out,
    ease_out,
    linear,
)

# Parser
from .parser import (
    ParsedCommand,
    ServoTarget,
    parse_command,
    resolve_special_angle,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "Servo",
    "ServoCalibration",
    "ServoGroup",
    "MultiServo",  # Backward compatibility alias
    "PULSE_MIN",
    "PULSE_MAX",
    "PULSE_CENTER",
    # Config
    "ConfigManager",
    "get_default_config_path",
    # Motion
    "linear",
    "ease_out",
    "ease_in",
    "ease_in_out",
    "EASING_FUNCTIONS",
    "calculate_duration",
    "calculate_step_count",
    "FMS_MULTIPLIERS",
    # Parser
    "parse_command",
    "resolve_special_angle",
    "ParsedCommand",
    "ServoTarget",
]

# Backward compatibility alias for ninja_core
MultiServo = ServoGroup
