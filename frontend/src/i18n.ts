import i18next from 'i18next';
import locI18next from 'loc-i18next';
// import LngDetector from 'i18next-browser-languagedetector';
import translation from './locales/translation.json';

const API_CLONE = '/api/config';

export async function initLocale(): Promise<void> {
    let language = undefined;
    try {
        const response = await fetch(API_CLONE);
        const data = await response.json();
        language = data.lang;
    } catch (error) {
        console.error('Error fetching language:', error);
    }

    i18next.init({
        lng: language,
        // debug: true,
        resources: translation,
      });
    const localize = locI18next.init(i18next);
    localize("#app");
}
