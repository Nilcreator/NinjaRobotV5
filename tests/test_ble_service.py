from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types

import pytest

from ninja_ble.chunking import ChunkReassembler


def decode_ble_json_updates(updates):
    reassembler = ChunkReassembler()
    for packet in updates:
        if packet.startswith(b"{"):
            return json.loads(packet.decode("utf-8"))
        complete, payload = reassembler.process_packet(packet)
        if complete:
            return json.loads(payload.decode("utf-8"))
    return None


def test_ble_service_chunks_large_broadcasts(monkeypatch):
    custom_name = "Classroom Ninja 1"

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append(bytes(char.value))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(
        FakeDispatcher(),
        service_name=custom_name,
    )
    service._running = True
    service._server = FakeBlessServer(name=custom_name)

    message = {"type": "chat", "text": "z" * 1800, "category": "chat_response"}

    import asyncio

    asyncio.run(service.on_broadcast(message))

    assert len(service._server.updates) > 3

    reassembler = ChunkReassembler()
    reassembled = None
    for packet in service._server.updates:
        complete, payload = reassembler.process_packet(packet)
        if complete:
            reassembled = payload

    assert reassembled is not None
    assert json.loads(reassembled.decode("utf-8")) == message


def test_ble_service_chunks_mid_sized_save_status_notifications(monkeypatch):
    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append((characteristic_uuid, bytes(char.value)))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(FakeDispatcher())
    service._running = True
    service._server = FakeBlessServer()

    message = {
        "type": "action_save_status",
        "protocol_version": "ble-chunk-v1",
        "request_id": "save-action-1",
        "status": "conflict",
        "message": "Action already exists. Please choose a new name.",
        "code": "action_name_conflict",
        "action_name": "A Very Long Blockly Movement Name",
        "action_slug": "a-very-long-blockly-movement-name",
        "can_overwrite": False,
    }

    asyncio.run(service.on_broadcast(message))

    response_updates = [
        payload
        for characteristic_uuid, payload in service._server.updates
        if characteristic_uuid == service_module.CHAR_RESPONSE_UUID
    ]
    assert len(response_updates) > 1

    reassembler = ChunkReassembler()
    reassembled = None
    for packet in response_updates:
        complete, payload = reassembler.process_packet(packet)
        if complete:
            reassembled = payload

    assert reassembled is not None
    assert json.loads(reassembled.decode("utf-8")) == message


def test_ble_service_answers_robot_info_from_configured_name(monkeypatch):
    custom_name = "NinjaV4 Sasuke"

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append(bytes(char.value))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def __init__(self):
            self.commands = []

        def register_listener(self, listener):
            self.listener = listener

        async def handle_command(self, source, command):
            self.commands.append((source, command))
            return {"status": "unexpected"}

    dispatcher = FakeDispatcher()
    service = service_module.NinjaBLEService(
        dispatcher,
        service_name=custom_name,
        robot_profile={
            "robot_type": "humanoid",
            "robot_type_label": "Humanoid",
            "api_keys": {"gemini": "SECRET"},
            "hardware_configuration": {
                "servos": {
                    "gpio_pins": [12, 13],
                    "calibration": {
                        "12": {"center_pulse": 1500},
                    },
                },
            },
        },
    )
    service._running = True
    service._server = FakeBlessServer(name=custom_name)

    async def dispatch_robot_info():
        service._handle_legacy_json(
            json.dumps(
                {
                    "type": "robot_info",
                    "request_id": "robot-info-1",
                }
            ).encode("utf-8")
        )
        for _ in range(5):
            await asyncio.sleep(0)

    asyncio.run(dispatch_robot_info())

    assert dispatcher.commands == []
    assert service._server.updates

    reassembler = ChunkReassembler()
    reassembled = None
    for packet in service._server.updates:
        if packet.startswith(b"{"):
            reassembled = packet
            break
        complete, payload = reassembler.process_packet(packet)
        if complete:
            reassembled = payload

    assert reassembled is not None
    message = json.loads(reassembled.decode("utf-8"))
    assert message["type"] == "robot_info"
    assert message["request_id"] == "robot-info-1"
    assert message["service_name"] == custom_name
    assert message["name"] == custom_name
    assert message["robot_type"] == "humanoid"
    assert message["hardware_configuration"]["servos"]["gpio_pins"] == [12, 13]
    assert "api_keys" not in message


def test_ble_service_robot_info_falls_back_when_profile_provider_fails(monkeypatch):
    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append(bytes(char.value))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    def failing_provider():
        raise RuntimeError("profile unavailable")

    service = service_module.NinjaBLEService(
        FakeDispatcher(),
        service_name="Fallback Ninja",
        robot_info_provider=failing_provider,
    )
    service._running = True
    service._server = FakeBlessServer()

    async def dispatch_robot_info():
        service._handle_legacy_json(
            json.dumps({"type": "robot_info", "request_id": "robot-info-fallback"}).encode("utf-8")
        )
        for _ in range(20):
            await asyncio.sleep(0)

    asyncio.run(dispatch_robot_info())

    message = decode_ble_json_updates(service._server.updates)
    assert message["type"] == "robot_info"
    assert message["service_name"] == "Fallback Ninja"
    assert message["profile_error"] == "RuntimeError"


