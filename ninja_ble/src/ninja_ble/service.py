import asyncio
import logging
import json
from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

from ninja_core.dispatcher import CommandDispatcher

log = logging.getLogger(__name__)

# --- constants ---
SERVICE_NAME = "NinjaRobot Service"
SERVICE_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

# Control (Write): For receiving JSON commands (Chat, HAL)
CHAR_COMMAND_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

# Response (Notify): For sending JSON updates (AI response, Status)
CHAR_RESPONSE_UUID = "00000003-710e-4a5b-8d75-3e5b444bc3cf"


class NinjaBLEService:
    def __init__(self, dispatcher: CommandDispatcher):
        self.dispatcher = dispatcher
        self.server = BlessServer(name=SERVICE_NAME)
        self.loop = asyncio.get_event_loop()
        self._running = False
        
        # Register self as listener to Dispatcher broadcasts
        self.dispatcher.register_listener(self.on_broadcast)

    async def start(self):
        """Start the GATT Server."""
        log.info("Starting BLE Service...")
        
        # 1. Add Service
        await self.server.add_new_service(SERVICE_UUID)
        
        # 2. Add Command Characteristic (Write)
        await self.server.add_new_characteristic(
            SERVICE_UUID,
            CHAR_COMMAND_UUID,
            properties=GATTCharacteristicProperties.write,
            permissions=GATTAttributePermissions.writeable,
            value=None,
        )
        
        # 3. Add Response Characteristic (Notify)
        await self.server.add_new_characteristic(
            SERVICE_UUID,
            CHAR_RESPONSE_UUID,
            properties=GATTCharacteristicProperties.notify,
            permissions=GATTAttributePermissions.readable,
            value=None,
        )
        
        # 4. Start Advertising
        self.server.set_write_callback(CHAR_COMMAND_UUID, self.on_write)
        started = await self.server.start()
        
        if started:
            self._running = True
            log.info(f"BLE Service '{SERVICE_NAME}' advertising...")
        else:
            log.error("Failed to start BLE advertising")

    async def stop(self):
        """Stop the GATT Server."""
        if self._running:
            await self.server.stop()
            self._running = False
            log.info("BLE Service stopped")
    
    def on_write(self, characteristic: BlessGATTCharacteristic, value: bytes): 
        """
        Handle incoming write request (Command).
        Decodes bytes -> JSON -> Dispatcher.
        """
        try:
            # Decode payload
            json_str = value.decode("utf-8")
            command_data = json.loads(json_str)
            
            log.debug(f"BLE Write: {command_data}")
            
            # Forward to central Dispatcher
            # Note: handle_command is async, so we create a task
            asyncio.create_task(self.dispatcher.handle_command("ble", command_data))
            
        except json.JSONDecodeError:
            log.error("BLE Write Error: Invalid JSON")
        except Exception as e:
            log.error(f"BLE Write Error: {e}")

    async def on_broadcast(self, message: dict):
        """
        Handle broadcast from Dispatcher (AI Response / Status).
        Encodes JSON -> bytes -> BLE Notify.
        """
        if not self._running:
            return

        try:
            # Encode response
            json_str = json.dumps(message)
            payload = json_str.encode("utf-8")
            
            # Update characteristic (triggers notify if client subscribed)
            # Bless automatically handles notification if connected & subscribed
            self.server.get_characteristic(CHAR_RESPONSE_UUID).value = payload
            self.server.update_value(SERVICE_UUID, CHAR_RESPONSE_UUID)
            
            log.debug(f"BLE Notify: {message}")
            
        except Exception as e:
            log.error(f"BLE Broadcast Error: {e}")
