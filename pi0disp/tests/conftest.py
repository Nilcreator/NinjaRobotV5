"""Pytest fixtures for mocking pigpio on PC/Mac."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock ninja_utils before any imports that need it
mock_ninja_utils = MagicMock()
mock_ninja_utils.get_module_logger = MagicMock(return_value=MagicMock())
mock_ninja_utils.Actuator = type("Actuator", (), {
    "initialize": lambda self: None,
    "execute": lambda self, command: None,
    "off": lambda self: None,
})
sys.modules["ninja_utils"] = mock_ninja_utils


@pytest.fixture(autouse=True)
def mock_pigpio(monkeypatch):
    """Mock pigpio for all tests — no hardware required.

    This fixture automatically mocks the pigpio module so tests can run
    on development machines without a Raspberry Pi.
    """
    mock_pigpio_module = MagicMock()

    # Create a mock pi instance
    mock_pi = MagicMock()
    mock_pi.connected = True
    mock_pi.spi_open.return_value = 0  # Valid SPI handle
    mock_pi.spi_write.return_value = (0, b"")
    mock_pi.spi_close.return_value = 0
    mock_pi.write.return_value = 0
    mock_pi.set_mode.return_value = 0
    mock_pi.set_PWM_dutycycle.return_value = 0

    # Standard pigpio constants
    mock_pigpio_module.OUTPUT = 1
    mock_pigpio_module.pi.return_value = mock_pi

    monkeypatch.setitem(sys.modules, "pigpio", mock_pigpio_module)

    return mock_pi
