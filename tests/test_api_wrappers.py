import logging

from ninja_core.api_wrappers import DisplayWrapper, DistanceWrapper, RobotWrapper, ServoWrapper


def test_distance_wrapper_returns_sensor_distance():
    class FakeSensor:
        def get_data(self):
            return {"distance_mm": 123, "is_valid": True}

    assert DistanceWrapper(FakeSensor()).read() == 123


def test_distance_wrapper_returns_fallback_for_invalid_sensor_data(caplog):
    class FakeSensor:
        def get_data(self):
            return {"distance_mm": -1, "is_valid": False}

    with caplog.at_level(logging.WARNING):
        assert DistanceWrapper(FakeSensor()).read() == 9999

    assert "Distance read unavailable or invalid" in caplog.text


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


def test_robot_wrapper_request_stop_preserves_display_for_idle_restore(monkeypatch):
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
    assert robot._hal.display.off_called is False
    assert robot._hal.servos.off_called is True


def test_robot_wrapper_uses_shared_faces_for_expressions():
    class SharedFaces:
        def __init__(self):
            self.play_calls = []

        def play(self, name, duration_s):
            self.play_calls.append((name, duration_s))

    class FakeHal:
        buzzer = None
        display = None
        distance_sensor = None
        servos = None

    faces = SharedFaces()
    robot = RobotWrapper(FakeHal(), cooperative_sleep=lambda duration: None, faces=faces)

    robot.expression("angry", duration=2.0)

    assert robot._faces is faces
    assert faces.play_calls == [("angry", 2.0)]


def test_display_clear_marks_blockly_display_hold():
    class FakeDisplay:
        def __init__(self):
            self.commands = []

        def execute(self, command):
            self.commands.append(command)

    class FakeHal:
        def __init__(self):
            self.display = FakeDisplay()

    class FakeRuntimePipeline:
        def __init__(self):
            self.hold_called = False

        def mark_display_hold(self):
            self.hold_called = True

    hal = FakeHal()
    pipeline = FakeRuntimePipeline()

    DisplayWrapper(hal, runtime_pipeline=pipeline).clear()

    assert hal.display.commands == [{"clear": True}]
    assert pipeline.hold_called is True
