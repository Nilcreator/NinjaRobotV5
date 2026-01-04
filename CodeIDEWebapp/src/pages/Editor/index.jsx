import { useState, useCallback, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { BlocklyWorkspace } from '../../components/blockly';
import { ConnectionPanel } from '../../components/bluetooth';
import { IconButton } from '../../components/common';
import useBluetooth from '../../hooks/useBluetooth';
import useKeyboardShortcuts from '../../hooks/useKeyboardShortcuts';
import styles from './Editor.module.css';

const Editor = () => {
    const { t, i18n } = useTranslation();
    const [code, setCode] = useState('# Your code will appear here\n');
    const [isSending, setIsSending] = useState(false);
    const [isCodePanelOpen, setIsCodePanelOpen] = useState(false);
    const [codePanelWidth, setCodePanelWidth] = useState(400);

    // Refs
    const workspaceRef = useRef(null);
    const fileInputRef = useRef(null);
    const isDraggingRef = useRef(false);

    // Hooks
    const {
        isSupported,
        isConnected,
        isConnecting,
        deviceName,
        error,
        connect,
        disconnect,
        sendCode,
    } = useBluetooth();

    // === Handlers ===

    const handleCodeChange = useCallback((newCode) => {
        setCode(newCode);
    }, []);

    // Handle direct code editing in textarea
    const handleCodeEdit = (e) => {
        setCode(e.target.value);
    };

    // Run code on robot
    const handleRun = async () => {
        if (!isConnected) {
            alert(t('editor.toolbar.failed', { error: 'Not connected' }));
            return;
        }
        setIsSending(true);
        try {
            await sendCode(code);
        } catch (err) {
            alert(`❌ ${t('editor.toolbar.failed', { error: err.message })}`);
        } finally {
            setIsSending(false);
        }
    };

    // Stop robot
    const handleStop = async () => {
        if (!isConnected) return;
        try {
            await sendCode('robot.stop()');
        } catch (err) {
            console.error('Stop failed:', err);
        }
    };

    // Clear workspace
    const handleClear = () => {
        if (workspaceRef.current && confirm(t('editor.workspace.clear_confirm'))) {
            workspaceRef.current.clear();
        }
    };

    // Undo/Redo
    const handleUndo = () => {
        if (workspaceRef.current) workspaceRef.current.undo(false);
    };

    const handleRedo = () => {
        if (workspaceRef.current) workspaceRef.current.undo(true);
    };

    // Download Python code
    const handleDownload = () => {
        const blob = new Blob([code], { type: 'text/x-python' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ninja_code.py';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // Upload Python file
    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const pythonCode = event.target?.result;
            if (typeof pythonCode === 'string') {
                setCode(pythonCode);
                setIsCodePanelOpen(true);
            }
        };
        reader.readAsText(file);
        e.target.value = '';
    };

    // Toggle code panel
    const toggleCodePanel = () => {
        setIsCodePanelOpen(!isCodePanelOpen);
        setTimeout(() => {
            if (workspaceRef.current) {
                import('blockly').then((Blockly) => {
                    Blockly.svgResize(workspaceRef.current);
                });
            }
        }, 350);
    };

    // Drag resize for code panel
    const handleResizeMouseDown = (e) => {
        e.preventDefault();
        isDraggingRef.current = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    };

    useEffect(() => {
        const handleMouseMove = (e) => {
            if (!isDraggingRef.current) return;
            const newWidth = window.innerWidth - e.clientX;
            const minWidth = 280;
            const maxWidth = window.innerWidth * 0.6;
            if (newWidth >= minWidth && newWidth <= maxWidth) {
                setCodePanelWidth(newWidth);
            }
        };

        const handleMouseUp = () => {
            if (isDraggingRef.current) {
                isDraggingRef.current = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Trigger Blockly resize
                if (workspaceRef.current) {
                    import('blockly').then((Blockly) => {
                        Blockly.svgResize(workspaceRef.current);
                    });
                }
            }
        };

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    const [isLocaleLoaded, setIsLocaleLoaded] = useState(false);

    // ... (existing refs)

    // ... (existing hooks)

    // ... (existing handlers)

    // Load Blockly Locale with Explicit Imports (Vite-friendly)
    useEffect(() => {
        const loadLocale = async () => {
            setIsLocaleLoaded(false); // Reset loaded state
            const lang = i18n.language;
            try {
                switch (lang) {
                    case 'ja':
                        await import('blockly/msg/ja');
                        break;
                    case 'zh-TW':
                        await import('blockly/msg/zh-hant');
                        break;
                    case 'zh-CN':
                        await import('blockly/msg/zh-hans');
                        break;
                    case 'en':
                    default:
                        await import('blockly/msg/en');
                        break;
                }
            } catch (e) {
                console.warn(`Failed to load Blockly locale for ${lang}`, e);
            } finally {
                setIsLocaleLoaded(true); // Ready to render workspace
            }
        };
        loadLocale();
    }, [i18n.language]);

    // Keyboard Shortcuts
    useKeyboardShortcuts({
        onSave: handleDownload,
        onUndo: handleUndo,
        onRedo: handleRedo,
        onRun: handleRun
    });

    return (
        <div className={styles.editor}>
            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                accept=".py,.txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
            />

            {/* === TOOLBAR === */}
            <div className={styles.toolbar}>
                {/* Left: File & Edit Actions */}
                <div className={styles.toolGroup}>
                    <IconButton icon="💾" label={t('editor.toolbar.save')} onClick={handleDownload} />
                    <IconButton icon="📂" label={t('editor.toolbar.open')} onClick={handleUploadClick} />
                    <div className={styles.divider} />
                    <IconButton icon="↩️" label={t('editor.toolbar.undo')} onClick={handleUndo} />
                    <IconButton icon="↪️" label={t('editor.toolbar.redo')} onClick={handleRedo} />
                    <IconButton icon="🗑️" label={t('editor.toolbar.clear')} onClick={handleClear} />
                </div>

                {/* Center: Run Controls */}
                <div className={styles.toolGroup}>
                    <IconButton
                        icon={isSending ? '⏳' : '▶️'}
                        label={isSending ? t('editor.toolbar.sending') : t('editor.toolbar.run')}
                        onClick={handleRun}
                        disabled={!isConnected || isSending}
                        variant="primary"
                        size="large"
                    />
                    <IconButton
                        icon="⏹️"
                        label={t('editor.toolbar.stop')}
                        onClick={handleStop}
                        disabled={!isConnected}
                        variant="danger"
                    />
                </div>

                {/* Right: Connection & View */}
                <div className={styles.toolGroup}>
                    <ConnectionPanel
                        isSupported={isSupported}
                        isConnected={isConnected}
                        isConnecting={isConnecting}
                        deviceName={deviceName}
                        error={error}
                        onConnect={connect}
                        onDisconnect={disconnect}
                    />
                    <div className={styles.divider} />
                    <IconButton
                        icon="🐍"
                        label={isCodePanelOpen ? t('editor.panel.hide') : t('editor.panel.show')}
                        onClick={toggleCodePanel}
                        variant={isCodePanelOpen ? 'active' : 'default'}
                    />
                </div>
            </div>

            {/* === WORKSPACE === */}
            <div className={styles.workspaceContainer}>
                <div
                    className={`${styles.blocklyArea} ${isCodePanelOpen ? styles.withCodePanel : ''}`}
                    style={isCodePanelOpen ? { marginRight: `${codePanelWidth}px` } : undefined}
                >
                    {/* Only render workspace after locale is loaded to ensure correct language */}
                    {isLocaleLoaded && (
                        <BlocklyWorkspace
                            key={i18n.language}
                            onCodeChange={handleCodeChange}
                            workspaceRef={workspaceRef}
                        />
                    )}
                </div>

                <div
                    className={`${styles.codePanel} ${isCodePanelOpen ? styles.open : ''}`}
                    style={{ width: `${codePanelWidth}px` }}
                >
                    {/* Drag handle */}
                    <div
                        className={styles.resizeHandle}
                        onMouseDown={handleResizeMouseDown}
                    />

                    <div className={styles.codePanelHeader}>
                        <span>{t('editor.panel.title')}</span>
                        <div className={styles.codePanelActions}>
                            <button
                                className={styles.copyBtn}
                                onClick={() => navigator.clipboard.writeText(code)}
                                title={t('editor.panel.copy')}
                            >
                                📋
                            </button>
                            <button className={styles.closeCodePanel} onClick={toggleCodePanel} title="Close panel">×</button>
                        </div>
                    </div>
                    <div className={styles.codePanelContent}>
                        <textarea
                            className={styles.codeEditor}
                            value={code}
                            onChange={handleCodeEdit}
                            spellCheck={false}
                            placeholder="# Write or edit Python code here..."
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Editor;
