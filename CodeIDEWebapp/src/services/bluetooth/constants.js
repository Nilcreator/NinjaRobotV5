/**
 * BLE Protocol Constants for NinjaRobot V5 communication.
 * Must match values in ninja_ble/chunking.py
 */

// GATT Service and Characteristic UUIDs
export const SERVICE_UUID = '00000001-710e-4a5b-8d75-3e5b444bc3cf';
export const CHAR_COMMAND_UUID = '00000002-710e-4a5b-8d75-3e5b444bc3cf';
export const CHAR_RESPONSE_UUID = '00000003-710e-4a5b-8d75-3e5b444bc3cf';

// Packet type identifiers
export const PACKET_HEADER = 0x01;
export const PACKET_DATA = 0x02;
export const PACKET_EOF = 0x03;

// Protocol settings
export const CHUNK_SIZE = 500; // bytes per DATA packet
export const TRANSFER_TIMEOUT = 30000; // ms
