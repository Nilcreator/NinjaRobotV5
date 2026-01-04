/**
 * @file Help/index.jsx
 * @description Help page with getting started and troubleshooting.
 */

import { useTranslation } from 'react-i18next';
import styles from './Help.module.css';

function Help() {
    const { t } = useTranslation();

    return (
        <div className={styles.help}>
            <div className={styles.container}>
                <h1>{t('help.title')}</h1>

                <section className={styles.section}>
                    <h2>📚 {t('help.gettingStarted')}</h2>
                    <p>{t('help.gettingStartedText')}</p>
                </section>

                <section className={styles.section}>
                    <h2>🔧 {t('help.troubleshooting')}</h2>
                    <p>{t('help.troubleshootingText')}</p>
                </section>
            </div>
        </div>
    );
}

export default Help;
