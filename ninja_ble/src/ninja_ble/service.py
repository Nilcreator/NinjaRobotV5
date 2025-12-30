import asyncio
import logging
import json
from typing import Any

from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

from ninja_core.dispatcher import CommandDispatcher

log = logging.getLogger(__name__)

# --- Constants ---
SERVICE_NAME = "NinjaRobot"
SERVICE_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

# Command Characteristic (Write): For receiving JSON commands
CHAR_COMMAND_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

# Response Characteristic (Notify): For sending JSON updates
CHAR_RESPONSE_UUID = "00000003-710e-4a5b-8d75-3e5b444bc3cf"


def read_request(characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
    """Handle read requests. Returns current characteristic value."""
    log.debug(f"Read request for {characteristic.uuid}")
    return characteristic.value or bytearray()


class NinjaBLEService:
    """BLE GATT Server for NinjaRobot V5."""

    def __init__(self, dispatcher: CommandDispatcher):
        self.dispatcher = dispatcher
        self._running = False
        self._server: BlessServer | None = None

        # Register self as listener to Dispatcher broadcasts
        self.dispatcher.register_listener(self.on_broadcast)

    def _write_request(
        self,
        characteristic: BlessGATTCharacteristic,
        value: Any,
        **kwargs,
    ):
        """
        Handle write requests to characteristics.
        This is called by bless when a client writes to a characteristic.
        """
        # Only process writes to the Command characteristic
        if str(characteristic.uuid).lower() == CHAR_COMMAND_UUID.lower():
            try:
                # Decode payload
                if isinstance(value, (bytes, bytearray)):
                    json_str = value.decode("utf-8")
                else:
                    json_str = str(value)

                command_data = json.loads(json_str)
                log.info(f"BLE Command: {command_data}")

                # Forward to Dispatcher (async)
                asyncio.create_task(
                    self.dispatcher.handle_command("ble", command_data)
                )

            except json.JSONDecodeError:
                log.error("BLE Write Error: Invalid JSON")
            except Exception as e:
                log.error(f"BLE Write Error: {e}")

    async def start(self):
        """Start the GATT Server."""
        log.info("Starting BLE Service...")

        # Create server with callbacks
        self._server = BlessServer(
            name=SERVICE_NAME,
            read_request_func=read_request,
            write_request_func=self._write_request,
        )

        # Add Service
        await self._server.add_new_service(SERVICE_UUID)

        # Add Command Characteristic (Write)
        await self._server.add_new_characteristic(
            SERVICE_UUID,
            CHAR_COMMAND_UUID,
            properties=(
                GATTCharacteristicProperties.write
                | GATTCharacteristicProperties.write_without_response
            ),
            permissions=GATTAttributePermissions.writeable,
            value=bytearray(b""),
        )

        # Add Response Characteristic (Notify)
        await self._server.add_new_characteristic(
            SERVICE_UUID,
            CHAR_RESPONSE_UUID,
            properties=(
                GATTCharacteristicProperties.read
                | GATTCharacteristicProperties.notify
            ),
            permissions=GATTAttributePermissions.readable,
            value=bytearray(b"{}"),
        )

        # Start Advertising
        started = await self._server.start()

        if started:
            self._running = True
            log.info(f"BLE Service '{SERVICE_NAME}' advertising...")
        else:
            log.error("Failed to start BLE advertising")

    async def stop(self):
        """Stop the GATT Server."""
        if self._running and self._server:
            await self._server.stop()
            self._running = False
            log.info("BLE Service stopped")

    async def on_broadcast(self, message: dict):
        """
        Handle broadcast from Dispatcher (AI Response / Status).
        Encodes JSON -> bytes -> BLE Notify.
        """
        if not self._running or not self._server:
            return

        try:
            # Encode response
            json_str = json.dumps(message)
            payload = bytearray(json_str.encode("utf-8"))

            # Update characteristic value (triggers notify)
            char = self._server.get_characteristic(CHAR_RESPONSE_UUID)
            if char:
                char.value = payload
                self._server.update_value(SERVICE_UUID, CHAR_RESPONSE_UUID)
                log.debug(f"BLE Notify: {message}")

        except Exception as e:
            log.error(f"BLE Broadcast Error: {e}")
