import React, { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import Svg, { Circle, Defs, Line, LinearGradient, Path, Stop } from 'react-native-svg';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Chip, IconBadge, PageTitle, Screen, SectionRow, SimulatedTag, Toggle, TopBar } from '../../components/ui';
import { series as demoSeries } from '../../data/mock';
import { useT } from '../../i18n';
import { PATIENT_ID, usePoll } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

type Point = { at: number; v: number };
type ReportTwin = {
  vitals?: Record<string, { series?: { at: string; value: { value?: number } | null; simulated?: boolean }[] }>;
  checkins?: { history?: { at: string; scores_1_to_5: Record<string, number> }[] };
  medications?: { last_48h?: Record<string, number> };
};

const getReportTwin = (apiUrl: string, hours: number) =>
  fetch(`${apiUrl.replace(/\/$/, '')}/patients/${PATIENT_ID}/twin?hours=${hours}`).then(r => (r.ok ? (r.json() as Promise<ReportTwin>) : Promise.reject(new Error(String(r.status)))));

const toPoints = (rows?: { at: string; value: { value?: number } | null }[]): Point[] =>
  (rows ?? []).map(r => ({ at: Date.parse(r.at), v: r.value?.value as number })).filter(p => typeof p.v === 'number' && !Number.isNaN(p.at));

const demoPoints = (values: number[]): Point[] => values.map((v, i) => ({ at: Date.now() - (values.length - 1 - i) * 86400000, v }));

/** Trend of the second half against the first half, relative to the series' own spread. */
function trendOf(points: Point[]): 'up' | 'down' | 'steady' | null {
  if (points.length < 3) return null;
  const half = Math.floor(points.length / 2);
  const avg = (xs: Point[]) => xs.reduce((s, p) => s + p.v, 0) / xs.length;
  const a = avg(points.slice(0, half)), b = avg(points.slice(half));
  const range = Math.max(...points.map(p => p.v)) - Math.min(...points.map(p => p.v)) || 1;
  const d = (b - a) / range;
  return d > 0.15 ? 'up' : d < -0.15 ? 'down' : 'steady';
}

