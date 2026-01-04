/**
 * @file Header.jsx
 * @description Global header with Logo, Navigation, Language Selector, and BLE Status.
 * Displayed on all pages.
 */

import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useBluetooth } from '../../contexts/BluetoothContext';
import LanguageSelector from '../common/LanguageSelector';
import styles from './Header.module.css';

function Header() {
    const { t } = useTranslation();
    const location = useLocation();
    const { isConnected, deviceName } = useBluetooth();
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const navLinks = [
        { path: '/', label: 'home' },
        { path: '/agent', label: 'agent' },
        { path: '/code', label: 'code' },
        { path: '/help', label: 'help' },
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <header className={styles.header}>
            <div className={styles.container}>
                {/* Logo */}
                <NavLink to="/" className={styles.logo}>
                    <span className={styles.logoIcon}>🥷</span>
                    <span className={styles.logoText}>NinjaRobot</span>
                </NavLink>

                {/* Mobile Menu Button */}
                <button
                    className={styles.menuButton}
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    aria-label="Toggle menu"
                    aria-expanded={isMenuOpen}
                >
                    <span className={styles.menuIcon}>{isMenuOpen ? '✕' : '☰'}</span>
                </button>

                {/* Navigation + Status */}
                <nav className={`${styles.nav} ${isMenuOpen ? styles.navOpen : ''}`}>
                    {navLinks.map((link) => (
                        <NavLink
                            key={link.path}
                            to={link.path}
                            className={`${styles.navLink} ${isActive(link.path) ? styles.active : ''}`}
                            onClick={() => setIsMenuOpen(false)}
                        >
                            {t(`nav.${link.label}`)}
                        </NavLink>
                    ))}

                    <div className={styles.divider} />

                    <LanguageSelector />

                    {/* BLE Status Indicator */}
                    <div
                        className={`${styles.bleStatus} ${isConnected ? styles.connected : ''}`}
                        title={isConnected ? t('header.connected') + `: ${deviceName}` : t('header.disconnected')}
                    >
                        <span className={styles.bleIcon}>📶</span>
                        <span className={styles.bleDot} />
                    </div>
                </nav>
            </div>
        </header>
    );
}

export default Header;
