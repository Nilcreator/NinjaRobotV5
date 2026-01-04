import { useState } from 'react';
import { Button } from '../common';
import styles from './ProjectDialog.module.css';

const ProjectDialog = ({
    isOpen,
    onClose,
    mode, // 'save' | 'open'
    projects,
    onSave,
    onLoad,
    onDelete
}) => {
    // Use a key-based approach - name resets when dialog content changes
    const [name, setName] = useState('');

    // Early return if not open (component won't render, state resets on remount)
    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!name.trim()) return;

        if (mode === 'save') {
            onSave(name.trim());
        }
        setName('');
        onClose();
    };

    const handleLoad = (pName) => {
        onLoad(pName);
        onClose();
    };

    const handleDelete = (pName, e) => {
        e.stopPropagation();
        if (confirm(`Delete project "${pName}"?`)) {
            onDelete(pName);
        }
    };

    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget) {
            setName('');
            onClose();
        }
    };

    const handleClose = () => {
        setName('');
        onClose();
    };

    return (
        <div className={styles.overlay} onClick={handleOverlayClick}>
            <div className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="dialog-title">
                <div className={styles.header}>
                    <h3 id="dialog-title">{mode === 'save' ? '💾 Save Project' : '📂 Open Project'}</h3>
                    <button className={styles.closeBtn} onClick={handleClose} aria-label="Close">×</button>
                </div>

                <div className={styles.content}>
                    {mode === 'save' && (
                        <form onSubmit={handleSubmit} className={styles.form}>
                            <input
                                type="text"
                                placeholder="Enter project name..."
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className={styles.input}
                                autoFocus
                                aria-label="Project name"
                            />
                            <Button type="submit" variant="cta" disabled={!name.trim()}>Save</Button>
                        </form>
                    )}

                    <div className={styles.list}>
                        <h4 className={styles.listTitle}>
                            {mode === 'save' ? 'Overwrite Existing' : 'Your Projects'}
                        </h4>
                        {projects.length === 0 ? (
                            <p className={styles.empty}>No saved projects yet</p>
                        ) : (
                            <ul>
                                {projects.map(p => (
                                    <li
                                        key={p}
                                        className={styles.item}
                                        onClick={() => mode === 'open' && handleLoad(p)}
                                        role={mode === 'open' ? 'button' : undefined}
                                        tabIndex={mode === 'open' ? 0 : undefined}
                                    >
                                        <span className={styles.itemName}>📄 {p}</span>
                                        <div className={styles.itemActions}>
                                            {mode === 'save' && (
                                                <button
                                                    type="button"
                                                    className={styles.selectBtn}
                                                    onClick={() => setName(p)}
                                                >
                                                    Use Name
                                                </button>
                                            )}
                                            <button
                                                type="button"
                                                className={styles.deleteBtn}
                                                onClick={(e) => handleDelete(p, e)}
                                                title="Delete project"
                                                aria-label={`Delete ${p}`}
                                            >
                                                🗑️
                                            </button>
                                            {mode === 'open' && (
                                                <Button size="small" onClick={() => handleLoad(p)}>Open</Button>
                                            )}
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProjectDialog;
