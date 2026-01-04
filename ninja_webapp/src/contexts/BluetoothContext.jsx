/**
 * @file BluetoothContext.jsx
 * @description React Context for global BLE connection state.
 * Provides connection status to Header and all pages.
 */

import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { bluetoothService } from '../services/bluetooth/BluetoothService';

const BluetoothContext = createContext(null);

export function BluetoothProvider({ children }) {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [deviceName, setDeviceName] = useState(null);
    const [error, setError] = useState(null);
    const [isSupported] = useState(() => {
        if (typeof navigator === 'undefined') return false;
        return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
    });

    useEffect(() => {
        const handleEvent = (event) => {
            if (event.type === 'connected') {
                setIsConnected(true);
                setDeviceName(event.deviceName);
                setError(null);
            } else if (event.type === 'disconnected') {
                setIsConnected(false);
                setDeviceName(null);
            }
        };

        bluetoothService.addListener(handleEvent);
        return () => bluetoothService.removeListener(handleEvent);
    }, []);

    const connect = useCallback(async () => {
        setIsConnecting(true);
        setError(null);
        try {
            await bluetoothService.connect();
        } catch (err) {
            setError(err.message);
            console.error('BLE connect error:', err);
        } finally {
            setIsConnecting(false);
        }
    }, []);

    const disconnect = useCallback(() => {
        bluetoothService.disconnect();
        setIsConnected(false);
        setDeviceName(null);
    }, []);

    const sendCode = useCallback(async (code) => {
        if (!isConnected) {
            throw new Error('Not connected to robot');
        }
        await bluetoothService.sendCode(code);
    }, [isConnected]);

    const value = {
        isSupported,
        isConnected,
        isConnecting,
        deviceName,
        error,
        connect,
        disconnect,
        sendCode,
    };

    return (
        <BluetoothContext.Provider value={value}>
            {children}
        </BluetoothContext.Provider>
    );
}

export function useBluetooth() {
    const context = useContext(BluetoothContext);
    if (!context) {
        throw new Error('useBluetooth must be used within BluetoothProvider');
    }
    return context;
}

export default BluetoothContext;
