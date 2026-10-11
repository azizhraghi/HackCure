import React, { useState } from 'react';
import { Linking, Pressable, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { MiniLine } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, haptic, Muted, PageTitle, RoundButton, Screen, SimulatedTag, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { LockTone, RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

const call = (n: string) => Linking.openURL(`tel:${n}`).catch(() => {});

/** F04 — lock-screen notification preview */
export function LockPreviewScreen({ navigation, route }: RootScreen<'LockPreview'>) {
  const { t } = useT();
  const tone: LockTone = route.params.tone;
  const content = {
    info: [t('lock.info'), t('lock.infoT'), t('lock.infoC'), t('lock.now')],
    attention: [t('lock.attention'), t('lock.attT'), t('lock.attC'), t('lock.ago')],
    urgent: [t('lock.urgent'), t('lock.urgT'), t('lock.urgC'), t('lock.now')],
  }[tone];
  const markBg = tone === 'info' ? '#1e88e5' : tone === 'attention' ? '#ffb347' : '#ff6b6b';
  const target = tone === 'info' ? 'FamilyInfo' : tone === 'attention' ? 'FamilyAttention' : 'FamilyUrgent';
  const colors = tone === 'urgent' ? ['#f7b5b5', '#e87979'] : ['#b7dff4', '#d8cdf8', '#f2d8ea'];

  return (
    <LinearGradient colors={colors} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ flex: 1 }}>
      <SafeAreaView style={{ flex: 1, paddingHorizontal: 18 }}>
        <Pressable onPress={() => navigation.goBack()} style={{ alignSelf: 'flex-end', marginTop: 6, padding: 6 }}><Icon name="close" size={22} color="#17223c" /></Pressable>
        <View style={{ alignItems: 'center', marginTop: 20 }}>
          <T size={68} w={800} spacing={-4} color="#17223c" style={{ lineHeight: 72 }}>12:41</T>
          <T size={13} w={700} color="#17223c" style={{ marginTop: 8 }}>{t('lock.date')}</T>
        </View>
        <Animated.View entering={FadeInDown.delay(200)}>
          <Pressable onPress={() => { haptic(); navigation.replace(target); }}
            style={{ minHeight: 145, marginTop: 90, padding: 13, borderWidth: 1, borderColor: 'rgba(27,42,74,0.35)', borderRadius: 21, backgroundColor: 'rgba(255,255,255,0.78)', flexDirection: 'row', gap: 9 }}>
            <View style={{ width: 37, height: 37, borderRadius: 10, borderWidth: 1.2, borderColor: '#1b2a4a', backgroundColor: markBg, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={tone === 'info' ? 'check' : 'bell'} size={18} color={tone === 'attention' ? '#1b2a4a' : '#fff'} />
            </View>
            <View style={{ flex: 1 }}>
              <T size={6} color="#536078"><T size={6} w={800} color="#536078">{t('lock.app')}</T> · {content[3]}</T>
              <T size={8} w={800} upper color="#1b2a4a" style={{ marginTop: 6 }}>{content[0]}</T>
              <T size={11} w={800} lh={1.35} color="#1b2a4a" style={{ marginTop: 3 }}>{content[1]}</T>
              <T size={7} lh={1.4} color="#59677e" style={{ marginTop: 4 }}>{content[2]}</T>
            </View>
          </Pressable>
        </Animated.View>
        <View style={{ flex: 1 }} />
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 12, marginBottom: 14 }}>
          {(['camera', 'activity'] as IconName[]).map(i => <View key={i} style={{ width: 43, height: 43, borderRadius: 22, backgroundColor: 'rgba(27,42,74,0.32)', alignItems: 'center', justifyContent: 'center' }}><Icon name={i} size={19} color="#fff" /></View>)}
        </View>
        <T size={7} color="#fff" center style={{ marginBottom: 14 }}>{t('lock.swipe')}</T>
      </SafeAreaView>
    </LinearGradient>
  );
}

