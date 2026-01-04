import { useState, useEffect, useCallback } from 'react';
import { bluetoothService } from '../services/bluetooth';

/**
 * React hook for managing BLE connection to NinjaRobot.
 */
export function useBluetooth() {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [deviceName, setDeviceName] = useState(null);
    const [error, setError] = useState(null);
    const [isSupported] = useState(() => {
        // Check on mount (client-side only)
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
            } else if (event.type === 'message') {
                // Can be extended to handle robot responses
                console.log('Robot message:', event.data);
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
        setError(null);
        try {
            await bluetoothService.sendCode(code);
        } catch (err) {
            setError(err.message);
            throw err;
        }
    }, [isConnected]);

    const sendCommand = useCallback(async (command) => {
        if (!isConnected) {
            throw new Error('Not connected to robot');
        }
        setError(null);
        try {
            await bluetoothService.sendCommand(command);
        } catch (err) {
            setError(err.message);
            throw err;
        }
    }, [isConnected]);

    return {
        isSupported,
        isConnected,
        isConnecting,
        deviceName,
        error,
        connect,
        disconnect,
        sendCode,
        sendCommand,
    };
}

export default useBluetooth;
