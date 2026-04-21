import time

from ninja_core.safe_executor import SafeExecutor


class DummyHal:
    def __init__(self):
        self.buzzer = None
        self.display = None
        self.distance_sensor = None
        self.servos = None


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
