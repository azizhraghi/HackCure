import React, { useEffect } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';
import { useT } from '../i18n';
import { useTheme } from '../theme/ThemeContext';
import { Icon } from './Icon';
import { T } from './T';
import { haptic } from './ui';

const BLUE_A = '#1e88e5';
const BLUE_B = '#6a5cf5';

/** Floating "Ask SurgiGuard" button shown above the tab bar on every patient tab. */
export function AssistantFab() {
  const nav = useNavigation();
  const { t } = useT();
  const insets = useSafeAreaInsets();
  const ring = useSharedValue(0);
  useEffect(() => {
    ring.value = withRepeat(withTiming(1, { duration: 1600, easing: Easing.out(Easing.quad) }), -1, false); // restarts from 0
  }, [ring]);
  const halo = useAnimatedStyle(() => ({ opacity: 0.45 * (1 - ring.value), transform: [{ scale: 1 + ring.value * 0.35 }] }));
  return (
    <View pointerEvents="box-none" style={{ position: 'absolute', right: 16, bottom: Math.max(insets.bottom, 10) + 74 }}>
      <Animated.View pointerEvents="none" style={[{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, borderRadius: 30, backgroundColor: BLUE_A }, halo]} />
      <Pressable accessibilityRole="button" accessibilityLabel={t('ai.fab')} onPress={() => { haptic('impactMedium'); nav.navigate('AIAssistant'); }}
        style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 12, paddingLeft: 13, paddingRight: 17, borderRadius: 30,
          backgroundColor: BLUE_A, borderWidth: 1.5, borderColor: '#ffffff', transform: [{ scale: pressed ? 0.96 : 1 }],
          shadowColor: '#1b2a4a', shadowOpacity: 0.3, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 8 })}>
        <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.22)', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="sparkle" size={17} color="#ffffff" />
        </View>
        <T size={10} w={800} color="#ffffff">{t('ai.fab')}</T>
      </Pressable>
    </View>
  );
}

/** Big assistant entry on Home: a search-style field plus suggestion chips that open the chat with the question. */
export function AssistantBar() {
  const nav = useNavigation();
  const { c } = useTheme();
  const { t, list } = useT();
  const open = (question?: string) => { haptic(); nav.navigate('AIAssistant', question ? { question } : undefined); };
  return (
    <View style={{ marginTop: 12, borderRadius: 24, borderWidth: 1.5, borderColor: c.ink, overflow: 'hidden' }}>
      <Svg width="100%" height="100%" style={{ position: 'absolute' }}>
        <Defs>
          <LinearGradient id="assistantBar" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={BLUE_A} /><Stop offset="1" stopColor={BLUE_B} />
          </LinearGradient>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#assistantBar)" />
      </Svg>
      <View style={{ padding: 14 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.22)', borderWidth: 1.2, borderColor: '#ffffff', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="sparkle" size={21} color="#ffffff" />
          </View>
          <View style={{ flex: 1 }}>
            <T size={13} w={800} color="#ffffff">{t('ai.barTitle')}</T>
            <T size={7.5} color="rgba(255,255,255,0.9)" style={{ marginTop: 2 }}>{t('ai.barSub')}</T>
          </View>
        </View>
        <Pressable onPress={() => open()} accessibilityRole="search"
          style={({ pressed }) => ({ marginTop: 12, height: 46, borderRadius: 23, backgroundColor: '#ffffff', flexDirection: 'row', alignItems: 'center', paddingLeft: 16, paddingRight: 6, opacity: pressed ? 0.85 : 1 })}>
          <T size={9.5} color="#64718a" style={{ flex: 1 }}>{t('ai.placeholder')}</T>
          <View style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: BLUE_A, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="send" size={16} color="#ffffff" />
          </View>
        </Pressable>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6, paddingTop: 10 }}>
          {list('ai.suggestions').map(s => (
            <Pressable key={s} onPress={() => open(s)}
              style={{ paddingVertical: 7, paddingHorizontal: 11, borderRadius: 99, borderWidth: 1, borderColor: 'rgba(255,255,255,0.7)', backgroundColor: 'rgba(255,255,255,0.16)' }}>
              <T size={8} w={700} color="#ffffff">{s}</T>
            </Pressable>
          ))}
        </ScrollView>
      </View>
    </View>
  );
}
