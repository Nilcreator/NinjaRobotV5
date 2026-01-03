import unittest
import struct
import binascii
import time
from unittest.mock import MagicMock
from ninja_ble.chunking import (
    ChunkReassembler, 
    ReassemblerState, 
    PACKET_HEADER, 
    PACKET_DATA, 
    PACKET_EOF,
    create_header_packet,
    create_data_packets,
    create_eof_packet
)

class TestChunkingProtocol(unittest.TestCase):
    def setUp(self):
        self.mock_ack = MagicMock()
        self.reassembler = ChunkReassembler(on_ack=self.mock_ack)
        self.payload = b"Hello, NinjaRobot! This is a test payload for chunking."
        self.payload_large = b"A" * 1200 # Larger than 2 chunks (500*2)

    def test_packet_creation_helpers(self):
        """Verify helper functions create correct packet structures."""
        # Header
        header = create_header_packet(self.payload)
        self.assertEqual(header[0], PACKET_HEADER)
        self.assertEqual(len(header), 11) # 1+2+4+4
        
        # Data
        data_packets = create_data_packets(self.payload)
        self.assertTrue(len(data_packets) > 0)
        self.assertEqual(data_packets[0][0], PACKET_DATA)
        
        # EOF
        eof = create_eof_packet(len(data_packets))
        self.assertEqual(eof[0], PACKET_EOF)
        self.assertEqual(len(eof), 3) # 1+2

    def test_successful_reassembly_small(self):
        """Test reassembling a small payload (1 chunk)."""
        # 1. Header
        header = create_header_packet(self.payload)
        complete, res = self.reassembler.process_packet(header)
        self.assertFalse(complete)
        self.assertEqual(self.reassembler._state, ReassemblerState.RECEIVING)
        self.mock_ack.assert_called_with(0, "ok", None)

        # 2. Data
        packets = create_data_packets(self.payload)
        for pkt in packets:
            complete, res = self.reassembler.process_packet(pkt)
            self.assertFalse(complete)
        
        # 3. EOF
        eof = create_eof_packet(len(packets))
        complete, res = self.reassembler.process_packet(eof)
        
        self.assertTrue(complete)
        self.assertEqual(res, self.payload)
        self.assertEqual(self.reassembler._state, ReassemblerState.IDLE)

    def test_successful_reassembly_large(self):
        """Test reassembling a large payload (multiple chunks)."""
        header = create_header_packet(self.payload_large)
        self.reassembler.process_packet(header)
        
        packets = create_data_packets(self.payload_large)
        for pkt in packets:
            self.reassembler.process_packet(pkt)
            
        eof = create_eof_packet(len(packets))
        complete, res = self.reassembler.process_packet(eof)
        
        self.assertTrue(complete)
        self.assertEqual(res, self.payload_large)

    def test_crc_mismatch(self):
        """Test that bad CRC triggers an error."""
        # Create header with correct CRC for ORIGINAL payload
        header = create_header_packet(self.payload)
        self.reassembler.process_packet(header)
        
        # Create data packets for DIFFERENT payload
        corrupted_payload = b"Hello, NinjaRobot! This is a CORRUPTED payload."
        packets = create_data_packets(corrupted_payload)
        for pkt in packets:
            self.reassembler.process_packet(pkt)
            
        eof = create_eof_packet(len(packets))
        complete, res = self.reassembler.process_packet(eof)
        
        self.assertFalse(complete)
        self.assertIsNone(res)
        self.assertEqual(self.reassembler._state, ReassemblerState.ERROR)

    def test_missing_chunks(self):
        """Test reaction to EOF when chunks are missing."""
        header = create_header_packet(self.payload_large)
        self.reassembler.process_packet(header)
        
        packets = create_data_packets(self.payload_large)
        # Skip the last packet
        for pkt in packets[:-1]:
            self.reassembler.process_packet(pkt)
            
        eof = create_eof_packet(len(packets)) # Claim we sent all
        complete, res = self.reassembler.process_packet(eof)
        
        self.assertFalse(complete)
        self.assertEqual(self.reassembler._state, ReassemblerState.ERROR)

if __name__ == '__main__':
    unittest.main()
