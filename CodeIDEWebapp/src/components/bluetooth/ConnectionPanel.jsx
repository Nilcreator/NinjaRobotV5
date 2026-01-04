import { IconButton } from '../common';
import styles from './ConnectionPanel.module.css';
import { useTranslation } from 'react-i18next';

const ConnectionPanel = ({
    isSupported,
    isConnected,
    isConnecting,
    deviceName,
    error,
    onConnect,
    onDisconnect
}) => {
    const { t } = useTranslation();

    if (!isSupported) {
        return (
            <div className={styles.container} title={t('editor.toolbar.unsupported')}>
                <IconButton
                    icon="⚠️"
                    label={t('editor.toolbar.unsupported')}
                    disabled
                    variant="danger"
                />
            </div>
        );
    }

    if (isConnected) {
        return (
            <div className={styles.container}>
                <div className={styles.statusIndicator}>
                    <span className={styles.pulse}></span>
                </div>
                <IconButton
                    icon="🔌"
                    label={t('editor.toolbar.connected', { name: deviceName })}
                    onClick={onDisconnect}
                    variant="success"
                />
            </div>
        );
    }

    return (
        <div className={styles.container}>
            {error && (
                <div className={styles.error} title={error}>
                    !
                </div>
            )}
            <IconButton
                icon={isConnecting ? '⏳' : '🔗'}
                label={isConnecting ? t('editor.toolbar.connecting') : t('editor.toolbar.connect')}
                onClick={onConnect}
                disabled={isConnecting}
                variant={error ? 'danger' : 'default'}
            />
        </div>
    );
};

export default ConnectionPanel;
