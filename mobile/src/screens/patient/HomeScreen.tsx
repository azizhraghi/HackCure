import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { MiniBars, MiniLine, ScoreRing } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Card, haptic, IconBadge, PageTitle, RoundButton, Screen, SectionRow, SimulatedTag } from '../../components/ui';
import { metrics, patient } from '../../data/mock';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

export function HomeHeader({ greeting, name, avatar, avatarBg }: { greeting: string; name: string; avatar: string; avatarBg?: string }) {
  const { c } = useTheme();
  const nav = useNavigation();
  return (
    <View style={{ height: 60, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Avatar initials={avatar} online bg={avatarBg} />
      <View style={{ flex: 1 }}>
        <T size={9} color={c.muted}>{greeting}</T>
        <T size={14} w={800} style={{ marginTop: 2 }}>{name}</T>
      </View>
      <View style={{ flexDirection: 'row', gap: 6 }}>
        <RoundButton icon="sparkle" size={35} onPress={() => nav.navigate('AIAssistant')} />
        <RoundButton icon="bell" size={35} onPress={() => nav.navigate('SensingRequest')} />
      </View>
    </View>
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

export function HomeScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const [taskDone, setTaskDone] = useState(false);
  const [taskHidden, setTaskHidden] = useState(false);

  return (
    <Screen>
      <HomeHeader greeting={t('home.welcome')} name={`${patient.first} 👋`} avatar={patient.initials} />
      <PageTitle>{t('home.title')}</PageTitle>

      {/* Sensor alert → active sensing request */}
      <Pressable onPress={() => nav.navigate('SensingRequest')}>
        <Card bg={c.lilacBg} radius={16} style={{ padding: 10, flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <IconBadge icon="sensor" bg={c.surface} size={32} radius={10} />
          <View style={{ flex: 1 }}>
            <T size={7} w={800} spacing={0.8} upper color={c.muted}>{t('home.alert')}</T>
            <T size={9.5} w={800} style={{ marginTop: 2 }}>{t('home.alertSub')}</T>
          </View>
          <View style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: 99, backgroundColor: c.primary, borderWidth: 1, borderColor: c.ink }}>
            <T size={8} w={800} color="#fff">{t('home.alertCta')}</T>
          </View>
        </Card>
      </Pressable>

      {!taskHidden && (
        <Pressable onPress={() => nav.navigate('WoundScan')}>
          <Card bg={c.task} radius={22} style={{ padding: 16, minHeight: 131, overflow: 'hidden' }}>
            <View style={{ position: 'absolute', width: 100, height: 100, borderRadius: 50, borderWidth: 18, borderColor: 'rgba(255,255,255,0.18)', right: -25, bottom: -38 }} />
            <Pressable onPress={() => setTaskHidden(true)} style={{ position: 'absolute', right: 11, top: 10, width: 26, height: 26, borderRadius: 13, borderWidth: 1.2, borderColor: c.ink, backgroundColor: 'rgba(255,255,255,0.5)', alignItems: 'center', justifyContent: 'center', zIndex: 2 }}>
              <Icon name="close" size={16} />
            </Pressable>
            <T size={8} w={800} spacing={1.2}>{t('home.task')}</T>
            <T size={16} w={800} lh={1.3} style={{ marginTop: 6, textDecorationLine: taskDone ? 'line-through' : 'none' }}>{t('home.taskTitle')}</T>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 11 }}>
              <T size={8}>{t('home.about')}</T>
              <Pressable onPress={() => { haptic('notificationSuccess'); setTaskDone(v => !v); }} style={{ borderWidth: 1.2, borderColor: c.ink, backgroundColor: taskDone ? c.green : c.surface, borderRadius: 99, paddingVertical: 7, paddingHorizontal: 12 }}>
                <T size={9} w={800}>{taskDone ? '✓ ' : ''}{t('common.done')} ›</T>
              </Pressable>
            </View>
          </Card>
        </Pressable>
      )}

      <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
        <Card bg={c.pink} style={{ flex: 1, height: 145, padding: 12, overflow: 'hidden' }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <T size={7.5} w={800} spacing={0.7}>{t('home.woundTemp')}</T>
            <SimulatedTag style={{ paddingVertical: 1 }} />
          </View>
          <T size={31} w={800} spacing={-1.6} style={{ marginTop: 5 }}>{metrics.woundTemp}<T size={12} w={800}>°C</T></T>
          <T size={7.5} color={c.muted}>{t('home.normal')}</T>
          <MiniBars />
        </Card>
        <Card bg={c.yellow} style={{ flex: 1, height: 145, padding: 12, overflow: 'hidden' }}>
          <T size={7.5} w={800} spacing={0.7}>{t('home.pain')}</T>
          <T size={31} w={800} spacing={-1.6} style={{ marginTop: 5 }}>{metrics.pain}<T size={12} w={800}>/10</T></T>
          <T size={7.5} w={700} color={c.trackText}>{t('home.painDown')}</T>
          <MiniLine />
        </Card>
      </View>

      <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
        <Shortcut icon="pill" title={t('home.meds')} sub={t('home.medsSub')} bg={c.lavender} onPress={() => nav.navigate('Medications')} />
        <Shortcut icon="sparkle" title={t('home.ai')} sub={t('home.aiSub')} bg={c.sky} onPress={() => nav.navigate('AIAssistant')} />
      </View>

      <SectionRow title={t('home.check')} right={<Pressable onPress={() => nav.navigate('PatientTabs', { screen: 'Reports' })}><T size={8} w={800} color={c.primary}>{t('common.viewDetails')}</T></Pressable>} />
      <Card radius={20} style={{ height: 116, padding: 10, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <ScoreRing value={patient.score} label={t('home.score')} />
        <View style={{ flex: 1 }}>
          <T size={10} w={800}>{t('home.onTrack')}</T>
          <T size={7} color={c.muted} style={{ marginTop: 3, marginBottom: 10 }}>{t('home.ahead')}</T>
          <View style={{ flexDirection: 'row', gap: 13 }}>
            <View style={{ flexDirection: 'row', gap: 5 }}>
              <T size={13}>☾</T>
              <View><T size={9} w={800}>{metrics.sleep}</T><T size={6} color={c.muted}>{t('home.lastNight')}</T></View>
            </View>
            <View style={{ flexDirection: 'row', gap: 5 }}>
              <T size={13}>◷</T>
              <View><T size={9} w={800}>{t('common.day')} {patient.day}</T><T size={6} color={c.muted}>{t('home.of42')}</T></View>
            </View>
          </View>
        </View>
      </Card>

      <Card bg={c.mint} radius={16} style={{ marginTop: 10, padding: 11, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <IconBadge icon="calendar" bg={c.surface} size={32} radius={10} />
        <View style={{ flex: 1 }}>
          <T size={6.5} w={800} spacing={0.8} color={c.muted}>{t('home.appt')}</T>
          <T size={10} w={800} style={{ marginTop: 2 }}>{t('home.apptTitle')}</T>
          <T size={7.5} color={c.muted} style={{ marginTop: 1 }}>{t('home.apptSub')}</T>
        </View>
      </Card>
    </Screen>
  );
}
