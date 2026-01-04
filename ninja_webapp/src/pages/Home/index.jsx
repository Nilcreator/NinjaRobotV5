/**
 * @file Home/index.jsx
 * @description Home page with quick action buttons.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
import styles from './Home.module.css';

function Home() {
    const { t } = useTranslation();
    const [isShuttingDown, setIsShuttingDown] = useState(false);

    const handleShutdown = async () => {
        if (!window.confirm(t('home.shutdownConfirm') || 'Are you sure you want to power off the robot?')) {
            return;
        }

        setIsShuttingDown(true);
        try {
            const response = await fetch('/api/system/shutdown', { method: 'POST' });
            const data = await response.json();
            if (data.status === 'shutting_down') {
                alert(t('home.shutdownSuccess') || 'Robot is shutting down...');
            }
        } catch (error) {
            console.error('Shutdown failed:', error);
            alert(t('home.shutdownError') || 'Failed to shut down robot.');
            setIsShuttingDown(false);
        }
    };

    return (
        <div className={styles.home}>
            <div className={styles.hero}>
                <span className={styles.logo}>🥷</span>
                <h1>{t('home.welcome')}</h1>
                <p className={styles.subtitle}>{t('home.subtitle')}</p>

                <div className={styles.actions}>
                    <Link to="/agent">
                        <Button variant="cta" size="large">
                            💬 {t('home.chatButton')}
                        </Button>
                    </Link>
                    <Link to="/code">
                        <Button variant="primary" size="large">
                            🧩 {t('home.codeButton')}
                        </Button>
                    </Link>
                </div>

                {/* System Control Section */}
                <div className={styles.systemControl}>
                    <Button
                        variant="danger"
                        onClick={handleShutdown}
                        disabled={isShuttingDown}
                    >
                        ⏻ {isShuttingDown ? (t('home.shuttingDown') || 'Shutting down...') : (t('home.shutdownButton') || 'Power Off Robot')}
                    </Button>
                </div>
            </div>
        </div>
    );
}

export default Home;
