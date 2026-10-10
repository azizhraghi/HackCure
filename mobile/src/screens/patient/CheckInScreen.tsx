import React, { useState } from 'react';
import { Linking, Pressable, View } from 'react-native';
import Slider from '@react-native-community/slider';
import { useNavigation } from '@react-navigation/native';
import Animated, { FadeIn, ZoomIn } from 'react-native-reanimated';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, haptic, IconBadge, Muted, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { answerRequest, OTHER_CHIP_KEYS, submitCheckin, WOUND_CHIP_KEYS, type CheckinResult } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

function ScaleCard({ label, value, onChange, bg, icon, none, worst }: { label: string; value: number; onChange: (v: number) => void; bg: string; icon: IconName; none: string; worst: string }) {
  const { c } = useTheme();
  return (
    <Card bg={bg} radius={19} style={{ padding: 12, marginBottom: 9 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <IconBadge icon={icon} bg={c.surface} size={28} />
        <T size={10} w={800} style={{ flex: 1 }}>{label}</T>
        <T size={24} w={800} spacing={-1}>{value}<T size={10} w={800}>/10</T></T>
      </View>
      <Slider minimumValue={0} maximumValue={10} step={1} value={value} onValueChange={v => { if (Math.round(v) !== value) haptic('selection'); onChange(Math.round(v)); }}
        minimumTrackTintColor="#1b2a4a" maximumTrackTintColor="rgba(27,42,74,0.25)" thumbTintColor="#1e88e5" style={{ height: 34, marginHorizontal: -8 }} />
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <T size={7} color={c.muted}>0 · {none}</T><T size={7} color={c.muted}>10 · {worst}</T>
      </View>
    </Card>
  );
}

function ChipToggle({ label, on, onPress, danger }: { label: string; on: boolean; onPress: () => void; danger?: boolean }) {
  const { c } = useTheme();
  return (
    <Pressable onPress={() => { haptic('selection'); onPress(); }}
      style={{ paddingVertical: 8, paddingHorizontal: 12, borderRadius: 99, borderWidth: 1.2, borderColor: c.ink, backgroundColor: on ? (danger ? c.urgent : c.pink) : c.surface, flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      {on && <Icon name="check" size={12} color={danger ? '#fff' : c.text} />}
      <T size={9} w={800} color={on && danger ? '#fff' : c.text}>{label}</T>
    </Pressable>
  );
}

export function CheckInScreen() {
  const { c } = useTheme();
  const { t, list } = useT();
  const nav = useNavigation();
  const [pain, setPain] = useState(3);
  const [fatigue, setFatigue] = useState(4);
  const [mobility, setMobility] = useState(5);
  const [wound, setWound] = useState<number[]>([]);
  const [other, setOther] = useState<number[]>([]);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [clarified, setClarified] = useState<string | null>(null);
  const { apiUrl } = useAppState();

  const toggle = (arr: number[], set: (v: number[]) => void, i: number) => set(arr.includes(i) ? arr.filter(x => x !== i) : [...arr, i]);
  const woundChips = list('checkin.woundChips');
  const otherChips = list('checkin.otherChips');
  // Drainage, warmth, chills, fever → warning signs; shortness of breath / calf pain → emergency
  const warning = wound.includes(2) || wound.includes(3) || other.includes(0) || other.includes(1) || pain >= 7;
  const emergency = other.includes(4) || other.includes(5) || result?.status === 'urgent';

  const submit = async () => {
    haptic('notificationSuccess');
    setBusy(true);
    try {
      const chips = [...wound.map(i => WOUND_CHIP_KEYS[i]), ...other.map(i => OTHER_CHIP_KEYS[i])].filter(Boolean);
      setResult(await submitCheckin(apiUrl, { pain, fatigue, mobility, chips }));
    } catch {
      setResult(null); // backend unreachable: keep the local (offline) confirmation
    } finally {
      setBusy(false);
      setSent(true);
    }
  };

  const clarify = async (index: number, label: string) => {
    if (result?.status !== 'ok' || !result.clarification) return;
    haptic('selection');
    setClarified(label);
    try { await answerRequest(apiUrl, result.clarification.id, { option_index: index }); } catch { /* shown as answered locally */ }
  };

  if (sent) {
    return (
      <Screen>
        <TopBar title={t('checkin.top')} back={false} />
        <Animated.View entering={ZoomIn} style={{ alignItems: 'center', marginTop: 40 }}>
          <View style={{ width: 70, height: 70, borderRadius: 35, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.green, alignItems: 'center', justifyContent: 'center' }}><Icon name="check" size={32} /></View>
          <PageTitle center>{t('checkin.sentTitle')}</PageTitle>
          <Muted center>{t('checkin.sentSub')}</Muted>
        </Animated.View>
        {result?.status === 'urgent' && (
          <Pressable onPress={() => Linking.openURL('tel:112')}>
            <Card bg={c.urgent} radius={16} style={{ padding: 12, marginTop: 12, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
              <IconBadge icon="phone" bg="#fff" size={32} />
              <T size={9} w={800} color="#1b2a4a" lh={1.4} style={{ flex: 1 }}>{result.message || t('checkin.emergency')}</T>
            </Card>
          </Pressable>
        )}
        {result?.status === 'ok' && result.clarification && (
          <Card bg={c.lavender} radius={16} style={{ padding: 12, marginTop: 12 }}>
            <T size={7} w={800} spacing={0.8} color={c.muted}>{t('checkin.oneMore')}</T>
            <T size={10} w={800} lh={1.4} style={{ marginTop: 4 }}>{result.clarification.prompt}</T>
            {clarified
              ? <T size={9} w={700} style={{ marginTop: 8 }}>✓ {clarified}</T>
              : result.clarification.options.map((o, i) => (
                <Pressable key={o} onPress={() => clarify(i, o)} style={{ marginTop: 7, padding: 10, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.surface }}>
                  <T size={9} w={700}>{o}</T>
                </Pressable>
              ))}
          </Card>
        )}
        {warning && <Card bg={c.peach} radius={16} style={{ padding: 12, borderColor: c.review }}><T size={9} w={700} lh={1.45}>{t('checkin.warning')}</T></Card>}
        <Button secondary style={{ marginTop: 20 }} onPress={() => { setSent(false); setResult(null); setClarified(null); }}>{t('common.edit')}</Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <TopBar title={t('checkin.top')} back={false} />
      <View style={{ flexDirection: 'row', gap: 10 }}>
        {([['activity', t('checkin.rehab'), t('checkin.rehabSub'), c.sky, 'Rehab'], ['camera', t('checkin.scan'), t('checkin.scanSub'), c.lavender, 'WoundScan']] as const).map(([icon, title, sub, bg, route]) => (
          <Pressable key={route} style={{ flex: 1 }} onPress={() => nav.navigate(route)}>
            <Card bg={bg} radius={17} style={{ padding: 11, minHeight: 74 }}>
              <IconBadge icon={icon} bg={c.surface} size={28} />
              <T size={9.5} w={800} style={{ marginTop: 7 }}>{title}</T>
              <T size={7} color={c.muted} style={{ marginTop: 2 }}>{sub}</T>
            </Card>
          </Pressable>
        ))}
      </View>

      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 18 }}>{t('checkin.kicker')}</T>
      <PageTitle style={{ marginTop: 6 }}>{t('checkin.title')}</PageTitle>
      <Muted>{t('checkin.sub')}</Muted>

      <ScaleCard label={t('checkin.pain')} value={pain} onChange={setPain} bg={c.yellow} icon="activity" none={t('checkin.none')} worst={t('checkin.worst')} />
      <ScaleCard label={t('checkin.fatigue')} value={fatigue} onChange={setFatigue} bg={c.lavender} icon="moon" none={t('checkin.none')} worst={t('checkin.worst')} />
      <ScaleCard label={t('checkin.mobility')} value={mobility} onChange={setMobility} bg={c.sky} icon="rotate" none={t('checkin.none')} worst={t('checkin.worst')} />

      <SectionRow title={t('checkin.wound')} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        {woundChips.map((x, i) => <ChipToggle key={x} label={x} on={wound.includes(i)} onPress={() => toggle(wound, setWound, i)} />)}
      </View>
      <SectionRow title={t('checkin.other')} />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        {otherChips.map((x, i) => <ChipToggle key={x} label={x} on={other.includes(i)} danger={i >= 4} onPress={() => toggle(other, setOther, i)} />)}
      </View>

      {emergency && (
        <Animated.View entering={FadeIn}>
          <Pressable onPress={() => Linking.openURL('tel:112')}>
            <Card bg={c.urgent} radius={16} style={{ padding: 12, marginTop: 12, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
              <IconBadge icon="phone" bg="#fff" size={32} />
              <T size={9} w={800} color="#1b2a4a" lh={1.4} style={{ flex: 1 }}>{t('checkin.emergency')}</T>
            </Card>
          </Pressable>
        </Animated.View>
      )}
      {warning && !emergency && (
        <Animated.View entering={FadeIn}>
          <View style={{ padding: 12, marginTop: 12, borderRadius: 16, borderWidth: 1.5, borderColor: c.review, backgroundColor: c.peach }}>
            <T size={9} w={700} lh={1.45}>{t('checkin.warning')}</T>
          </View>
        </Animated.View>
      )}

      <Button style={{ marginTop: 16 }} onPress={busy ? undefined : submit}>{busy ? '…' : t('checkin.submit')}</Button>
    </Screen>
  );
}
