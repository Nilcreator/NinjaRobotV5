from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from typing import Any

from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

from ninja_core.dispatcher import CommandDispatcher
from .chunking import (
    CHUNK_SIZE,
    PACKET_HEADER,
    PACKET_DATA,
    PACKET_EOF,
    ChunkReassembler,
    create_data_packets,
    create_eof_packet,
    create_header_packet,
)

log = logging.getLogger(__name__)

# --- Constants ---
SERVICE_NAME = "NinjaRobot"
SERVICE_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

# Command Characteristic (Write): For receiving JSON commands
CHAR_COMMAND_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

# Response Characteristic (Notify): For sending JSON updates
CHAR_RESPONSE_UUID = "00000003-710e-4a5b-8d75-3e5b444bc3cf"

BLE_START_ATTEMPTS = 2
BLE_RECOVERY_DELAY_SECONDS = 1.0
ADVERTISEMENT_ERROR_FRAGMENT = "register advertisement"
ADVERTISING_NOT_READY_MESSAGE = "BLE advertising did not start"


class NinjaBLEService:
    """BLE GATT Server for NinjaRobot V5."""

    def __init__(self, dispatcher: CommandDispatcher):
        self.dispatcher = dispatcher
        self._running = False
        self._server: BlessServer | None = None

        # Chunk reassembler for large payloads
        self._reassembler = ChunkReassembler(on_ack=self._send_ack_sync)
        self._notify_lock: asyncio.Lock | None = None
        self._next_outbound_transfer_id = 1
        self._loop: asyncio.AbstractEventLoop | None = None

        # Register self as listener to Dispatcher broadcasts
        self.dispatcher.register_listener(self.on_broadcast)

    @property
    def is_running(self) -> bool:
        """Return whether the BLE server is started and ready to notify clients."""
        return self._running

    def _send_ack_sync(
        self,
        transfer_id: int,
        phase: str,
        seq: int,
        status: str,
        msg: str | None = None,
    ):
        """Synchronous wrapper to send ACK (schedules async task)."""
        ack_msg = {
            "type": "ack",
            "transfer_id": transfer_id,
            "phase": phase,
            "seq": seq,
            "status": status,
        }
        if msg:
            ack_msg["msg"] = msg
        self._schedule_task(self.on_broadcast(ack_msg))

    def _schedule_task(self, coro):
        """Schedule a coroutine from BLE callbacks, even if they run off-loop."""
        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(lambda: asyncio.create_task(coro))
            return

        try:
            asyncio.create_task(coro)
        except RuntimeError:
            log.error("BLE callback fired without a running asyncio loop")
            coro.close()

    def _allocate_outbound_transfer_id(self) -> int:
        transfer_id = self._next_outbound_transfer_id
        self._next_outbound_transfer_id += 1
        if self._next_outbound_transfer_id > 0xFFFFFFFF:
            self._next_outbound_transfer_id = 1
        return transfer_id

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

            self._schedule_task(
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

            self._schedule_task(
                self.dispatcher.handle_command("ble", command_data)
            )

        except json.JSONDecodeError:
            log.error("BLE Chunked Payload Error: Invalid JSON")
            self._schedule_task(
                self.on_broadcast({"type": "error", "msg": "Invalid JSON payload"})
            )
        except Exception as e:
            log.error(f"BLE Chunked Payload Error: {e}")
            self._schedule_task(
                self.on_broadcast({"type": "error", "msg": str(e)})
            )

    async def start(self):
        """Start the GATT Server."""
        log.info("Starting BLE Service...")
        self._loop = asyncio.get_running_loop()
        if self._notify_lock is None:
            self._notify_lock = asyncio.Lock()

        if self._running:
            log.info("BLE Service is already advertising")
            return

        last_error: Exception | None = None
        for attempt in range(1, BLE_START_ATTEMPTS + 1):
            try:
                await self._configure_server()
                await self._start_configured_server()
            except Exception as exc:
                last_error = exc
                self._running = False
                log.warning(
                    "BLE advertising start attempt %s/%s failed: %s",
                    attempt,
                    BLE_START_ATTEMPTS,
                    exc,
                )
                await self._cleanup_server()

                if (
                    attempt >= BLE_START_ATTEMPTS
                    or not self._is_recoverable_start_error(exc)
                ):
                    raise

                await self._recover_bluez_advertising()
                await asyncio.sleep(BLE_RECOVERY_DELAY_SECONDS)
                continue

            self._running = True
            log.info(f"BLE Service '{SERVICE_NAME}' advertising...")
            return

        if last_error:
            raise last_error

    async def _configure_server(self):
        """Create and configure a fresh Bless GATT server instance."""
        await self._cleanup_server()

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

    async def _start_configured_server(self):
        """Start advertising and validate the server reached an active state."""
        if not self._server:
            raise RuntimeError("BLE server has not been configured")

        # Start Advertising
        started = await self._server.start()
        advertising = True
        is_advertising = getattr(self._server, "is_advertising", None)
        if callable(is_advertising):
            try:
                advertising = bool(await is_advertising())
            except Exception as exc:
                log.warning("Could not verify BLE advertising state: %s", exc)

        if started is False or not advertising:
            raise RuntimeError(ADVERTISING_NOT_READY_MESSAGE)

    def _is_recoverable_start_error(self, exc: Exception) -> bool:
        """Return whether a BLE start failure is worth an adapter recovery retry."""
        message = str(exc).lower()
        return (
            ADVERTISEMENT_ERROR_FRAGMENT in message
            or ADVERTISING_NOT_READY_MESSAGE.lower() in message
        )

    async def _cleanup_server(self):
        """Best-effort cleanup for a partially-started Bless server."""
        server = self._server
        self._server = None
        self._running = False
        if not server:
            return

        try:
            await server.stop()
        except Exception as exc:
            log.debug("BLE server cleanup ignored: %s", exc)

    async def _recover_bluez_advertising(self):
        """Recover BlueZ adapter state after a failed advertisement registration."""
        if sys.platform != "linux":
            return

        bluetoothctl = shutil.which("bluetoothctl")
        if not bluetoothctl:
            log.warning("Cannot recover BLE adapter state: bluetoothctl not found")
            return

        log.warning("Recovering BlueZ advertisement state via Bluetooth power cycle")
        await asyncio.to_thread(self._run_bluetoothctl_power, bluetoothctl, "off")
        await asyncio.sleep(BLE_RECOVERY_DELAY_SECONDS)
        await asyncio.to_thread(self._run_bluetoothctl_power, bluetoothctl, "on")

    @staticmethod
    def _run_bluetoothctl_power(bluetoothctl: str, state: str):
        command = [bluetoothctl, "power", state]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("Bluetooth adapter recovery command failed: %s", exc)
            return

        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout).strip()
            log.warning(
                "Bluetooth adapter recovery command returned %s: %s",
                completed.returncode,
                output,
            )

    async def stop(self):
        """Stop the GATT Server."""
        if self._server:
            await self._server.stop()
            self._running = False
            self._loop = None
            log.info("BLE Service stopped")

    async def on_broadcast(self, message: dict):
        """
        Handle broadcast from Dispatcher (AI Response / Status).
        Encodes JSON -> bytes -> BLE Notify.
        """
        if not self._running or not self._server:
            return

        try:
            payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
            await self._notify_payload(payload)
            log.debug(f"BLE Notify: {message}")

        except Exception as e:
            log.error(f"BLE Broadcast Error: {e}")

    async def _notify_payload(self, payload: bytes):
        if self._notify_lock is None:
            self._notify_lock = asyncio.Lock()

        async with self._notify_lock:
            if len(payload) <= CHUNK_SIZE:
                await self._notify_packet(payload)
                return

            transfer_id = self._allocate_outbound_transfer_id()
            data_packets = create_data_packets(payload, transfer_id, CHUNK_SIZE)
            packets = [
                create_header_packet(payload, transfer_id, CHUNK_SIZE),
                *data_packets,
                create_eof_packet(transfer_id, len(data_packets)),
            ]

            for packet in packets:
                await self._notify_packet(packet)
                await asyncio.sleep(0)

    async def _notify_packet(self, payload: bytes):
        if not self._server:
            return

        char = self._server.get_characteristic(CHAR_RESPONSE_UUID)
        if not char:
            return

        char.value = bytearray(payload)
        self._server.update_value(SERVICE_UUID, CHAR_RESPONSE_UUID)
