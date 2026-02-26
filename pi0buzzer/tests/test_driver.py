"""Unit tests for pi0buzzer.core.driver.Buzzer."""

import time


import pytest


class TestBuzzerInit:
    """Test Buzzer initialization."""

    def test_init_creates_instance(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        assert b.pin == 17
        assert b.pi is mock_pi
        assert not b.is_initialized

    def test_init_with_external_pi(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        assert b._is_external_pi is True

    def test_init_without_pi(self, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17)
        assert b._is_external_pi is False

    def test_init_default_volume(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        assert b.volume == 128

    def test_init_custom_volume(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi, volume=64)
        assert b.volume == 64

    def test_init_volume_clamped(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi, volume=999)
        assert b.volume == 255

        b2 = Buzzer(pin=17, pi=mock_pi, volume=-5)
        assert b2.volume == 0


class TestBuzzerInitialize:
    """Test Buzzer.initialize() method."""

    def test_initialize_starts_worker(self, buzzer):
        assert buzzer.is_initialized
        assert buzzer._worker_thread is not None
        assert buzzer._worker_thread.is_alive()

    def test_initialize_is_idempotent(self, buzzer):
        """Calling initialize() twice should not create duplicate workers."""
        thread1 = buzzer._worker_thread
        buzzer.initialize()
        assert buzzer._worker_thread is thread1

    def test_initialize_fails_without_pigpiod(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        mock_pi.connected = False
        b = Buzzer(pin=17, pi=mock_pi)
        with pytest.raises(ConnectionError):
            b.initialize()

    def test_initialize_sets_pin_mode(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        b.initialize()
        mock_pi.set_mode.assert_called_once()
        b.off()


class TestBuzzerExecute:
    """Test Buzzer.execute() method."""

    def test_execute_queues_sound(self, buzzer):
        buzzer.execute({"frequency": 440, "duration": 0.1})
        # Give worker time to process
        time.sleep(0.3)
        buzzer.pi.set_PWM_frequency.assert_called()

    def test_execute_clamps_frequency(self, buzzer):
        buzzer.execute({"frequency": 5, "duration": 0.01})
        time.sleep(0.2)
        # Should be clamped to MIN_FREQUENCY (20)
        buzzer.pi.set_PWM_frequency.assert_called_with(17, 20)

    def test_execute_clamps_high_frequency(self, buzzer):
        buzzer.execute({"frequency": 99999, "duration": 0.01})
        time.sleep(0.2)
        buzzer.pi.set_PWM_frequency.assert_called_with(17, 20000)

    def test_execute_ignores_zero_frequency(self, buzzer):
        buzzer.execute({"frequency": 0, "duration": 0.1})
        time.sleep(0.2)
        buzzer.pi.set_PWM_frequency.assert_not_called()

    def test_execute_ignores_negative_frequency(self, buzzer):
        buzzer.execute({"frequency": -100, "duration": 0.1})
        time.sleep(0.2)
        buzzer.pi.set_PWM_frequency.assert_not_called()

    def test_execute_when_not_initialized(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        # Should not raise, just log warning
        b.execute({"frequency": 440, "duration": 0.1})


class TestBuzzerPlaySound:
    """Test legacy play_sound() compatibility."""

    def test_play_sound_delegates_to_execute(self, buzzer):
        buzzer.play_sound(440, 0.1)
        time.sleep(0.3)
        buzzer.pi.set_PWM_frequency.assert_called()


class TestBuzzerVolume:
    """Test volume property."""

    def test_volume_setter(self, buzzer):
        buzzer.volume = 200
        assert buzzer.volume == 200

    def test_volume_clamped(self, buzzer):
        buzzer.volume = 999
        assert buzzer.volume == 255

        buzzer.volume = -10
        assert buzzer.volume == 0

    def test_volume_applied_in_playback(self, buzzer):
        buzzer.volume = 64
        buzzer.execute({"frequency": 440, "duration": 0.01})
        time.sleep(0.2)
        # Worker should use the updated volume
        buzzer.pi.set_PWM_dutycycle.assert_any_call(17, 64)


class TestBuzzerPause:
    """Test queue-based pause support."""

    def test_queue_pause(self, buzzer):
        buzzer.queue_pause(0.1)
        # Should not crash; pause is processed in worker
        time.sleep(0.3)

    def test_queue_pause_when_not_initialized(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        b = Buzzer(pin=17, pi=mock_pi)
        b.queue_pause(0.1)  # Should be silently ignored


class TestBuzzerOff:
    """Test Buzzer.off() method."""

    def test_off_stops_worker(self, buzzer):
        buzzer.off()
        assert not buzzer.is_initialized
        assert not buzzer._worker_thread.is_alive()

    def test_off_silences_buzzer(self, buzzer):
        buzzer.off()
        buzzer.pi.set_PWM_dutycycle.assert_called_with(17, 0)

    def test_off_does_not_stop_external_pi(self, buzzer):
        buzzer.off()
        buzzer.pi.stop.assert_not_called()


class TestBuzzerContextManager:
    """Test context manager support."""

    def test_context_manager(self, mock_pi, mock_pigpio):
        from pi0buzzer.core.driver import Buzzer

        with Buzzer(pin=17, pi=mock_pi) as b:
            assert b.is_initialized
        assert not b.is_initialized
