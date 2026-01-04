import { useTranslation, Trans } from 'react-i18next';
import { Card } from '../../components/common';
import styles from './Help.module.css';

const Help = () => {
    const { t } = useTranslation();

    const topics = [
        {
            title: t('help.topics.getting_started.title'),
            items: [
                t('help.topics.getting_started.items.0'),
                t('help.topics.getting_started.items.1'),
                t('help.topics.getting_started.items.2'),
            ],
        },
        {
            title: t('help.topics.block_reference.title'),
            items: [
                t('help.topics.block_reference.items.0'),
                t('help.topics.block_reference.items.1'),
                t('help.topics.block_reference.items.2'),
                t('help.topics.block_reference.items.3'),
            ],
        },
        {
            title: t('help.topics.troubleshooting.title'),
            items: [
                t('help.topics.troubleshooting.items.0'),
                t('help.topics.troubleshooting.items.1'),
                t('help.topics.troubleshooting.items.2'),
            ],
        },
    ];

    return (
        <div className={styles.help}>
            <h1>{t('help.title')}</h1>
            <p className={styles.subtitle}>
                {t('help.subtitle')}
            </p>

            <div className={styles.topicGrid}>
                {topics.map((topic, index) => (
                    <Card key={index} padding="large">
                        <h3>{topic.title}</h3>
                        <ul className={styles.topicList}>
                            {topic.items.map((item, i) => (
                                <li key={i}>{item}</li>
                            ))}
                        </ul>
                    </Card>
                ))}
            </div>

            <Card variant="feature" padding="large" className={styles.supportCard}>
                <h3>{t('help.support.title')}</h3>
                <p>
                    <Trans i18nKey="help.support.text">
                        Visit the{' '}
                        <a
                            href="https://github.com/Nilcreator/NinjaRobotV5"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            GitHub Repository
                        </a>{' '}
                        for detailed documentation and community support.
                    </Trans>
                </p>
            </Card>
        </div>
    );
};

export default Help;
