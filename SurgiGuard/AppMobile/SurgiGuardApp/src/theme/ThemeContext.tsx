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
