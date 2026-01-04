/**
 * @file LanguageSelector.jsx
 * @description Dropdown for selecting UI language.
 * Supports: English, 日本語, 繁體中文, 简体中文
 */

import { useTranslation } from 'react-i18next';
import styles from './LanguageSelector.module.css';

const languages = [
    { code: 'en', label: 'English', flag: '🇺🇸' },
    { code: 'ja', label: '日本語', flag: '🇯🇵' },
    { code: 'zh-TW', label: '繁體中文', flag: '🇹🇼' },
    { code: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
];

function LanguageSelector() {
    const { i18n } = useTranslation();

    const handleChange = (e) => {
        i18n.changeLanguage(e.target.value);
    };

    const currentLang = languages.find(l => l.code === i18n.language) || languages[0];

    return (
        <div className={styles.selector}>
            <span className={styles.flag}>{currentLang.flag}</span>
            <select
                value={i18n.language}
                onChange={handleChange}
                className={styles.select}
                aria-label="Select language"
            >
                {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                        {lang.label}
                    </option>
                ))}
            </select>
        </div>
    );
}

export default LanguageSelector;
