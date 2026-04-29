from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Optional, Callable, Iterable, List

from .contracts import (
    PROTOCOL_VERSION,
    build_action_save_status_event,
    build_chat_event,
    build_error_event,
    build_execution_log_event,
    build_execution_manifest,
    build_execution_status_event,
    build_execute_received_event,
    ensure_request_id,
)
from .action_library import (
    ActionLibrary,
    ActionLibraryError,
    ActionNameConflictError,
    ActionValidationError,
)
from .safe_executor import SafeExecutor
from .runtime_pipeline import RuntimePipeline

if TYPE_CHECKING:
    from .hal import HardwareAbstractionLayer

log = logging.getLogger(__name__)


class CommandDispatcher:
    """
    Central hub for routing commands from various sources (BLE, Web)
    to the appropriate handlers (HAL, Agent, Executor) and broadcasting updates back.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CommandDispatcher, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        hal: Optional[HardwareAbstractionLayer] = None,
        runtime_pipeline: RuntimePipeline | None = None,
    ):
        # Singleton init check
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.hal = hal
        self.agent = None  # NinjaAgent instance (set via attach_agent)
        self.runtime_pipeline = runtime_pipeline
        # Initialize SafeExecutor with callback for broadcasting logs
        self.safe_executor = SafeExecutor(
            self.hal,
            on_print=self._on_executor_print,
            runtime_pipeline=self.runtime_pipeline,
        )
        self._listeners: List[Callable[[dict], Any]] = []
        self._active_request_id: str | None = None
        self.action_library = ActionLibrary()
        self._native_movement_names: set[str] = set()
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        self._initialized = True
        log.info("CommandDispatcher initialized.")

    def attach_hal(self, hal: HardwareAbstractionLayer):
        """Update the HAL reference if not provided during init."""
        self.hal = hal
        if self.runtime_pipeline:
            self.runtime_pipeline.attach_hal(hal)
        if self.safe_executor:
            self.safe_executor.attach_hal(hal)

    def attach_runtime_pipeline(self, runtime_pipeline: RuntimePipeline):
        """Attach the native/Blockly ownership coordinator."""
        self.runtime_pipeline = runtime_pipeline
        if self.hal:
            self.runtime_pipeline.attach_hal(self.hal)
        if self.safe_executor:
            self.safe_executor.attach_runtime_pipeline(runtime_pipeline)

    def attach_faces(self, faces):
        """Share the native face engine with Blockly user code."""
        if self.runtime_pipeline:
            self.runtime_pipeline.attach_faces(faces)
        if self.safe_executor:
            self.safe_executor.attach_faces(faces)

    def attach_agent(self, agent):
        """Attach the NinjaAgent for processing chat commands."""
        self.agent = agent
        log.info("NinjaAgent attached to Dispatcher.")

    def attach_action_library(
        self,
        action_library: ActionLibrary,
        native_movement_names: Optional[Iterable[str]] = None,
    ):
        """Attach the persistent Blockly action library."""
        self.action_library = action_library
        if native_movement_names is not None:
            self._native_movement_names = {str(name) for name in native_movement_names}

    def register_listener(self, callback: Callable[[dict], Any]):
        """Register a callback for broadcasts (e.g., WebSocket send, BLE notify)."""
        self._listeners.append(callback)

    async def broadcast(self, message: dict):
        """Send a message to all registered listeners (WebSockets & BLE)."""
        log.debug(f"Broadcasting: {message}")
        for callback in self._listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                log.error(f"Error in broadcast listener: {e}")

    def _on_executor_print(self, msg: str):
        """Callback for SafeExecutor to broadcast logs."""
        event = build_execution_log_event(self._active_request_id, msg)
        
        # This is called from the executor thread, so we must schedule it on the main loop.
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.broadcast(event))
            )
        else:
             log.warning("Main event loop not available, cannot broadcast log.")

    async def handle_command(self, source: str, command: dict) -> dict:
        """
        Process an incoming command JSON.

        Args:
            source: Identifier of the source (e.g., "ble", "web").
            command: The command dictionary.

        Returns:
            A response dictionary.
        """
        # Log full command for debugging
        cmd_type = command.get("type")
        request_id = ensure_request_id(command)
        log.info(f"[{source.upper()}] Command type='{cmd_type}' payload={command}")

        try:
            if cmd_type == "hal":
                return await self._handle_hal_command(command)
            elif cmd_type == "chat":
                return await self._handle_chat_command(command)
            elif cmd_type == "execute":
                return await self._handle_execute_command(command)
            elif cmd_type == "save_action":
                return await self._handle_save_action_command(command)
            elif cmd_type == "stop": # Shortcut for stopping execution
                 self.safe_executor.stop()
                 if self.runtime_pipeline:
                     self.runtime_pipeline.abort_blockly()
                 if self._active_request_id:
                     await self.broadcast(
                         build_execution_status_event(
                             self._active_request_id,
                             "stop_requested",
                             "Stop requested by user",
                         )
                     )
                 return {
                     "status": "ok",
                     "message": "Stop signal sent",
                     "request_id": request_id,
                     "protocol_version": PROTOCOL_VERSION,
                 }
            else:
                log.warning(f"Unknown command type: {cmd_type}")
                return {
                    "status": "error",
                    "message": f"Unknown type: {cmd_type}",
                    "request_id": request_id,
                    "protocol_version": PROTOCOL_VERSION,
                }

        except Exception as e:
            log.error(f"Error processing command: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "request_id": request_id,
                "protocol_version": PROTOCOL_VERSION,
            }

    async def _handle_chat_command(self, cmd_data: dict) -> dict:
        """Process chat commands via NinjaAgent."""
        user_text = cmd_data.get("text", "")
        request_id = ensure_request_id(cmd_data, "chat")

        # Broadcast user message first
        await self.broadcast(
            build_chat_event(
                user_text,
                sender="user",
                request_id=request_id,
                category="chat_input",
            )
        )

        # If no agent, just echo
        if not self.agent:
            log.warning("No agent attached. Echoing only.")
            return {"status": "ok", "message": "No agent available"}

        # Process with AI Agent
        try:
            result = await self.agent.process_command(user_text)
            response_text = result.get("response", "I couldn't process that.")

            # Broadcast AI response
            await self.broadcast(
                build_chat_event(
                    response_text,
                    sender="ninja",
                    request_id=request_id,
                    category="chat_response",
                )
            )

            return {
                "status": "ok",
                "response": response_text,
                "request_id": request_id,
                "protocol_version": PROTOCOL_VERSION,
            }

        except Exception as e:
            log.error(f"Agent error: {e}")
            error_msg = f"Error: {e}"
            await self.broadcast(
                build_chat_event(
                    error_msg,
                    sender="ninja",
                    request_id=request_id,
                    category="chat_error",
                )
            )
            return {
                "status": "error",
                "message": str(e),
                "request_id": request_id,
                "protocol_version": PROTOCOL_VERSION,
            }

    async def _handle_hal_command(self, cmd_data: dict) -> dict:
        """Handle hardware control commands."""
        if not self.hal:
            return {"status": "error", "message": "HAL not attached"}

        action = cmd_data.get("command")
        payload = cmd_data.get("payload", {})

        if action == "execute":
            if "servos" in payload and self.hal.servos:
                self.hal.servos.execute(payload["servos"])

            if "buzzer" in payload and self.hal.buzzer:
                self.hal.buzzer.execute(payload["buzzer"])

            if "display" in payload and self.hal.display:
                self.hal.display.execute(payload["display"])

            return {"status": "ok", "message": "Executed"}

        return {"status": "error", "message": f"Unknown HAL action: {action}"}

    async def _handle_save_action_command(self, cmd_data: dict) -> dict:
        """Persist a complete Blockly action without executing it."""
        request_id = ensure_request_id(cmd_data, "save-action")
        manifest = build_execution_manifest(cmd_data.get("manifest"))

        try:
            record = self.action_library.save_action(
                name=cmd_data.get("name", ""),
                code=cmd_data.get("code", ""),
                workspace_state=cmd_data.get("workspace_state"),
                manifest=manifest,
                native_movement_names=self._native_movement_names,
                overwrite=bool(cmd_data.get("overwrite", False)),
            )
        except ActionNameConflictError as exc:
            event = build_action_save_status_event(
                request_id,
                "conflict",
                str(exc),
                action_name=exc.action_name or str(cmd_data.get("name", "")),
                action_slug=exc.action_slug,
                code="action_name_conflict",
                can_overwrite=exc.can_overwrite,
            )
            await self.broadcast(event)
            return {
                "status": "error",
                "error_code": "action_name_conflict",
                "message": str(exc),
                "request_id": request_id,
                "protocol_version": manifest["protocol_version"],
                "manifest": manifest,
                "save_status": "conflict",
                "action_name": exc.action_name or str(cmd_data.get("name", "")),
                "action_slug": exc.action_slug,
                "can_overwrite": exc.can_overwrite,
            }
        except ActionValidationError as exc:
            event = build_action_save_status_event(
                request_id,
                "error",
                str(exc),
                action_name=str(cmd_data.get("name", "")),
                code="action_validation_failed",
            )
            await self.broadcast(event)
            return {
                "status": "error",
                "error_code": "action_validation_failed",
                "message": str(exc),
                "request_id": request_id,
                "protocol_version": manifest["protocol_version"],
                "manifest": manifest,
                "save_status": "error",
                "action_name": str(cmd_data.get("name", "")),
            }
        except ActionLibraryError as exc:
            event = build_action_save_status_event(
                request_id,
                "error",
                str(exc),
                action_name=str(cmd_data.get("name", "")),
                code="action_save_failed",
            )
            await self.broadcast(event)
            return {
                "status": "error",
                "error_code": "action_save_failed",
                "message": str(exc),
                "request_id": request_id,
                "protocol_version": manifest["protocol_version"],
                "manifest": manifest,
                "save_status": "error",
                "action_name": str(cmd_data.get("name", "")),
            }
        except Exception as exc:
            event = build_action_save_status_event(
                request_id,
                "error",
                str(exc),
                action_name=str(cmd_data.get("name", "")),
                code="action_save_failed",
            )
            await self.broadcast(event)
            return {
                "status": "error",
                "error_code": "action_save_failed",
                "message": str(exc),
                "request_id": request_id,
                "protocol_version": manifest["protocol_version"],
                "manifest": manifest,
                "save_status": "error",
                "action_name": str(cmd_data.get("name", "")),
            }

        if self.agent and hasattr(self.agent, "refresh_capabilities"):
            self.agent.refresh_capabilities()

        event = build_action_save_status_event(
            request_id,
            "overwritten" if record.get("overwritten") else "saved",
            (
                f"Overwrote Blockly action '{record['name']}'"
                if record.get("overwritten")
                else f"Saved Blockly action '{record['name']}'"
            ),
            action_name=record["name"],
            action_slug=record["slug"],
            overwritten=bool(record.get("overwritten", False)),
        )
        await self.broadcast(event)
        return {
            "status": "ok",
            "request_id": request_id,
            "protocol_version": manifest["protocol_version"],
            "manifest": manifest,
            "action_name": record["name"],
            "action_slug": record["slug"],
            "save_status": event["status"],
            "message": event["message"],
            "overwritten": bool(record.get("overwritten", False)),
        }

    async def execute_action_chain(
        self,
        action_chain: list[dict],
        *,
        request_id: str | None = None,
    ) -> dict:
        """Replay saved Blockly actions through the normal SafeExecutor pipeline."""
        resolved_request_id = request_id or ensure_request_id(
            {"type": "action_replay"},
            "action-replay",
        )
        code = self.action_library.build_replay_code(action_chain)
        return await self._handle_execute_command(
            {
                "type": "execute",
                "request_id": resolved_request_id,
                "manifest": {
                    "generator_version": "saved-blockly-action",
                    "source": "ninja-action-library",
                },
                "workspace_state": None,
                "code": code,
                "explain": False,
                "await_completion": True,
            }
        )

    def _on_execution_complete(self, request_id: str, result: dict):
        """Callback when SafeExecutor finishes/fails."""

        
        # Broadcast status update
        # We need to run incomplete broadcast on loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._process_execution_result(request_id, result))
            )
            
    async def _process_execution_result(self, request_id: str, result: dict):
        """Async processor for execution results (running on main loop)."""
        status = result.get("status")
        await self.broadcast(
            build_execution_status_event(
                request_id,
                status,
                result.get("message", ""),
            )
        )

        if self._active_request_id == request_id:
            self._active_request_id = None
            if self.runtime_pipeline:
                self.runtime_pipeline.complete_blockly(status)
        
        # If error, ask NinjaAgent to explain
        if status == "error":
            error_msg = result.get("message", "Unknown error")
            code = result.get("code", "")
            traceback_text = result.get("traceback")

            if traceback_text:
                log.error("Execution %s failed with traceback:\n%s", request_id, traceback_text)

            await self.broadcast(
                build_error_event(
                    "execution_failed",
                    error_msg,
                    request_id=request_id,
                )
            )
            
            # Broadcast the error as a chat message first (immediate feedback)
            await self.broadcast(
                build_chat_event(
                    f"⚠️ Error executing code: {error_msg}",
                    sender="ninja",
                    request_id=request_id,
                    category="execution_error",
                )
            )
            
            # Use MAIN agent for analysis
            if self.agent:
                 analysis = await self.agent.analyze_error(code, error_msg)
                 await self.broadcast(
                    build_chat_event(
                        f"💡 Diagnosis: {analysis}",
                        sender="ninja",
                        request_id=request_id,
                        category="analysis",
                    )
                 )

    async def _handle_execute_command(self, cmd_data: dict) -> dict:
        """Handle code execution commands (Direct Execution + AI Explanation)."""
        action = cmd_data.get("action", "run")
        request_id = ensure_request_id(cmd_data, "execute")
        manifest = build_execution_manifest(cmd_data.get("manifest"))

        if action == "stop":
            self.safe_executor.stop()
            if self.runtime_pipeline:
                self.runtime_pipeline.abort_blockly()
            if self._active_request_id:
                await self.broadcast(
                    build_execution_status_event(
                        self._active_request_id,
                        "stop_requested",
                        "Stop requested by user",
                    )
                )
            return {
                "status": "ok",
                "message": "Stop signal sent",
                "request_id": request_id,
                "protocol_version": PROTOCOL_VERSION,
            }

        code = cmd_data.get("code", "")
        workspace_state = cmd_data.get("workspace_state")
        explain = cmd_data.get("explain", True)
        await_completion = bool(cmd_data.get("await_completion"))

        # Log the received command
        log.info(f"[EXECUTE] Code received ({len(code)} chars)")

        if not code:
            return {
                "status": "error",
                "message": "No code provided",
                "request_id": request_id,
                "protocol_version": PROTOCOL_VERSION,
            }

        previous_request_id = self._active_request_id
        self._active_request_id = request_id

        completion_future: asyncio.Future | None = None
        if await_completion:
            loop = self._loop if self._loop and self._loop.is_running() else asyncio.get_running_loop()
            completion_future = loop.create_future()

        def handle_execution_complete(execution_result: dict):
            if completion_future is None:
                self._on_execution_complete(request_id, execution_result)
                return

            loop = self._loop if self._loop and self._loop.is_running() else completion_future.get_loop()

            async def process_and_finish():
                await self._process_execution_result(request_id, execution_result)
                if not completion_future.done():
                    completion_future.set_result(execution_result)

            loop.call_soon_threadsafe(lambda: asyncio.create_task(process_and_finish()))

        result = self.safe_executor.execute(
            code,
            on_complete=handle_execution_complete,
            on_start=self.runtime_pipeline.begin_blockly if self.runtime_pipeline else None,
        )

        if result.get("status") == "error":
            self._active_request_id = previous_request_id
            if result.get("error_code") == "syntax_error":
                await self.broadcast(
                    build_execute_received_event(
                        request_id,
                        code,
                        workspace_state,
                    )
                )
                await self.broadcast(
                    build_execution_status_event(
                        request_id,
                        "error",
                        result.get("message", "Python syntax error"),
                    )
                )
                await self.broadcast(
                    build_error_event(
                        "syntax_error",
                        result.get("message", "Python syntax error"),
                        request_id=request_id,
                        details=result.get("syntax_error"),
                    )
                )
                return {
                    **result,
                    "request_id": request_id,
                    "protocol_version": manifest["protocol_version"],
                    "manifest": manifest,
                }

            await self.broadcast(
                build_error_event(
                    "execute_rejected",
                    result.get("message", "Code execution rejected"),
                    request_id=request_id,
                )
            )
            return {
                **result,
                "request_id": request_id,
                "protocol_version": manifest["protocol_version"],
                "manifest": manifest,
            }

        # 1. Broadcast "received" (Instant feedback)
        await self.broadcast(
            build_execute_received_event(
                request_id,
                code,
                workspace_state,
            )
        )
        await self.broadcast(
            build_execution_status_event(
                request_id,
                "started",
                "Code execution started",
            )
        )

        # 2. Trigger Parallel AI Explanation (Non-blocking)
        if self.agent and explain:
            # Fire and forget explanation task
            asyncio.create_task(self._explain_code_async(request_id, code))
        else:
             await self.broadcast(
                build_chat_event(
                    "🚀 Executing code...",
                    sender="ninja",
                    request_id=request_id,
                    category="execution_status",
                )
            )

        response = {
            **result,
            "request_id": request_id,
            "protocol_version": manifest["protocol_version"],
            "manifest": manifest,
        }
        if completion_future is not None:
            response["execution_result"] = await completion_future
        return response

    async def _explain_code_async(self, request_id: str, code: str):
        """Helper to run code explanation in background."""
        try:
            log.info("Starting background code explanation...")
            explanation = await self.agent.explain_code(code)
            log.info(f"Explanation ready: {explanation[:30]}...")
            
            await self.broadcast(
                build_chat_event(
                    f"🤖 Logic: {explanation}",
                    sender="ninja",
                    request_id=request_id,
                    category="explanation",
                )
            )
            log.info("Explanation broadcast sent.")
        except Exception as e:
            log.error(f"Explanation failed: {e}", exc_info=True)
