from ninja_ble.chunking import (
    ChunkReassembler,
    create_data_packets,
    create_eof_packet,
    create_header_packet,
)


def test_chunk_reassembler_round_trip():
    acknowledgements = []
    payload = b'{"type":"execute","code":"' + (b"x" * 1400) + b'"}'
    transfer_id = 17

    reassembler = ChunkReassembler(
        on_ack=lambda transfer, phase, seq, status, msg=None: acknowledgements.append(
            (transfer, phase, seq, status, msg)
        )
    )

    is_complete, reassembled = reassembler.process_packet(create_header_packet(payload, transfer_id))
    assert is_complete is False
    assert reassembled is None

    packets = create_data_packets(payload, transfer_id)
    for packet in packets:
        is_complete, reassembled = reassembler.process_packet(packet)
        assert is_complete is False
        assert reassembled is None

    is_complete, reassembled = reassembler.process_packet(
        create_eof_packet(transfer_id, len(packets))
    )

    assert is_complete is True
    assert reassembled == payload
    assert acknowledgements[0] == (transfer_id, "header", 0, "ok", None)
    assert acknowledgements[-1] == (transfer_id, "eof", -1, "complete", None)


def test_chunk_reassembler_rejects_unexpected_transfer_id():
    acknowledgements = []
    payload = b"payload"

    reassembler = ChunkReassembler(
        on_ack=lambda transfer, phase, seq, status, msg=None: acknowledgements.append(
            (transfer, phase, seq, status, msg)
        )
    )

    reassembler.process_packet(create_header_packet(payload, 5))
    is_complete, reassembled = reassembler.process_packet(create_data_packets(payload, 6)[0])

    assert is_complete is False
    assert reassembled is None
    assert acknowledgements[-1] == (6, "data", 0, "error", "Unexpected transfer ID")
