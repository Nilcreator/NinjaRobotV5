import styles from './IconButton.module.css';

/**
 * Icon-only button with tooltip.
 * 
 * @param {string} icon - Emoji or icon character
 * @param {string} label - Tooltip text (accessibility + hover)
 * @param {function} onClick - Click handler
 * @param {boolean} disabled - Disabled state
 * @param {string} variant - 'default' | 'primary' | 'danger' | 'active'
 * @param {string} size - 'normal' | 'large'
 */
const IconButton = ({
    icon,
    label,
    onClick,
    disabled = false,
    variant = 'default',
    size = 'normal',
    className = ''
}) => {
    return (
        <button
            className={`${styles.button} ${styles[variant]} ${styles[size]} ${className}`}
            onClick={onClick}
            disabled={disabled}
            title={label}
            aria-label={label}
        >
            <span className={styles.icon}>{icon}</span>
            <span className={styles.tooltip}>{label}</span>
        </button>
    );
};

export default IconButton;
