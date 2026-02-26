"""Shared test fixtures for pi0buzzer test suite."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_pi():
    """Create a mocked pigpio.pi instance."""
    pi = MagicMock()
    pi.connected = True
    pi.set_mode = MagicMock()
    pi.set_PWM_dutycycle = MagicMock()
    pi.set_PWM_frequency = MagicMock()
    pi.stop = MagicMock()
    return pi


@pytest.fixture
def mock_pigpio(mock_pi):
    """Patch the pigpio module to return our mock pi."""
    with patch("pi0buzzer.core.driver.pigpio") as mock_module:
        mock_module.pi.return_value = mock_pi
        mock_module.OUTPUT = 1
        yield mock_module


@pytest.fixture
def buzzer(mock_pi, mock_pigpio):
    """Create an initialized Buzzer with mocked pigpio."""
    from pi0buzzer.core.driver import Buzzer

    b = Buzzer(pin=17, pi=mock_pi)
    b.initialize()
    yield b
    if b.is_initialized:
        b.off()


@pytest.fixture
def music_buzzer(mock_pi, mock_pigpio):
    """Create an initialized MusicBuzzer with mocked pigpio."""
    from pi0buzzer.core.music import MusicBuzzer

    b = MusicBuzzer(pin=17, pi=mock_pi)
    b.initialize()
    yield b
    if b.is_initialized:
        b.off()


@pytest.fixture
def tmp_config(tmp_path):
    """Provide a temporary config file path."""
    return str(tmp_path / "test_buzzer.json")
