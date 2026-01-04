import styles from './CodePreview.module.css';

const CodePreview = ({ code, title = 'Python Code' }) => {
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            // Could add a toast notification here
        } catch (err) {
            console.error('Failed to copy code:', err);
        }
    };

    return (
        <div className={styles.preview}>
            <div className={styles.header}>
                <h4 className={styles.title}>🐍 {title}</h4>
                <button className={styles.copyBtn} onClick={handleCopy} title="Copy to clipboard">
                    📋 Copy
                </button>
            </div>
            <pre className={styles.code}>
                <code>{code || '# Your code will appear here'}</code>
            </pre>
        </div>
    );
};

export default CodePreview;
