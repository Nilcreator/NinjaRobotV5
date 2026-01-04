import styles from './Footer.module.css';

const Footer = () => {
    const currentYear = new Date().getFullYear();

    return (
        <footer className={styles.footer}>
            <div className={styles.container}>
                <p className={styles.copyright}>
                    © {currentYear} NinjaRobotCode Platform. Built for STEAM Education.
                </p>
                <div className={styles.links}>
                    <a
                        href="https://github.com/Nilcreator/NinjaRobotV5"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        GitHub
                    </a>
                    <span className={styles.separator}>•</span>
                    <a href="/help">Documentation</a>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
