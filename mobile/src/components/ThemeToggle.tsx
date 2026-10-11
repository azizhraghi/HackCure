import React from 'react';
import { Pressable, View } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { useT } from '../i18n';
import { T } from './T';

/** Always available, including onboarding, without covering screen actions. */
export function ThemeToggle() {
  const { c, isDark, setDark } = useTheme();
  const { lang } = useT();
  const label = lang === 'fr' ? (isDark ? 'Mode clair' : 'Mode sombre') : (isDark ? 'Light mode' : 'Dark mode');
  return <View style={{ backgroundColor:c.bg, paddingHorizontal:16, paddingVertical:5, alignItems:'flex-end' }}>
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={() => setDark(!isDark)}
      hitSlop={4} style={({pressed}) => ({minHeight:32, paddingHorizontal:12, borderRadius:99, borderWidth:1,
        borderColor:c.ink, backgroundColor:c.surface, justifyContent:'center', opacity:pressed ? .7 : 1})}>
      <T size={10} w={700}>{isDark ? '☀' : '☾'}  {label}</T>
    </Pressable>
  </View>;
}
