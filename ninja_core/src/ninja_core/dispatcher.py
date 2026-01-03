import asyncio
import logging
from typing import Any, Optional, Callable, List

from .hal import HardwareAbstractionLayer
from .safe_executor import SafeExecutor

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

    def __init__(self, hal: Optional[HardwareAbstractionLayer] = None):
        # Singleton init check
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.hal = hal
        self.agent = None  # NinjaAgent instance (set via attach_agent)
        # Initialize SafeExecutor with callback for broadcasting logs
        self.safe_executor = SafeExecutor(
            self.hal, 
            on_print=self._on_executor_print
        )
        self._listeners: List[Callable[[dict], Any]] = []
        self._initialized = True
        log.info("CommandDispatcher initialized.")

    def attach_hal(self, hal: HardwareAbstractionLayer):
        """Update the HAL reference if not provided during init."""
        self.hal = hal
        if self.safe_executor:
            self.safe_executor.hal = hal

    def attach_agent(self, agent):
        """Attach the NinjaAgent for processing chat commands."""
        self.agent = agent
        log.info("NinjaAgent attached to Dispatcher.")

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
        # Use asyncio.run_coroutine_threadsafe if called from thread?
        # SafeExecutor runs in a thread. Broadcast is async.
        # We need to bridge the thread to the event loop.
        # However, _on_executor_print is called from the executor thread.
        # We can't await here directly if the loop is in another thread.
        # Assuming Dispatcher lives in Main Loop.
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
             # Creating task might not work if we are in another thread without loop context?
             # No, asyncio.create_task requires running loop in current thread usually?
             # Actually, loop.call_soon_threadsafe is better.
             loop.call_soon_threadsafe(
                 lambda: asyncio.create_task(self.broadcast({
                     "type": "execution_log", 
                     "content": msg
                 }))
             )
        else:
             log.warning("Event loop not running, cannot broadcast log.")

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
        log.info(f"[{source.upper()}] Command type='{cmd_type}' payload={command}")

        try:
            if cmd_type == "hal":
                return await self._handle_hal_command(command)
            elif cmd_type == "chat":
                return await self._handle_chat_command(command)
            elif cmd_type == "execute":
                return await self._handle_execute_command(command)
            elif cmd_type == "stop": # Shortcut for stopping execution
                 self.safe_executor.stop()
                 return {"status": "ok", "message": "Stop signal sent"}
            else:
                log.warning(f"Unknown command type: {cmd_type}")
                return {"status": "error", "message": f"Unknown type: {cmd_type}"}

        except Exception as e:
            log.error(f"Error processing command: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _handle_chat_command(self, cmd_data: dict) -> dict:
        """Process chat commands via NinjaAgent."""
        user_text = cmd_data.get("text", "")

        # Broadcast user message first
        await self.broadcast({"type": "chat", "sender": "user", "text": user_text})

        # If no agent, just echo
        if not self.agent:
            log.warning("No agent attached. Echoing only.")
            return {"status": "ok", "message": "No agent available"}

        # Process with AI Agent
        try:
            result = await self.agent.process_command(user_text)
            response_text = result.get("response", "I couldn't process that.")

            # Broadcast AI response
            await self.broadcast({
                "type": "chat",
                "sender": "ninja",
                "text": response_text,
            })

            return {"status": "ok", "response": response_text}

        except Exception as e:
            log.error(f"Agent error: {e}")
            error_msg = f"Error: {e}"
            await self.broadcast({"type": "chat", "sender": "ninja", "text": error_msg})
            return {"status": "error", "message": str(e)}

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

    async def _handle_execute_command(self, cmd_data: dict) -> dict:
        """Handle code execution commands (Phase 4 - SafeExecutor)."""
        action = cmd_data.get("action", "run")
        
        if action == "stop":
             self.safe_executor.stop()
             return {"status": "ok", "message": "Stop signal sent"}

        code = cmd_data.get("code", "")

        # Log the received command
        log.info(f"[EXECUTE] Code received ({len(code)} chars)")

        if not code:
            return {"status": "error", "message": "No code provided"}

        # Broadcast received confirmation
        await self.broadcast({
            "type": "execute_received",
            "code_length": len(code),
            "preview": code[:500] + ("..." if len(code) > 500 else ""),
        })

        # Execute SafeExecutor
        result = self.safe_executor.execute(code)
        
        # We return the initial status (e.g. "started").
        # Logs will be streamed via _on_executor_print callback.
        return result

