from __future__ import annotations

import asyncio


def test_execute_command_broadcasts_contract_envelope(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print
            self.stop_called = False

        def execute(self, code, on_complete=None, on_start=None):
            if on_start:
                on_start()
            self.code = code
            self.on_complete = on_complete
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            self.stop_called = True

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-001",
                "manifest": {"generator_version": "web-blockly-test"},
                "workspace_state": {"blocks": []},
                "code": 'print("hi")',
            },
        )

        assert result["status"] == "started"
        assert result["request_id"] == "exec-001"
        assert result["protocol_version"] == "blockly-v1"
        assert result["manifest"]["generator_version"] == "web-blockly-test"
        assert messages[0]["type"] == "execute_received"
        assert messages[0]["request_id"] == "exec-001"
        assert messages[0]["code_length"] == len('print("hi")')
        assert messages[0]["workspace_received"] is True
        assert messages[1]["type"] == "execution_status"
        assert messages[1]["status"] == "started"
        assert messages[2]["type"] == "chat"
        assert messages[2]["request_id"] == "exec-001"

    asyncio.run(run_test())


def test_stop_command_broadcasts_stop_requested(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print
            self.stop_called = False

        def execute(self, code, on_complete=None, on_start=None):
            if on_start:
                on_start()
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            self.stop_called = True

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        dispatcher._active_request_id = "exec-active"
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "stop",
                "request_id": "stop-001",
            },
        )

        assert result["status"] == "ok"
        assert result["request_id"] == "stop-001"
        assert messages[0]["type"] == "execution_status"
        assert messages[0]["request_id"] == "exec-active"
        assert messages[0]["status"] == "stop_requested"

    asyncio.run(run_test())


def test_hal_command_reports_unknown_action(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=object())
        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "hal",
                "command": "unknown",
                "payload": {},
            },
        )

        assert result == {
            "status": "error",
            "message": "Unknown HAL action: unknown",
        }

    asyncio.run(run_test())


def test_runtime_error_broadcasts_structured_error_event(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print

        def execute(self, code, on_complete=None, on_start=None):
            if on_start:
                on_start()
            if on_complete:
                on_complete(
                    {
                        "status": "error",
                        "message": "Boom",
                        "traceback": "Traceback details",
                        "code": code,
                    }
                )
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-err",
                "code": "raise ValueError('Boom')",
            },
        )

        for _ in range(5):
            if dispatcher._active_request_id is None:
                break
            await asyncio.sleep(0)

        assert result["status"] == "started"
        assert dispatcher._active_request_id is None
        assert any(
            message["type"] == "error"
            and message["request_id"] == "exec-err"
            and message["code"] == "execution_failed"
            for message in messages
        )
        assert any(
            message["type"] == "execution_status"
            and message["request_id"] == "exec-err"
            and message["status"] == "error"
            for message in messages
        )

    asyncio.run(run_test())


def test_syntax_error_broadcasts_details_without_started_status(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print

        def execute(self, code, on_complete=None, on_start=None):
            return {
                "status": "error",
                "error_code": "syntax_error",
                "message": "Syntax error on line 3: unexpected indent",
                "syntax_error": {
                    "line": 3,
                    "offset": 2,
                    "text": " x = 1",
                    "message": "unexpected indent",
                },
                "code": code,
            }

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-syntax",
                "workspace_state": {"blocks": []},
                "code": "if True:\n  print('ok')\n x = 1\n",
            },
        )

        assert result["status"] == "error"
        assert result["error_code"] == "syntax_error"
        assert dispatcher._active_request_id is None
        assert messages[0]["type"] == "execute_received"
        assert messages[0]["workspace_received"] is True
        assert any(
            message["type"] == "execution_status"
            and message["request_id"] == "exec-syntax"
            and message["status"] == "error"
            for message in messages
        )
        assert any(
            message["type"] == "error"
            and message["request_id"] == "exec-syntax"
            and message["code"] == "syntax_error"
            and message["details"]["line"] == 3
            for message in messages
        )
        assert not any(
            message["type"] == "execution_status"
            and message["status"] == "started"
            for message in messages
        )

    asyncio.run(run_test())


