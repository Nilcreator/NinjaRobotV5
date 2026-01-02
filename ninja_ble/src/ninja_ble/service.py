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
from .chunking import ChunkReassembler, PACKET_HEADER, PACKET_DATA, PACKET_EOF

log = logging.getLogger(__name__)

# --- Constants ---
SERVICE_NAME = "NinjaRobot"
SERVICE_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

# Command Characteristic (Write): For receiving JSON commands
CHAR_COMMAND_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

# Response Characteristic (Notify): For sending JSON updates
CHAR_RESPONSE_UUID = "00000003-710e-4a5b-8d75-3e5b444bc3cf"


class NinjaBLEService:
    """BLE GATT Server for NinjaRobot V5."""

    def __init__(self, dispatcher: CommandDispatcher):
        self.dispatcher = dispatcher
        self._running = False
        self._server: BlessServer | None = None

        # Chunk reassembler for large payloads
        self._reassembler = ChunkReassembler(on_ack=self._send_ack_sync)

        # Register self as listener to Dispatcher broadcasts
        self.dispatcher.register_listener(self.on_broadcast)

    def _send_ack_sync(self, seq: int, status: str, msg: str | None = None):
        """Synchronous wrapper to send ACK (schedules async task)."""
        ack_msg = {"type": "ack", "seq": seq, "status": status}
        if msg:
            ack_msg["msg"] = msg
        asyncio.create_task(self.on_broadcast(ack_msg))

    def _on_read(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        """Handle read requests. Returns current characteristic value."""
        log.debug(f"Read request for {characteristic.uuid}")
        return characteristic.value if characteristic.value else bytearray(b"{}")

    def _on_write(
        self,
        characteristic: BlessGATTCharacteristic,
        value: Any,
        **kwargs,
    ):
        """Handle write requests to characteristics."""
        log.debug(f"Write to {characteristic.uuid}: len={len(value) if value else 0}")

        # Only process writes to the Command characteristic
        char_uuid = str(characteristic.uuid).lower()
        if CHAR_COMMAND_UUID.lower() not in char_uuid:
            return

        if not value or len(value) == 0:
            return

        # Convert to bytes if needed
        if isinstance(value, bytearray):
            data = bytes(value)
        elif isinstance(value, bytes):
            data = value
        else:
            data = str(value).encode("utf-8")

        # Check for chunked packet (first byte is packet type)
        if data[0] in (PACKET_HEADER, PACKET_DATA, PACKET_EOF):
            complete, payload = self._reassembler.process_packet(data)
            if complete and payload:
                self._dispatch_payload(payload)
        else:
            # Legacy: Direct JSON command (backward compatible)
            self._handle_legacy_json(data)

    def _handle_legacy_json(self, data: bytes):
        """Handle legacy single-packet JSON commands."""
        try:
            json_str = data.decode("utf-8")
            command_data = json.loads(json_str)
            log.info(f"BLE Command (legacy): {command_data}")

            asyncio.create_task(
                self.dispatcher.handle_command("ble", command_data)
            )

        except json.JSONDecodeError:
            log.error("BLE Write Error: Invalid JSON")
        except Exception as e:
            log.error(f"BLE Write Error: {e}")

    def _dispatch_payload(self, payload: bytes):
        """Dispatch a complete reassembled payload."""
        try:
            json_str = payload.decode("utf-8")
            command_data = json.loads(json_str)
            log.info(f"BLE Command (chunked): {command_data}")

            asyncio.create_task(
                self.dispatcher.handle_command("ble", command_data)
            )

        except json.JSONDecodeError:
            log.error("BLE Chunked Payload Error: Invalid JSON")
            asyncio.create_task(
                self.on_broadcast({"type": "error", "msg": "Invalid JSON payload"})
            )
        except Exception as e:
            log.error(f"BLE Chunked Payload Error: {e}")
            asyncio.create_task(
                self.on_broadcast({"type": "error", "msg": str(e)})
            )

    async def start(self):
        """Start the GATT Server."""
        log.info("Starting BLE Service...")

        # Create server
        self._server = BlessServer(name=SERVICE_NAME)

        # Set callbacks AFTER creation (required by bless API)
        self._server.read_request_func = self._on_read
        self._server.write_request_func = self._on_write

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

        # Add Response Characteristic (Notify + Read)
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
