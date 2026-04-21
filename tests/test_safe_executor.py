import time

from ninja_core.safe_executor import SafeExecutor


class DummyHal:
    def __init__(self):
        self.buzzer = None
        self.display = None
        self.distance_sensor = None
        self.servos = None


class StopTrackingComponent:
    def __init__(self):
        self.width = 240
        self.height = 240
        self.off_called = False

    def off(self):
        self.off_called = True


class StopTrackingHal:
    def __init__(self):
        self.buzzer = StopTrackingComponent()
        self.display = StopTrackingComponent()
        self.distance_sensor = None
        self.servos = StopTrackingComponent()


def wait_for_executor(executor, timeout=1.0):
    deadline = time.time() + timeout
    while executor.is_running() and time.time() < deadline:
        time.sleep(0.01)


def test_stop_interrupts_cooperative_sleep():
    executor = SafeExecutor(DummyHal())

    result = executor.execute("sleep(1.0)")
    assert result["status"] == "started"

    time.sleep(0.1)
    executor.stop()
    wait_for_executor(executor)

    assert executor.get_result()["status"] == "stopped"


def test_stop_interrupts_imported_time_sleep():
    executor = SafeExecutor(DummyHal())

    result = executor.execute("import time\ntime.sleep(1.0)")
    assert result["status"] == "started"

    time.sleep(0.1)
    executor.stop()
    wait_for_executor(executor)

    assert executor.get_result()["status"] == "stopped"


def test_executor_can_run_again_after_stop():
    executor = SafeExecutor(DummyHal())

    first_result = executor.execute("sleep(1.0)")
    assert first_result["status"] == "started"

    time.sleep(0.1)
    executor.stop()
    wait_for_executor(executor)
    assert executor.get_result()["status"] == "stopped"
    assert executor.is_running() is False

    second_result = executor.execute("print('ready again')")
    assert second_result["status"] == "started"

    wait_for_executor(executor)
    assert executor.get_result()["status"] == "success"


def test_syntax_error_does_not_start_thread_or_stop_hardware():
    hal = StopTrackingHal()
    executor = SafeExecutor(hal)

    result = executor.execute("if True:\n  print('ok')\n x = 1\n")

    assert result["status"] == "error"
    assert result["error_code"] == "syntax_error"
    assert result["syntax_error"]["line"] == 3
    assert executor.is_running() is False
    assert executor.get_result() == result
    assert hal.buzzer.off_called is False
    assert hal.display.off_called is False
    assert hal.servos.off_called is False


def test_executor_can_run_after_syntax_error():
    executor = SafeExecutor(DummyHal())

    first_result = executor.execute("if True:\n  print('ok')\n x = 1\n")
    assert first_result["error_code"] == "syntax_error"

    second_result = executor.execute("print('ready')")
    assert second_result["status"] == "started"

    wait_for_executor(executor)
    assert executor.get_result()["status"] == "success"
