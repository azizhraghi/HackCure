import React, { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { dark, light, type Palette } from './tokens';


const KEY = 'sg.darkMode';

type ThemeValue = { c: Palette; isDark: boolean; setDark: (v: boolean) => void };

const ThemeContext = createContext<ThemeValue>({ c: light, isDark: false, setDark: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY).then(v => v === '1' && setIsDark(true)).catch(() => {});
  }, []);

  const value = useMemo<ThemeValue>(() => ({
    c: isDark ? dark : light,
    isDark,
    setDark: (v: boolean) => {
      setIsDark(v);
      AsyncStorage.setItem(KEY, v ? '1' : '0').catch(() => {});
    },
  }), [isDark]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);

/** Palette of the holographic twin stage (always dark, cyan accents), whatever the app theme. */
export const holo: Palette = {
  ...dark,
  ink: 'rgba(110,220,255,0.5)', primary: '#36c6ff', surface: '#0b1d30', glass: 'rgba(6,22,38,0.82)',
  stageA: '#0f3550', stageB: '#071a2b', stageC: '#02060c', text: '#e6f7ff', title: '#f2fbff', muted: '#8fb3c9',
};

export function HoloTheme({ children }: { children: ReactNode }) {
  const parent = useContext(ThemeContext);
  return <ThemeContext.Provider value={{ ...parent, c: holo, isDark: true }}>{children}</ThemeContext.Provider>;
}
