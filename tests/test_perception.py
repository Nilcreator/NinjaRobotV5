import time

from ninja_core.perception import DistanceMonitor


class FakeHal:
    def __init__(self, sensor):
        self.distance_sensor = sensor


class FlakySensor:
    def __init__(self):
        self.calls = 0
        self.reinitialize_calls = 0

    def get_range(self):
        self.calls += 1
        if self.calls <= 2:
            raise RuntimeError("temporary i2c failure")
        return 321

    def reinitialize(self):
        self.reinitialize_calls += 1


class RecoveringSensor:
    def __init__(self):
        self.calls = 0
        self.reinitialize_calls = 0

    def get_range(self):
        self.calls += 1
        if self.calls <= 3:
            raise RuntimeError("stuck i2c bus")
        return 222

    def reinitialize(self):
        self.reinitialize_calls += 1


def wait_for(predicate, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_distance_monitor_continues_after_transient_sensor_errors():
    sensor = FlakySensor()
    monitor = DistanceMonitor(FakeHal(sensor))

    monitor.start_continuous(interval=0.01)
    try:
        assert wait_for(lambda: monitor.get_continuous_distance() == 321)
        assert sensor.calls >= 3
        assert monitor._is_running is True
    finally:
        monitor.stop_continuous()


def test_distance_monitor_attempts_reinitialize_after_repeated_errors():
    sensor = RecoveringSensor()
    monitor = DistanceMonitor(FakeHal(sensor))

    monitor.start_continuous(interval=0.01)
    try:
        assert wait_for(lambda: monitor.get_continuous_distance() == 222)
        assert sensor.reinitialize_calls >= 1
    finally:
        monitor.stop_continuous()