/** Line chart (one or more series) with min/max guides. */
function LineChart({ lines, height = 110, min, max, minSpan = 0 }: { lines: { points: Point[]; color: string }[]; height?: number; min?: number; max?: number; minSpan?: number }) {
  const { c } = useTheme();
  const all = lines.flatMap(l => l.points);
  if (all.length < 2) return <View style={{ height, alignItems: 'center', justifyContent: 'center' }}><T size={8} color={c.muted}>—</T></View>;
  let lo = min ?? Math.min(...all.map(p => p.v)), hi = max ?? Math.max(...all.map(p => p.v));
  if (hi - lo < minSpan) { const mid = (hi + lo) / 2; lo = mid - minSpan / 2; hi = mid + minSpan / 2; } // small wiggles stay small
  const t0 = Math.min(...all.map(p => p.at)), t1 = Math.max(...all.map(p => p.at));
  const W = 300, H = 100, pad = 6;
  const x = (at: number) => pad + ((at - t0) / (t1 - t0 || 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - ((v - lo) / (hi - lo || 1)) * (H - 2 * pad);
  return (
    <Svg width="100%" height={height} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <Defs>
        {lines.map((l, i) => (
          <LinearGradient key={i} id={`area${i}`} x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={l.color} stopOpacity={0.22} /><Stop offset="1" stopColor={l.color} stopOpacity={0} />
          </LinearGradient>
        ))}
      </Defs>
      {[0.25, 0.5, 0.75].map(f => <Line key={f} x1={pad} x2={W - pad} y1={pad + f * (H - 2 * pad)} y2={pad + f * (H - 2 * pad)} stroke={c.line} strokeWidth={1} />)}
      {lines.map((l, i) => {
        const pts = [...l.points].sort((a, b) => a.at - b.at);
        if (pts.length < 2) return null;
        const d = pts.map((p, k) => `${k ? 'L' : 'M'}${x(p.at).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' ');
        const last = pts[pts.length - 1];
        return (
          <React.Fragment key={i}>
            {lines.length === 1 && <Path d={`${d} L${x(last.at).toFixed(1)} ${H - pad} L${x(pts[0].at).toFixed(1)} ${H - pad} Z`} fill={`url(#area${i})`} />}
            <Path d={d} fill="none" stroke={l.color} strokeWidth={2.4} strokeLinejoin="round" strokeLinecap="round" />
            <Circle cx={x(last.at)} cy={y(last.v)} r={3.5} fill={l.color} />
          </React.Fragment>
        );
      })}
    </Svg>
  );
}

function ChartCard({ icon, title, what, unit, points, color, bg, decimals = 0, simulated, goodWhen, minSpan }: {
  icon: IconName; title: string; what: string; unit: string; points: Point[]; color: string; bg: string; decimals?: number; simulated?: boolean; minSpan?: number;
  /** Which direction is good news for the patient (drives the analysis wording) */
  goodWhen?: 'down' | 'up' | 'steady';
}) {
  const { c } = useTheme();
  const { t } = useT();
  const vals = points.map(p => p.v);
  const latest = vals[vals.length - 1];
  const avg = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : undefined;
  const trend = trendOf(points);
  const good = trend && goodWhen && trend === goodWhen;
  return (
    <Card bg={bg} radius={19} style={{ padding: 12, marginBottom: 9 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <IconBadge icon={icon} bg={c.surface} size={28} />
        <T size={10.5} w={800} style={{ flex: 1 }}>{title}</T>
        {simulated && <SimulatedTag />}
      </View>
      <View style={{ flexDirection: 'row', gap: 16, marginTop: 8 }}>
        <View><T size={6.5} w={800} color={c.muted}>{t('reports.latest')}</T><T size={17} w={800} spacing={-0.5}>{latest !== undefined ? latest.toFixed(decimals) : '—'}<T size={8} w={800}> {unit}</T></T></View>
        <View><T size={6.5} w={800} color={c.muted}>{t('reports.average')}</T><T size={17} w={800} spacing={-0.5}>{avg !== undefined ? avg.toFixed(decimals) : '—'}<T size={8} w={800}> {unit}</T></T></View>
      </View>
      <View style={{ marginTop: 6, backgroundColor: c.surface, borderRadius: 14, borderWidth: 1, borderColor: c.line, padding: 6 }}>
        <LineChart lines={[{ points, color }]} height={96} minSpan={minSpan} />
      </View>
      {trend && (
        <T size={8} w={700} lh={1.4} color={good ? c.trackText : c.text} style={{ marginTop: 7 }}>
          {trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'} {t(`reports.trend_${trend}`, { what })}{good ? ` ${t('reports.goodNews')}` : ''}
        </T>
      )}
    </Card>
  );
}

export function ReportsScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const [week, setWeek] = useState(true);
  const hours = week ? 168 : 24;
  const fetcher = useCallback((url: string) => getReportTwin(url, hours), [hours]);
  const poll = usePoll(fetcher, 15000);
  const twin = poll.data;
  const { refresh } = poll;
  useEffect(() => { refresh(); }, [hours, refresh]); // Day / Week switched: reload now

  const hr = toPoints(twin?.vitals?.hr?.series), temp = toPoints(twin?.vitals?.temp?.series), spo2 = toPoints(twin?.vitals?.spo2?.series);
  const history = twin?.checkins?.history ?? [];
  const sym = (k: string) => history.map(h => ({ at: Date.parse(h.at), v: h.scores_1_to_5[k] })).filter(p => typeof p.v === 'number');
  const pain = sym('pain'), fatigue = sym('fatigue'), mobility = sym('mobility');
  const meds = twin?.medications?.last_48h;
  const taken = meds?.taken ?? 0;
  const missed = (meds?.not_taken ?? 0) + (meds?.unknown ?? 0);
  const symTrend = trendOf(pain);

  const milestones: [string, string, boolean][] = [
    [t('reports.ms1'), t('reports.ms1s'), true], [t('reports.ms2'), t('reports.ms2s'), false], [t('reports.ms3'), t('reports.ms3s'), false],
  ];
  const appts: [string, string, string, IconName, string][] = [
    [t('reports.a1'), t('reports.a1s'), t('reports.a1d'), 'activity', c.lavender],
    [t('reports.a2'), t('reports.a2s'), t('reports.a2d'), 'check', c.yellow],
    [t('reports.a3'), t('reports.a3s'), t('reports.a3d'), 'calendar', c.sky],
  ];

  return (
    <Screen>
      <TopBar title={t('reports.top')} back={false} action={<Toggle options={[t('common.day'), t('common.week')]} value={week ? t('common.week') : t('common.day')} onChange={v => setWeek(v === t('common.week'))} />} />
      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 6 }}>{week ? t('reports.kickerWeek') : t('reports.kickerDay')}</T>
      <PageTitle style={{ marginTop: 6 }}>{t('reports.chartsTitle')}</PageTitle>

      {/* Symptoms from the daily check-ins */}
      <Card bg={c.green} radius={20} style={{ padding: 12, marginBottom: 9 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <IconBadge icon="checkin" bg={c.surface} size={28} />
          <View style={{ flex: 1 }}>
            <T size={10.5} w={800}>{t('reports.symptoms')}</T>
            <T size={7} color={c.muted} style={{ marginTop: 1 }}>{t('reports.symptomsSub')}</T>
          </View>
        </View>
        <View style={{ marginTop: 8, backgroundColor: c.surface, borderRadius: 14, borderWidth: 1, borderColor: c.ink, padding: 6 }}>
          <LineChart lines={[{ points: pain, color: '#ef695d' }, { points: fatigue, color: '#8a6ee0' }, { points: mobility, color: '#1e88e5' }]} min={1} max={5} height={110} />
        </View>
        <View style={{ flexDirection: 'row', gap: 12, marginTop: 7, flexWrap: 'wrap' }}>
          {([[t('checkin.pain'), '#ef695d'], [t('checkin.fatigue'), '#8a6ee0'], [t('checkin.mobility'), '#1e88e5']] as const).map(([l, col]) => (
            <View key={l} style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}><View style={{ width: 14, height: 3, borderRadius: 2, backgroundColor: col }} /><T size={7.5} w={700}>{l}</T></View>
          ))}
        </View>
        <T size={8} w={700} lh={1.4} style={{ marginTop: 7 }}>
          {pain.length < 2 ? t('reports.symptomsFew') : symTrend === 'down' ? t('reports.painDown') : symTrend === 'up' ? t('reports.painUp') : t('reports.painSteady')}
        </T>
      </Card>

      <SectionRow title={t('reports.vitals')} />
      <ChartCard icon="heart" title={t('reports.hr')} what={t('reports.whatHr')} minSpan={20} unit="bpm" points={hr.length ? hr : demoPoints(demoSeries.hr)} simulated={!hr.length || undefined} color="#1e88e5" bg={c.sky} goodWhen="steady" />
      <ChartCard icon="thermo" title={t('reports.bodyTemp')} what={t('reports.whatTemp')} minSpan={1.5} unit="°C" decimals={1} points={temp.length ? temp : demoPoints(demoSeries.temp)} simulated={!temp.length || undefined} color="#ef695d" bg={c.pink} goodWhen="steady" />
      <ChartCard icon="drop" title="SpO₂" what={t('reports.whatSpo2')} minSpan={10} unit="%" points={spo2} color="#218d65" bg={c.mint} goodWhen="steady" />

      <SectionRow title={t('reports.medsTitle')} />
      <Card bg={c.lavender} radius={19} style={{ padding: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <IconBadge icon="pill" bg={c.surface} size={28} />
          <T size={10.5} w={800} style={{ flex: 1 }}>{t('reports.adherence')}</T>
          <Chip tone="white">{taken}/{taken + missed}</Chip>
        </View>
        <View style={{ flexDirection: 'row', height: 14, marginTop: 10, borderRadius: 7, overflow: 'hidden', borderWidth: 1, borderColor: c.ink, backgroundColor: c.surface }}>
          <View style={{ flex: taken || 0.0001, backgroundColor: c.track }} />
          <View style={{ flex: missed || 0.0001, backgroundColor: c.review }} />
        </View>
        <T size={8} w={700} lh={1.4} style={{ marginTop: 7 }}>{missed === 0 ? t('reports.adherenceAll') : t('reports.adherenceSome', { n: missed })}</T>
      </Card>

      <SectionRow title={t('reports.milestones')} />
      <Card radius={17}>
        {milestones.map(([title, sub, done], i) => (
          <View key={title} style={{ minHeight: 50, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 11, borderBottomWidth: i < 2 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 24, height: 24, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: done ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {done ? <Icon name="check" size={14} /> : <T size={7} w={800}>{i + 1}</T>}
            </View>
            <View style={{ flex: 1 }}><T size={9} w={800}>{title}</T><T size={7} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
          </View>
        ))}
      </Card>

      <SectionRow title={t('reports.appts')} />
      {appts.map(([title, sub, date, icon, bg]) => (
        <Card key={title} bg={bg} radius={16} style={{ padding: 10, marginBottom: 8, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <IconBadge icon={icon} bg={c.surface} size={32} radius={10} />
          <View style={{ flex: 1 }}><T size={9.5} w={800}>{title}</T><T size={7.5} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
          <View style={{ paddingVertical: 5, paddingHorizontal: 8, borderRadius: 99, backgroundColor: c.surface, borderWidth: 1, borderColor: c.ink }}><T size={7.5} w={800}>{date}</T></View>
        </Card>
      ))}
      <View style={{ height: 76 }} />{/* room for the floating assistant button */}
    </Screen>
  );
}
