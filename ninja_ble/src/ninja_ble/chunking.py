"""BLE Chunking Protocol for large payload transfers.

Protocol:
    HEADER (0x01): [0x01][total_chunks:2B][crc32:4B][payload_len:4B]
    DATA   (0x02): [0x02][seq:2B][chunk_data:N bytes]
    EOF    (0x03): [0x03][chunks_received:2B]
"""

import binascii
import logging
import struct
import time
from enum import Enum, auto
from typing import Callable

log = logging.getLogger(__name__)

# Packet type constants
PACKET_HEADER = 0x01
PACKET_DATA = 0x02
PACKET_EOF = 0x03

# Timeout in seconds
TRANSFER_TIMEOUT = 30.0


class ReassemblerState(Enum):
    """State machine states for ChunkReassembler."""

    IDLE = auto()
    RECEIVING = auto()
    COMPLETE = auto()
    ERROR = auto()


class ChunkReassembler:
    """Reassembles chunked BLE packets into complete payloads.

    Usage:
        reassembler = ChunkReassembler(on_ack=send_ack_callback)
        complete, payload = reassembler.process_packet(data)
        if complete:
            # payload contains the full, verified data
    """

    def __init__(self, on_ack: Callable[[int, str, str | None], None] | None = None):
        """Initialize the reassembler.

        Args:
            on_ack: Callback function(seq, status, msg) for sending ACKs.
        """
        self._on_ack = on_ack
        self._reset()

    def _reset(self):
        """Reset state to IDLE."""
        self._state = ReassemblerState.IDLE
        self._expected_chunks = 0
        self._expected_crc = 0
        self._expected_length = 0
        self._chunks: dict[int, bytes] = {}
        self._last_activity = 0.0

    def process_packet(self, data: bytes | bytearray) -> tuple[bool, bytes | None]:
        """Process an incoming packet.

        Args:
            data: Raw packet bytes.

        Returns:
            Tuple of (is_complete, payload).
            - is_complete: True if reassembly finished successfully.
            - payload: The complete payload bytes if complete, else None.
        """
        if len(data) < 1:
            log.warning("Empty packet received")
            return False, None

        # Check for timeout
        if self._state == ReassemblerState.RECEIVING:
            if time.time() - self._last_activity > TRANSFER_TIMEOUT:
                log.warning("Transfer timeout, resetting")
                self._send_ack(-1, "error", "Transfer timeout")
                self._reset()

        packet_type = data[0]

        if packet_type == PACKET_HEADER:
            return self._handle_header(data)
        elif packet_type == PACKET_DATA:
            return self._handle_data(data)
        elif packet_type == PACKET_EOF:
            return self._handle_eof(data)
        else:
            # Not a chunked packet (legacy JSON)
            return False, None

    def _handle_header(self, data: bytes) -> tuple[bool, bytes | None]:
        """Handle HEADER packet: [0x01][total_chunks:2B][crc32:4B][payload_len:4B]."""
        if len(data) < 11:
            log.error(f"HEADER packet too short: {len(data)} bytes")
            self._send_ack(-1, "error", "Invalid HEADER length")
            return False, None

        # Parse header
        total_chunks = struct.unpack_from("<H", data, 1)[0]
        expected_crc = struct.unpack_from("<I", data, 3)[0]
        payload_len = struct.unpack_from("<I", data, 7)[0]

        log.info(
            f"HEADER: chunks={total_chunks}, crc=0x{expected_crc:08X}, len={payload_len}"
        )

        # Reset and initialize
        self._reset()
        self._state = ReassemblerState.RECEIVING
        self._expected_chunks = total_chunks
        self._expected_crc = expected_crc
        self._expected_length = payload_len
        self._last_activity = time.time()

        self._send_ack(0, "ok")
        return False, None

    def _handle_data(self, data: bytes) -> tuple[bool, bytes | None]:
        """Handle DATA packet: [0x02][seq:2B][chunk_data:N bytes]."""
        if self._state != ReassemblerState.RECEIVING:
            log.warning("DATA received but not in RECEIVING state")
            self._send_ack(-1, "error", "Unexpected DATA packet")
            return False, None

        if len(data) < 3:
            log.error(f"DATA packet too short: {len(data)} bytes")
            self._send_ack(-1, "error", "Invalid DATA length")
            return False, None

        seq = struct.unpack_from("<H", data, 1)[0]
        chunk_data = data[3:]

        log.debug(f"DATA: seq={seq}, len={len(chunk_data)}")

        # Store chunk
        self._chunks[seq] = bytes(chunk_data)
        self._last_activity = time.time()

        self._send_ack(seq, "ok")
        return False, None

    def _handle_eof(self, data: bytes) -> tuple[bool, bytes | None]:
        """Handle EOF packet: [0x03][chunks_received:2B]."""
        if self._state != ReassemblerState.RECEIVING:
            log.warning("EOF received but not in RECEIVING state")
            self._send_ack(-1, "error", "Unexpected EOF packet")
            return False, None

        # Check we have all chunks
        received_count = len(self._chunks)
        if received_count != self._expected_chunks:
            log.error(
                f"Missing chunks: got {received_count}, expected {self._expected_chunks}"
            )
            self._send_ack(-1, "error", f"Missing chunks: {received_count}/{self._expected_chunks}")
            self._state = ReassemblerState.ERROR
            return False, None

        # Reassemble payload
        payload = b"".join(self._chunks[i] for i in range(self._expected_chunks))

        # Verify length
        if len(payload) != self._expected_length:
            log.error(
                f"Length mismatch: got {len(payload)}, expected {self._expected_length}"
            )
            self._send_ack(-1, "error", "Length mismatch")
            self._state = ReassemblerState.ERROR
            return False, None

        # Verify CRC32
        actual_crc = binascii.crc32(payload) & 0xFFFFFFFF
        if actual_crc != self._expected_crc:
            log.error(
                f"CRC mismatch: got 0x{actual_crc:08X}, expected 0x{self._expected_crc:08X}"
            )
            self._send_ack(-1, "error", "CRC mismatch")
            self._state = ReassemblerState.ERROR
            return False, None

        log.info(f"Reassembly complete: {len(payload)} bytes, CRC OK")
        self._send_ack(-1, "complete")
        self._state = ReassemblerState.COMPLETE

        # Reset for next transfer
        result = payload
        self._reset()
        return True, result

    def _send_ack(self, seq: int, status: str, msg: str | None = None):
        """Send ACK via callback if registered."""
        if self._on_ack:
            try:
                self._on_ack(seq, status, msg)
            except Exception as e:
                log.error(f"ACK callback error: {e}")


