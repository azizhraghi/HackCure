import React from 'react';
import { Linking, Pressable, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { MiniLine, WoundThumb } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Button, Card, Chip, PageTitle, Screen, SimulatedTag, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function EscalationScreen({ navigation }: RootScreen<'Escalation'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const { familyAck, setFamilyAck } = useAppState();
  const timeline: [IconName, string, string, string][] = [
    ['sensor', t('escalation.s1'), t('escalation.s1s'), '07:30'],
    ['camera', t('escalation.s2'), t('escalation.s2s'), '09:42'],
    ['checkin', t('escalation.s3'), t('escalation.s3s'), '10:06'],
  ];
  const loop = list('escalation.loopSteps');
  const loopDone = 2; // sent + seen; decision in progress

  return (
    <Screen>
      <TopBar title={t('escalation.top')} />
      <View style={{ height: 68, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Avatar initials="ER" portrait size={43} />
        <View style={{ flex: 1 }}>
          <T size={6} spacing={0.8}>{t('escalation.shared')}</T>
          <T size={11} w={800} style={{ marginVertical: 2 }}>Dr. Elena Ruiz</T>
          <T size={7} color={c.muted}>{t('escalation.sent')}</T>
        </View>
        <View style={{ width: 21, height: 21, borderRadius: 11, backgroundColor: c.green, alignItems: 'center', justifyContent: 'center' }}><Icon name="check" size={16} /></View>
      </View>
      <PageTitle size={26}>{t('escalation.title')}</PageTitle>

      <View style={{ minHeight: 92, borderWidth: 1.5, borderColor: '#eb6c63', backgroundColor: c.warnBg, borderRadius: 18, padding: 11, flexDirection: 'row', gap: 10 }}>
        <View style={{ width: 29, height: 29, borderRadius: 15, backgroundColor: '#ef6c63', borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T w={800} color="#fff">!</T></View>
        <View style={{ flex: 1 }}>
          <T size={6} w={800} spacing={0.8} color={c.urgentText}>{t('escalation.attention')}</T>
          <T size={10} w={800} style={{ marginVertical: 3 }}>{t('escalation.abnormal')}</T>
          <T size={7} lh={1.4}>{t('escalation.abnormalSub')}</T>
        </View>
      </View>

      <Pressable onPress={() => setFamilyAck(!familyAck)}>
        <View style={{ minHeight: 50, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.amber, borderRadius: 14, marginTop: 8, paddingVertical: 7, paddingHorizontal: 9, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Icon name="bell" size={16} />
          <View style={{ flex: 1 }}>
            <T size={8} w={800}>{t('escalation.family')}</T>
            <T size={6} color={c.muted} style={{ marginTop: 2 }}>{t('escalation.familySub')}</T>
          </View>
          <T w={800}>›</T>
        </View>
      </Pressable>
      {familyAck && (
        <Animated.View entering={FadeIn} style={{ height: 29, marginTop: 6, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderRadius: 99, backgroundColor: c.green, borderWidth: 1, borderColor: c.ink }}>
          <Icon name="check" size={15} /><T size={7} w={800}>{t('escalation.seen')}</T>
        </Animated.View>
      )}

      <Card radius={20} style={{ padding: 11, marginTop: 9 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View><T size={6} spacing={0.8}>{t('escalation.package')}</T><T size={14} w={800} style={{ marginTop: 2 }}>{t('escalation.changed')}</T></View>
          <Chip tone="blue">{t('escalation.sources')}</Chip>
        </View>
        <View style={{ marginVertical: 9 }}>
          {timeline.map(([icon, title, sub, time], i) => (
            <View key={title} style={{ minHeight: 45, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              {i < timeline.length - 1 && <View style={{ position: 'absolute', left: 13, top: 36, height: 19, borderLeftWidth: 1, borderStyle: 'dashed', borderColor: '#9aa6b9' }} />}
              <View style={{ width: 27, height: 27, borderRadius: 9, borderWidth: 1, borderColor: c.ink, backgroundColor: c.blue, alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} size={15} /></View>
              <View style={{ flex: 1 }}><T size={8} w={800}>{title}</T><T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{sub}</T></View>
              <T size={6} color={c.faint}>{time}</T>
            </View>
          ))}
        </View>
        <View style={{ flexDirection: 'row', gap: 7 }}>
          <View style={{ flex: 1.15, height: 90, borderWidth: 1.1, borderColor: c.ink, borderRadius: 12, padding: 7, backgroundColor: '#fff5e1', overflow: 'hidden' }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><T size={5.5} w={800} color="#1b2a4a">{t('escalation.temperature')}</T><SimulatedTag style={{ paddingVertical: 1 }} /></View>
            <T size={15} w={800} color="#1b2a4a">38.2°C <T size={9} color="#e7514a">↑</T></T>
            <MiniLine color="#ef695d" fill height={35} style={{ marginTop: 0 }} />
          </View>
          <View style={{ flex: 0.85, height: 90, borderWidth: 1.1, borderColor: c.ink, borderRadius: 12, padding: 7, backgroundColor: '#fde8e5', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 3 }}>
            <WoundThumb width={46} height={52} radius={7} border={false} />
            <WoundThumb width={46} height={52} radius={7} border={false} worse />
            <View style={{ position: 'absolute', bottom: 3, backgroundColor: '#fff', borderRadius: 5, paddingHorizontal: 4, paddingVertical: 1 }}><T size={5.5} color="#1b2a4a">{t('escalation.compare')}</T></View>
          </View>
        </View>
        <View style={{ marginTop: 8, borderLeftWidth: 3, borderLeftColor: c.primary, backgroundColor: c.quote, borderTopRightRadius: 9, borderBottomRightRadius: 9, paddingVertical: 7, paddingHorizontal: 9 }}>
          <T size={7} w={700} lh={1.4}>{t('escalation.quote')}</T>
          <T size={5.5} w={500} color={c.muted} style={{ marginTop: 3 }}>{t('escalation.quoteSrc')}</T>
        </View>
        <T size={6} color={c.muted} center style={{ marginTop: 8 }}>✦ {t('escalation.uncertainty')}</T>
      </Card>

      {/* Closed-loop follow-up verification */}
      <Card bg={c.ice} radius={18} style={{ padding: 11, marginTop: 9 }}>
        <T size={6} spacing={0.8}>{t('escalation.loop')}</T>
        <T size={12} w={800} style={{ marginTop: 2, marginBottom: 8 }}>{t('escalation.loopTitle')}</T>
        {loop.map((step, i) => (
          <View key={step} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 26 }}>
            {i < loop.length - 1 && <View style={{ position: 'absolute', left: 9, top: 19, height: 14, borderLeftWidth: 1.5, borderColor: i < loopDone ? c.primary : '#aeb8c9', borderStyle: i < loopDone ? 'solid' : 'dashed' }} />}
            <View style={{ width: 19, height: 19, borderRadius: 10, borderWidth: 1, borderColor: c.ink, backgroundColor: i < loopDone ? c.primary : i === loopDone ? c.yellow : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {i < loopDone ? <Icon name="check" size={11} color="#fff" /> : <T size={6.5} w={800}>{i + 1}</T>}
            </View>
            <T size={8} w={i === loopDone ? 800 : 600} color={i > loopDone ? c.muted : c.text}>{step}</T>
          </View>
        ))}
      </Card>

      <View style={{ flexDirection: 'row', gap: 8, marginTop: 9 }}>
        <Button icon="phone" flat height={43} style={{ flex: 1 }} size={11} onPress={() => Linking.openURL('tel:+10000000000')}>{t('escalation.call')}</Button>
        <Button secondary icon="message" flat height={43} style={{ flex: 1 }} size={11} onPress={() => navigation.navigate('AIAssistant')}>{t('escalation.message')}</Button>
      </View>
    </Screen>
  );
}