def test_rejected_second_execute_preserves_active_request_id(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print
            self.calls = 0

        def execute(self, code, on_complete=None, on_start=None):
            self.calls += 1
            if self.calls == 1:
                if on_start:
                    on_start()
                self.on_complete = on_complete
                return {"status": "started", "message": "Code execution started"}
            return {"status": "error", "message": "Code already running"}

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        messages = []
        dispatcher.register_listener(messages.append)

        first_result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-active",
                "code": 'print("first")',
            },
        )
        assert first_result["status"] == "started"
        assert dispatcher._active_request_id == "exec-active"

        second_result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-rejected",
                "code": 'print("second")',
            },
        )

        assert second_result["status"] == "error"
        assert second_result["request_id"] == "exec-rejected"
        assert dispatcher._active_request_id == "exec-active"
        assert any(
            message["type"] == "error"
            and message["request_id"] == "exec-rejected"
            and message["code"] == "execute_rejected"
            for message in messages
        )

    asyncio.run(run_test())


def test_executor_logs_remain_correlated_after_rejected_second_execute(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print
            self.calls = 0

        def execute(self, code, on_complete=None, on_start=None):
            self.calls += 1
            if self.calls == 1:
                if on_start:
                    on_start()
                self.on_complete = on_complete
                return {"status": "started", "message": "Code execution started"}
            return {"status": "error", "message": "Code already running"}

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        messages = []
        dispatcher.register_listener(messages.append)

        await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-active",
                "code": 'print("first")',
            },
        )
        await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-rejected",
                "code": 'print("second")',
            },
        )

        dispatcher._on_executor_print("still running\n")
        for _ in range(5):
            if any(message["type"] == "execution_log" for message in messages):
                break
            await asyncio.sleep(0)

        assert any(
            message["type"] == "execution_log"
            and message["request_id"] == "exec-active"
            and message["content"] == "still running\n"
            for message in messages
        )

    asyncio.run(run_test())


def test_execution_logs_are_broadcast_without_truncation(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print

        def execute(self, code, on_complete=None, on_start=None):
            if on_start:
                on_start()
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        dispatcher._active_request_id = "exec-log"
        messages = []
        dispatcher.register_listener(messages.append)

        long_message = "L" * 240
        dispatcher._on_executor_print(long_message)

        for _ in range(5):
            if any(message["type"] == "execution_log" for message in messages):
                break
            await asyncio.sleep(0)

        assert any(
            message["type"] == "execution_log"
            and message["request_id"] == "exec-log"
            and message["content"] == long_message
            for message in messages
        )

    asyncio.run(run_test())


def test_runtime_pipeline_begins_and_completes_for_successful_execute(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.hal = hal
            self.on_print = on_print
            self.runtime_pipeline = runtime_pipeline

        def execute(self, code, on_complete=None, on_start=None):
            if on_start:
                on_start()
            self.on_complete = on_complete
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            return None

    class FakeRuntimePipeline:
        def __init__(self):
            self.events = []

        def begin_blockly(self):
            self.events.append("begin")

        def complete_blockly(self, status):
            self.events.append(("complete", status))

        def abort_blockly(self):
            self.events.append("abort")

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        pipeline = FakeRuntimePipeline()
        dispatcher = dispatcher_module.CommandDispatcher(
            hal=None,
            runtime_pipeline=pipeline,
        )

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-pipeline",
                "code": "print('ok')",
            },
        )
        assert result["status"] == "started"
        assert pipeline.events == ["begin"]

        dispatcher.safe_executor.on_complete(
            {"status": "success", "message": "", "code": "print('ok')"}
        )
        for _ in range(5):
            if ("complete", "success") in pipeline.events:
                break
            await asyncio.sleep(0)

        assert ("complete", "success") in pipeline.events

    asyncio.run(run_test())


def test_runtime_pipeline_not_started_for_syntax_error(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            return None

        def execute(self, code, on_complete=None, on_start=None):
            return {
                "status": "error",
                "error_code": "syntax_error",
                "message": "Syntax error on line 1: invalid syntax",
                "syntax_error": {"line": 1},
                "code": code,
            }

        def stop(self):
            return None

    class FakeRuntimePipeline:
        def __init__(self):
            self.events = []

        def begin_blockly(self):
            self.events.append("begin")

        def complete_blockly(self, status):
            self.events.append(("complete", status))

        def abort_blockly(self):
            self.events.append("abort")

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        pipeline = FakeRuntimePipeline()
        dispatcher = dispatcher_module.CommandDispatcher(
            hal=None,
            runtime_pipeline=pipeline,
        )

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "execute",
                "request_id": "exec-syntax",
                "code": "if",
            },
        )

        assert result["status"] == "error"
        assert pipeline.events == []

    asyncio.run(run_test())