def create_header_packet(payload: bytes) -> bytes:
    """Create a HEADER packet for the given payload.

    Args:
        payload: The complete payload to be chunked.

    Returns:
        HEADER packet bytes.
    """
    crc = binascii.crc32(payload) & 0xFFFFFFFF
    # Assume 512 byte chunks (adjust as needed)
    chunk_size = 500
    total_chunks = (len(payload) + chunk_size - 1) // chunk_size

    return struct.pack("<BHII", PACKET_HEADER, total_chunks, crc, len(payload))


def create_data_packets(payload: bytes, chunk_size: int = 500) -> list[bytes]:
    """Create DATA packets for the given payload.

    Args:
        payload: The complete payload.
        chunk_size: Max chunk size in bytes.

    Returns:
        List of DATA packet bytes.
    """
    packets = []
    for i in range(0, len(payload), chunk_size):
        chunk = payload[i : i + chunk_size]
        seq = i // chunk_size
        packet = struct.pack("<BH", PACKET_DATA, seq) + chunk
        packets.append(packet)
    return packets


def create_eof_packet(chunks_received: int) -> bytes:
    """Create an EOF packet.

    Args:
        chunks_received: Number of chunks received.

    Returns:
        EOF packet bytes.
    """
    return struct.pack("<BH", PACKET_EOF, chunks_received)
