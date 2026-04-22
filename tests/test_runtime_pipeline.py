from ninja_core.runtime_pipeline import RuntimePipeline


class FakeFaces:
    def __init__(self):
        self.calls = []

    def stop(self):
        self.calls.append(("stop",))

    def play(self, name, duration_s):
        self.calls.append(("play", name, duration_s))


class FakeSound:
    def __init__(self):
        self.stop_calls = []

    def stop(self, restart_buzzer=False):
        self.stop_calls.append(restart_buzzer)


class FakeServos:
    def __init__(self):
        self.abort_called = False

    def abort(self):
        self.abort_called = True


class FakeHal:
    def __init__(self):
        self.servos = FakeServos()


def test_blockly_begin_stops_native_outputs():
    hal = FakeHal()
    faces = FakeFaces()
    sound = FakeSound()
    pipeline = RuntimePipeline(hal=hal, faces=faces, sound=sound)

    pipeline.begin_blockly()

    assert pipeline.mode == "blockly"
    assert ("stop",) in faces.calls
    assert sound.stop_calls == [True]
    assert hal.servos.abort_called is True


def test_successful_blockly_completion_resumes_idle():
    faces = FakeFaces()
    pipeline = RuntimePipeline(faces=faces)

    pipeline.begin_blockly()
    pipeline.complete_blockly("success")

    assert pipeline.mode == "native"
    assert faces.calls[-1] == ("play", "idle", float("inf"))


def test_display_hold_keeps_clear_screen_until_native_reclaim():
    faces = FakeFaces()
    pipeline = RuntimePipeline(faces=faces)

    pipeline.begin_blockly()
    pipeline.mark_display_hold()
    pipeline.complete_blockly("success")

    assert pipeline.mode == "blockly_hold"
    assert faces.calls == [("stop",)]

    pipeline.reclaim_native()

    assert pipeline.mode == "native"
    assert faces.calls[-1] == ("play", "idle", float("inf"))
