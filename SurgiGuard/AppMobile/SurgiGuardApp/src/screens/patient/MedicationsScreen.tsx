import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { ScoreRing } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, haptic, IconBadge, PageTitle, Screen, SectionRow, TopBar, toneColor } from '../../components/ui';
import type { DoseState } from '../../data/mock';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

type Dose = { id: string; med: string; purpose: string; time: string; slot: 'morning' | 'afternoon' | 'evening'; tone: string };

const DOSES: Dose[] = [
  { id: 'd1', med: 'meds.m1', purpose: 'meds.m1p', time: '08:00', slot: 'morning', tone: 'pink' },
  { id: 'd2', med: 'meds.m3', purpose: 'meds.m3p', time: '08:00', slot: 'morning', tone: 'sky' },
  { id: 'd3', med: 'meds.m2', purpose: 'meds.m2p', time: '09:00', slot: 'morning', tone: 'yellow' },
  { id: 'd4', med: 'meds.m1', purpose: 'meds.m1p', time: '14:00', slot: 'afternoon', tone: 'pink' },
  { id: 'd5', med: 'meds.m1', purpose: 'meds.m1p', time: '20:00', slot: 'evening', tone: 'pink' },
  { id: 'd6', med: 'meds.m4', purpose: 'meds.m4p', time: '20:00', slot: 'evening', tone: 'lavender' },
];

