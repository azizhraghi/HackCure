import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { getMotorTests, getRehabPlan, runMotorTest, setMotorConsent, type MotorOutcome, type MotorTests, type RehabPlan } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { Icon } from '../Icon';
import { T } from '../T';
import { Button, Card, haptic, IconBadge, SimulatedTag } from '../ui';
import { MotionCapture, requestCameraPermission } from './MotionCapture';

/** What each test needs MediaPipe to track (same as backend/web/story.html). */
const NEEDS: Record<string, string[]> = {
  arm_hold: ['pose'], finger_to_nose: ['pose'], hand_open_close: ['pose', 'hands'],
  smile: ['face'], eyebrows_and_eyes: ['face'], head_and_gaze: ['face'],
};

type Phase = 'idle' | 'capturing' | 'measuring' | 'result' | 'error';

/** Video testing corner: the patient films a short guided movement; D1 measures it on the backend. */
export function MovementTestCorner() {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const [info, setInfo] = useState<MotorTests | null>(null);
  const [test, setTest] = useState('arm_hold');
  const [agreed, setAgreed] = useState(false);
  const [phase, setPhase] = useState<Phase>('idle');
  const [outcome, setOutcome] = useState<MotorOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMotorTests(apiUrl).then(r => { setInfo(r); setAgreed(r.consent); }).catch(() => setInfo(null));
  }, [apiUrl]);

  const current = info?.tests.find(x => x.id === test);
  const seconds = current?.seconds ?? 10;
  const name = (id: string) => t(`motion.t_${id}`, { defaultValue: info?.tests.find(x => x.id === id)?.name ?? id });

  const start = async () => {
    haptic('impactMedium');
    setError(null);
    setOutcome(null);
    try {
      if (!info?.consent) { await setMotorConsent(apiUrl, true); setInfo(i => (i ? { ...i, consent: true } : i)); }
      if (!(await requestCameraPermission())) { setError(t('motion.noPermission')); setPhase('error'); return; }
      setPhase('capturing');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  };

  const measure = useCallback(async (body: { frames?: object[]; demo?: string }) => {
    setPhase('measuring');
    try {
      setOutcome(await runMotorTest(apiUrl, test, body));
      setPhase('result');
      haptic('notificationSuccess');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  }, [apiUrl, test]);

  const onFrames = useCallback((frames: object[]) => {
    if (frames.length < 5) { setError(t('motion.tooShort')); setPhase('error'); return; }
    measure({ frames });
  }, [measure, t]);
  const onCaptureError = useCallback((reason: string) => { setError(`${t('motion.cameraFailed')} (${reason})`); setPhase('error'); }, [t]);

  const sample = async () => {
    if (!info?.consent) { try { await setMotorConsent(apiUrl, true); } catch {} }
    measure({ demo: current?.demo_variants[0] ?? 'normal' });
  };

  return (
    <Card radius={22} style={{ overflow: 'hidden', marginBottom: 12, borderWidth: 1.5 }}>
      <View style={{ padding: 13, backgroundColor: '#0f2236' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}>
          <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: '#e5484d', alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: '#ffffff' }}>
            <Icon name="camera" size={18} color="#ffffff" />
          </View>
          <View style={{ flex: 1 }}>
            <T size={6.5} w={800} spacing={1} color="#8fd8ff">{t('motion.kicker')}</T>
            <T size={12} w={800} color="#ffffff" style={{ marginTop: 1 }}>{t('motion.title')}</T>
          </View>
        </View>
        <T size={7.5} lh={1.4} color="#c9dceb" style={{ marginTop: 7 }}>{t('motion.sub')}</T>
      </View>

      <View style={{ padding: 12 }}>
        {info?.blocked ? (
          <View style={{ padding: 10, borderRadius: 12, backgroundColor: c.warnBg, borderWidth: 1, borderColor: c.warnBorder }}>
            <T size={8.5} w={700} lh={1.4}>{info.blocked}</T>
          </View>
        ) : (
          <>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
              {(info?.tests ?? []).map(x => (
                <Pressable key={x.id} disabled={phase === 'capturing' || phase === 'measuring'} onPress={() => { haptic('selection'); setTest(x.id); setPhase('idle'); setOutcome(null); }}
                  style={{ paddingVertical: 7, paddingHorizontal: 11, borderRadius: 99, borderWidth: 1.2, borderColor: c.ink, backgroundColor: test === x.id ? c.primary : c.surface }}>
                  <T size={8} w={800} color={test === x.id ? '#fff' : c.text}>{name(x.id)} · {x.seconds}s</T>
                </Pressable>
              ))}
            </ScrollView>
            <T size={8.5} lh={1.45} style={{ marginTop: 9 }}>{t(`motion.i_${test}`, { defaultValue: current?.instructions ?? '' })}</T>

            {phase === 'capturing' && (
              <View style={{ marginTop: 10 }}>
                <MotionCapture test={test} seconds={seconds} kinds={NEEDS[test] ?? ['pose']} onFrames={onFrames} onError={onCaptureError}
                  labels={{ loading: t('motion.loading'), ready: t('motion.ready'), recording: t('motion.recording'), measuring: t('motion.measuring'), failed: t('motion.cameraFailed') }} />
                <Button secondary style={{ marginTop: 8 }} onPress={() => setPhase('idle')}>{t('common.cancel')}</Button>
              </View>
            )}

            {phase === 'measuring' && (
              <View style={{ marginTop: 12, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <ActivityIndicator color={c.primary} /><T size={9} w={700}>{t('motion.measuring')}</T>
              </View>
            )}

            {(phase === 'idle' || phase === 'error' || phase === 'result') && (
              <>
                {!info?.consent && (
                  <Pressable onPress={() => setAgreed(v => !v)} style={{ flexDirection: 'row', gap: 8, alignItems: 'center', marginTop: 10 }}>
                    <View style={{ width: 20, height: 20, borderRadius: 5, borderWidth: 1.4, borderColor: c.ink, backgroundColor: agreed ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
                      {agreed && <Icon name="check" size={13} />}
                    </View>
                    <T size={7.5} lh={1.35} style={{ flex: 1 }}>{t('motion.consent')}</T>
                  </Pressable>
                )}
                <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
                  <Button style={{ flex: 1, opacity: agreed || info?.consent ? 1 : 0.5 }} height={46} size={11}
                    onPress={agreed || info?.consent ? start : undefined}>{`● ${t('motion.start', { n: seconds })}`}</Button>
                </View>
                <Pressable onPress={sample} style={{ alignSelf: 'center', marginTop: 8, padding: 4 }}>
                  <T size={8} color={c.muted} style={{ textDecorationLine: 'underline' }}>{t('motion.sample')}</T>
                </Pressable>
              </>
            )}

            {phase === 'error' && error && <T size={8} color={c.urgentText} lh={1.4} style={{ marginTop: 6 }}>{error}</T>}
            {phase === 'result' && outcome && <MotionResult outcome={outcome} />}
          </>
        )}
      </View>
    </Card>
  );
}

function MotionResult({ outcome }: { outcome: MotorOutcome }) {
  const { c } = useTheme();
  const { t } = useT();
  const r = outcome.result;
  const statusTone = r.status === 'complete' ? c.green : r.status === 'limited' ? c.yellow : c.peach;
  // one row per measurement code, left / right / overall values side by side
  const rows = new Map<string, { unit: string; left?: number | null; right?: number | null; all?: number | null }>();
  r.measurements.forEach(m => {
    const row = rows.get(m.code) ?? { unit: m.unit };
    if (m.side === 'left') row.left = m.value; else if (m.side === 'right') row.right = m.value; else row.all = m.value;
    rows.set(m.code, row);
  });
  const f = (v?: number | null) => (v === null || v === undefined ? '—' : Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(2));
  return (
    <View style={{ marginTop: 12, padding: 11, borderRadius: 16, borderWidth: 1, borderColor: c.line, backgroundColor: c.bg }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <T size={7} w={800} spacing={0.8} color={c.muted} style={{ flex: 1 }}>{t('motion.measured')}</T>
        {outcome.synthetic && <SimulatedTag />}
        <View style={{ paddingVertical: 3, paddingHorizontal: 9, borderRadius: 99, backgroundColor: statusTone, borderWidth: 1, borderColor: c.ink }}>
          <T size={7} w={800}>{t(`motion.status_${r.status}`)}</T>
        </View>
      </View>
      {[...rows.entries()].map(([code, row]) => (
        <View key={code} style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: c.line }}>
          <T size={8} w={700} style={{ flex: 1 }}>{code.replace(/_/g, ' ')}</T>
          {row.all !== undefined
            ? <T size={8.5} w={800}>{f(row.all)} <T size={6.5} color={c.muted}>{row.unit}</T></T>
            : <T size={8.5} w={800}>L {f(row.left)} · R {f(row.right)} <T size={6.5} color={c.muted}>{row.unit}</T></T>}
        </View>
      ))}
      {r.observations.map(o => <T key={o} size={8.5} lh={1.4} style={{ marginTop: 5 }}>• {o}</T>)}
      {outcome.compared_with_previous && outcome.changes_since_previous.length > 0 && (
        <T size={7.5} color={c.muted} style={{ marginTop: 6 }}>{t('motion.compared', { n: outcome.changes_since_previous.length })}</T>
      )}
      {r.status === 'not_interpretable' ? (
        <View style={{ marginTop: 8, padding: 8, borderRadius: 10, backgroundColor: c.peach }}>
          <T size={8} w={700} lh={1.4}>{t('motion.retry')}</T>
          {r.limitations.map(l => <T key={l} size={7.5} color={c.muted} lh={1.35} style={{ marginTop: 3 }}>• {l}</T>)}
        </View>
      ) : (
        <View style={{ marginTop: 8, padding: 8, borderRadius: 10, backgroundColor: r.review_suggested ? c.amber : c.mint }}>
          <T size={8} w={700} lh={1.4}>{r.review_suggested ? t('motion.review') : t('motion.allGood')}</T>
        </View>
      )}
      <T size={6.5} color={c.muted} lh={1.35} style={{ marginTop: 6 }}>{outcome.note}</T>
    </View>
  );
}

const CATEGORY_KEYS: Record<string, string> = { knee_flexion: 'kneeFlexion', straight_leg_raise: 'slr', ankle_pumps: 'anklePumps' };

/** Today's rehabilitation exercises from the D1 prescription; the patient ticks what was done. */
export function RehabToday({ done, onChange }: { done: string[]; onChange: (ids: string[]) => void }) {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const { apiUrl } = useAppState();
  const [plan, setPlan] = useState<RehabPlan | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { getRehabPlan(apiUrl).then(setPlan).catch(() => setPlan(null)); }, [apiUrl]);
  if (!plan || plan.exercises.length === 0) return null;
  const toggle = (id: string) => { haptic('selection'); onChange(done.includes(id) ? done.filter(x => x !== id) : [...done, id]); };
  return (
    <Card bg={c.mint} radius={19} style={{ padding: 12, marginTop: 14 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <IconBadge icon="activity" bg={c.surface} size={28} />
        <View style={{ flex: 1 }}>
          <T size={7} w={800} spacing={0.8} color={c.muted}>{t('rehabToday.kicker', { n: plan.daily_sessions })}</T>
          <T size={10.5} w={800} style={{ marginTop: 1 }}>{t('rehabToday.title')}</T>
        </View>
        <T size={9} w={800} color={c.trackText}>{done.length}/{plan.exercises.length}</T>
      </View>
      {plan.exercises.map(ex => {
        const on = done.includes(ex.exercise_id);
        const key = CATEGORY_KEYS[ex.category];
        return (
          <View key={ex.exercise_id} style={{ marginTop: 8, padding: 10, borderRadius: 14, borderWidth: 1, borderColor: on ? c.track : c.line, backgroundColor: c.surface }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}>
              <Pressable onPress={() => toggle(ex.exercise_id)} accessibilityRole="checkbox" accessibilityState={{ checked: on }}
                style={{ width: 26, height: 26, borderRadius: 13, borderWidth: 1.4, borderColor: c.ink, backgroundColor: on ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
                {on && <Icon name="check" size={15} />}
              </Pressable>
              <Pressable style={{ flex: 1 }} onPress={() => setOpen(open === ex.exercise_id ? null : ex.exercise_id)}>
                <T size={9.5} w={800} style={{ textDecorationLine: on ? 'line-through' : 'none' }}>{key ? t(`rehabToday.${key}`) : ex.name}</T>
                <T size={7.5} color={c.muted} style={{ marginTop: 2 }}>
                  {t('rehabToday.dose', { sets: ex.target_sets, reps: ex.target_reps })}
                  {ex.min_hold_duration_sec ? ` · ${t('rehabToday.hold', { s: ex.min_hold_duration_sec })}` : ''}
                  {ex.target_rom_deg ? ` · ${t('rehabToday.goal', { deg: Math.round(ex.target_rom_deg) })}` : ''}
                </T>
              </Pressable>
              <T size={8} color={c.muted}>{open === ex.exercise_id ? '▴' : '▾'}</T>
            </View>
            {open === ex.exercise_id && (
              <View style={{ marginTop: 7, paddingLeft: 35 }}>
                {key && <T size={8} lh={1.4}>{t(`rehabToday.${key}How`)}</T>}
                {ex.precautions.map(p => <T key={p} size={7.5} color={c.muted} lh={1.35} style={{ marginTop: 3 }}>• {p}</T>)}
              </View>
            )}
          </View>
        );
      })}
      <View style={{ marginTop: 9, padding: 8, borderRadius: 10, backgroundColor: c.amber }}>
        <T size={7.5} w={700} lh={1.4}>{t('rehabToday.stop')}</T>
      </View>
      <Pressable onPress={() => nav.navigate('Rehab')} style={{ alignSelf: 'flex-start', marginTop: 8 }}>
        <T size={8} w={800} color={c.primary}>{t('rehabToday.camera')} ›</T>
      </Pressable>
    </Card>
  );
}
