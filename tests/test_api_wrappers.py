import logging

from ninja_core.api_wrappers import RobotWrapper, ServoWrapper


def test_servo_wrapper_clamps_out_of_range_angles_and_logs(caplog):
    servo = ServoWrapper(None, 0)

    with caplog.at_level(logging.WARNING):
        servo.angle = 120

    assert servo.angle == 90
    assert "out-of-range servo angle 120" in caplog.text


def test_servo_wrapper_move_clamps_negative_angles_and_logs(caplog):
    servo = ServoWrapper(None, 1)

    with caplog.at_level(logging.WARNING):
        servo.move(-120, duration=0.5)

    assert servo.angle == -90
    assert "out-of-range servo angle -120" in caplog.text


def test_robot_wrapper_request_stop_turns_off_hal_components(monkeypatch):
    class FakeFaces:
        def __init__(self, hal):
            self.hal = hal
            self.stop_called = False

        def stop(self):
            self.stop_called = True

    class FakeComponent:
        def __init__(self):
            self.off_called = False

        def off(self):
            self.off_called = True

    class FakeHal:
        def __init__(self):
            self.buzzer = FakeComponent()
            self.display = FakeComponent()
            self.servos = FakeComponent()
            self.distance_sensor = None

    monkeypatch.setattr("ninja_core.api_wrappers.AnimatedFaces", FakeFaces)
    robot = RobotWrapper(FakeHal())

    robot.request_stop()

    assert robot._faces.stop_called is True
    assert robot._hal.buzzer.off_called is True
    assert robot._hal.display.off_called is True
    assert robot._hal.servos.off_called is True
