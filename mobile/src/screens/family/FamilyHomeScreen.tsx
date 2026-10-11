import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { MiniBars, MiniLine } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { formatAgo, LiveVitalsCard } from '../../components/LiveVitals';
import { T } from '../../components/T';
import { Avatar, Card, haptic, IconBadge, RoundButton, Screen, SectionRow, SimulatedTag } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { metrics } from '../../data/mock';
import { useAlerts, useFollowedPatient } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { getCaregiverAlerts, getCaregiverTasks, getDigest, markTaskDone, usePoll } from '../../services/api';
import { initials } from '../../services/backend';

const ACTIVE_ALERT_WINDOW_MS = 6 * 3600 * 1000;
import { useTheme } from '../../theme/ThemeContext';

export function CaregiverBanner() {
  const { c } = useTheme();
  const { t } = useT();
  const { resetRole } = useAppState();
  return (
    <View style={{ height: 41, marginHorizontal: -16, marginTop: -4, marginBottom: 3, paddingHorizontal: 16, backgroundColor: c.primary, flexDirection: 'row', alignItems: 'center', gap: 7 }}>
      <Icon name="profile" size={15} color="#fff" />
      <T size={8} color="#fff" style={{ flex: 1 }}>{t('fam.banner')}<T size={8} w={800} color="#fff">{t('fam.readOnly')}</T></T>
      <Pressable onPress={resetRole} style={{ borderWidth: 1, borderColor: '#fff', borderRadius: 99, backgroundColor: 'rgba(255,255,255,0.16)', paddingVertical: 5, paddingHorizontal: 8 }}>
        <T size={7} w={800} color="#fff">{t('fam.switch')}</T>
      </Pressable>
    </View>
  );
}

