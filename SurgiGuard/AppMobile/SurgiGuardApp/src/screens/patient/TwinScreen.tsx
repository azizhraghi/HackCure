import React, { useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import Slider from '@react-native-community/slider';
import { useNavigation } from '@react-navigation/native';
import Animated, { Easing, FadeIn, FadeInDown, SlideInDown, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import Svg, { Defs, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { MiniLine, useCountUp, WoundThumb } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Twin3D, type Twin3DHandle } from '../../components/twin/Twin3D';
import { Card, Chip, haptic, Screen, SimulatedTag, Toggle, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

const LAYERS = ['Overview', 'Wound', 'Mobility', 'Sensors', 'Muscles'];
const STAGE_H = 509;

function Ecg() {
  const x = useSharedValue(0);
  useEffect(() => { x.value = withRepeat(withTiming(1, { duration: 2500, easing: Easing.linear }), -1, false); }, [x]);
  const style = useAnimatedStyle(() => ({ transform: [{ translateX: -x.value * 390 }] }));
  return (
    <Animated.View style={[{ width: 780, height: 70, flexDirection: 'row', opacity: 0.4 }, style]}>
      {[0, 1].map(i => (
        <Svg key={i} width={390} height={70} viewBox="0 0 390 70">
          <Path d="M0 35h70l10-13 12 34 15-49 14 28h45l9-10 11 20 13-10h191" fill="none" stroke="#1e88e5" strokeWidth={2} />
        </Svg>
      ))}
    </Animated.View>
  );
}

type Callout = { key: string; icon: IconName; label: string; value: string; trend: string; expected: string; tone: 'track' | 'review'; status: string; pos: object };

export function TwinScreen() {
  const { c } = useTheme();
  const { t, list } = useT();
  const nav = useNavigation();
  const twin = useRef<Twin3DHandle>(null);
  const [weekView, setWeekView] = useState(false);
  const [layer, setLayer] = useState('Overview');
  const [day, setDay] = useState(4);
  const [selected, setSelected] = useState<string | null>(null);
  const [sliderW, setSliderW] = useState(1);

  const progress = (day - 1) / 41;
  const mobility = Math.round(64 + progress * 55);
  const healing = Math.round(91 + progress * 10);
  const mobilityShown = useCountUp(mobility);
  const healingShown = useCountUp(healing);
  const angle = Math.round(74 + progress * 25);

  const callouts: Callout[] = [
    { key: 'mobility', icon: 'rotate', label: t('twin.mobility'), value: `${mobilityShown}%`, trend: '↑', expected: t('twin.expected', { v: `${Math.min(95, mobility + 7)}%` }), tone: 'track', status: t('common.onTrack'), pos: { left: 9, top: 116 } },
    { key: 'temp', icon: 'thermo', label: t('twin.temp'), value: '37.8°C', trend: '↑', expected: t('twin.expected', { v: '≤37.4°C' }), tone: 'review', status: t('twin.needsAttention'), pos: { right: 9, top: 105 } },
    { key: 'pain', icon: 'activity', label: t('twin.pain'), value: '3/10', trend: '↓', expected: t('twin.expected', { v: '4/10' }), tone: 'track', status: t('common.onTrack'), pos: { left: 9, top: 281 } },
    { key: 'wound', icon: 'camera', label: t('twin.wound'), value: `${healingShown}/100`, trend: '↑', expected: t('twin.expected', { v: '89/100' }), tone: 'track', status: t('common.onTrack'), pos: { right: 9, top: 267 } },
  ];
  const sel = callouts.find(x => x.key === selected);
  const layerNames = list('twin.layers');

  return (
    <Screen>
      <TopBar title={t('twin.top')} back={false} action={<Toggle options={[t('common.day'), t('common.week')]} value={weekView ? t('common.week') : t('common.day')} onChange={v => setWeekView(v === t('common.week'))} />} />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 4, paddingBottom: 8, paddingTop: 2 }}>
        {LAYERS.map((x, i) => (
          <Pressable key={x} onPress={() => { haptic('selection'); setLayer(x); }}
            style={{ paddingVertical: 7, paddingHorizontal: 10, borderRadius: 99, borderWidth: 1, borderColor: layer === x ? c.ink : '#bdc7d6', backgroundColor: layer === x ? c.primary : c.surface }}>
            <T size={7.5} w={700} color={layer === x ? '#fff' : c.text}>{layerNames[i]}</T>
          </Pressable>
        ))}
      </ScrollView>

      <View style={{ height: STAGE_H, borderWidth: 1.5, borderColor: c.ink, borderRadius: 25, overflow: 'hidden' }}>
        <Svg width="100%" height="100%" style={{ position: 'absolute' }}>
          <Defs>
            <RadialGradient id="stage" cx="50%" cy="40%" rx="75%" ry="65%">
              <Stop offset="0" stopColor={c.stageA} /><Stop offset="0.54" stopColor={c.stageB} /><Stop offset="1" stopColor={c.stageC} />
            </RadialGradient>
          </Defs>
          <Rect width="100%" height="100%" fill="url(#stage)" />
        </Svg>

        <View pointerEvents="none" style={{ position: 'absolute', top: 103, left: 0, right: 0, height: 70, overflow: 'hidden' }}>
          <Ecg />
          <View style={{ position: 'absolute', left: 12, top: 3, flexDirection: 'row', gap: 4 }}>
            <View style={{ paddingHorizontal: 6, paddingVertical: 3, borderRadius: 99, backgroundColor: 'rgba(255,255,255,0.75)' }}><T size={6} w={800} color="#1e88e5">72 bpm</T></View>
          </View>
        </View>

        <Twin3D ref={twin} day={day} layer={layer} highlighted={selected} onTapKnee={() => nav.navigate('TwinDetail')}
          loadingLabel={t('twin.loading')} fallbackLabel={t('twin.fallback')} />

        {/* status chip */}
        <View style={{ position: 'absolute', left: 12, top: 11, height: 25, paddingHorizontal: 9, flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderColor: c.ink, borderRadius: 99, backgroundColor: c.glass }}>
          <Icon name="check" size={13} color={c.trackText} />
          <T size={6.5} w={800} color={c.trackText}>{t('twin.status', { day })}</T>
        </View>

        {/* view controls */}
        <View style={{ position: 'absolute', right: 10, top: 42, flexDirection: 'row', borderWidth: 1, borderColor: c.ink, borderRadius: 10, overflow: 'hidden', backgroundColor: c.glass }}>
          {([['rotate', <Icon key="r" name="rotate" size={15} />], ['zoom', <T key="z" size={14} w={800}>＋</T>], ['reset', <T key="h" size={14} w={800}>⌂</T>]] as const).map(([cmd, node], i) => (
            <Pressable key={cmd} onPress={() => { haptic('selection'); twin.current?.command(cmd); }} style={{ width: 34, height: 34, alignItems: 'center', justifyContent: 'center', borderRightWidth: i < 2 ? 1 : 0, borderRightColor: '#d4dbe5' }}>
              {node}
            </Pressable>
          ))}
        </View>

        {/* callout cards */}
        {callouts.map((item, i) => (
          <Animated.View key={item.key} entering={FadeInDown.delay(i * 80).duration(420)} style={[{ position: 'absolute', width: 113 }, item.pos]}>
            <Pressable onPress={() => { haptic('selection'); setSelected(item.key); }}
              style={{ minHeight: 65, padding: 7, paddingLeft: 10, borderWidth: selected === item.key ? 1.5 : 1, borderColor: selected === item.key ? c.primary : 'rgba(27,42,74,0.58)', borderRadius: 12, backgroundColor: c.glass, transform: [{ translateY: selected === item.key ? -2 : 0 }] }}>
              <View style={{ position: 'absolute', left: 0, top: 9, bottom: 9, width: 3, borderTopRightRadius: 4, borderBottomRightRadius: 4, backgroundColor: item.tone === 'review' ? c.review : c.track }} />
              <View style={{ flexDirection: 'row', gap: 5 }}>
                <View style={{ width: 23, height: 23, borderRadius: 7, alignItems: 'center', justifyContent: 'center', backgroundColor: item.tone === 'review' ? '#fff0d8' : '#e8f5f1' }}>
                  <Icon name={item.icon} size={14} color="#1b2a4a" />
                </View>
                <View style={{ flex: 1 }}>
                  <T size={5.5} w={800} numberOfLines={1}>{item.label}</T>
                  <T size={10} w={800} style={{ marginTop: 2 }}>{item.value} <T size={7} w={800} color={item.tone === 'review' ? c.reviewText : c.trackText}>{item.trend}</T></T>
                </View>
              </View>
              <T size={5} w={600} color={c.muted} style={{ marginTop: 4 }} lh={1.3}>
                <T size={5} w={800} color={item.tone === 'review' ? c.reviewText : c.trackText}>{item.status}</T> · {item.expected}
              </T>
            </Pressable>
          </Animated.View>
        ))}

        {/* layer readouts */}
        {layer === 'Wound' && (
          <Animated.View entering={FadeIn} style={{ position: 'absolute', left: 25, bottom: 62, padding: 5, flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderColor: c.ink, borderRadius: 10, backgroundColor: c.glass }}>
            <View style={{ alignItems: 'center' }}><WoundThumb width={35} height={31} radius={6} /><T size={4.5}>{t('scan.day1')}</T></View>
            <T w={800}>→</T>
            <View style={{ alignItems: 'center' }}><WoundThumb width={35} height={31} radius={6} /><T size={4.5}>{t('common.today')}</T></View>
          </Animated.View>
        )}
        {layer === 'Mobility' && (
          <Animated.View entering={FadeIn} style={{ position: 'absolute', right: 12, bottom: 62, width: 109, padding: 7, borderWidth: 1, borderColor: c.ink, borderRadius: 10, backgroundColor: c.glass }}>
            <T size={6}>{t('twin.kneeAngle')}</T><T size={16} w={800}>{angle}°</T><T size={6} color={c.muted}>{t('twin.goal')}</T>
          </Animated.View>
        )}
        {layer === 'Sensors' && (
          <Animated.View entering={FadeIn} style={{ position: 'absolute', left: 12, right: 12, bottom: 62, flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 4 }}>
            <Chip tone="yellow">37.8°C</Chip><Chip tone="blue">{t('twin.moisture')}</Chip>
            <View style={{ paddingHorizontal: 6, paddingVertical: 4, borderRadius: 99, backgroundColor: '#fff' }}><T size={5.5} color="#1b2a4a">{t('twin.signal')}</T></View>
            <SimulatedTag />
          </Animated.View>
        )}
        {layer === 'Muscles' && (
          <Animated.View entering={FadeIn} style={{ position: 'absolute', left: 12, bottom: 62, flexDirection: 'row', gap: 7, padding: 6, borderWidth: 1, borderColor: c.ink, borderRadius: 9, backgroundColor: c.surface }}>
            {[[t('twin.low'), '#f2c1cf'], [t('twin.moderate'), '#df7ea0'], [t('twin.active'), '#b54c73']].map(([l, col]) => (
              <View key={l} style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}><View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: col }} /><T size={5}>{l}</T></View>
            ))}
          </Animated.View>
        )}

        {/* day slider */}
        <View style={{ position: 'absolute', left: 13, right: 13, bottom: 10, flexDirection: 'row', alignItems: 'flex-end', gap: 4 }}>
          <T size={5.5} w={800} style={{ marginBottom: 7 }}>{t('common.day')} 1</T>
          <View style={{ flex: 1 }} onLayout={e => setSliderW(e.nativeEvent.layout.width)}>
            <View pointerEvents="none" style={{ position: 'absolute', bottom: 26, left: Math.min(Math.max(progress * sliderW - 38, 0), sliderW - 76), width: 76, paddingVertical: 4, borderRadius: 7, backgroundColor: '#1b2a4a', alignItems: 'center' }}>
              <T size={5.5} w={800} color="#fff">{t('common.day')} {day} · {day === 4 ? t('twin.todayTag') : day < 4 ? t('twin.past') : t('twin.preview')}</T>
            </View>
            <Slider minimumValue={1} maximumValue={42} step={1} value={day} onValueChange={v => setDay(Math.round(v))}
              minimumTrackTintColor="#1e88e5" maximumTrackTintColor="#a9e3fa" thumbTintColor="#1e88e5" style={{ height: 30 }} />
          </View>
          <T size={5.5} w={800} style={{ marginBottom: 7 }}>{t('common.day')} 42</T>
        </View>

        {/* evidence bottom sheet */}
        {sel && (
          <Animated.View entering={SlideInDown.duration(300)} style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 174, padding: 14, paddingBottom: 10, flexDirection: 'row', gap: 10, borderTopWidth: 1.5, borderColor: c.ink, borderTopLeftRadius: 22, borderTopRightRadius: 22, backgroundColor: c.surface }}>
            <View style={{ width: 118, justifyContent: 'space-between' }}>
              <View>
                <T size={5.5} spacing={0.7}>{t('twin.trend')}</T>
                <T size={9} w={800} style={{ marginTop: 3 }}>{sel.label}</T>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}>
                {sel.key === 'wound'
                  ? <WoundThumb width={34} height={34} radius={7} />
                  : <View style={{ width: 30, height: 30, borderRadius: 8, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name={sel.key === 'temp' ? 'sensor' : 'activity'} size={17} /></View>}
                <View style={{ flex: 1 }}>
                  <T size={4.8}>{t('twin.latest')}</T>
                  <T size={5.5} w={800} lh={1.3} style={{ marginTop: 2 }}>{sel.key === 'wound' ? t('twin.photoAnalyzed') : t('twin.liveReading')}</T>
                </View>
              </View>
            </View>
            <View style={{ flex: 1, paddingTop: 20 }}>
              <View style={{ position: 'absolute', left: 0, right: 0, top: 38, height: 28, borderRadius: 5, backgroundColor: 'rgba(94,211,160,0.17)' }} />
              <MiniLine color={selected === 'temp' ? '#FFB347' : '#1e88e5'} fill height={64} />
              {selected === 'temp' && <SimulatedTag style={{ marginTop: 6 }} />}
            </View>
            <Pressable onPress={() => setSelected(null)} accessibilityLabel={t('common.close')} style={{ position: 'absolute', right: 11, top: 9, width: 30, height: 30, borderRadius: 15, borderWidth: 1, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="close" size={14} />
            </Pressable>
          </Animated.View>
        )}
      </View>

      <Pressable onPress={() => nav.navigate('PatientTabs', { screen: 'Reports' })}>
        <Card bg={c.green} radius={18} style={{ height: 92, marginTop: 9, paddingVertical: 10, paddingHorizontal: 12, flexDirection: 'row', overflow: 'hidden' }}>
          <View style={{ width: '52%' }}>
            <T size={6.5} w={800}>{t('twin.expVsActual')}</T>
            <T size={14} w={800} style={{ marginTop: 5 }}>{t('common.onTrack')} <T size={14} w={800} color={c.trackText}>✓</T></T>
            <T size={7} style={{ marginTop: 4 }}>{t('twin.ahead')}</T>
          </View>
          <View style={{ flex: 1 }}>
            <MiniLine color="#1e88e5" fill style={{ position: 'absolute', top: 4 }} />
            <MiniLine color="#70809d" dashed style={{ position: 'absolute', top: 11, opacity: 0.6 }} />
          </View>
        </Card>
      </Pressable>
    </Screen>
  );
}
