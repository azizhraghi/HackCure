import React, { useEffect } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { BlurView } from '@react-native-community/blur';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withTiming, ZoomIn } from 'react-native-reanimated';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Button, Chip, SimulatedTag } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

function Ripple({ inset, delay }: { inset: number; delay: number }) {
  const p = useSharedValue(0);
  useEffect(() => {
    const id = setTimeout(() => { p.value = withRepeat(withTiming(1, { duration: 1800, easing: Easing.out(Easing.quad) }), -1, false); }, delay);
    return () => clearTimeout(id);
  }, [p, delay]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: 0.85 + p.value * 0.25 }], opacity: 1 - p.value * 0.6 }));
  return <Animated.View style={[{ position: 'absolute', top: inset, left: inset, right: inset, bottom: inset, borderRadius: 99, borderWidth: 1, borderColor: '#9679e2' }, style]} />;
}

export function SensingRequestScreen({ navigation }: RootScreen<'SensingRequest'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const steps = list('sensing.steps');
  return (
    <View style={{ flex: 1 }}>
      {/* blurred page behind (.blur-page) */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: c.bg, padding: 16, paddingTop: 50, opacity: 0.9 }]}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, height: 60 }}>
          <Avatar initials="SM" /><View><T size={9} color={c.muted}>{t('sensing.morning')}</T><T size={14} w={800}>Sarah</T></View>
        </View>
        <T size={29} w={800} style={{ marginVertical: 13 }}>{t('sensing.activity')}</T>
        <View style={{ height: 190, borderWidth: 1, borderColor: c.ink, backgroundColor: c.sky, borderRadius: 23 }} />
        <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
          <View style={{ flex: 1, height: 190, backgroundColor: c.pink, borderWidth: 1, borderColor: c.ink, borderRadius: 20 }} />
          <View style={{ flex: 1, height: 190, backgroundColor: c.yellow, borderWidth: 1, borderColor: c.ink, borderRadius: 20 }} />
        </View>
      </View>
      <BlurView style={StyleSheet.absoluteFill} blurType="light" blurAmount={6} reducedTransparencyFallbackColor="white" />
      <View style={[StyleSheet.absoluteFill, { backgroundColor: c.scrim, justifyContent: 'center', padding: 20 }]}>
        <Animated.View entering={ZoomIn.duration(260)} style={{ backgroundColor: c.lilacBg, borderWidth: 1.5, borderColor: c.ink, borderRadius: 27, padding: 20, alignItems: 'center' }}>
          <Pressable onPress={() => navigation.goBack()} style={{ position: 'absolute', right: 13, top: 13, width: 30, height: 30, borderRadius: 15, backgroundColor: c.surface, borderWidth: 1.2, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="close" />
          </Pressable>
          <View style={{ width: 95, height: 95, alignItems: 'center', justifyContent: 'center', marginBottom: 3 }}>
            <Ripple inset={0} delay={0} /><Ripple inset={10} delay={500} />
            <View style={{ width: 51, height: 51, borderRadius: 17, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="sensor" size={28} />
            </View>
          </View>
          <View style={{ flexDirection: 'row', gap: 5, alignItems: 'center' }}>
            <Chip tone="lavender">{t('sensing.chip')}</Chip><SimulatedTag />
          </View>
          <T size={22} w={800} center spacing={-0.7} style={{ marginTop: 10, lineHeight: 26 }}>{t('sensing.title')}</T>
          <T size={10} center lh={1.5} color={c.muted} style={{ marginTop: 9, marginBottom: 14, marginHorizontal: 5 }}>{t('sensing.body')}</T>
          <Button icon="camera" flat height={45} style={{ alignSelf: 'stretch' }} onPress={() => navigation.replace('WoundScan')}>{t('sensing.photo')}</Button>
          <Button secondary flat height={45} style={{ alignSelf: 'stretch', marginTop: 8 }} onPress={() => navigation.goBack()}>{t('common.later')}</Button>
          <View style={{ alignSelf: 'stretch', borderTopWidth: 1, borderTopColor: '#c6bfdc', marginTop: 16, paddingTop: 12 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <T size={8} w={800}>{t('sensing.evidence')}</T><T size={8}>{t('sensing.count')}</T>
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 }}>
              <View style={{ position: 'absolute', left: 25, right: 25, top: 10, borderTopWidth: 1, borderStyle: 'dashed', borderColor: '#7c7790' }} />
              {steps.map((s, i) => (
                <View key={s} style={{ width: 62, alignItems: 'center' }}>
                  <View style={{ width: 21, height: 21, borderRadius: 11, borderWidth: 1, borderColor: c.ink, backgroundColor: i < 3 ? c.primary : c.surface, alignItems: 'center', justifyContent: 'center' }}>
                    <T size={7} w={800} color={i < 3 ? '#fff' : c.text}>{i < 3 ? '✓' : '4'}</T>
                  </View>
                  <T size={5.5} center style={{ marginTop: 4 }}>{s}</T>
                </View>
              ))}
            </View>
          </View>
          <Pressable onPress={() => navigation.replace('Escalation')} style={{ marginTop: 14 }}>
            <T size={8} w={800} color={c.primary} style={{ textDecorationLine: 'underline' }}>{t('sensing.seeAlert')}</T>
          </Pressable>
        </Animated.View>
      </View>
    </View>
  );
}
