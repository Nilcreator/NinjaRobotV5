/**
 * @file i18n.js
 * @description i18next configuration for multilingual support.
 * Supports: English, 日本語, 繁體中文, 简体中文
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import ja from './locales/ja.json';
import zhTW from './locales/zh-tw.json';
import zhCN from './locales/zh-cn.json';

const resources = {
    en: { translation: en },
    ja: { translation: ja },
    'zh-TW': { translation: zhTW },
    'zh-CN': { translation: zhCN },
};

i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
        resources,
        fallbackLng: 'en',
        supportedLngs: ['en', 'ja', 'zh-TW', 'zh-CN'],

        detection: {
            order: ['localStorage', 'navigator'],
            caches: ['localStorage'],
        },

        interpolation: {
            escapeValue: false, // React already escapes
        },
    });

export default i18n;