def test_stop_command_aborts_blockly_pipeline(monkeypatch):
    import ninja_core.dispatcher as dispatcher_module

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.stop_called = False

        def execute(self, code, on_complete=None, on_start=None):
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            self.stop_called = True

    class FakeRuntimePipeline:
        def __init__(self):
            self.abort_called = False

        def begin_blockly(self):
            return None

        def complete_blockly(self, status):
            return None

        def abort_blockly(self):
            self.abort_called = True

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        pipeline = FakeRuntimePipeline()
        dispatcher = dispatcher_module.CommandDispatcher(
            hal=None,
            runtime_pipeline=pipeline,
        )
        result = await dispatcher.handle_command(
            "ble",
            {"type": "stop", "request_id": "stop-pipeline"},
        )

        assert result["status"] == "ok"
        assert dispatcher.safe_executor.stop_called is True
        assert pipeline.abort_called is True

    asyncio.run(run_test())


def test_save_action_command_persists_and_broadcasts_status(tmp_path, monkeypatch):
    import ninja_core.dispatcher as dispatcher_module
    from ninja_core.action_library import ActionLibrary

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        dispatcher.attach_action_library(
            ActionLibrary(tmp_path / "ninja_actions"),
            native_movement_names=["Poweroff"],
        )
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "save_action",
                "request_id": "save-action-1",
                "name": "Happy Wave",
                "workspace_state": {"blocks": []},
                "code": 'from ninja_core import robot\nrobot.expression("happy")\n',
            },
        )

        assert result["status"] == "ok"
        assert result["action_name"] == "Happy Wave"
        assert messages == [
            {
                "type": "action_save_status",
                "protocol_version": "blockly-v1",
                "request_id": "save-action-1",
                "status": "saved",
                "message": "Saved Blockly action 'Happy Wave'",
                "action_name": "Happy Wave",
                "action_slug": "happy-wave",
            }
        ]

    asyncio.run(run_test())


def test_save_action_command_rejects_native_name_conflict(tmp_path, monkeypatch):
    import ninja_core.dispatcher as dispatcher_module
    from ninja_core.action_library import ActionLibrary

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            return None

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        dispatcher = dispatcher_module.CommandDispatcher(hal=None)
        dispatcher.attach_action_library(
            ActionLibrary(tmp_path / "ninja_actions"),
            native_movement_names=["Poweroff"],
        )
        messages = []
        dispatcher.register_listener(messages.append)

        result = await dispatcher.handle_command(
            "ble",
            {
                "type": "save_action",
                "request_id": "save-action-conflict",
                "name": "Poweroff",
                "code": 'print("conflict")',
            },
        )

        assert result["status"] == "error"
        assert result["error_code"] == "action_name_conflict"
        assert messages[0]["type"] == "action_save_status"
        assert messages[0]["status"] == "conflict"
        assert messages[0]["code"] == "action_name_conflict"

    asyncio.run(run_test())


def test_execute_action_chain_replays_saved_action_and_waits(tmp_path, monkeypatch):
    import ninja_core.dispatcher as dispatcher_module
    from ninja_core.action_library import ActionLibrary

    class StubSafeExecutor:
        def __init__(self, hal, on_print=None, runtime_pipeline=None):
            self.code = None

        def execute(self, code, on_complete=None, on_start=None):
            self.code = code
            if on_start:
                on_start()

            async def complete_later():
                await asyncio.sleep(0)
                if on_complete:
                    on_complete({"status": "success", "message": "done", "code": code})

            asyncio.create_task(complete_later())
            return {"status": "started", "message": "Code execution started"}

        def stop(self):
            return None

    class FakeRuntimePipeline:
        def __init__(self):
            self.events = []

        def begin_blockly(self):
            self.events.append("begin")

        def complete_blockly(self, status):
            self.events.append(("complete", status))

    monkeypatch.setattr(dispatcher_module, "SafeExecutor", StubSafeExecutor)
    dispatcher_module.CommandDispatcher._instance = None

    async def run_test():
        action_library = ActionLibrary(tmp_path / "ninja_actions")
        action_library.save_action(
            name="Blink",
            code='from ninja_core import robot\nrobot.display.clear()\n',
        )
        pipeline = FakeRuntimePipeline()
        dispatcher = dispatcher_module.CommandDispatcher(
            hal=None,
            runtime_pipeline=pipeline,
        )
        dispatcher.attach_action_library(action_library)

        result = await dispatcher.execute_action_chain(
            [{"name": "Blink", "repetitions": 2}],
            request_id="action-replay-1",
        )

        assert result["status"] == "started"
        assert result["execution_result"]["status"] == "success"
        assert "for _ninja_action_repeat_0 in range(2):" in dispatcher.safe_executor.code
        assert "    robot.display.clear()" in dispatcher.safe_executor.code
        assert pipeline.events == ["begin", ("complete", "success")]

    asyncio.run(run_test())
