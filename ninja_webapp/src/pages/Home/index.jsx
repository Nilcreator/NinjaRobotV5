/**
 * @file Home/index.jsx
 * @description Home page with hero image and power-off slider.
 */

import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
import PowerOffSlider from '../../components/common/PowerOffSlider';
import styles from './Home.module.css';

function Home() {
    const { t } = useTranslation();

    return (
        <div className={styles.homePage}>
            {/* Hero Section */}
            <div className={styles.heroSection}>
                <img
                    src="/robot-hero.png"
                    alt="NinjaRobot"
                    className={styles.heroImage}
                />
                <h1 className={styles.title}>{t('home.welcome')}</h1>
                <p className={styles.subtitle}>{t('home.subtitle')}</p>

                <Link to="/agent" className={styles.ctaLink}>
                    <Button variant="cta" size="large">
                        💬 {t('home.chatButton')}
                    </Button>
                </Link>
            </div>

            {/* System Control Section */}
            <div className={styles.systemSection}>
                <h3 className={styles.sectionTitle}>
                    ⚡ {t('home.systemTitle') || 'System Control'}
                </h3>
                <PowerOffSlider />
            </div>
        </div>
    );
}

export default Home;
