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
