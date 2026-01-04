/**
 * @file Code/index.jsx
 * @description Code page with Blockly visual programming and Python code panel.
 * Mobile-optimized with vertical layout for portrait mode.
 */

import { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import BlocklyWorkspace from '../../components/blockly/BlocklyWorkspace';
import IconButton from '../../components/common/IconButton';
import styles from './Code.module.css';

function Code() {
    const { t } = useTranslation();

    const [code, setCode] = useState('# Your code will appear here\n');
    const [isCodePanelOpen, setIsCodePanelOpen] = useState(false);
    const [isRunning, setIsRunning] = useState(false);
    const workspaceRef = useRef(null);

    const handleCodeChange = useCallback((newCode) => {
        setCode(newCode);
    }, []);

    const handleRun = async () => {
        setIsRunning(true);
        try {
            const response = await fetch('/api/code/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code }),
            });
            const data = await response.json();
            if (data.status === 'error') {
                alert(`Error: ${data.detail || 'Execution failed'}`);
            }
        } catch (err) {
            alert(`Network Error: ${err.message}`);
        } finally {
            // We don't necessarily know when it finishes unless we poll, 
            // but for UX, let's keep button spinning briefly then stop.
            // Or we rely on the server to return immediately? 
            // Dispatcher returns immediately often, or waits. 
            // Let's just set false after call returns.
            setIsRunning(false);
        }
    };

    const handleStop = async () => {
        try {
            await fetch('/api/code/stop', { method: 'POST' });
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
                    {/* Run / Stop */}
                    <IconButton
                        icon="▶️"
                        label={t('code.run')}
                        onClick={handleRun}
                        disabled={isRunning}
                        variant="success"
                    />
                    <IconButton
                        icon="⏹️"
                        label={t('code.stop')}
                        onClick={handleStop}
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
