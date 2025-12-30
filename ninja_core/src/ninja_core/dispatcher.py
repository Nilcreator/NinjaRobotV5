import asyncio
import logging
from typing import Any, Optional, Callable, List

from .hal import HardwareAbstractionLayer

log = logging.getLogger(__name__)

class CommandDispatcher:
    """
    Central hub for routing commands from various sources (BLE, Web)
    to the appropriate handlers (HAL, Agent) and broadcasting updates back.
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
        self._listeners: List[Callable[[dict], Any]] = []  # List of broadcast callbacks
        self._initialized = True
        log.info("CommandDispatcher initialized.")

    def attach_hal(self, hal: HardwareAbstractionLayer):
        """Update the HAL reference if not provided during init."""
        self.hal = hal

    def register_listener(self, callback: Callable[[dict], Any]):
        """Register a callback for broadcasts (e.g., WebSocket send, BLE notify)."""
        self._listeners.append(callback)

    async def broadcast(self, message: dict):
        """Send a message to all registered listeners (WebSockets & BLE)."""
        log.debug(f"Broadcasting: {message}")
        for callback in self._listeners:
            try:
                # If callback is async, await it; otherwise call directly
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                log.error(f"Error in broadcast listener: {e}")

    async def handle_command(self, source: str, command: dict) -> dict:
        """
        Process an incoming command JSON.
        
        Args:
            source: Identifier of the source (e.g., "ble", "web").
            command: The command dictionary. Expected format:
                     { "type": "hal"|"chat", "command": str, "payload": dict }
        
        Returns:
            A response dictionary to be sent back to the requester (or broadcasted).
        """
        log.info(f"Received command from {source}: {command}")
        
        cmd_type = command.get("type")
        
        try:
            if cmd_type == "hal":
                return await self._handle_hal_command(command)
            elif cmd_type == "chat":
                # For chat, we might just broadcast the user's text for now
                # In Step 3, we'll hook up the actual AI Agent here.
                # Broadcasting ensures 'echo' to other clients.
                await self.broadcast({"type": "chat", "sender": "user", "text": command.get("text")})
                return {"status": "ok", "message": "Chat received"}
            else:
                log.warning(f"Unknown command type: {cmd_type}")
                return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

        except Exception as e:
            log.error(f"Error processing command: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _handle_hal_command(self, cmd_data: dict) -> dict:
        """Handle hardware control commands."""
        # Expected: { "command": "execute", "payload": { "servos": {...}, "buzzer": {...} } }
        if not self.hal:
             return {"status": "error", "message": "HAL not attached"}

        action = cmd_data.get("command")
        payload = cmd_data.get("payload", {})

        if action == "execute":
            # 1. Servo Control
            if "servos" in payload and self.hal.servos:
                # payload["servos"] might be {"angles": [...]} or {"pin":, "angle":}
                self.hal.servos.execute(payload["servos"])
            
            # 2. Buzzer Control
            if "buzzer" in payload and self.hal.buzzer:
                 self.hal.buzzer.execute(payload["buzzer"]) # e.g. {"frequency": 440, "duration": 0.5}
            
            # 3. Display Control
            if "display" in payload and self.hal.display:
                self.hal.display.execute(payload["display"])

            return {"status": "ok", "message": "Executed"}
        
        return {"status": "error", "message": f"Unknown HAL action: {action}"}
