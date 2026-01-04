/**
 * @file Home/index.jsx
 * @description Home page with quick action buttons and power-off slider.
 */

import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
import PowerOffSlider from '../../components/common/PowerOffSlider';
import styles from './Home.module.css';

function Home() {
    const { t } = useTranslation();

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
                </div>

                {/* System Control - Power Off Slider */}
                <div className={styles.systemControl}>
                    <h3 className={styles.controlTitle}>
                        ⚡ {t('home.systemTitle') || 'System Control'}
                    </h3>
                    <PowerOffSlider />
                </div>
            </div>
        </div>
    );
}

export default Home;
