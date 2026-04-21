"""ninja_ble - BLE GATT Server for NinjaRobot V5."""

from .chunking import ChunkReassembler, PACKET_HEADER, PACKET_DATA, PACKET_EOF

try:
    from .service import NinjaBLEService
except ModuleNotFoundError:
    NinjaBLEService = None

__all__ = [
    "NinjaBLEService",
    "ChunkReassembler",
    "PACKET_HEADER",
    "PACKET_DATA",
    "PACKET_EOF",
]
