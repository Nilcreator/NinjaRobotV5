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
        self._loop = asyncio.get_running_loop()  # Capture main loop
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
        # Truncate long logs to prevent BLE packet fragmentation issues
        safe_msg = msg[:120] + "..." if len(msg) > 120 else msg
        
        # This is called from the executor thread, so we must schedule it on the main loop.
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.broadcast({
                    "type": "execution_log", 
                    "content": safe_msg
                }))
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

    def _on_execution_complete(self, result: dict):
        """Callback when SafeExecutor finishes/fails."""

        
        # Broadcast status update
        # We need to run incomplete broadcast on loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._process_execution_result(result))
            )
            
    async def _process_execution_result(self, result: dict):
        """Async processor for execution results (running on main loop)."""
        status = result.get("status")
        await self.broadcast({
            "type": "execution_status",
            "status": status,
            "message": result.get("message", "")
        })
        
        # If error, ask NinjaCoderAgent to explain
        if status == "error":
            error_msg = result.get("message", "Unknown error")
            code = result.get("code", "")
            
            # Broadcast the error as a chat message first (immediate feedback)
            await self.broadcast({
                "type": "chat", 
                "sender": "ninja", 
                "text": f"⚠️ Error executing code: {error_msg}"
            })
            
            # Then analyze if we have an agent
            if self.agent: # Use attached NinjaAgent? Or CoderAgent? 
                # Ideally we use NinjaCoderAgent, but Dispatcher doesn't hold reference to it currently.
                # It holds NinjaAgent.
                # We should probably pass CoderAgent to Dispatcher too?
                # Or just let NinjaAgent handle it? NinjaAgent is "general".
                # Let's attach CoderAgent to Dispatcher via attach_coder_agent method.
                if hasattr(self, "coder_agent") and self.coder_agent:
                     analysis = await self.coder_agent.analyze_error(code, error_msg)
                     await self.broadcast({
                        "type": "chat", 
                        "sender": "ninja", 
                        "text": f"💡 Diagnosis: {analysis}"
                     })
                     
    def attach_coder_agent(self, agent):
        """Attach the NinjaCoderAgent."""
        self.coder_agent = agent
        log.info("NinjaCoderAgent attached to Dispatcher.")

    async def _handle_execute_command(self, cmd_data: dict) -> dict:
        """Handle code execution commands (Phase 4 - SafeExecutor + AI Agent)."""
        action = cmd_data.get("action", "run")

        if action == "stop":
            self.safe_executor.stop()
            return {"status": "ok", "message": "Stop signal sent"}

        code = cmd_data.get("code", "")

        # Log the received command
        log.info(f"[EXECUTE] Code received ({len(code)} chars)")

        if not code:
            return {"status": "error", "message": "No code provided"}

        # Broadcast received confirmation with FULL code for system log
        await self.broadcast({
            "type": "execute_received",
            "code_length": len(code),
            "full_code": code,
        })

        # --- AI Translation / Optimization Step ---
        if self.coder_agent:
            # Notify Chat with a detailed message about what was received
            # Extract key actions from code for description
            actions_found = []
            if "buzzer.play" in code or "buzzer.tone" in code:
                actions_found.append("🔊 Sound")
            if "display.image" in code or "display.clear" in code:
                actions_found.append("🖼️ Display")
            if "distance.read" in code:
                actions_found.append("📏 Distance Sensor")
            if "servo" in code.lower():
                actions_found.append("🦾 Servo")
            
            actions_desc = ", ".join(actions_found) if actions_found else "custom logic"
            
            await self.broadcast({
                "type": "chat",
                "sender": "ninja",
                "text": f"📥 Code received! Detected: {actions_desc}. Optimizing..."
            })

            try:
                # Ask Agent to translate/fix the code
                result_data = await self.coder_agent.translate_code(code)
                translated_code = result_data.get("code", code)
                explanation = result_data.get("explanation", "Code optimized.")

                # If code changed, notify
                if translated_code != code:
                    log.info("Agent optimized the code.")
                    log.debug(f"Original:\n{code}\nTranslated:\n{translated_code}")
                    
                    await self.broadcast({
                        "type": "chat",
                        "sender": "ninja",
                        "text": f"✅ {explanation}", 
                        "optimized_code": translated_code,
                        "original_code": code
                    })
                    code = translated_code
                else:
                    await self.broadcast({
                        "type": "chat",
                        "sender": "ninja",
                        "text": f"✅ Code looks good! {explanation}"
                    })

            except Exception as e:
                log.error(f"Translation failed: {e}")
                await self.broadcast({
                    "type": "chat",
                    "sender": "ninja",
                    "text": f"⚠️ Optimization failed ({e}). Running original code..."
                })
        else:
            log.warning("No CoderAgent attached, skipping translation.")
            await self.broadcast({
                "type": "chat",
                "sender": "ninja",
                "text": "📥 Code received. Executing directly..."
            })

        # Execute SafeExecutor with callback
        result = self.safe_executor.execute(code, on_complete=self._on_execution_complete)

        return result

