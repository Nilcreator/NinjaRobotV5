import { useTranslation } from 'react-i18next';
import styles from './LanguageSelector.module.css';

const LanguageSelector = () => {
    const { i18n } = useTranslation();

    const changeLanguage = (e) => {
        const lang = e.target.value;
        i18n.changeLanguage(lang);

        // Update URL search param for sharing
        const url = new URL(window.location);
        url.searchParams.set('lang', lang);
        window.history.pushState({}, '', url);
    };

    return (
        <select
            className={styles.select}
            onChange={changeLanguage}
            value={i18n.language}
            aria-label="Select Language"
        >
            <option value="en">English</option>
            <option value="ja">日本語</option>
            <option value="zh-TW">繁體中文</option>
            <option value="zh-CN">简体中文</option>
        </select>
    );
};

export default LanguageSelector;
