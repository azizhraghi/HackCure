import React, { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Svg, { Circle, Path } from 'react-native-svg';
import { ArcGauge } from '../../components/charts';
import { CameraPreview } from '../../components/CameraPreview';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Chip, haptic, Screen, SectionRow, Toggle, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

/** .pose-camera mock person used when the camera is unavailable */
function MockPose() {
  return (
    <LinearGradient colors={['#d7d5cf', '#9ea4a0']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={StyleSheet.absoluteFill}>
      <View style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 48, backgroundColor: '#7d8c82' }} />
      <View style={{ position: 'absolute', width: 28, height: 28, borderRadius: 14, backgroundColor: '#495963', left: 181, top: 17 }} />
      <View style={{ position: 'absolute', width: 42, height: 89, borderRadius: 20, backgroundColor: '#5d7180', left: 174, top: 41, transform: [{ rotate: '5deg' }] }} />
      <View style={{ position: 'absolute', width: 23, height: 87, borderRadius: 13, backgroundColor: '#465865', left: 184, top: 118, transform: [{ rotate: '31deg' }] }} />
      <View style={{ position: 'absolute', width: 23, height: 87, borderRadius: 13, backgroundColor: '#465865', left: 222, top: 160, transform: [{ rotate: '-61deg' }] }} />
    </LinearGradient>
  );
}

export function RehabScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const [week, setWeek] = useState(false);
  const [done, setDone] = useState([true, false, false]);
  const exercises = [[t('rehab.ex1'), t('rehab.ex1s')], [t('rehab.ex2'), t('rehab.ex2s')], [t('rehab.ex3'), t('rehab.ex3s')]];

  return (
    <Screen>
      <TopBar title={t('rehab.top')} action={<Toggle options={[t('common.day'), t('common.week')]} value={week ? t('common.week') : t('common.day')} onChange={v => setWeek(v === t('common.week'))} />} />
      <Card bg={c.sky} radius={23} style={{ height: 279, paddingVertical: 12, paddingHorizontal: 14, overflow: 'hidden' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <T size={7} w={800} spacing={1}>{t('rehab.goal')}</T>
          <Chip>{t('rehab.target')}</Chip>
        </View>
        <ArcGauge value={week ? 76 : 82} label={t('rehab.flexion')} />
        <T size={12} w={800} center lh={1.4} style={{ marginTop: -5 }}>{t('rehab.push')}</T>
      </Card>

      <View style={{ height: 221, marginTop: 9, borderWidth: 1.5, borderColor: c.ink, borderRadius: 21, overflow: 'hidden' }}>
        <CameraPreview position="front" fallback={<MockPose />} permissionLabel={t('rehab.permission')} />
        <Svg width="100%" height="100%" viewBox="0 0 350 220" style={StyleSheet.absoluteFill}>
          <Path d="M193 58 180 130 250 177" fill="none" stroke="#66e7b1" strokeWidth={3} />
          <Path d="M180 100a30 30 0 0 1 27 44" fill="none" stroke="#fbe19b" strokeWidth={2} strokeDasharray="4 3" />
          {[[193, 58, 5], [180, 130, 7], [250, 177, 5]].map(([x, y, r]) => <Circle key={x} cx={x} cy={y} r={r} fill="#1e88e5" stroke="#fff" strokeWidth={2} />)}
        </Svg>
        <View style={{ position: 'absolute', left: 107, top: 103, width: 58, height: 58, borderRadius: 29, backgroundColor: '#fbe19b', borderWidth: 1.4, borderColor: '#1b2a4a', alignItems: 'center', justifyContent: 'center' }}>
          <T size={17} w={800} color="#1b2a4a">92°</T>
          <T size={5} color="#1b2a4a">{t('rehab.targetSmall')}</T>
        </View>
        <Chip tone="dark" style={{ position: 'absolute', bottom: 9, alignSelf: 'center' }}>{t('rehab.reps')}</Chip>
        <View style={{ position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(20,30,45,0.75)', borderRadius: 9, paddingVertical: 5, paddingHorizontal: 7 }}>
          <T size={6} spacing={0.5} color="#fff"><T size={6} color="#ff5d58">●</T> {t('rehab.live')}</T>
        </View>
      </View>

      <View style={{ flexDirection: 'row', gap: 7, marginTop: 9 }}>
        {[[t('rehab.maxAngle'), '98°', '', t('rehab.plus'), c.yellow], [t('rehab.repsK'), '12', '/20', t('rehab.form'), c.pink], [t('rehab.painAfter'), '3', '/10', t('rehab.within'), c.green]].map(([k, v, sup, s, bg]) => (
          <Card key={k} bg={bg} radius={16} style={{ flex: 1, height: 98, padding: 10 }}>
            <T size={6} w={800}>{k}</T>
            <T size={21} w={800} style={{ marginTop: 11, marginBottom: 3 }}>{v}<T size={8} w={800}>{sup}</T></T>
            <T size={6.5}>{s}</T>
          </Card>
        ))}
      </View>

      <SectionRow title={t('rehab.exercises')} />
      <Card radius={17}>
        {exercises.map(([name, sub], i) => (
          <Pressable key={name} onPress={() => { haptic('notificationSuccess'); setDone(d => d.map((x, n) => (n === i ? !x : x))); }}
            style={{ minHeight: 52, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 11, borderBottomWidth: i < 2 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 30, height: 30, borderRadius: 9, borderWidth: 1, borderColor: c.ink, backgroundColor: [c.sky, c.lavender, c.yellow][i], alignItems: 'center', justifyContent: 'center' }}><Icon name="activity" size={16} /></View>
            <View style={{ flex: 1 }}>
              <T size={9} w={800} style={{ textDecorationLine: done[i] ? 'line-through' : 'none' }}>{name}</T>
              <T size={7} color={c.muted} style={{ marginTop: 2 }}>{sub}</T>
            </View>
            <View style={{ width: 24, height: 24, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: done[i] ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {done[i] && <Icon name="check" size={14} />}
            </View>
          </Pressable>
        ))}
      </Card>
    </Screen>
  );
}
