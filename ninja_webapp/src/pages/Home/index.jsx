/**
 * @file Home/index.jsx
 * @description Home page with quick action buttons.
 */

import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Button from '../../components/common/Button';
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
                    <Link to="/code">
                        <Button variant="primary" size="large">
                            🧩 {t('home.codeButton')}
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default Home;