def test_ble_service_chunks_robot_info_profile(monkeypatch):
    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append(bytes(char.value))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    calibration = {
        str(pin): {
            "min_pulse": 500,
            "center_pulse": 1500,
            "max_pulse": 2500,
            "angle_range": 180,
            "speed": 80,
        }
        for pin in range(2, 28)
    }
    service = service_module.NinjaBLEService(
        FakeDispatcher(),
        service_name="Profile Ninja",
        robot_profile={
            "robot_type": "spider",
            "hardware_configuration": {
                "servos": {
                    "gpio_pins": list(range(2, 28)),
                    "calibration": calibration,
                },
            },
        },
    )
    service._running = True
    service._server = FakeBlessServer()

    async def dispatch_robot_info():
        service._handle_legacy_json(
            json.dumps({"type": "robot_info", "request_id": "robot-info-large"}).encode("utf-8")
        )
        for _ in range(100):
            await asyncio.sleep(0)

    asyncio.run(dispatch_robot_info())

    assert len(service._server.updates) > 1
    message = decode_ble_json_updates(service._server.updates)
    assert message is not None
    assert message["type"] == "robot_info"
    assert message["robot_type"] == "spider"
    assert message["hardware_configuration"]["servos"]["gpio_pins"] == list(range(2, 28))


def test_ble_service_reads_cached_command_response(monkeypatch):
    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }
            self.updates = []

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            char = self._characteristics[characteristic_uuid]
            self.updates.append((characteristic_uuid, bytes(char.value)))

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def __init__(self):
            self.commands = []

        def register_listener(self, listener):
            self.listener = listener

        async def handle_command(self, source, command):
            self.commands.append((source, command))
            return {"status": "unexpected"}

    dispatcher = FakeDispatcher()
    service = service_module.NinjaBLEService(dispatcher)
    service._running = True
    service._server = FakeBlessServer()
    save_event = {
        "type": "action_save_status",
        "protocol_version": "ble-chunk-v1",
        "request_id": "save-action-1",
        "status": "saved",
        "message": "Saved Blockly action",
        "action_name": "Wave",
        "action_slug": "wave",
    }

    async def dispatch_status_query():
        await service.on_broadcast(save_event)
        service._handle_legacy_json(
            json.dumps(
                {
                    "type": "get_command_response",
                    "request_id": "save-action-1",
                }
            ).encode("utf-8")
        )
        await asyncio.sleep(0)

    asyncio.run(dispatch_status_query())

    assert dispatcher.commands == []
    status_char = service._server.get_characteristic(service_module.CHAR_STATUS_UUID)
    assert json.loads(status_char.value.decode("utf-8")) == save_event


def test_ble_service_reports_pending_command_response(monkeypatch):
    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
                "00000004-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray()),
            }

        def get_characteristic(self, uuid):
            return self._characteristics.get(uuid)

        def update_value(self, service_uuid, characteristic_uuid):
            return None

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(FakeDispatcher())
    service._running = True
    service._server = FakeBlessServer()
    service._pending_command_requests.add("save-action-pending")

    async def dispatch_status_query():
        service._handle_legacy_json(
            json.dumps(
                {
                    "type": "get_command_response",
                    "request_id": "save-action-pending",
                }
            ).encode("utf-8")
        )
        await asyncio.sleep(0)

    asyncio.run(dispatch_status_query())

    status_char = service._server.get_characteristic(service_module.CHAR_STATUS_UUID)
    assert json.loads(status_char.value.decode("utf-8")) == {
        "type": "command_response_status",
        "protocol_version": "blockly-v1",
        "request_id": "save-action-pending",
        "status": "pending",
    }


def test_ble_service_start_accepts_no_return_bless_start(monkeypatch):
    custom_name = "Desk Robot A"

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self.read_request_func = None
            self.write_request_func = None
            self.services = []
            self.characteristics = []
            self.started = False

        async def add_new_service(self, uuid):
            self.services.append(uuid)

        async def add_new_characteristic(
            self,
            service_uuid,
            characteristic_uuid,
            properties,
            permissions,
            value,
        ):
            self.characteristics.append(
                (service_uuid, characteristic_uuid, properties, permissions, value)
            )

        async def start(self):
            self.started = True
            return None

        async def is_advertising(self):
            return self.started

        async def stop(self):
            self.started = False
            return True

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(
        FakeDispatcher(),
        service_name=custom_name,
    )

    import asyncio

    asyncio.run(service.start())

    assert service.is_running is True
    assert service.service_name == custom_name
    assert service._server.name == custom_name
    assert service._server.services == [service_module.SERVICE_UUID]
    assert len(service._server.characteristics) == 3


