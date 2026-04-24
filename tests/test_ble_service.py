from __future__ import annotations

import importlib
import json
import sys
import types

import pytest

from ninja_ble.chunking import ChunkReassembler


def test_ble_service_chunks_large_broadcasts(monkeypatch):
    custom_name = "Classroom Ninja 1"

    class FakeBlessServer:
        def __init__(self, name=None):
            self.name = name
            self._characteristics = {
                "00000003-710e-4a5b-8d75-3e5b444bc3cf": types.SimpleNamespace(value=bytearray())
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
    assert len(service._server.characteristics) == 2


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

    service_only._service_uuids.append(service_module.SERVICE_UUID)

    assert name_only.LocalName == custom_name
    assert service_only.ServiceUUIDs == [service_module.SERVICE_UUID]
    assert connectable_only.Type == "peripheral"
