/**
 * @file Footer.jsx
 * @description Simple footer with copyright.
 */

import styles from './Footer.module.css';

function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className={styles.footer}>
            <div className={styles.container}>
                <p className={styles.copyright}>
                    © {currentYear} NinjaRobot. Built for STEAM Education.
                </p>
            </div>
        </footer>
    );
}

export default Footer;
