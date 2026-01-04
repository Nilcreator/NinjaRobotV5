/**
 * BluetoothService - Singleton for managing BLE connection to NinjaRobot.
 */

import {
    SERVICE_UUID,
    CHAR_COMMAND_UUID,
    CHAR_RESPONSE_UUID,
    CHUNK_SIZE,
    TRANSFER_TIMEOUT,
} from './constants';
import {
    createHeaderPacket,
    createDataPackets,
    createEofPacket,
    stringToBytes,
} from './chunker';

class BluetoothService {
    constructor() {
        this.device = null;
        this.server = null;
        this.commandCharacteristic = null;
        this.responseCharacteristic = null;
        this._listeners = [];
        this._ackResolver = null;
    }

    /**
     * Check if Web Bluetooth API is available.
     * @returns {boolean}
     */
    static isSupported() {
        return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
    }

    /**
     * Get connection status.
     * @returns {boolean}
     */
    get isConnected() {
        return !!(this.server && this.server.connected);
    }

    /**
     * Get connected device name.
     * @returns {string|null}
     */
    get deviceName() {
        return this.device?.name || null;
    }

    /**
     * Connect to NinjaRobot via BLE.
     * @returns {Promise<void>}
     */
    async connect() {
        if (!BluetoothService.isSupported()) {
            throw new Error('Web Bluetooth is not supported in this browser');
        }

        // Request device
        this.device = await navigator.bluetooth.requestDevice({
            filters: [{ name: 'NinjaRobot' }],
            optionalServices: [SERVICE_UUID],
        });

        // Listen for disconnection
        this.device.addEventListener('gattserverdisconnected', () => {
            this._notifyListeners({ type: 'disconnected' });
            this._cleanup();
        });

        // Connect to GATT server
        this.server = await this.device.gatt.connect();

        // Get service
        const service = await this.server.getPrimaryService(SERVICE_UUID);

        // Get characteristics
        this.commandCharacteristic = await service.getCharacteristic(CHAR_COMMAND_UUID);
        this.responseCharacteristic = await service.getCharacteristic(CHAR_RESPONSE_UUID);

        // Subscribe to notifications
        await this.responseCharacteristic.startNotifications();
        this.responseCharacteristic.addEventListener(
            'characteristicvaluechanged',
            this._onNotification.bind(this)
        );

        this._notifyListeners({ type: 'connected', deviceName: this.deviceName });
    }

    /**
     * Disconnect from the device.
     */
    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
        this._cleanup();
    }

    /**
     * Send a small JSON command (legacy mode, <512 bytes).
     * @param {object} command - JSON command object
     */
    async sendCommand(command) {
        if (!this.isConnected || !this.commandCharacteristic) {
            throw new Error('Not connected');
        }
        const jsonStr = JSON.stringify(command);
        const data = stringToBytes(jsonStr);
        await this.commandCharacteristic.writeValue(data);
    }

    /**
     * Send a large payload using chunking protocol.
     * @param {object} payload - JSON payload object
     * @returns {Promise<void>}
     */
    async sendLargePayload(payload) {
        if (!this.isConnected || !this.commandCharacteristic) {
            throw new Error('Not connected');
        }

        const jsonStr = JSON.stringify(payload);
        const data = stringToBytes(jsonStr);

        // For small payloads, use legacy mode
        if (data.length <= CHUNK_SIZE) {
            await this.commandCharacteristic.writeValue(data);
            return;
        }

        // Create packets
        const headerPacket = createHeaderPacket(data, CHUNK_SIZE);
        const dataPackets = createDataPackets(data, CHUNK_SIZE);
        const eofPacket = createEofPacket(dataPackets.length);

        // Send HEADER and wait for ACK
        await this.commandCharacteristic.writeValue(headerPacket);
        await this._waitForAck(0, 'HEADER');

        // Send DATA packets
        for (let i = 0; i < dataPackets.length; i++) {
            await this.commandCharacteristic.writeValue(dataPackets[i]);
            await this._waitForAck(i, `DATA[${i}]`);
        }

        // Send EOF and wait for complete
        await this.commandCharacteristic.writeValue(eofPacket);
        await this._waitForAck(-1, 'EOF', 'complete');
    }

    /**
     * Send generated code to robot.
     * @param {string} code - Python code string
     */
    async sendCode(code) {
        const payload = {
            type: 'execute',
            code: code,
        };
        await this.sendLargePayload(payload);
    }

    /**
     * Add a listener for BLE events.
     * @param {Function} callback - Event callback
     */
    addListener(callback) {
        this._listeners.push(callback);
    }

    /**
     * Remove a listener.
     * @param {Function} callback - Event callback
     */
    removeListener(callback) {
        this._listeners = this._listeners.filter((l) => l !== callback);
    }

    // --- Private Methods ---

    _cleanup() {
        this.device = null;
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

            // Handle ACK messages
            if (message.type === 'ack' && this._ackResolver) {
                this._ackResolver(message);
                return;
            }

            // Notify listeners of other messages
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

// Export singleton instance
export const bluetoothService = new BluetoothService();
export default bluetoothService;
