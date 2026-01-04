import styles from './Button.module.css';

const Button = ({
    children,
    variant = 'primary',
    size = 'medium',
    disabled = false,
    fullWidth = false,
    onClick,
    type = 'button',
    ...props
}) => {
    const classNames = [
        styles.button,
        styles[variant],
        styles[size],
        fullWidth ? styles.fullWidth : '',
    ].filter(Boolean).join(' ');

    return (
        <button
            type={type}
            className={classNames}
            disabled={disabled}
            onClick={onClick}
            {...props}
        >
            {children}
        </button>
    );
};

export default Button;
