/**
 * @file IconButton.jsx
 * @description Icon-only button with tooltip.
 */

import styles from './IconButton.module.css';

function IconButton({
    icon,
    label,
    onClick,
    disabled = false,
    variant = 'default',
    size = 'normal',
    className = ''
}) {
    return (
        <button
            className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`}
            onClick={onClick}
            disabled={disabled}
            title={label}
            aria-label={label}
        >
            <span className={styles.icon}>{icon}</span>
        </button>
    );
}

export default IconButton;
