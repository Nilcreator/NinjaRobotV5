import styles from './Card.module.css';

const Card = ({
    children,
    variant = 'default',
    padding = 'medium',
    className = '',
    ...props
}) => {
    const classNames = [
        styles.card,
        styles[variant],
        styles[`padding${padding.charAt(0).toUpperCase() + padding.slice(1)}`],
        className,
    ].filter(Boolean).join(' ');

    return (
        <div className={classNames} {...props}>
            {children}
        </div>
    );
};

export default Card;
