/**
 * @file BluetoothService.js
 * @description Singleton BLE service for NinjaRobot communication.
 * Handles connection, chunking protocol, and command transmission.
 */

import { createHeaderPacket, createDataPackets, createEofPacket } from './chunker';

// BLE Service and Characteristic UUIDs (matching ninja_ble/service.py)
const SERVICE_UUID = '00000001-710e-4a5b-8d75-3e5b444bc3cf';
const CHAR_COMMAND_UUID = '00000002-710e-4a5b-8d75-3e5b444bc3cf';
const CHAR_RESPONSE_UUID = '00000003-710e-4a5b-8d75-3e5b444bc3cf';

const TRANSFER_TIMEOUT = 10000; // 10 seconds

class BluetoothService {
    constructor() {
        this.device = null;
        this.server = null;
        this.commandCharacteristic = null;
        this.responseCharacteristic = null;
        this._listeners = [];
        this._ackResolver = null;
    }

    static isSupported() {
        return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
    }

    get isConnected() {
        return !!(this.server && this.server.connected);
    }

    get deviceName() {
        return this.device?.name || null;
    }

    async connect() {
        if (!BluetoothService.isSupported()) {
            throw new Error('Web Bluetooth is not supported in this browser');
        }

        this.device = await navigator.bluetooth.requestDevice({
            filters: [{ name: 'NinjaRobot' }],
            optionalServices: [SERVICE_UUID],
        });

        this.device.addEventListener('gattserverdisconnected', () => {
            this._notifyListeners({ type: 'disconnected' });
            this._cleanup();
        });

        this.server = await this.device.gatt.connect();
        const service = await this.server.getPrimaryService(SERVICE_UUID);

        this.commandCharacteristic = await service.getCharacteristic(CHAR_COMMAND_UUID);
        this.responseCharacteristic = await service.getCharacteristic(CHAR_RESPONSE_UUID);

        await this.responseCharacteristic.startNotifications();
        this.responseCharacteristic.addEventListener('characteristicvaluechanged', (e) => this._onNotification(e));

        this._notifyListeners({
            type: 'connected',
            deviceName: this.device.name,
        });
    }

    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
        this._cleanup();
    }

    async sendCode(code) {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }

        const command = JSON.stringify({ type: 'execute', payload: { code } });
        await this._sendChunked(command);
    }

    async sendCommand(command) {
        if (!this.isConnected) {
            throw new Error('Not connected');
        }

        const payload = JSON.stringify(command);
        await this._sendChunked(payload);
    }

    async _sendChunked(data) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(data);

        // Send header
        const header = createHeaderPacket(bytes.length);
        await this.commandCharacteristic.writeValue(header);
        await this._waitForAck(0, 'header');

        // Send data chunks
        const chunks = createDataPackets(bytes);
        for (let i = 0; i < chunks.length; i++) {
            await this.commandCharacteristic.writeValue(chunks[i]);
            await this._waitForAck(i + 1, `chunk ${i + 1}`);
        }

        // Send EOF
        const eof = createEofPacket();
        await this.commandCharacteristic.writeValue(eof);
        await this._waitForAck(-1, 'eof', 'complete');
    }

    addListener(callback) {
        this._listeners.push(callback);
    }

    removeListener(callback) {
        this._listeners = this._listeners.filter(l => l !== callback);
    }

    _cleanup() {
        this.server = null;
        this.commandCharacteristic = null;
        this.responseCharacteristic = null;
    }

    _notifyListeners(event) {
        this._listeners.forEach((listener) => {
            try {
                listener(event);
            } catch (e) {
                console.error('BLE listener error:', e);
            }
        });
    }

    _onNotification(event) {
        const value = event.target.value;
        const decoder = new TextDecoder('utf-8');
        const jsonStr = decoder.decode(value);

        try {
            const message = JSON.parse(jsonStr);

            if (message.type === 'ack' && this._ackResolver) {
                this._ackResolver(message);
                return;
            }

            this._notifyListeners({ type: 'message', data: message });
        } catch {
            console.warn('Invalid JSON notification:', jsonStr);
        }
    }

    _waitForAck(expectedSeq, context, expectedStatus = 'ok') {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                this._ackResolver = null;
                reject(new Error(`ACK timeout for ${context}`));
            }, TRANSFER_TIMEOUT);

            this._ackResolver = (ack) => {
                clearTimeout(timeout);
                this._ackResolver = null;

                if (ack.status === 'error') {
                    reject(new Error(`ACK error for ${context}: ${ack.msg || 'Unknown'}`));
                } else if (ack.status === expectedStatus || ack.status === 'ok') {
                    resolve(ack);
                } else if (expectedSeq === -1 && ack.status === 'complete') {
                    resolve(ack);
                } else {
                    reject(new Error(`Unexpected ACK status: ${ack.status}`));
                }
            };
        });
    }
}

export const bluetoothService = new BluetoothService();
export default bluetoothService;
