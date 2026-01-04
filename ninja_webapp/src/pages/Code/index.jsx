/**
 * @file Code/index.jsx
 * @description Code page with Blockly visual programming and Python code panel.
 * Mobile-optimized with vertical layout for portrait mode.
 */

import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useBluetooth } from '../../contexts/BluetoothContext';
import BlocklyWorkspace from '../../components/blockly/BlocklyWorkspace';
import IconButton from '../../components/common/IconButton';
import Button from '../../components/common/Button';
import styles from './Code.module.css';

function Code() {
    const { t } = useTranslation();
    const { isSupported, isConnected, isConnecting, deviceName, connect, disconnect, sendCode } = useBluetooth();

    const [code, setCode] = useState('# Your code will appear here\n');
    const [isCodePanelOpen, setIsCodePanelOpen] = useState(false);
    const [isRunning, setIsRunning] = useState(false);
    const workspaceRef = useRef(null);

    const handleCodeChange = useCallback((newCode) => {
        setCode(newCode);
    }, []);

    const handleConnect = async () => {
        if (isConnected) {
            disconnect();
        } else {
            await connect();
        }
    };

    const handleRun = async () => {
        if (!isConnected) {
            alert(t('code.unsupported'));
            return;
        }

        setIsRunning(true);
        try {
            await sendCode(code);
        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setIsRunning(false);
        }
    };

    const handleStop = async () => {
        if (!isConnected) return;
        try {
            await sendCode('robot.stop()');
        } catch (err) {
            console.error('Stop failed:', err);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(code);
    };

    const toggleCodePanel = () => {
        setIsCodePanelOpen(!isCodePanelOpen);
    };

    return (
        <div className={styles.code}>
            {/* Toolbar */}
            <div className={styles.toolbar}>
                <div className={styles.toolGroup}>
                    {/* Connection */}
                    {isSupported ? (
                        <Button
                            variant={isConnected ? 'success' : 'secondary'}
                            size="small"
                            onClick={handleConnect}
                            disabled={isConnecting}
                        >
                            {isConnecting ? '⏳' : isConnected ? '🔗' : '🔌'}
                            {' '}
                            {isConnecting
                                ? t('code.connecting')
                                : isConnected
                                    ? t('code.connected', { name: deviceName })
                                    : t('code.connect')}
                        </Button>
                    ) : (
                        <Button variant="danger" size="small" disabled>
                            ⚠️ {t('code.unsupported')}
                        </Button>
                    )}
                </div>

                <div className={styles.toolGroup}>
                    {/* Run / Stop */}
                    <IconButton
                        icon="▶️"
                        label={t('code.run')}
                        onClick={handleRun}
                        disabled={!isConnected || isRunning}
                        variant="success"
                    />
                    <IconButton
                        icon="⏹️"
                        label={t('code.stop')}
                        onClick={handleStop}
                        disabled={!isConnected}
                        variant="danger"
                    />

                    <div className={styles.divider} />

                    {/* Code View Toggle */}
                    <IconButton
                        icon="📝"
                        label={isCodePanelOpen ? t('code.hideCode') : t('code.viewCode')}
                        onClick={toggleCodePanel}
                        variant={isCodePanelOpen ? 'active' : 'default'}
                    />
                </div>
            </div>

            {/* Workspace Container */}
            <div className={styles.workspaceContainer}>
                {/* Blockly Area */}
                <div className={`${styles.blocklyArea} ${isCodePanelOpen ? styles.withCodePanel : ''}`}>
                    <BlocklyWorkspace
                        onCodeChange={handleCodeChange}
                        workspaceRef={workspaceRef}
                    />
                </div>

                {/* Code Panel */}
                <div className={`${styles.codePanel} ${isCodePanelOpen ? styles.open : ''}`}>
                    <div className={styles.codePanelHeader}>
                        <span>📄 {t('code.codePanel')}</span>
                        <div className={styles.codePanelActions}>
                            <button className={styles.copyBtn} onClick={handleCopy} title={t('code.copy')}>
                                📋
                            </button>
                            <button className={styles.closeBtn} onClick={toggleCodePanel}>
                                ✕
                            </button>
                        </div>
                    </div>
                    <div className={styles.codePanelContent}>
                        <pre className={styles.codePreview}>{code}</pre>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Code;
