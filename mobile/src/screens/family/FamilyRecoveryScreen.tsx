import React from 'react';
import { View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { ScoreRing, TrajectoryChart } from '../../components/charts';
import { BodyFigure } from '../../components/figures';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Chip, IconBadge, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { patient } from '../../data/mock';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';
import { CaregiverBanner } from './FamilyHomeScreen';

export function FamilyRecoveryScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const milestones: [string, string, boolean][] = [
    [t('reports.ms1'), t('reports.ms1s'), true], [t('reports.ms2'), t('reports.ms2s'), false], [t('reports.ms3'), t('reports.ms3s'), false],
  ];
  return (
    <Screen>
      <CaregiverBanner />
      <TopBar title={t('famRecovery.top')} back={false} />
      <PageTitle size={26} style={{ marginTop: 0 }}>{t('famRecovery.title')}</PageTitle>
      <Chip tone="lavender" style={{ marginBottom: 10 }}>{t('famRecovery.shared')}</Chip>

      <Card radius={20} style={{ height: 116, padding: 10, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <ScoreRing value={patient.score} label={t('famRecovery.score')} />
        <View style={{ flex: 1 }}>
          <T size={10} w={800}>{t('famRecovery.onTrack')}</T>
          <T size={7} color={c.muted} style={{ marginTop: 3 }}>{t('fam.surgery')}</T>
        </View>
      </Card>

      <SectionRow title={t('famRecovery.twin')} />
      <LinearGradient colors={['#f8fcff', '#dbeef9', '#e6def8']} style={{ height: 200, borderWidth: 1.5, borderColor: c.ink, borderRadius: 22, flexDirection: 'row', alignItems: 'center', overflow: 'hidden' }}>
        <View style={{ width: 120, alignItems: 'center' }}><BodyFigure width={92} height={190} /></View>
        <View style={{ flex: 1, paddingRight: 12, gap: 8 }}>
          <Chip tone="green">{t('common.onTrack')} ✓</Chip>
          <T size={11} w={800} color="#1b2a4a">{t('famRecovery.twinSub')}</T>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
            <Icon name="camera" size={13} color="#64718a" />
            <T size={7} color="#64718a" style={{ flex: 1 }}>{t('famRecovery.hidden')}</T>
          </View>
        </View>
      </LinearGradient>

      <Card bg={c.green} radius={18} style={{ marginTop: 10, padding: 11 }}>
        <T size={6.5} w={800}>{t('twin.expVsActual')}</T>
        <TrajectoryChart height={80} />
      </Card>

      <SectionRow title={t('famRecovery.milestones')} />
      <Card radius={17}>
        {milestones.map(([title, sub, done], i) => (
          <View key={title} style={{ minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 11, borderBottomWidth: i < 2 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 24, height: 24, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: done ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {done ? <Icon name="check" size={14} /> : <T size={7} w={800}>{i + 1}</T>}
            </View>
            <View style={{ flex: 1 }}><T size={9} w={800}>{title}</T><T size={7} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
          </View>
        ))}
      </Card>

      <SectionRow title={t('famRecovery.appts')} />
      {[[t('reports.a1'), t('reports.a1d'), c.lavender], [t('reports.a3'), t('reports.a3d'), c.sky]].map(([title, date, bg]) => (
        <Card key={title} bg={bg} radius={16} style={{ padding: 10, marginBottom: 8, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <IconBadge icon="calendar" bg={c.surface} size={30} />
          <T size={9.5} w={800} style={{ flex: 1 }}>{title}</T>
          <T size={8} w={800}>{date}</T>
        </Card>
      ))}
    </Screen>
  );
}
