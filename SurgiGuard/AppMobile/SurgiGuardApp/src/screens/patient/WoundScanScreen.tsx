import React, { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Svg, { Defs, Ellipse, RadialGradient, Rect, Stop } from 'react-native-svg';
import { CameraPreview } from '../../components/CameraPreview';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Chip, haptic, RoundButton, Screen, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

/** .camera-gradient + .wound-shape — design look when the camera is unavailable */
function MockSkin() {
  return (
    <Svg width="100%" height="100%" style={StyleSheet.absoluteFill}>
      <Defs>
        <RadialGradient id="skin" cx="50%" cy="50%" rx="70%" ry="60%">
          <Stop offset="0" stopColor="#e4b39d" /><Stop offset="0.45" stopColor="#c58e7e" /><Stop offset="0.78" stopColor="#34475a" /><Stop offset="1" stopColor="#273748" />
        </RadialGradient>
        <RadialGradient id="wound" cx="50%" cy="50%" rx="50%" ry="50%">
          <Stop offset="0.1" stopColor="#a54c48" /><Stop offset="0.25" stopColor="#db746b" /><Stop offset="0.45" stopColor="#e9a08f" /><Stop offset="0.47" stopColor="#e9a08f" stopOpacity={0} />
        </RadialGradient>
      </Defs>
      <Rect width="100%" height="100%" fill="url(#skin)" />
      <Ellipse cx="50%" cy="40%" rx="68" ry="30" fill="url(#wound)" />
    </Svg>
  );
}

function Corners({ color = '#fff', size = 42, width = 270, height = 225 }: { color?: string; size?: number; width?: number; height?: number }) {
  const b = { position: 'absolute' as const, width: size, height: size, borderColor: color };
  return (
    <View pointerEvents="none" style={{ width, height }}>
      <View style={[b, { left: 0, top: 0, borderLeftWidth: 3, borderTopWidth: 3, borderTopLeftRadius: 13 }]} />
      <View style={[b, { right: 0, top: 0, borderRightWidth: 3, borderTopWidth: 3, borderTopRightRadius: 13 }]} />
      <View style={[b, { left: 0, bottom: 0, borderLeftWidth: 3, borderBottomWidth: 3, borderBottomLeftRadius: 13 }]} />
      <View style={[b, { right: 0, bottom: 0, borderRightWidth: 3, borderBottomWidth: 3, borderBottomRightRadius: 13 }]} />
    </View>
  );
}
export { Corners };

function WoundHalf({ label, today }: { label: string; today?: boolean }) {
  return (
    <View style={{ flex: 1, backgroundColor: today ? '#e2b29c' : '#dca892', alignItems: 'center', justifyContent: 'center', borderLeftWidth: today ? 1 : 0, borderLeftColor: '#fff' }}>
      <Svg width={today ? 60 : 76} height={27} style={{ opacity: today ? 0.76 : 1, transform: [{ rotate: '-6deg' }] }}>
        <Defs>
          <RadialGradient id={`wh${today ? 1 : 0}`} cx="50%" cy="50%" rx="50%" ry="50%">
            <Stop offset="0" stopColor="#a34f49" /><Stop offset="0.35" stopColor="#dc7a6d" /><Stop offset="0.67" stopColor="#dc7a6d" stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Rect width="100%" height="100%" fill={`url(#wh${today ? 1 : 0})`} />
      </Svg>
      <T size={6} w={800} color="#fff" style={{ position: 'absolute', top: 6, left: 6, textShadowColor: '#333', textShadowRadius: 2 }}>{label}</T>
    </View>
  );
}

export function WoundScanScreen({ navigation }: RootScreen<'WoundScan'>) {
  const { c } = useTheme();
  const { t } = useT();
  const [torch, setTorch] = useState(false);
  const [captured, setCaptured] = useState(false);
  const [saved, setSaved] = useState(false);

  return (
    <Screen>
      <TopBar title={t('scan.top')} action={<RoundButton icon="close" onPress={() => navigation.goBack()} />} />
      <View style={{ height: 407, marginHorizontal: -16, backgroundColor: '#273748', overflow: 'hidden', alignItems: 'center' }}>
        <CameraPreview fallback={<MockSkin />} permissionLabel={t('scan.allow')} torch={torch} />
        <View style={{ position: 'absolute', top: 50 }}><Corners /></View>
        <Chip tone="dark" style={{ position: 'absolute', top: 294, alignSelf: 'center' }}>{captured ? t('scan.captured') : t('scan.align')}</Chip>
        <View style={{ position: 'absolute', left: 31, right: 31, bottom: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <T size={8} color="#fff">{t('scan.auto')}</T>
          <Pressable onPress={() => { haptic('impactMedium'); setCaptured(true); setSaved(false); }}
            style={({ pressed }) => ({ width: 61, height: 61, borderRadius: 31, borderWidth: 4, borderColor: '#fff', backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center', transform: [{ scale: pressed ? 0.94 : 1 }] })}>
            <Icon name="camera" size={26} color="#fff" />
          </Pressable>
          <Pressable onPress={() => setTorch(v => !v)}><T size={8} color="#fff">{torch ? t('scan.flashOn') : t('scan.flashOff')}</T></Pressable>
        </View>
      </View>

      <View style={{ backgroundColor: c.surface, marginHorizontal: -16, paddingHorizontal: 16, paddingVertical: 10 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 9 }}>
          <View>
            <T size={6} spacing={1} color={c.muted}>{t('scan.ai')}</T>
            <T size={14} w={800} style={{ marginTop: 2 }}>{t('scan.progress')}</T>
          </View>
          <Chip tone="green">{t('scan.good')}</Chip>
        </View>
        <View style={{ height: 92, flexDirection: 'row', borderWidth: 1.3, borderColor: c.ink, borderRadius: 15, overflow: 'hidden' }}>
          <WoundHalf label={t('scan.day1')} />
          <WoundHalf label={t('scan.today')} today />
          <View style={{ position: 'absolute', left: '50%', top: '50%', marginLeft: -14, marginTop: -14, width: 27, height: 27, borderRadius: 14, backgroundColor: '#fff', borderWidth: 1, borderColor: '#1b2a4a', alignItems: 'center', justifyContent: 'center' }}>
            <T size={9} w={800} color="#1b2a4a">‹ ›</T>
          </View>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginVertical: 8 }}>
          <Chip tone="pink" style={{ flexGrow: 1 }}><T size={9} w={800}>{t('scan.redness')}  ↑ 12%</T></Chip>
          <Chip tone="yellow" style={{ flexGrow: 1 }}><T size={9} w={800}>{t('scan.swelling')}  {t('scan.stable')}</T></Chip>
          <Chip tone="green" style={{ flexGrow: 1 }}><T size={9} w={800}>{t('scan.area')}  ↓ 8%</T></Chip>
          <Chip tone="blue" style={{ flexGrow: 1, alignSelf: 'stretch', width: '100%' }}><T size={9} w={800}>{t('scan.discharge')}  {t('scan.none')}</T></Chip>
        </View>
        <Button onPress={() => { haptic('notificationSuccess'); setSaved(true); setTimeout(() => navigation.goBack(), 900); }}>{saved ? t('scan.saved') : t('scan.save')}</Button>
      </View>
    </Screen>
  );
}