function useAck() {
  const { setFamilyAck } = useAppState();
  const [seen, setSeen] = useState(false);
  return { seen, mark: () => { haptic('notificationSuccess'); setSeen(true); setFamilyAck(true); } };
}

/** F05 — info update detail */
export function FamilyInfoScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const { seen, mark } = useAck();
  const rows: [IconName, string, string][] = [['checkin', t('info.pain'), t('info.painV')], ['activity', t('info.symptoms'), t('info.noNew')], ['check', t('info.status'), t('common.onTrack')]];
  return (
    <Screen>
      <TopBar title={t('info.top')} />
      <View style={{ width: 70, height: 70, borderRadius: 35, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.sky, alignSelf: 'center', marginTop: 34, marginBottom: 12, alignItems: 'center', justifyContent: 'center' }}><Icon name="check" size={27} /></View>
      <Chip tone="blue" style={{ alignSelf: 'center' }}>{t('info.chip')}</Chip>
      <PageTitle center size={26}>{t('info.title')}</PageTitle>
      <Muted center>{t('info.when')}</Muted>
      <Card radius={18} style={{ marginTop: 16, marginBottom: 12 }}>
        {rows.map(([icon, k, v], i) => (
          <View key={k} style={{ height: 68, flexDirection: 'row', alignItems: 'center', gap: 11, paddingHorizontal: 12, borderBottomWidth: i < 2 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 33, height: 33, borderRadius: 10, backgroundColor: c.blue, alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} /></View>
            <View><T size={5.5} spacing={0.7}>{k}</T><T size={9} w={800} style={{ marginTop: 3 }}>{v}</T></View>
          </View>
        ))}
      </Card>
      <Card bg={c.green} radius={15} style={{ minHeight: 72, padding: 11, marginBottom: 24 }}>
        <T size={9} w={800}>{t('info.good')}</T>
        <T size={7} lh={1.5} style={{ marginTop: 4 }}>{t('info.routine')}</T>
      </Card>
      <Button onPress={mark}>{seen ? `${t('common.seenDone')} ✓` : t('common.seen')}</Button>
    </Screen>
  );
}

