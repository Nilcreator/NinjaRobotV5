import { useState, useCallback, useEffect } from 'react';
import styles from './ResizablePane.module.css';

/**
 * A split-pane component with a draggable divider.
 * Supports horizontal split.
 * 
 * @param {React.ReactNode} left - Left panel content
 * @param {React.ReactNode} right - Right panel content
 * @param {number} initialRightWidth - Initial width of right panel in pixels
 * @param {string} persistKey - localStorage key to persist width
 */
const ResizablePane = ({ left, right, initialRightWidth = 400, persistKey }) => {
    const [rightWidth, setRightWidth] = useState(() => {
        if (persistKey) {
            const saved = localStorage.getItem(persistKey);
            return saved ? parseInt(saved, 10) : initialRightWidth;
        }
        return initialRightWidth;
    });

    const [isDragging, setIsDragging] = useState(false);

    const handleMouseDown = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (!isDragging) return;

        // Calculate new width relative to window right edge
        const newWidth = window.innerWidth - e.clientX;

        // Constraints
        const minWidth = 280;
        const maxWidth = window.innerWidth * 0.5; // Max 50%

        if (newWidth >= minWidth && newWidth <= maxWidth) {
            setRightWidth(newWidth);
        }
    }, [isDragging]);

    // Persist width
    useEffect(() => {
        if (persistKey) {
            localStorage.setItem(persistKey, rightWidth.toString());
        }
    }, [rightWidth, persistKey]);

    // Global event listeners for drag
    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none'; // Prevent text selection
        } else {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    return (
        <div className={styles.container}>
            <div className={styles.leftPane}>
                {left}
            </div>

            <div
                className={`${styles.resizer} ${isDragging ? styles.active : ''}`}
                onMouseDown={handleMouseDown}
            >
                <div className={styles.handle} />
            </div>

            <div
                className={styles.rightPane}
                style={{ width: `${rightWidth}px` }}
            >
                {right}
            </div>
        </div>
    );
};

export default ResizablePane;
