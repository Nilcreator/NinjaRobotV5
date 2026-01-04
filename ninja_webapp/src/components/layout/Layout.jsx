/**
 * @file Layout.jsx
 * @description Layout wrapper with Header, main content, and Footer.
 */

import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import styles from './Layout.module.css';

function Layout() {
    return (
        <div className={styles.layout}>
            <Header />
            <main className={styles.main}>
                <Outlet />
            </main>
            <Footer />
        </div>
    );
}

export default Layout;
