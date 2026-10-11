import React from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Icon } from '../../components/Icon';
import { alertIcon, formatAgo } from '../../components/LiveVitals';
import { T } from '../../components/T';
import { Card, Muted, PageTitle, RoundButton, Screen, SectionRow, TopBar } from '../../components/ui';
import { useAlerts, useFollowedPatient } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import type { LockTone } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

/** Alerts raised by the multi-agent system for the followed patient, newest first. */
export function UpdatesScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const { patient } = useFollowedPatient();
  const { data: alerts, loading, error } = useAlerts(patient?.patient_id);
  const toneBg = { 1: c.green, 2: '#ffe1b8', 3: '#ffd3d3' } as const;
  const previews: [LockTone, string, string][] = [['info', t('lock.info'), c.sky], ['attention', t('lock.attention'), c.review], ['urgent', t('lock.urgent'), c.urgent]];

  return (
    <Screen>
      <TopBar title={t('updates.top')} back={false} action={<RoundButton icon="bell" onPress={() => nav.navigate('LockPreview', { tone: 'attention' })} />} />
      <PageTitle size={26}>{t('updates.title')}</PageTitle>
      <Muted>{patient ? `${patient.full_name} · ${t('updates.sub')}` : t('updates.sub')}</Muted>
      <Card radius={19}>
        {loading && !alerts && <ActivityIndicator color={c.primary} style={{ margin: 20 }} />}
        {error && !alerts && <T size={8.5} w={700} color={c.urgentText} style={{ padding: 12 }}>{t('live.offline')}</T>}
        {alerts?.length === 0 && <T size={8.5} color={c.muted} style={{ padding: 12 }}>{t('updates.empty')}</T>}
        {alerts?.map((a, i) => {
          const urgent = a.severity >= 3;
          const open = urgent ? () => nav.navigate('FamilyUrgent', { title: `${t(`alerts.${a.type}`)} · ${patient?.full_name ?? ''}`, message: a.message }) : undefined;
          return (
            <Pressable key={a.id} disabled={!open} onPress={open}
              style={({ pressed }) => ({ minHeight: 76, flexDirection: 'row', alignItems: 'center', padding: 9, borderBottomWidth: i < alerts.length - 1 ? 1 : 0, borderBottomColor: c.line, opacity: pressed ? 0.7 : 1 })}>
              <T size={6.5} color={c.muted} style={{ width: 56 }}>{formatAgo(t, a.created_at)}</T>
              <View style={{ width: 31, height: 31, marginRight: 10, borderRadius: 9, borderWidth: 1, borderColor: c.ink, backgroundColor: toneBg[a.severity], alignItems: 'center', justifyContent: 'center' }}>
                <Icon name={alertIcon(a.type)} size={17} color="#1b2a4a" />
              </View>
              <View style={{ flex: 1 }}>
                <T size={8.5} w={800}>{t(`alerts.${a.type}`)} · {t('alerts.severity', { n: a.severity })}</T>
                <T size={7.5} lh={1.4} color={c.muted} style={{ marginTop: 2 }}>{a.message}</T>
              </View>
              {open && <T w={800}>›</T>}
            </Pressable>
          );
        })}
      </Card>

      <SectionRow title={t('updates.previewsSub')} kicker={t('updates.previews')} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {previews.map(([tone, label, bg]) => (
          <Pressable key={tone} style={{ flex: 1 }} onPress={() => nav.navigate('LockPreview', { tone })}>
            <Card bg={bg} radius={15} style={{ height: 70, padding: 10, justifyContent: 'space-between' }}>
              <Icon name={tone === 'info' ? 'check' : 'bell'} size={18} color="#1b2a4a" />
              <T size={8.5} w={800} color="#1b2a4a">{label}</T>
            </Card>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}
