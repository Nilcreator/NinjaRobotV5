/**
 * @file i18n.js
 * @description Internationalization configuration for NinjaRobot Code IDE.
 * 
 * Supported Languages:
 * - en (English) — Fallback language
 * - ja (Japanese)
 * - zh-TW (Traditional Chinese)
 * - zh-CN (Simplified Chinese)
 * 
 * Language Detection Order:
 * 1. URL query parameter (?lang=ja)
 * 2. localStorage (i18nextLng)
 * 3. Browser navigator.language
 * 
 * @see locales/ folder for translation JSON files
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation resources
import en from './locales/en.json';
import ja from './locales/ja.json';
import zhTW from './locales/zh-tw.json';
import zhCN from './locales/zh-cn.json';

i18n
    .use(LanguageDetector)      // Auto-detect user language
    .use(initReactI18next)      // Connect to React
    .init({
        resources: {
            en: { translation: en },
            ja: { translation: ja },
            'zh-TW': { translation: zhTW },
            'zh-CN': { translation: zhCN }
        },
        fallbackLng: 'en',                              // Default if detection fails
        supportedLngs: ['en', 'ja', 'zh-TW', 'zh-CN'],   // Whitelist
        detection: {
            order: ['querystring', 'localStorage', 'navigator'],
            lookupQuerystring: 'lang',                  // ?lang=ja
            lookupLocalStorage: 'i18nextLng',           // localStorage key
            caches: ['localStorage'],                   // Persist selection
        },
        interpolation: {
            escapeValue: false,  // React already escapes values
        },
        react: {
            useSuspense: false   // Don't block render during load
        }
    });

/**
 * Sync document.documentElement.lang attribute on language change.
 * Important for accessibility and SEO.
 */
i18n.on('languageChanged', (lng) => {
    document.documentElement.lang = lng;
});

export default i18n;