export function MedicationsScreen({ navigation }: RootScreen<'Medications'>) {
  const { c } = useTheme();
  const { t } = useT();
  const [states, setStates] = useState<Record<string, DoseState>>({ d1: 'taken', d2: 'taken', d3: 'taken' });
  const set = (id: string, s: DoseState) => { haptic(s === 'taken' ? 'notificationSuccess' : 'selection'); setStates(v => ({ ...v, [id]: s })); };
  const takenCount = Object.values(states).filter(s => s === 'taken').length;
  const next = DOSES.find(d => !states[d.id]);

  return (
    <Screen>
      <TopBar title={t('meds.top')} />
      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 6 }}>{t('meds.kicker')}</T>
      <PageTitle style={{ marginTop: 6 }}>{t('meds.title')}</PageTitle>
      <Chip tone="green" style={{ marginBottom: 12 }}><Icon name="shield" size={12} /><T size={9} w={800}>{t('meds.verified')}</T></Chip>

      <View style={{ flexDirection: 'row', gap: 10 }}>
        <Card bg={c.sky} radius={19} style={{ flex: 1.1, padding: 12, height: 128 }}>
          <T size={7.5} w={800} spacing={0.7}>{t('meds.next')}</T>
          {next ? (
            <>
              <T size={26} w={800} spacing={-1} style={{ marginTop: 6 }}>{next.time}</T>
              <T size={9} w={800} numberOfLines={1}>{t(next.med)}</T>
              <T size={7} color={c.muted} style={{ marginTop: 2 }}>{t('meds.in')}</T>
            </>
          ) : <T size={22} w={800} style={{ marginTop: 10 }}>✓</T>}
        </Card>
        <Card bg={c.surface} radius={19} style={{ flex: 1, padding: 10, height: 128, alignItems: 'center' }}>
          <T size={7.5} w={800} spacing={0.7}>{t('meds.adherence')}</T>
          <View style={{ marginTop: 6 }}><ScoreRing value={93} size={64} thickness={7} /></View>
          <T size={6.5} color={c.muted} center style={{ marginTop: 4 }}>{t('meds.adherenceSub')}</T>
        </Card>
      </View>

      {(['morning', 'afternoon', 'evening'] as const).map(slot => (
        <View key={slot}>
          <SectionRow title={t(`meds.${slot}`)} right={`${DOSES.filter(d => d.slot === slot).length}`} />
          <Card radius={17}>
            {DOSES.filter(d => d.slot === slot).map((d, i, arr) => {
              const s = states[d.id];
              return (
                <View key={d.id} style={{ minHeight: 60, flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 10, paddingVertical: 8, borderBottomWidth: i < arr.length - 1 ? 1 : 0, borderBottomColor: c.line, opacity: s === 'skipped' ? 0.55 : 1 }}>
                  <View style={{ width: 34, height: 34, borderRadius: 10, borderWidth: 1, borderColor: c.ink, backgroundColor: toneColor(c, d.tone), alignItems: 'center', justifyContent: 'center' }}><Icon name="pill" size={18} /></View>
                  <View style={{ flex: 1 }}>
                    <T size={9} w={800} style={{ textDecorationLine: s === 'taken' ? 'line-through' : 'none' }}>{t(d.med)}</T>
                    <T size={7} color={c.muted} style={{ marginTop: 2 }}>{d.time} · {t(d.purpose)}</T>
                  </View>
                  {s ? (
                    <Pressable onPress={() => setStates(v => { const n = { ...v }; delete n[d.id]; return n; })}>
                      <Animated.View entering={FadeIn}>
                        <Chip tone={s === 'taken' ? 'green' : 'white'}>{s === 'taken' ? `✓ ${t('meds.taken')}` : t('meds.skipped')}</Chip>
                      </Animated.View>
                    </Pressable>
                  ) : (
                    <View style={{ flexDirection: 'row', gap: 5 }}>
                      <Pressable onPress={() => set(d.id, 'skipped')} style={{ paddingVertical: 7, paddingHorizontal: 9, borderRadius: 99, borderWidth: 1, borderColor: c.ink }}><T size={8} w={800}>{t('meds.skip')}</T></Pressable>
                      <Pressable onPress={() => set(d.id, 'taken')} style={{ paddingVertical: 7, paddingHorizontal: 11, borderRadius: 99, borderWidth: 1, borderColor: c.ink, backgroundColor: c.primary }}><T size={8} w={800} color="#fff">{t('meds.take')}</T></Pressable>
                    </View>
                  )}
                </View>
              );
            })}
          </Card>
        </View>
      ))}

      <SectionRow title={t('meds.missed')} />
      <Card bg={c.warnBg} radius={16} style={{ padding: 11, flexDirection: 'row', alignItems: 'center', gap: 9, borderColor: c.warnBorder }}>
        <View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: c.warnDot, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T w={800} color="#1b2a4a">!</T></View>
        <View style={{ flex: 1 }}><T size={9} w={800}>{t('meds.missedItem')}</T><T size={7} color={c.muted} style={{ marginTop: 2 }}>{t('meds.missedSub')}</T></View>
      </Card>

      <SectionRow title={t('meds.screening')} />
      <Card bg={c.mint} radius={16} style={{ padding: 11 }}>
        <View style={{ flexDirection: 'row', gap: 9, alignItems: 'center' }}>
          <IconBadge icon="shield" bg={c.surface} size={30} />
          <T size={8.5} w={700} lh={1.4} style={{ flex: 1 }}>{t('meds.screeningSub')}</T>
        </View>
        <View style={{ height: 1, backgroundColor: c.line, marginVertical: 9 }} />
        <T size={8} w={800}>• {t('meds.allergy')}</T>
        <View style={{ marginTop: 7, padding: 9, borderRadius: 12, borderWidth: 1.2, borderColor: c.review, backgroundColor: c.peach }}>
          <T size={8} w={700} lh={1.4}>⚠ {t('meds.interaction')}</T>
        </View>
      </Card>

      <Button icon="sparkle" secondary style={{ marginTop: 14 }} onPress={() => navigation.navigate('AIAssistant', { question: t('ai.suggestions').split('|')[2] })}>{t('meds.ask')}</Button>
      <T size={6} color={c.muted} center style={{ marginTop: 10 }}>{takenCount}/{DOSES.length} · {t('settings.disclaimer')}</T>
    </Screen>
  );
}
