/**
 * @file chunker.js
 * @description Utilities for chunking data for BLE transmission.
 * Protocol matches ninja_ble/service.py expectations.
 */

const CHUNK_SIZE = 500; // Max payload per BLE packet

/**
 * Create header packet (0x01).
 * @param {number} totalSize - Total data size in bytes
 * @returns {Uint8Array}
 */
export function createHeaderPacket(totalSize) {
    const header = new Uint8Array(5);
    header[0] = 0x01; // Header type
    // Total size as 4 bytes (big-endian)
    header[1] = (totalSize >> 24) & 0xff;
    header[2] = (totalSize >> 16) & 0xff;
    header[3] = (totalSize >> 8) & 0xff;
    header[4] = totalSize & 0xff;
    return header;
}

/**
 * Create data packets (0x02).
 * @param {Uint8Array} data - Full data to chunk
 * @returns {Uint8Array[]}
 */
export function createDataPackets(data) {
    const packets = [];
    let offset = 0;
    let seq = 0;

    while (offset < data.length) {
        const chunkData = data.slice(offset, offset + CHUNK_SIZE);
        const packet = new Uint8Array(3 + chunkData.length);

        packet[0] = 0x02; // Data type
        packet[1] = (seq >> 8) & 0xff;
        packet[2] = seq & 0xff;
        packet.set(chunkData, 3);

        packets.push(packet);
        offset += CHUNK_SIZE;
        seq++;
    }

    return packets;
}

/**
 * Create EOF packet (0x03).
 * @returns {Uint8Array}
 */
export function createEofPacket() {
    return new Uint8Array([0x03]);
}

/**
 * Convert string to bytes.
 * @param {string} str
 * @returns {Uint8Array}
 */
export function stringToBytes(str) {
    return new TextEncoder().encode(str);
}
