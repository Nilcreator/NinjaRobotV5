import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageSelector } from '../common';
import styles from './Header.module.css';
import logo from '../../assets/images/hprobots_logo_white.png';

const Header = () => {
    const { t } = useTranslation();
    const location = useLocation();
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const navLinks = [
        { path: '/', label: 'Home' },
        { path: '/editor', label: 'Editor' },
        { path: '/help', label: 'Help' },
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <header className={styles.header}>
            <div className={styles.container}>
                <Link to="/" className={styles.logo}>
                    <img src={logo} alt="NinjaRobot Code IDE" className={styles.logoImg} />
                    <span className={styles.logoText}>NinjaRobot Code IDE</span>
                </Link>

                <button
                    className={styles.menuButton}
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    aria-label="Toggle menu"
                    aria-expanded={isMenuOpen}
                >
                    <span className={styles.menuIcon}>{isMenuOpen ? '✕' : '☰'}</span>
                </button>

                <nav className={`${styles.nav} ${isMenuOpen ? styles.navOpen : ''}`}>
                    <LanguageSelector />
                    {navLinks.map((link) => (
                        <Link
                            key={link.path}
                            to={link.path}
                            className={`${styles.navLink} ${isActive(link.path) ? styles.active : ''}`}
                            onClick={() => setIsMenuOpen(false)}
                        >
                            {t(`nav.${link.label.toLowerCase()}`)}
                        </Link>
                    ))}
                </nav>
            </div>
        </header>
    );
};

export default Header;
