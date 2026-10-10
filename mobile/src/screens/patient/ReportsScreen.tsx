import React, { useState } from 'react';
import { View } from 'react-native';
import Svg, { Circle, Polyline } from 'react-native-svg';
import { TrajectoryChart } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Chip, IconBadge, PageTitle, Screen, SectionRow, SimulatedTag, Toggle, TopBar } from '../../components/ui';
import { series } from '../../data/mock';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

function Spark({ values, color }: { values: number[]; color: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${36 - ((v - min) / (max - min || 1)) * 30}`).join(' ');
  const last = pts.split(' ').pop()!.split(',');
  return (
    <Svg width="100%" height={40} viewBox="0 0 104 40" preserveAspectRatio="none">
      <Polyline points={pts} fill="none" stroke={color} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
      <Circle cx={last[0]} cy={last[1]} r={3} fill={color} />
    </Svg>
  );
}

export function ReportsScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const [week, setWeek] = useState(true);

  const vitals: [string, string, string, number[], string, string][] = [
    [t('reports.temp'), `${series.temp[6]}°C`, c.pink, series.temp, '#ef695d', 'thermo'],
    [t('reports.hr'), `${series.hr[6]} bpm`, c.sky, series.hr, '#1e88e5', 'heart'],
    [t('reports.steps'), `${series.steps[6]}`, c.green, series.steps, '#218d65', 'activity'],
  ];
  const milestones: [string, string, boolean][] = [
    [t('reports.ms1'), t('reports.ms1s'), true], [t('reports.ms2'), t('reports.ms2s'), false], [t('reports.ms3'), t('reports.ms3s'), false],
  ];
  const appts: [string, string, string, IconName, string][] = [
    [t('reports.a1'), t('reports.a1s'), t('reports.a1d'), 'activity', c.lavender],
    [t('reports.a2'), t('reports.a2s'), t('reports.a2d'), 'check', c.yellow],
    [t('reports.a3'), t('reports.a3s'), t('reports.a3d'), 'calendar', c.sky],
  ];
  const docs = [t('upload.discharge'), t('upload.operative'), t('upload.labs'), t('upload.meds')];

  return (
    <Screen>
      <TopBar title={t('reports.top')} back={false} action={<Toggle options={[t('common.day'), t('common.week')]} value={week ? t('common.week') : t('common.day')} onChange={v => setWeek(v === t('common.week'))} />} />
      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 6 }}>{t('reports.kicker')}</T>
      <PageTitle style={{ marginTop: 6 }}>{t('reports.title')}</PageTitle>

      <Card bg={c.green} radius={20} style={{ padding: 12 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <View>
            <T size={13} w={800}>{t('reports.trajectory')}</T>
            <T size={7.5} color={c.muted} style={{ marginTop: 2 }}>{t('reports.trajectorySub')}</T>
          </View>
          <Chip>{t('common.onTrack')} ✓</Chip>
        </View>
        <View style={{ marginTop: 8, backgroundColor: c.surface, borderRadius: 14, borderWidth: 1, borderColor: c.ink, padding: 8 }}>
          <TrajectoryChart height={110} />
        </View>
        <View style={{ flexDirection: 'row', gap: 14, marginTop: 8 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}><View style={{ width: 16, height: 3, borderRadius: 2, backgroundColor: c.primary }} /><T size={8} w={700}>{t('reports.observed')}</T></View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}><View style={{ width: 16, borderTopWidth: 2, borderStyle: 'dashed', borderColor: c.muted }} /><T size={8} w={700}>{t('reports.expected')}</T></View>
        </View>
      </Card>

      <SectionRow title={t('reports.vitals')} right={<SimulatedTag />} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {vitals.map(([label, value, bg, values, col, icon]) => (
          <Card key={label} bg={bg} radius={17} style={{ flex: 1, padding: 10 }}>
            <Icon name={icon as IconName} size={16} />
            <T size={7} w={800} style={{ marginTop: 6 }} numberOfLines={1}>{label}</T>
            <T size={15} w={800} spacing={-0.5} style={{ marginTop: 2 }}>{value}</T>
            <T size={6} color={c.muted}>{t('reports.avg')}</T>
            <Spark values={values} color={col} />
          </Card>
        ))}
      </View>

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

      <SectionRow title={t('reports.docs')} right={`${docs.length}`} />
      <Card radius={17} style={{ paddingHorizontal: 11 }}>
        {docs.map((d, i) => (
          <View key={d} style={{ height: 46, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i < docs.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 29, borderRadius: 7, borderWidth: 1, borderColor: c.ink, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name="file" size={16} /></View>
            <T size={9.5} w={800} style={{ flex: 1 }}>{d}</T>
            <T size={11} w={800}>›</T>
          </View>
        ))}
      </Card>
    </Screen>
  );
}
