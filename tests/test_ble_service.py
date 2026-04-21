from __future__ import annotations

import importlib
import json
import sys
import types

from ninja_ble.chunking import ChunkReassembler


def test_ble_service_chunks_large_broadcasts(monkeypatch):
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

    service = service_module.NinjaBLEService(FakeDispatcher())
    service._running = True
    service._server = FakeBlessServer(name="NinjaRobot")

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

    service = service_module.NinjaBLEService(FakeDispatcher())

    import asyncio

    asyncio.run(service.start())

    assert service.is_running is True
    assert service._server.name == "NinjaRobot"
    assert service._server.services == [service_module.SERVICE_UUID]
    assert len(service._server.characteristics) == 2


def test_ble_service_recovers_from_register_advertisement_failure(monkeypatch):
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

    service = service_module.NinjaBLEService(FakeDispatcher())
    recoveries = []

    async def fake_recover_bluez_advertising():
        recoveries.append(True)

    service._recover_bluez_advertising = fake_recover_bluez_advertising

    import asyncio

    asyncio.run(service.start())

    assert service.is_running is True
    assert len(created_servers) == 2
    assert created_servers[0].stopped is True
    assert created_servers[1].name == "NinjaRobot"
    assert recoveries == [True]
