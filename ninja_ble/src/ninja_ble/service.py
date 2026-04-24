from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions,
)

from ninja_core.config import DEFAULT_BLE_NAME, normalize_ble_name
from ninja_core.contracts import PROTOCOL_VERSION, ensure_request_id
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
SERVICE_NAME = DEFAULT_BLE_NAME
SERVICE_UUID = "00000001-710e-4a5b-8d75-3e5b444bc3cf"

# Command Characteristic (Write): For receiving JSON commands
CHAR_COMMAND_UUID = "00000002-710e-4a5b-8d75-3e5b444bc3cf"

# Response Characteristic (Notify): For sending JSON updates
CHAR_RESPONSE_UUID = "00000003-710e-4a5b-8d75-3e5b444bc3cf"

BLE_ADVERTISEMENT_PROFILES = ("name_only", "service_only", "connectable_only")
BLE_START_ATTEMPTS = len(BLE_ADVERTISEMENT_PROFILES)
BLE_RECOVERY_DELAY_SECONDS = 1.0
BLE_ADAPTER_POWER_CYCLE_SECONDS = 0.75
ADVERTISEMENT_ERROR_FRAGMENT = "register advertisement"
ADVERTISING_NOT_READY_MESSAGE = "BLE advertising did not start"


class NinjaBLEService:
    """BLE GATT Server for NinjaRobot V5."""

    def __init__(
        self,
        dispatcher: CommandDispatcher,
        service_name: str = SERVICE_NAME,
    ):
        self.dispatcher = dispatcher
        self.service_name = normalize_ble_name(service_name)
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

            if self._handle_service_command(command_data):
                return

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

            if self._handle_service_command(command_data):
                return

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

    def _handle_service_command(self, command_data: dict[str, Any]) -> bool:
        """Handle BLE transport commands that should not enter robot runtime."""
        if not isinstance(command_data, dict):
            return False

        if command_data.get("type") != "robot_info":
            return False

        request_id = ensure_request_id(command_data, "robot-info")
        self._schedule_task(
            self.on_broadcast(
                {
                    "type": "robot_info",
                    "protocol_version": PROTOCOL_VERSION,
                    "request_id": request_id,
                    "name": self.service_name,
                    "service_name": self.service_name,
                    "display_name": self.service_name,
                    "ble_name": self.service_name,
                }
            )
        )
        return True

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
        for attempt, advertisement_profile in enumerate(
            BLE_ADVERTISEMENT_PROFILES,
            start=1,
        ):
            try:
                await self._configure_server(advertisement_profile)
                await self._start_configured_server()
            except Exception as exc:
                last_error = exc
                self._running = False
                log.warning(
                    "BLE advertising start attempt %s/%s (%s) failed: %s",
                    attempt,
                    BLE_START_ATTEMPTS,
                    advertisement_profile,
                    self._describe_start_error(exc),
                )
                if attempt == 1 and self._is_recoverable_start_error(exc):
                    await self._recover_adapter_after_start_failure()
                await self._cleanup_server()

                if (
                    attempt >= BLE_START_ATTEMPTS
                    or not self._is_recoverable_start_error(exc)
                ):
                    raise

                await asyncio.sleep(BLE_RECOVERY_DELAY_SECONDS)
                continue

            self._running = True
            log.info(
                "BLE Service '%s' advertising with %s profile...",
                self.service_name,
                advertisement_profile,
            )
            return

        if last_error:
            raise last_error

    async def _configure_server(self, advertisement_profile: str):
        """Create and configure a fresh Bless GATT server instance."""
        await self._cleanup_server()
        self._install_bluez_advertisement_patch(
            advertisement_profile,
            self.service_name,
        )

        # Create server
        self._server = BlessServer(name=self.service_name)

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

    def _describe_start_error(self, exc: Exception) -> str:
        """Return a concise BLE start error with D-Bus detail when available."""
        details = [str(exc) or exc.__class__.__name__]
        dbus_name = getattr(exc, "dbus_error", None) or getattr(exc, "_dbus_error_name", None)
        if dbus_name:
            details.append(f"D-Bus error: {dbus_name}")
        return " | ".join(details)

    async def _recover_adapter_after_start_failure(self) -> bool:
        """Best-effort BlueZ adapter reset for transient advertisement failures."""
        server = self._server
        adapter = getattr(server, "adapter", None)
        if adapter is None:
            return False

        try:
            from dbus_next.signature import Variant

            iface = adapter.get_interface("org.freedesktop.DBus.Properties")
            await iface.call_set("org.bluez.Adapter1", "Powered", Variant("b", False))
            await asyncio.sleep(BLE_ADAPTER_POWER_CYCLE_SECONDS)
            await iface.call_set("org.bluez.Adapter1", "Powered", Variant("b", True))
            await asyncio.sleep(BLE_ADAPTER_POWER_CYCLE_SECONDS)
            log.info("Power-cycled Bluetooth adapter after advertisement start failure.")
            return True
        except Exception as exc:
            log.debug("Bluetooth adapter recovery skipped/failed: %s", exc)
            return False

    def _install_bluez_advertisement_patch(
        self,
        advertisement_profile: str,
        service_name: str,
    ):
        """Patch Bless on BlueZ to use compact legacy advertisements for Chrome."""
        if sys.platform != "linux":
            return

        try:
            from bless.backends.bluezdbus.dbus import application
        except ImportError as exc:
            log.debug("BlueZ advertisement patch unavailable: %s", exc)
            return

        original_advertisement = getattr(
            application,
            "_ninja_original_BlueZLEAdvertisement",
            None,
        )
        if original_advertisement is None:
            application._ninja_original_BlueZLEAdvertisement = (
                application.BlueZLEAdvertisement
            )

        application.BlueZLEAdvertisement = self._build_bluez_advertisement_class(
            advertisement_profile,
            service_name,
        )

    @staticmethod
    def _build_bluez_advertisement_class(
        advertisement_profile: str,
        service_name: str = SERVICE_NAME,
    ):
        """Build a minimal LEAdvertisement1 class compatible with BlueZ legacy ads."""
        from dbus_next import PropertyAccess
        from dbus_next.service import ServiceInterface, dbus_property, method

        include_service_uuid = advertisement_profile == "service_only"
        include_local_name = advertisement_profile == "name_only"
        connectable_only = advertisement_profile == "connectable_only"

        class BaseNinjaAdvertisement(ServiceInterface):
            interface_name = "org.bluez.LEAdvertisement1"

            def __init__(self, advertising_type, index: int, app):
                self.path = app.base_path + "/advertisement" + str(index)
                self._type = advertising_type.value
                self._service_uuids: list[str] = []
                self._local_name = service_name
                super().__init__(self.interface_name)

            @method()
            def Release(self):  # noqa: N802
                log.debug("%s: Released", self.path)

            @dbus_property(access=PropertyAccess.READ)
            def Type(self) -> "s":  # type: ignore # noqa: F821 N802
                return self._type

        if connectable_only:
            return BaseNinjaAdvertisement

        if include_service_uuid:

            class NinjaServiceAdvertisement(BaseNinjaAdvertisement):
                @dbus_property(access=PropertyAccess.READ)
                def ServiceUUIDs(self) -> "as":  # type: ignore # noqa: F821 F722 N802
                    return self._service_uuids

            return NinjaServiceAdvertisement

        if include_local_name:

            class NinjaNameAdvertisement(BaseNinjaAdvertisement):
                @dbus_property(access=PropertyAccess.READ)
                def LocalName(self) -> "s":  # type: ignore # noqa: F821 N802
                    return self._local_name

            return NinjaNameAdvertisement

        raise ValueError(
            f"Unsupported BLE advertisement profile: {advertisement_profile}"
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
