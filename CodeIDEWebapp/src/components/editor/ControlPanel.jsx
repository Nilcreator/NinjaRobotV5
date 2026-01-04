import styles from './ControlPanel.module.css';

/**
 * Toolbar with robot control buttons (Run, Stop, etc.)
 */
const ControlPanel = ({
    onRun,
    onStop,
    onClear,
    isRunning = false,
    isConnected = false
}) => {
    return (
        <div className={styles.panel}>
            <button
                className={`${styles.button} ${styles.run}`}
                onClick={onRun}
                disabled={!isConnected || isRunning}
                title="Run code on robot (Meta+Enter)"
            >
                {isRunning ? '⏳ Running...' : '▶️ Run'}
            </button>

            <button
                className={`${styles.button} ${styles.stop}`}
                onClick={onStop}
                disabled={!isConnected}
                title="Stop robot execution"
            >
                ⏹️ Stop
            </button>

            <div className={styles.divider} />

            <button
                className={styles.button}
                onClick={onClear}
                title="Clear workspace"
            >
                🗑️ Clear
            </button>
        </div>
    );
};

export default ControlPanel;
