/**
 * Chunking utilities for BLE large payload transfer.
 * Matches the protocol in ninja_ble/chunking.py
 */

import { PACKET_HEADER, PACKET_DATA, PACKET_EOF, CHUNK_SIZE } from './constants';

/**
 * CRC32 lookup table (IEEE polynomial).
 */
const CRC32_TABLE = (() => {
    const table = new Uint32Array(256);
    for (let i = 0; i < 256; i++) {
        let c = i;
        for (let j = 0; j < 8; j++) {
            c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        }
        table[i] = c >>> 0;
    }
    return table;
})();

/**
 * Calculate CRC32 checksum for a Uint8Array.
 * @param {Uint8Array} data - Input data
 * @returns {number} CRC32 value (unsigned 32-bit)
 */
export function crc32(data) {
    let crc = 0xffffffff;
    for (let i = 0; i < data.length; i++) {
        crc = CRC32_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
}

/**
 * Create HEADER packet: [0x01][total_chunks:2B][crc32:4B][payload_len:4B]
 * @param {Uint8Array} payload - Complete payload
 * @param {number} chunkSize - Chunk size (default 500)
 * @returns {Uint8Array} 11-byte HEADER packet
 */
export function createHeaderPacket(payload, chunkSize = CHUNK_SIZE) {
    const totalChunks = Math.ceil(payload.length / chunkSize);
    const checksum = crc32(payload);
    const payloadLen = payload.length;

    const buffer = new ArrayBuffer(11);
    const view = new DataView(buffer);

    view.setUint8(0, PACKET_HEADER);
    view.setUint16(1, totalChunks, true); // Little-endian
    view.setUint32(3, checksum, true);
    view.setUint32(7, payloadLen, true);

    return new Uint8Array(buffer);
}

/**
 * Create DATA packets: [0x02][seq:2B][chunk_data:NB]
 * @param {Uint8Array} payload - Complete payload
 * @param {number} chunkSize - Chunk size (default 500)
 * @returns {Uint8Array[]} Array of DATA packets
 */
export function createDataPackets(payload, chunkSize = CHUNK_SIZE) {
    const packets = [];
    let seq = 0;

    for (let offset = 0; offset < payload.length; offset += chunkSize) {
        const chunk = payload.slice(offset, offset + chunkSize);
        const packet = new Uint8Array(3 + chunk.length);

        packet[0] = PACKET_DATA;
        // Sequence number (little-endian 16-bit)
        packet[1] = seq & 0xff;
        packet[2] = (seq >> 8) & 0xff;
        packet.set(chunk, 3);

        packets.push(packet);
        seq++;
    }

    return packets;
}

/**
 * Create EOF packet: [0x03][chunks_sent:2B]
 * @param {number} chunkCount - Number of DATA packets sent
 * @returns {Uint8Array} 3-byte EOF packet
 */
export function createEofPacket(chunkCount) {
    const buffer = new ArrayBuffer(3);
    const view = new DataView(buffer);

    view.setUint8(0, PACKET_EOF);
    view.setUint16(1, chunkCount, true); // Little-endian

    return new Uint8Array(buffer);
}

/**
 * Convert a string to UTF-8 Uint8Array.
 * @param {string} str - Input string
 * @returns {Uint8Array}
 */
export function stringToBytes(str) {
    return new TextEncoder().encode(str);
}
