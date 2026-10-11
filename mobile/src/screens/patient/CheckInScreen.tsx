import { createDemoSafetyEvent } from '../../services/api';
import React, { useEffect, useState } from 'react';
import { Linking, Pressable, View } from 'react-native';
import Slider from '@react-native-community/slider';
import { useNavigation } from '@react-navigation/native';
import Animated, { FadeIn, ZoomIn } from 'react-native-reanimated';
import { Icon, type IconName } from '../../components/Icon';
import { MovementTestCorner, RehabToday } from '../../components/motion/CheckinMotion';
import { T } from '../../components/T';
import { Button, Card, haptic, IconBadge, Muted, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { answerRequest, getMedicationGuide, getToday, usePoll, OTHER_CHIP_KEYS, submitCheckin, WOUND_CHIP_KEYS, type CheckinResult, type MedicationGuide, type Mood } from '../../services/api';
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

const MOODS: { code: Mood; face: string; bg: string }[] = [
  { code: 'very_good', face: '😄', bg: '#bff3d9' }, { code: 'good', face: '🙂', bg: '#dcefff' },
  { code: 'okay', face: '😐', bg: '#fbe19b' }, { code: 'unwell', face: '😣', bg: '#ffd6b8' }, { code: 'very_unwell', face: '😫', bg: '#f4c7ea' },
];

/** 😄 🙂 😐 😣 😫: how the patient feels overall (not a pain score, not an urgency level). */
function MoodPicker({ value, onChange }: { value: Mood | null; onChange: (m: Mood) => void }) {
  const { c } = useTheme();
  const { list } = useT();
  const labels = list('checkin.moods');
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 6, marginTop: 10, marginBottom: 14 }}>
      {MOODS.map((m, i) => {
        const on = value === m.code;
        return (
          <Pressable key={m.code} accessibilityRole="button" accessibilityLabel={labels[i]} onPress={() => { haptic('selection'); onChange(m.code); }}
            style={{ flex: 1, alignItems: 'center', paddingVertical: 9, borderRadius: 16, borderWidth: on ? 2 : 1.2, borderColor: on ? c.primary : c.ink,
              backgroundColor: on ? m.bg : c.surface, transform: [{ scale: on ? 1.06 : 1 }] }}>
            <T size={24}>{m.face}</T>
            <T size={6.5} w={800} center style={{ marginTop: 3 }} numberOfLines={1}>{labels[i]}</T>
          </Pressable>
        );
      })}
    </View>
  );
}

/** Today's medicines: what may be noticed (reassurance) and when to call the care team. */
function MedicinesToday() {
  const { c } = useTheme();
  const { t, lang } = useT();
  const { apiUrl } = useAppState();
  const [guide, setGuide] = useState<MedicationGuide | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => { getMedicationGuide(apiUrl, lang).then(setGuide).catch(() => setGuide(null)); }, [apiUrl, lang]);
  if (!guide || guide.items.length === 0) return null;
  return (
    <Card bg={c.lilacBg} radius={19} style={{ padding: 12, marginTop: 14 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <IconBadge icon="pill" bg={c.surface} size={28} />
        <View style={{ flex: 1 }}>
          <T size={7} w={800} spacing={0.8} color={c.muted}>{t('checkin.medsKicker')}</T>
          <T size={10.5} w={800} style={{ marginTop: 1 }}>{t('checkin.medsTitle')}</T>
        </View>
      </View>
      <View style={{ marginTop: 8, padding: 9, borderRadius: 12, backgroundColor: c.mint, borderWidth: 1, borderColor: c.track }}>
        <T size={8.5} w={700} lh={1.4}>💚 {guide.reassurance}</T>
      </View>
      {guide.items.map((m, i) => (
        <Pressable key={m.medication} onPress={() => { haptic('selection'); setOpen(open === i ? null : i); }}
          style={{ marginTop: 7, padding: 9, borderRadius: 13, borderWidth: 1, borderColor: c.line, backgroundColor: c.surface }}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <T size={9} w={800} style={{ flex: 1 }}>{m.medication}</T>
            <T size={7.5} color={c.muted}>{m.times.join(' · ')}  {open === i ? '▴' : '▾'}</T>
          </View>
          {open === i && (m.known ? (
            <View style={{ marginTop: 6 }}>
              <T size={7} w={800} spacing={0.6} color={c.trackText}>{t('checkin.mayNotice')}</T>
              {m.common.map(x => <T key={x} size={8} lh={1.4} style={{ marginTop: 2 }}>• {x}</T>)}
              <T size={7} w={800} spacing={0.6} color={c.urgentText} style={{ marginTop: 7 }}>{t('checkin.callIf')}</T>
              {m.call_if.map(x => <T key={x} size={8} lh={1.4} style={{ marginTop: 2 }}>• {x}</T>)}
            </View>
          ) : <T size={8} color={c.muted} style={{ marginTop: 6 }}>{t('checkin.medUnknown')}</T>)}
        </Pressable>
      ))}
      <T size={6.5} color={c.muted} lh={1.4} style={{ marginTop: 8 }}>{guide.note}</T>
    </Card>
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
  const [mood, setMood] = useState<Mood | null>(null);
  const [rehabDone, setRehabDone] = useState<string[]>([]);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [clarified, setClarified] = useState<string | null>(null);
  const { apiUrl } = useAppState();
  const day = usePoll(getToday, 30000).data?.patient.day;

  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState(false);

  const runSafetyDemo = async () => {
    if (demoBusy) return;
    setDemoBusy(true);
    setDemoError(false);
    try {
      const event = await createDemoSafetyEvent(apiUrl);
      nav.navigate('D3Demo', { event });
    } catch {
      setDemoError(true);
    } finally {
      setDemoBusy(false);
    }
  };

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
      setResult(await submitCheckin(apiUrl, { pain, fatigue, mobility, chips, mood: mood ?? undefined, rehab_done: rehabDone }));
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
        <Card bg={c.ice} radius={16} style={{ padding: 12, marginTop: 16 }}>
          <T size={8} w={800}>{t('d3Demo.entryTitle')}</T>
          <T size={7.5} color={c.muted} style={{ marginTop: 4, marginBottom: 9 }}>{t('d3Demo.entrySub')}</T>
          <Button secondary onPress={runSafetyDemo}>{demoBusy ? t('d3Demo.loading') : t('d3Demo.run')}</Button>
          {demoError && <T size={7.5} color={c.urgentText} style={{ marginTop: 7 }}>{t('d3Demo.error')}</T>}
        </Card>
        <Button secondary style={{ marginTop: 20 }} onPress={() => { setSent(false); setResult(null); setClarified(null); }}>{t('common.edit')}</Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <TopBar title={t('checkin.top')} back={false} />
      <MovementTestCorner />
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

      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 18 }}>{t('checkin.kickerDay', { n: day ?? '–' })}</T>
      <PageTitle style={{ marginTop: 6 }}>{t('checkin.title')}</PageTitle>
      <Muted>{t('checkin.sub')}</Muted>
      <MoodPicker value={mood} onChange={setMood} />

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

      <RehabToday done={rehabDone} onChange={setRehabDone} />
      <MedicinesToday />

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
      <View style={{ height: 76 }} />{/* room for the floating assistant button */}
    </Screen>
  );
}
