"""
NinjaRobot V5 Hardware Interfaces.

This module defines the Abstract Base Classes (ABCs) that all hardware drivers
must implement. These interfaces ensure plugin-based modularity, allowing
ninja_core to interact with any compatible sensor or actuator without knowing
the specific implementation details.

Usage:
    All hardware drivers (pi0buzzer, pi0servo, pi0disp, pi0vl53l0x) must inherit
    from either `Sensor` or `Actuator` and implement all abstract methods.

Example:
    class VL53L0X(Sensor):
        def initialize(self) -> None:
            # Setup I2C connection
            ...

        def get_data(self) -> dict:
            return {"distance_mm": self.get_range()}

        def close(self) -> None:
            self.pi.i2c_close(self.handle)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


# --- Data Classes for Standardized Output ---


@dataclass
class DistanceData:
    """Standardized output for distance sensors.
    
    Attributes:
        distance_mm: The measured distance in millimeters.
        is_valid: Whether the measurement is valid (not out of range).
        raw_value: The raw sensor value before calibration.
        timestamp: Optional timestamp of the measurement.
    """
    distance_mm: int
    is_valid: bool = True
    raw_value: Optional[int] = None
    timestamp: Optional[float] = None


# --- Abstract Base Classes ---


class Sensor(ABC):
    """Abstract Base Class for all sensor drivers.
    
    All sensors must provide a consistent interface for:
    - Initialization (connecting to hardware)
    - Data retrieval (getting measurements)
    - Cleanup (releasing resources)
    
    This allows ninja_core to treat all sensors uniformly, regardless of
    whether they are distance sensors, temperature sensors, cameras, etc.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the sensor hardware.
        
        This method should:
        - Establish connection to the sensor (I2C, SPI, etc.)
        - Perform any required calibration
        - Prepare the sensor for data collection
        
        Raises:
            ConnectionError: If the sensor cannot be connected.
            RuntimeError: If initialization fails.
        """
        pass

    @abstractmethod
    def get_data(self) -> dict[str, Any]:
        """Retrieve current sensor data.
        
        Returns:
            A dictionary containing sensor-specific data.
            For distance sensors, this should include at minimum:
            {"distance_mm": int, "is_valid": bool}
        
        Raises:
            RuntimeError: If the sensor is not initialized or fails to read.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Release sensor resources and close connections.
        
        This method should:
        - Close any open I2C/SPI handles
        - Release GPIO pins
        - Stop any background processes
        """
        pass


class Actuator(ABC):
    """Abstract Base Class for all actuator drivers.
    
    All actuators must provide a consistent interface for:
    - Initialization (connecting to hardware)
    - Command execution (performing actions)
    - Shutdown (safely turning off)
    
    This allows ninja_core to treat all actuators uniformly, regardless of
    whether they are servos, displays, buzzers, LEDs, etc.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the actuator hardware.
        
        This method should:
        - Establish connection to the actuator (GPIO, SPI, etc.)
        - Set the actuator to a safe default state
        - Prepare for receiving commands
        
        Raises:
            ConnectionError: If the actuator cannot be connected.
            RuntimeError: If initialization fails.
        """
        pass

    @abstractmethod
    def execute(self, command: dict[str, Any]) -> None:
        """Execute a command on the actuator.
        
        Args:
            command: A dictionary containing actuator-specific commands.
                For servos: {"pin": int, "angle": float}
                For buzzers: {"frequency": int, "duration": float}
                For displays: {"image": PIL.Image}
        
        Raises:
            ValueError: If the command is invalid.
            RuntimeError: If execution fails.
        """
        pass

    @abstractmethod
    def off(self) -> None:
        """Safely turn off the actuator.
        
        This method should:
        - Stop any ongoing operations
        - Set the actuator to a safe state (e.g., servo off, buzzer silent)
        - Release resources if necessary
        """
        pass