/** F06 — needs-attention detail */
export function FamilyAttentionScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const { seen, mark } = useAck();
  const signals: [IconName, string, string][] = [['sensor', t('attention.s1'), t('attention.s1s')], ['camera', t('attention.s2'), t('attention.s2s')], ['checkin', t('attention.s3'), t('attention.s3s')]];
  return (
    <Screen>
      <TopBar title={t('attention.top')} />
      <View style={{ minHeight: 112, borderWidth: 1.5, borderColor: c.review, borderRadius: 19, backgroundColor: c.peach, padding: 12, flexDirection: 'row', gap: 10 }}>
        <View style={{ width: 39, height: 39, borderRadius: 11, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.review, alignItems: 'center', justifyContent: 'center' }}><Icon name="thermo" size={24} color="#1b2a4a" /></View>
        <View style={{ flex: 1 }}>
          <T size={5.5} spacing={0.7} color={c.reviewText}>{t('attention.kicker')}</T>
          <T size={11} w={800} lh={1.35} style={{ marginVertical: 3 }}>{t('attention.title')}</T>
          <T size={6.5}>{t('attention.sub')}</T>
        </View>
      </View>
      <Card radius={17} style={{ marginTop: 9, padding: 10 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View><T size={5.5}>{t('attention.changed')}</T><T size={9} w={800} style={{ marginTop: 2 }}>{t('attention.rose')}</T></View>
          <View style={{ flexDirection: 'row', gap: 4 }}><SimulatedTag /><Chip tone="yellow">{t('attention.since')}</Chip></View>
        </View>
        <MiniLine color="#ef695d" fill height={51} style={{ marginTop: 1 }} />
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View><T size={5.5}>7:30 AM</T><T size={9} w={800} style={{ marginTop: 2 }}>36.9°C</T></View>
          <T w={800}>→</T>
          <View><T size={5.5}>10:06 AM</T><T size={9} w={800} style={{ marginTop: 2 }}>38.2°C</T></View>
        </View>
      </Card>
      <Card radius={17} style={{ marginTop: 9, padding: 10 }}>
        <T size={5.5} w={800} spacing={0.7}>{t('attention.signals')}</T>
        {signals.map(([icon, title, sub]) => (
          <View key={title} style={{ height: 48, flexDirection: 'row', alignItems: 'center', gap: 8, borderTopWidth: 1, borderTopColor: c.line, marginTop: 4 }}>
            <View style={{ width: 27, height: 27, borderRadius: 8, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} size={17} /></View>
            <View style={{ flex: 1 }}><T size={7.5} w={800}>{title}</T><T size={6} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
            <Icon name="check" size={16} color={c.trackText} />
          </View>
        ))}
      </Card>
      <View style={{ flexDirection: 'row', gap: 7, marginVertical: 9 }}>
        <Button icon="phone" flat height={43} size={9} style={{ flex: 0.8 }} onPress={() => call('+10000000001')}>{t('common.callSarah')}</Button>
        <Button secondary icon="phone" flat height={43} size={9} style={{ flex: 1.2 }} onPress={() => call('+10000000002')}>{t('attention.surgeon')}</Button>
      </View>
      <Button onPress={mark}>{seen ? `${t('common.acknowledged')} ✓` : t('common.seen')}</Button>
    </Screen>
  );
}

/** F07 — urgent alert (full-screen red) */
export function FamilyUrgentScreen({ navigation, route }: RootScreen<'FamilyUrgent'>) {
  const { t } = useT();
  const live = route.params;
  const { seen, mark } = useAck();
  return (
    <Screen bg="#ff6b6b" edges={['top', 'bottom']} style={{ paddingHorizontal: 20, paddingTop: 13 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <RoundButton icon="close" bg="rgba(255,255,255,0.7)" onPress={() => navigation.goBack()} />
        <Chip>{t('urgent.chip')}</Chip>
        <View style={{ width: 38 }} />
      </View>
      <View style={{ width: 92, height: 92, borderRadius: 46, borderWidth: 2, borderColor: '#1b2a4a', backgroundColor: '#fff', alignSelf: 'center', marginTop: 56, marginBottom: 20, alignItems: 'center', justifyContent: 'center' }}>
        <T size={50} w={800} color="#1b2a4a">!</T>
      </View>
      <T size={27} w={800} center spacing={-1} color="#1b2a4a" style={{ lineHeight: 32 }}>{live?.title ?? t('urgent.title')}</T>
      <T size={10} w={600} center lh={1.5} color="#1b2a4a" style={{ marginTop: 14, marginBottom: 22, marginHorizontal: 16 }}>{live?.message ?? t('urgent.body')}</T>
      <View style={{ borderWidth: 1.5, borderColor: '#1b2a4a', borderRadius: 16, backgroundColor: 'rgba(255,255,255,0.78)', padding: 12 }}>
        <T size={11} w={800} color="#1b2a4a">{t('urgent.act')}</T>
        <T size={7} lh={1.45} color="#1b2a4a" style={{ marginTop: 4 }}>{t('urgent.actSub')}</T>
      </View>
      <View style={{ gap: 8, marginTop: 18 }}>
        <Button icon="phone" flat color="#1b2a4a" onPress={() => call('112')}>{t('urgent.emergency')}</Button>
        <Button icon="phone" flat secondary color="#fff" textColor="#1b2a4a" onPress={() => call('+10000000001')}>{t('common.callSarah')}</Button>
        <Button flat secondary color="#fff" textColor="#1b2a4a" onPress={mark}>{seen ? t('urgent.waySeen') : t('urgent.way')}</Button>
      </View>
      <Pressable onPress={mark} style={{ marginTop: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <Icon name="check" size={16} color="#1b2a4a" />
        <T size={8} w={800} color="#1b2a4a" style={{ textDecorationLine: 'underline' }}>{seen ? t('common.acknowledged') : t('common.seen')}</T>
      </Pressable>
    </Screen>
  );
}
