import i18next from 'i18next';
import locI18next from 'loc-i18next';
// import LngDetector from 'i18next-browser-languagedetector';
import translation from './locales/translation.json';

const API_CLONE = '/api/config';

export async function initLocale(): Promise<void> {
    const language = localStorage.getItem('i18nextLng');
    i18next.init({
        // debug: true,
        lng: language,
        resources: translation,
    });
    const localize = locI18next.init(i18next);
    localize("body");

    // Async refresh language
    try {
        const response = await fetch(API_CLONE);
        const data = await response.json();
        const targetLanguage = data.lang;
        if (targetLanguage !== language) {
            localStorage.setItem('i18nextLng', language);
            i18next.changeLanguage(targetLanguage)
            localize("body");
        }
    } catch (error) {
        console.error('Error fetching language:', error);
    }
}
