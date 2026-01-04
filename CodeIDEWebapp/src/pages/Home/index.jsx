import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button, Card } from '../../components/common';
import styles from './Home.module.css';
import heroImage from '../../assets/images/otto_family.png';

const Home = () => {
    const { t } = useTranslation();

    const features = [
        {
            icon: '🎨',
            title: t('home.features.create.title'),
            description: t('home.features.create.desc'),
        },
        {
            icon: '📶',
            title: t('home.features.connect.title'),
            description: t('home.features.connect.desc'),
        },
        {
            icon: '💻',
            title: t('home.features.code.title'),
            description: t('home.features.code.desc'),
        },
    ];

    return (
        <div className={styles.home}>
            {/* Hero Section */}
            <section className={styles.hero}>
                <div className={styles.heroContent}>
                    <h1>{t('home.hero.title')}</h1>
                    <p className={styles.heroSubtitle}>
                        {t('home.hero.subtitle')}
                    </p>
                    <div className={styles.heroCta}>
                        <Link to="/editor">
                            <Button variant="cta" size="large">
                                {t('home.hero.cta_start')}
                            </Button>
                        </Link>
                        <Link to="/help">
                            <Button variant="secondary" size="large">
                                {t('home.hero.cta_learn')}
                            </Button>
                        </Link>
                    </div>
                </div>
                <div className={styles.heroImageContainer}>
                    <img src={heroImage} alt="NinjaRobot Family" className={styles.heroImage} />
                </div>
            </section>

            {/* Features Section */}
            <section className={styles.features}>
                <h2>{t('home.features.title')}</h2>
                <div className={styles.featureGrid}>
                    {features.map((feature, index) => (
                        <div key={index} className={styles.featureCard}>
                            <div className={styles.featureIcon}>{feature.icon}</div>
                            <h3>{feature.title}</h3>
                            <p>{feature.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Specs Section */}
            <section className={styles.specs}>
                <h2>{t('home.specs.title')}</h2>
                <Card padding="large">
                    <dl className={styles.specsList}>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.platform')}</dt>
                            <dd>Raspberry Pi Zero 2 W</dd>
                        </div>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.servos')}</dt>
                            <dd>8x PWM (GPIO 20-27)</dd>
                        </div>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.display')}</dt>
                            <dd>ST7789 240×240 SPI</dd>
                        </div>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.sensors')}</dt>
                            <dd>VL53L0X Distance (I2C)</dd>
                        </div>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.sound')}</dt>
                            <dd>Passive Buzzer (GPIO 17)</dd>
                        </div>
                        <div className={styles.specItem}>
                            <dt>{t('home.specs.items.connection')}</dt>
                            <dd>Bluetooth Low Energy (BLE)</dd>
                        </div>
                    </dl>
                </Card>
            </section>
        </div>
    );
};

export default Home;
