import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en/translation.json';
import hi from './locales/hi/translation.json';
import mr from './locales/mr/translation.json';

export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', short: 'EN' },
  { code: 'hi', label: 'हिन्दी', short: 'हि' },
  { code: 'mr', label: 'मराठी', short: 'म' },
];

// Fallback language used whenever a key is missing in the selected language.
export const FALLBACK_LANGUAGE = 'en';
const STORAGE_KEY = 'afa.language'; // UI language preference only - not auth data.

const readStored = () => {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return SUPPORTED_LANGUAGES.some((l) => l.code === v) ? v : null;
  } catch {
    return null;
  }
};

const detect = () => {
  const stored = readStored();
  if (stored) return stored;
  const nav = (navigator.language || '').slice(0, 2);
  return SUPPORTED_LANGUAGES.some((l) => l.code === nav) ? nav : FALLBACK_LANGUAGE;
};

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    hi: { translation: hi },
    mr: { translation: mr },
  },
  lng: detect(),
  fallbackLng: FALLBACK_LANGUAGE,
  interpolation: { escapeValue: false },
  returnEmptyString: false, // empty strings fall back instead of rendering blank
});

const applyDocumentLanguage = (lng) => {
  document.documentElement.lang = lng;
};
applyDocumentLanguage(i18n.language);
i18n.on('languageChanged', applyDocumentLanguage);

export function setLanguage(code) {
  if (!SUPPORTED_LANGUAGES.some((l) => l.code === code)) return;
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    /* storage unavailable - language still changes for this session */
  }
  return i18n.changeLanguage(code);
}

export default i18n;