export function FamilyHomeScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const [help, setHelp] = useState([false, true, false]);
  const [observed, setObserved] = useState(false);
  const tasks = [[t('fam.h1'), t('fam.h1s')], [t('fam.h2'), t('fam.h2s')], [t('fam.h3'), t('fam.h3s')]];
  const { apiUrl, session } = useAppState();
  const me = session?.user;
  // AI backend: care-team alerts, digest and tasks (permission-filtered for the caregiver)
  const aiAlerts = usePoll(getCaregiverAlerts, 4000).data;
  const apiTasks = usePoll(getCaregiverTasks, 4000);
  const digest = usePoll(getDigest, 30000).data;
  // SurgiGuard API (when signed in): the followed patient and the ESP32 alerts
  const { patient } = useFollowedPatient();
  const { data: deviceAlerts } = useAlerts(patient?.patient_id);
  const device = (deviceAlerts ?? [])
    .filter(a => a.status === 'OPEN' && Date.now() - Date.parse(a.created_at) < ACTIVE_ALERT_WINDOW_MS)
    .sort((a, b) => b.severity - a.severity)[0];
  const aiLevel = aiAlerts?.some(a => a.level === 'urgent') ? 2 : aiAlerts?.some(a => a.level === 'attention') ? 1 : 0;
  const deviceLevel = !device ? 0 : device.severity >= 3 ? 2 : 1;
  const level = Math.max(aiLevel, deviceLevel);
  const status = level === 0
    ? { bg: c.green, icon: 'check' as const, title: t('common.onTrack'), sub: t('fam.noUrgent') }
    : { bg: level === 2 ? c.urgent : c.amber, icon: 'bell' as const,
        title: level === 2 ? t('fam.stUrgent') : t('fam.stAttention'),
        sub: deviceLevel >= aiLevel && device ? `${t(`alerts.${device.type}`)} · ${formatAgo(t, device.created_at)}` : aiAlerts?.[0]?.title ?? '' };
  const openActive = () => {
    if (level === 0) return;
    if (deviceLevel >= aiLevel && device && device.severity >= 3) {
      nav.navigate('FamilyUrgent', { title: `${t(`alerts.${device.type}`)} · ${patient?.full_name ?? ''}`, message: device.message });
    } else nav.navigate(level === 2 ? 'FamilyUrgent' : 'FamilyAttention');
  };
  const done = async (id: string) => {
    haptic('notificationSuccess');
    try { await markTaskDone(apiUrl, id); } catch { /* next poll shows the real state */ }
    apiTasks.refresh();
  };

  return (
    <Screen>
      <CaregiverBanner />
      <View style={{ height: 60, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(me ? `${me.first_name} ${me.last_name}` : 'Ahmed')} bg={c.sky} online />
        <View style={{ flex: 1 }}><T size={9} color={c.muted}>{t('home.welcome')}</T><T size={14} w={800} style={{ marginTop: 2 }}>{t('fam.hi', { name: me?.first_name ?? 'Ahmed' })}</T></View>
        <RoundButton icon="bell" size={35} onPress={() => nav.navigate('FamilyTabs', { screen: 'Updates' })} />
      </View>

      <View style={{ height: 72, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(patient?.full_name ?? 'Sarah Miller')} size={47} />
        <View>
          <T size={5.5} spacing={0.7}>{t('fam.following')}</T>
          <T size={13} w={800} style={{ marginVertical: 2 }}>{patient?.full_name ?? (session ? t('fam.noPatient') : 'Sarah Miller')}</T>
          <T size={6.5} color={c.muted}>{patient ? `${patient.relationship}${patient.device_id ? ` · ${patient.device_id}` : ''}` : ''}</T>
        </View>
      </View>

      <Pressable onPress={openActive} disabled={level === 0}>
        <Card bg={status.bg} style={{ minHeight: 92, padding: 12, flexDirection: 'row', alignItems: 'center', gap: 11 }}>
          <View style={{ width: 42, height: 42, borderRadius: 21, borderWidth: 1.3, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}><Icon name={status.icon} size={20} /></View>
          <View style={{ flex: 1 }}>
            <T size={5.5} spacing={0.8}>{t('fam.status')}</T>
            <T size={18} w={800} style={{ marginVertical: 2 }}>{status.title}</T>
            <T size={6.5} numberOfLines={2}>{status.sub}</T>
          </View>
          {level > 0 && <T w={800}>›</T>}
        </Card>
      </Pressable>

      {digest && (
        <Card bg={c.sky} radius={16} style={{ marginTop: 10, padding: 11 }}>
          <T size={7} w={800} spacing={0.8} color={c.muted}>{t('fam.digest')}</T>
          <T size={9} lh={1.45} style={{ marginTop: 4 }}>{digest.digest.text}</T>
        </Card>
      )}

      {session && <><View style={{ height: 10 }} /><LiveVitalsCard patientId={patient?.patient_id} /></>}

      <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
        <Card bg={c.pink} style={{ flex: 1, height: 130, padding: 12, overflow: 'hidden' }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><T size={7.5} w={800} spacing={0.7}>{t('home.woundTemp')}</T><SimulatedTag style={{ paddingVertical: 1 }} /></View>
          <T size={31} w={800} spacing={-1.6} style={{ marginTop: 5 }}>{metrics.woundTemp}<T size={12} w={800}>°C</T></T>
          <T size={7.5} color={c.muted}>{t('home.normal')}</T>
          <MiniBars />
        </Card>
        <Card bg={c.yellow} style={{ flex: 1, height: 130, padding: 12, overflow: 'hidden' }}>
          <T size={7.5} w={800} spacing={0.7}>{t('home.pain')}</T>
          <T size={31} w={800} spacing={-1.6} style={{ marginTop: 5 }}>{metrics.pain}<T size={12} w={800}>/10</T></T>
          <T size={7.5} color={c.muted}>{t('fam.sharedBy')}</T>
          <MiniLine />
        </Card>
      </View>

      <Pressable onPress={() => nav.navigate('FamilyInfo')}>
        <View style={{ height: 57, marginTop: 9, borderWidth: 1.2, borderColor: c.ink, borderRadius: 14, backgroundColor: c.surface, paddingHorizontal: 9, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View style={{ width: 25, height: 25, borderRadius: 13, backgroundColor: c.green, alignItems: 'center', justifyContent: 'center' }}><Icon name="check" size={16} /></View>
          <View style={{ flex: 1 }}><T size={5.5} color={c.muted}>{t('fam.latest')}</T><T size={8} w={800} style={{ marginTop: 3 }}>{t('fam.latestTitle')}</T></View>
          <T w={800}>›</T>
        </View>
      </Pressable>

      <SectionRow title={t('fam.help')} />
      {apiTasks.data && (
        <Card radius={17}>
          {apiTasks.data.length === 0 && <T size={8} color={c.muted} style={{ padding: 12 }}>{t('fam.noTasks')}</T>}
          {apiTasks.data.map((task, i) => (
            <View key={task.id} style={{ minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 10, paddingVertical: 8, borderBottomWidth: i < apiTasks.data!.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
              <IconBadge icon={task.category === 'medications' ? 'pill' : task.category === 'alerts' ? 'bell' : 'activity'} bg={c.lavender} size={30} />
              <T size={8.5} w={700} lh={1.4} style={{ flex: 1 }}>{task.text}</T>
              <Pressable onPress={() => done(task.id)} style={{ paddingVertical: 6, paddingHorizontal: 10, borderRadius: 99, borderWidth: 1, borderColor: c.ink, backgroundColor: c.primary }}>
                <T size={7.5} w={800} color="#fff">{t('common.done')}</T>
              </Pressable>
            </View>
          ))}
        </Card>
      )}
      {!apiTasks.data && <Card radius={17}>
        {tasks.map(([title, sub], i) => (
          <View key={title} style={{ minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 9, paddingHorizontal: 10, borderBottomWidth: i < 2 ? 1 : 0, borderBottomColor: c.line }}>
            <IconBadge icon={i === 0 ? 'activity' : i === 1 ? 'pill' : 'calendar'} bg={[c.sky, c.lavender, c.yellow][i]} size={30} />
            <View style={{ flex: 1 }}><T size={8.5} w={800}>{title}</T><T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
            <Pressable onPress={() => { haptic('notificationSuccess'); setHelp(h => h.map((x, n) => (n === i ? !x : x))); }}
              style={{ paddingVertical: 6, paddingHorizontal: 10, borderRadius: 99, borderWidth: 1, borderColor: c.ink, backgroundColor: help[i] ? c.green : c.primary }}>
              <T size={7.5} w={800} color={help[i] ? c.text : '#fff'}>{help[i] ? t('fam.confirmed') : t('fam.willHelp')}</T>
            </Pressable>
          </View>
        ))}
      </Card>}

      <Pressable onPress={() => { haptic('notificationSuccess'); setObserved(true); }}>
        <View style={{ minHeight: 50, marginTop: 9, borderWidth: 1, borderStyle: 'dashed', borderColor: c.ink, borderRadius: 14, backgroundColor: c.amber, paddingHorizontal: 10, paddingVertical: 8, flexDirection: 'row', alignItems: 'center', gap: 9 }}>
          <Icon name="message" size={18} />
          {observed
            ? <Animated.View entering={FadeIn} style={{ flex: 1 }}><T size={8.5} w={800}>{t('fam.observeSent')}</T></Animated.View>
            : <View style={{ flex: 1 }}><T size={8.5} w={800}>{t('fam.observe')}</T><T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{t('fam.observeSub')}</T></View>}
        </View>
      </Pressable>

      <View style={{ marginTop: 9, borderWidth: 1.2, borderColor: c.ink, borderRadius: 14, backgroundColor: c.readonly, paddingVertical: 8, paddingHorizontal: 10 }}>
        <T size={5.5} w={800} spacing={0.8} style={{ marginBottom: 4 }}>{t('fam.readonly')}</T>
        {[[t('fam.plan'), t('fam.viewOnly')], [t('fam.meds'), t('fam.noChanges')], [t('fam.checkins'), t('fam.sarahAnswers')]].map(([a, b]) => (
          <View key={a} style={{ height: 24, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: c.line }}>
            <T size={7}>{a}</T><T size={6.5} w={800} color={c.muted}>{b}</T>
          </View>
        ))}
      </View>
      <T size={6.5} color={c.muted} center style={{ marginTop: 10 }}>{t('fam.caregiverNote')}</T>
    </Screen>
  );
}
