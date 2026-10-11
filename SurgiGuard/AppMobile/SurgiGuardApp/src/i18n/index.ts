import i18n from 'i18next';
import { initReactI18next, useTranslation } from 'react-i18next';
import { getLocales } from 'react-native-localize';
import AsyncStorage from '@react-native-async-storage/async-storage';
import en from './en';
import fr from './fr';

const KEY = 'sg.language';
export type Lang = 'en' | 'fr';

const deviceLang: Lang = getLocales()[0]?.languageCode === 'fr' ? 'fr' : 'en';

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr } },
  lng: deviceLang,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

// A language chosen in Settings overrides the device language
AsyncStorage.getItem(KEY).then(v => { if (v === 'en' || v === 'fr') i18n.changeLanguage(v); }).catch(() => {});

export function setLanguage(lang: Lang) {
  i18n.changeLanguage(lang);
  AsyncStorage.setItem(KEY, lang).catch(() => {});
}

/** t() plus `list()` for "a|b|c" strings */
export function useT() {
  const { t, i18n: inst } = useTranslation();
  const list = (key: string) => t(key).split('|');
  return { t, list, lang: (inst.language === 'fr' ? 'fr' : 'en') as Lang };
}

export default i18n;
