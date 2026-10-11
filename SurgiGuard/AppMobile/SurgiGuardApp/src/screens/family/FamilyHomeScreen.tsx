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
  const { session } = useAppState();
  const me = session?.user;
  const { patient } = useFollowedPatient();
  const { data: alerts } = useAlerts(patient?.patient_id);

  // Most severe open alert of the last hours drives the status card
  const active = (alerts ?? [])
    .filter(a => a.status === 'OPEN' && Date.now() - Date.parse(a.created_at) < ACTIVE_ALERT_WINDOW_MS)
    .sort((a, b) => b.severity - a.severity)[0];
  const status = !active
    ? { bg: c.green, icon: 'check' as const, title: t('common.onTrack'), sub: t('fam.noUrgent') }
    : { bg: active.severity >= 3 ? '#ffd3d3' : c.peach, icon: 'bell' as const,
        title: active.severity >= 3 ? t('fam.statusUrgent') : t('fam.statusAttention'),
        sub: `${t(`alerts.${active.type}`)} · ${formatAgo(t, active.created_at)}` };
  const openActive = () => {
    if (!active) return;
    if (active.severity >= 3) nav.navigate('FamilyUrgent', { title: `${t(`alerts.${active.type}`)} · ${patient?.full_name ?? ''}`, message: active.message });
    else nav.navigate('FamilyTabs', { screen: 'Updates' });
  };

  return (
    <Screen>
      <CaregiverBanner />
      <View style={{ height: 60, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(`${me?.first_name ?? ''} ${me?.last_name ?? ''}`)} bg={c.sky} online />
        <View style={{ flex: 1 }}><T size={9} color={c.muted}>{t('home.welcome')}</T><T size={14} w={800} style={{ marginTop: 2 }}>{t('fam.hi', { name: me?.first_name ?? '' })}</T></View>
        <RoundButton icon="bell" size={35} onPress={() => nav.navigate('FamilyTabs', { screen: 'Updates' })} />
      </View>

      <View style={{ height: 72, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(patient?.full_name ?? '?')} size={47} />
        <View>
          <T size={5.5} spacing={0.7}>{t('fam.following')}</T>
          <T size={13} w={800} style={{ marginVertical: 2 }}>{patient?.full_name ?? t('fam.noPatient')}</T>
          <T size={6.5} color={c.muted}>{patient ? `${patient.relationship}${patient.device_id ? ` · ${patient.device_id}` : ''}` : ''}</T>
        </View>
      </View>

      <Pressable onPress={openActive} disabled={!active}>
        <Card bg={status.bg} style={{ minHeight: 92, padding: 12, flexDirection: 'row', alignItems: 'center', gap: 11 }}>
          <View style={{ width: 42, height: 42, borderRadius: 21, borderWidth: 1.3, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}><Icon name={status.icon} size={20} /></View>
          <View style={{ flex: 1 }}>
            <T size={5.5} spacing={0.8} color="#1b2a4a">{t('fam.status')}</T>
            <T size={18} w={800} color="#1b2a4a" style={{ marginVertical: 2 }}>{status.title}</T>
            <T size={6.5} color="#1b2a4a">{status.sub}</T>
          </View>
          {active && <T w={800} color="#1b2a4a">›</T>}
        </Card>
      </Pressable>

      <View style={{ height: 10 }} />
      <LiveVitalsCard patientId={patient?.patient_id} />

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
      <Card radius={17}>
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
      </Card>

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
