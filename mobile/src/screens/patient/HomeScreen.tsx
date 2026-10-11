import React, { useMemo, useState } from 'react';
import { Image, Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import Svg, { Circle, Defs, LinearGradient, Rect, Stop } from 'react-native-svg';
import { AssistantBar } from '../../components/Assistant';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Card, haptic, IconBadge, RoundButton, Screen } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { patient as demoPatient } from '../../data/mock';
import { useLatestTelemetry } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { initials } from '../../services/backend';
import { getExpectedRecovery, getToday, getTwin, getMedications, usePoll } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

const TOTAL_DAYS = 42;
/** Milestones of the demo care plan (days after discharge), shown on the journey track. */
const MILESTONES = [
  { day: 1, key: 'home' }, { day: 14, key: 'staples' }, { day: 21, key: 'stairs' }, { day: 28, key: 'driving' }, { day: 42, key: 'full' },
] as const;

export function HomeHeader({ greeting, name, avatar, avatarBg, badge }: { greeting: string; name: string; avatar: string; avatarBg?: string; badge?: number }) {
  const { c } = useTheme();
  const nav = useNavigation();
  return (
    <View style={{ height: 60, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Avatar initials={avatar} online bg={avatarBg} />
      <View style={{ flex: 1 }}>
        <T size={9} color={c.muted}>{greeting}</T>
        <T size={15} w={800} style={{ marginTop: 2 }}>{name}</T>
      </View>
      <View style={{ flexDirection: 'row', gap: 6 }}>
        <RoundButton icon="sparkle" size={36} onPress={() => nav.navigate('AIAssistant')} />
        <View>
          <RoundButton icon="bell" size={36} onPress={() => nav.navigate('Requests')} />
          {!!badge && (
            <View pointerEvents="none" style={{ position: 'absolute', right: -2, top: -2, minWidth: 16, height: 16, borderRadius: 8, paddingHorizontal: 3, backgroundColor: c.urgent, borderWidth: 1.2, borderColor: c.surface, alignItems: 'center', justifyContent: 'center' }}>
              <T size={6.5} w={800} color="#fff">{badge}</T>
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

/** Day N of 42 as a ring (journey progress, not a health score). */
function DayRing({ day, size = 92 }: { day: number; size?: number }) {
  const { t } = useT();
  const r = size / 2 - 7;
  const circ = 2 * Math.PI * r;
  const p = Math.min(1, Math.max(0, day / TOTAL_DAYS));
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.45)" strokeWidth={8} fill="none" />
        <Circle cx={size / 2} cy={size / 2} r={r} stroke="#ffffff" strokeWidth={8} fill="none" strokeLinecap="round"
          strokeDasharray={`${circ * p} ${circ}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </Svg>
      <T size={7} w={800} color="#0e4f3c">{t('home.dayLabel')}</T>
      <T size={24} w={800} spacing={-1} color="#0e4f3c">{day}</T>
      <T size={7} w={700} color="#0e4f3c">{t('home.ofDays', { n: TOTAL_DAYS })}</T>
    </View>
  );
}

/** The recovery journey: milestones from home to full recovery, with "you are here". */
function JourneyTrack({ day }: { day: number }) {
  const { t } = useT();
  const [w, setW] = useState(1);
  const x = (d: number) => (Math.min(TOTAL_DAYS, Math.max(0, d)) / TOTAL_DAYS) * (w - 16) + 8;
  return (
    <View onLayout={e => setW(e.nativeEvent.layout.width)} style={{ height: 62, marginTop: 12 }}>
      <View style={{ position: 'absolute', left: 8, right: 8, top: 12, height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.45)' }} />
      <View style={{ position: 'absolute', left: 8, top: 12, height: 6, borderRadius: 3, width: Math.max(0, x(day) - 8), backgroundColor: '#ffffff' }} />
      {MILESTONES.map(m => {
        const done = day >= m.day;
        return (
          <View key={m.key} style={{ position: 'absolute', left: x(m.day) - 9, top: 6, width: 18, alignItems: 'center' }}>
            <View style={{ width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: '#ffffff', backgroundColor: done ? '#0e8a62' : 'rgba(255,255,255,0.35)', alignItems: 'center', justifyContent: 'center' }}>
              {done && <Icon name="check" size={11} color="#ffffff" />}
            </View>
          </View>
        );
      })}
      <View style={{ position: 'absolute', left: Math.min(Math.max(x(day) - 7, 0), w - 14), top: 3, width: 14, height: 24, alignItems: 'center' }}>
        <View style={{ width: 14, height: 14, borderRadius: 7, backgroundColor: '#ffb347', borderWidth: 2, borderColor: '#ffffff' }} />
      </View>
      {MILESTONES.filter(m => m.day > 1).map(m => (
        <T key={m.key} size={6} w={700} color="#0e4f3c" center numberOfLines={2}
          style={{ position: 'absolute', top: 30, width: 56, left: Math.min(Math.max(x(m.day) - 28, 0), w - 56) }}>
          {t(`home.ms_${m.key}`)}
        </T>
      ))}
    </View>
  );
}

function VitalTile({ icon, label, value, unit, bg }: { icon: IconName; label: string; value: string; unit: string; bg: string }) {
  return (
    <Card bg={bg} radius={16} style={{ flex: 1, padding: 10, minHeight: 74 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
        <Icon name={icon} size={13} />
        <T size={6.5} w={800} spacing={0.6}>{label}</T>
      </View>
      <T size={20} w={800} spacing={-1} style={{ marginTop: 5 }}>{value}<T size={9} w={800}>{unit}</T></T>
    </Card>
  );
}

function Shortcut({ icon, title, sub, bg, onPress }: { icon: IconName; title: string; sub: string; bg: string; onPress: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable onPress={() => { haptic(); onPress(); }} style={({ pressed }) => ({ flex: 1, opacity: pressed ? 0.8 : 1 })}>
      <Card bg={bg} radius={17} style={{ padding: 11, minHeight: 74 }}>
        <IconBadge icon={icon} bg={c.surface} size={28} />
        <T size={9.5} w={800} style={{ marginTop: 7 }}>{title}</T>
        <T size={7} color={c.muted} style={{ marginTop: 2 }}>{sub}</T>
      </Card>
    </Pressable>
  );
}

const fmt = (v: unknown, decimals = 0) => (typeof v === 'number' ? v.toFixed(decimals) : '—');

export function HomeScreen() {
  const { c } = useTheme();
  const { t, list } = useT();
  const nav = useNavigation();
  const { session, demo } = useAppState();
  const user = session?.user;
  const today = usePoll(getToday, 5000).data;
  const medications = usePoll(getMedications, 10000).data;
  const dueDose = medications?.today.find(d => d.status === 'due');
  const twin = usePoll(getTwin, 10000).data;
  const expected = usePoll(getExpectedRecovery, 20000).data; // Developer 1: what is normal today
  const telemetry = useLatestTelemetry(session?.profileId).data; // ESP32 through the SurgiGuard API (signed in)

  const day = today?.patient.day ?? (demo ? demoPatient.day : 0);
  const firstName = user?.first_name ?? today?.patient.first_name ?? (demo ? demoPatient.first : '');
  const fullName = user ? `${user.first_name} ${user.last_name}` : today?.patient.name ?? (demo ? demoPatient.name : '');
  const pending = today?.pending_requests ?? [];
  const careTeamBusy = (today?.open_alerts ?? 0) > 0;

  const hour = new Date().getHours();
  const greeting = t(hour < 12 ? 'home.morning' : hour < 18 ? 'home.afternoon' : 'home.evening');
  const phase = day <= 7 ? 'early' : day <= 21 ? 'steady' : 'stretch';
  const next = MILESTONES.find(m => m.day > day);

  // A different affirmation every day; tap for another one
  const affirmations = list('home.affirmations');
  const [affOffset, setAffOffset] = useState(0);
  const affirmation = useMemo(() => affirmations[(day + affOffset) % affirmations.length], [affirmations, day, affOffset]);

  const fresh = telemetry && Date.now() - Date.parse(telemetry.timestamp) < 120000;
  const hr = fresh ? telemetry?.bpm : twin?.vitals?.hr?.value?.value;
  const spo2 = fresh ? telemetry?.spo2 : twin?.vitals?.spo2?.value?.value;
  const temp = twin?.vitals?.temp?.value?.value;

  return (
    <Screen>
      <HomeHeader greeting={greeting} name={`${firstName} 👋`} avatar={initials(fullName)} badge={pending.length} />

      {/* Recovery journey: the highlight of the screen */}
      <Animated.View entering={FadeInDown.duration(450)}>
        <View style={{ marginTop: 6, borderRadius: 26, borderWidth: 1.5, borderColor: c.ink, overflow: 'hidden' }}>
          <Svg width="100%" height="100%" style={{ position: 'absolute' }}>
            <Defs>
              <LinearGradient id="journey" x1="0" y1="0" x2="1" y2="1">
                <Stop offset="0" stopColor="#7fe0b4" /><Stop offset="0.55" stopColor="#5ed3a0" /><Stop offset="1" stopColor="#4cc0d6" />
              </LinearGradient>
            </Defs>
            <Rect width="100%" height="100%" fill="url(#journey)" />
          </Svg>
          <View style={{ padding: 16 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
              <DayRing day={day} />
              <View style={{ flex: 1 }}>
                <T size={7} w={800} spacing={1} color="#0e4f3c">{t('home.journey')}</T>
                <T size={16} w={800} lh={1.25} color="#08362a" style={{ marginTop: 4 }}>
                  {day === 0 ? 'Add your medical reports to prepare your plan.' : careTeamBusy ? t('home.careTeamOnIt') : t(`home.phase_${phase}`)}
                </T>
                {next && <T size={8} w={700} color="#0e4f3c" style={{ marginTop: 6 }}>{t('home.nextMilestone', { what: t(`home.ms_${next.key}`), n: next.day - day })}</T>}
              </View>
            </View>
            <JourneyTrack day={day} />
            {expected?.status === 'ready' && expected.card && (
              <View style={{ marginTop: 6, padding: 10, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.72)' }}>
                <T size={6.5} w={800} spacing={0.8} color="#0e4f3c">{t('home.normalToday')}</T>
                <T size={8.5} w={600} lh={1.45} color="#08362a" style={{ marginTop: 3 }}>{expected.card.message}</T>
              </View>
            )}
          </View>
        </View>
      </Animated.View>

      {/* Recovery assistant: big and easy to find */}
      <AssistantBar />
      {day === 0 && <Pressable onPress={() => nav.navigate('Upload')}><Card bg={c.sky} radius={18} style={{ marginTop: 12, padding: 12 }}><T size={11} w={800}>Add your medical reports ›</T></Card></Pressable>}
      {dueDose && <Pressable onPress={() => nav.navigate('Medications')}>
        <Card bg={c.sky} radius={18} style={{ marginTop: 12, padding: 12, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
          {dueDose.photo ? <Image source={{ uri: dueDose.photo.url }} resizeMode="contain" style={{ width: 64, height: 64 }} /> : <Icon name="pill" size={26} />}
          <View style={{ flex: 1 }}><T size={8} w={800}>MEDICATION REMINDER · {dueDose.scheduled_for.slice(11, 16)}</T><T size={11} w={800} style={{ marginTop: 3 }}>{dueDose.name} {dueDose.dose}</T><T size={8} style={{ marginTop: 3 }}>Open to record your answer ›</T></View>
        </Card>
      </Pressable>}

      {/* Daily affirmation (replaces the task card) */}
      <Pressable onPress={() => { haptic('selection'); setAffOffset(o => o + 1); }}>
        <Animated.View key={affirmation} entering={FadeIn.duration(400)}>
          <Card bg={c.lilacBg} radius={20} style={{ marginTop: 12, padding: 14, flexDirection: 'row', gap: 11, alignItems: 'center' }}>
            <View style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: c.lavender, borderWidth: 1.2, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="sparkle" size={19} />
            </View>
            <View style={{ flex: 1 }}>
              <T size={6.5} w={800} spacing={1} color={c.muted}>{t('home.affirmationKicker')}</T>
              <T size={11} w={700} lh={1.4} style={{ marginTop: 3 }}>{affirmation}</T>
            </View>
          </Card>
        </Animated.View>
      </Pressable>

      {/* Only when the care team needs something */}
      {(pending.length > 0 || today?.next_step) && (
        <Pressable onPress={() => nav.navigate('Requests')}>
          <Card bg={c.peach} radius={18} style={{ marginTop: 12, padding: 12, flexDirection: 'row', alignItems: 'center', gap: 10, borderColor: c.review }}>
            <IconBadge icon={pending[0]?.kind === 'photo' ? 'camera' : 'message'} bg={c.surface} size={32} radius={10} />
            <View style={{ flex: 1 }}>
              <T size={6.5} w={800} spacing={0.8} color={c.muted}>{t('home.fromCareTeam')}</T>
              <T size={9.5} w={800} lh={1.35} style={{ marginTop: 2 }} numberOfLines={2}>{pending[0]?.prompt ?? today?.next_step?.body}</T>
              {today?.investigation_progress && <T size={7.5} color={c.muted} lh={1.4} style={{ marginTop: 4 }}>{t(`investigation.${today.investigation_progress.phase}`)}</T>}
            </View>
            <T w={800}>›</T>
          </Card>
        </Pressable>
      )}

      {/* Body today: three readings, live from the ESP32 when signed in */}
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, marginBottom: 7 }}>
        <T size={11} w={800}>{t('home.bodyToday')}</T>
        <T size={6.5} w={700} color={fresh ? c.trackText : c.muted}>{fresh ? t('home.liveEsp') : t('home.simulated')}</T>
      </View>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <VitalTile icon="heart" label={t('home.hr')} value={fmt(hr)} unit=" bpm" bg={c.pink} />
        <VitalTile icon="drop" label={t('home.spo2')} value={fmt(spo2)} unit="%" bg={c.sky} />
        <VitalTile icon="thermo" label={t('home.temp')} value={fmt(temp, 1)} unit="°C" bg={c.yellow} />
      </View>

      <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
        <Shortcut icon="pill" title={t('home.meds')} sub={medications?.today.find(d => ['due', 'upcoming'].includes(d.status))?.scheduled_for.slice(11, 16) ?? 'View your schedule'} bg={c.lavender} onPress={() => nav.navigate('Medications')} />
        <Shortcut icon="activity" title={t('checkin.rehab')} sub={t('checkin.rehabSub')} bg={c.mint} onPress={() => nav.navigate('Rehab')} />
      </View>

      <Card bg={c.surface} radius={16} style={{ marginTop: 10, padding: 11, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <IconBadge icon="calendar" bg={c.blue} size={32} radius={10} />
        <View style={{ flex: 1 }}>
          <T size={6.5} w={800} spacing={0.8} color={c.muted}>{t('home.appt')}</T>
          <T size={10} w={800} style={{ marginTop: 2 }}>{today?.appointments[0]?.title ?? 'No upcoming appointment recorded'}</T>
          {!!today?.appointments[0]?.at && <T size={7.5} color={c.muted} style={{ marginTop: 1 }}>{new Date(today.appointments[0].at).toLocaleString()}</T>}
        </View>
      </Card>
    </Screen>
  );
}