def test_ble_service_falls_back_to_compact_advertisement_profile(monkeypatch):
    custom_name = "Lab Robot 02"
    created_servers = []

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self.read_request_func = None
            self.write_request_func = None
            self.services = []
            self.characteristics = []
            self.started = False
            self.stopped = False
            created_servers.append(self)

        async def add_new_service(self, uuid):
            self.services.append(uuid)

        async def add_new_characteristic(
            self,
            service_uuid,
            characteristic_uuid,
            properties,
            permissions,
            value,
        ):
            self.characteristics.append(
                (service_uuid, characteristic_uuid, properties, permissions, value)
            )

        async def start(self):
            if len(created_servers) == 1:
                raise RuntimeError("Failed to register advertisement")
            self.started = True
            return True

        async def is_advertising(self):
            return self.started

        async def stop(self):
            self.stopped = True
            self.started = False
            return True

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(
        FakeDispatcher(),
        service_name=custom_name,
    )
    advertisement_profiles = []

    def fake_install_bluez_advertisement_patch(advertisement_profile, service_name):
        advertisement_profiles.append((advertisement_profile, service_name))

    service._install_bluez_advertisement_patch = (
        fake_install_bluez_advertisement_patch
    )

    import asyncio

    asyncio.run(service.start())

    assert service.is_running is True
    assert len(created_servers) == 2
    assert created_servers[0].stopped is True
    assert created_servers[1].name == custom_name
    assert advertisement_profiles == [
        ("name_only", custom_name),
        ("service_only", custom_name),
    ]


def test_ble_service_uses_connectable_only_last_resort_profile(monkeypatch):
    created_servers = []

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self.read_request_func = None
            self.write_request_func = None
            self.services = []
            self.characteristics = []
            self.started = False
            created_servers.append(self)

        async def add_new_service(self, uuid):
            self.services.append(uuid)

        async def add_new_characteristic(
            self,
            service_uuid,
            characteristic_uuid,
            properties,
            permissions,
            value,
        ):
            self.characteristics.append(
                (service_uuid, characteristic_uuid, properties, permissions, value)
            )

        async def start(self):
            if len(created_servers) < 3:
                raise RuntimeError("Failed to register advertisement")
            self.started = True
            return True

        async def is_advertising(self):
            return self.started

        async def stop(self):
            self.started = False
            return True

    bless_stub = types.SimpleNamespace(
        BlessServer=FakeBlessServer,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    class FakeDispatcher:
        def register_listener(self, listener):
            self.listener = listener

    service = service_module.NinjaBLEService(FakeDispatcher())
    advertisement_profiles = []

    def fake_install_bluez_advertisement_patch(advertisement_profile, service_name):
        advertisement_profiles.append((advertisement_profile, service_name))

    service._install_bluez_advertisement_patch = (
        fake_install_bluez_advertisement_patch
    )

    import asyncio

    asyncio.run(service.start())

    assert service.is_running is True
    assert [profile for profile, _ in advertisement_profiles] == [
        "name_only",
        "service_only",
        "connectable_only",
    ]


def test_compact_advertisement_properties_are_read_only(monkeypatch):
    pytest.importorskip("dbus_next")
    custom_name = "Robot Shelf 3"

    bless_stub = types.SimpleNamespace(
        BlessServer=object,
        BlessGATTCharacteristic=object,
        GATTCharacteristicProperties=types.SimpleNamespace(
            write=1,
            write_without_response=2,
            read=4,
            notify=8,
        ),
        GATTAttributePermissions=types.SimpleNamespace(
            writeable=1,
            readable=2,
        ),
    )
    monkeypatch.setitem(sys.modules, "bless", bless_stub)
    sys.modules.pop("ninja_ble.service", None)
    service_module = importlib.import_module("ninja_ble.service")

    name_advertisement = (
        service_module.NinjaBLEService._build_bluez_advertisement_class(
            "name_only",
            custom_name,
        )
    )
    service_advertisement = (
        service_module.NinjaBLEService._build_bluez_advertisement_class("service_only")
    )
    connectable_advertisement = (
        service_module.NinjaBLEService._build_bluez_advertisement_class(
            "connectable_only"
        )
    )

    assert name_advertisement.LocalName.access.value == "read"
    assert service_advertisement.ServiceUUIDs.access.value == "read"

    fake_app = types.SimpleNamespace(base_path="/org/ninja")
    fake_type = types.SimpleNamespace(value="peripheral")
    name_only = name_advertisement(fake_type, 0, fake_app)
    service_only = service_advertisement(fake_type, 1, fake_app)
    connectable_only = connectable_advertisement(fake_type, 2, fake_app)

    assert name_only.LocalName == custom_name
    assert service_only.ServiceUUIDs == [service_module.SERVICE_UUID]
    assert connectable_only.Type == "peripheral"
