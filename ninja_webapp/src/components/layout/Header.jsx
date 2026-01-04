import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSelector from '../common/LanguageSelector';
import styles from './Header.module.css';

function Header() {
    const { t } = useTranslation();
    const location = useLocation();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isServerActive, setIsServerActive] = useState(false);

    // Simple Server Health Check
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await fetch('/api/agent/status');
                if (res.ok) setIsServerActive(true);
                else setIsServerActive(false);
            } catch {
                setIsServerActive(false);
            }
        };

        checkStatus();
        const interval = setInterval(checkStatus, 10000); // Check every 10s
        return () => clearInterval(interval);
    }, []);

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
                    <img src="/logo.png" alt="NinjaRobot" className={styles.logoImage} style={{ height: '32px' }} />
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

                    {/* Server Status Indicator */}
                    <div
                        className={`${styles.bleStatus} ${isServerActive ? styles.connected : ''}`}
                        title={isServerActive ? 'Server: Online' : 'Server: Disconnected'}
                    >
                        <span className={styles.bleIcon}>{isServerActive ? '🟢' : '🔴'}</span>
                        <span className={styles.bleDot} />
                    </div>
                </nav>
            </div>
        </header>
    );
}

export default Header;
