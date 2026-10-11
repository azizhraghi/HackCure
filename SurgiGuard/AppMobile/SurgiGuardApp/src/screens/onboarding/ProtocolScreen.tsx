import React from 'react';
import { View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, Muted, PageTitle, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function ProtocolScreen({ navigation }: RootScreen<'Protocol'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const { completeOnboarding } = useAppState();
  const cards = [
    { k: 'med', bg: c.pink }, { k: 'act', bg: c.yellow }, { k: 'reh', bg: c.lavender }, { k: 'fol', bg: c.sky },
  ];
  return (
    <Screen>
      <TopBar title={t('protocol.top')} />
      <View style={{ width: 48, height: 48, borderRadius: 24, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.green, alignItems: 'center', justifyContent: 'center', alignSelf: 'center', marginTop: 5, marginBottom: 6 }}>
        <Icon name="check" size={25} />
      </View>
      <PageTitle center>{t('protocol.title')}</PageTitle>
      <Muted center>{t('protocol.sub')}</Muted>

      <Card bg={c.green} style={{ minHeight: 75, padding: 11, flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4, marginBottom: 9 }}>
        <View style={{ width: 39, height: 39, borderRadius: 20, backgroundColor: c.surface, borderWidth: 1.2, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T size={22}>◒</T></View>
        <View style={{ flex: 1 }}>
          <T size={7} w={700} spacing={0.8}>{t('protocol.detected')}</T>
          <T size={11} w={800} style={{ marginVertical: 3 }}>{t('protocol.surgery')}</T>
          <T size={8}>{t('protocol.surgerySub')}</T>
        </View>
        <Icon name="check" size={19} />
      </Card>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>
        {cards.map((card, i) => (
          <Animated.View key={card.k} entering={FadeInDown.delay(i * 80)} style={{ width: '48.7%' }}>
            <Card bg={card.bg} radius={15} style={{ minHeight: 80, padding: 10 }}>
              <T size={7.5} w={800} upper>{t(`protocol.${card.k}T`)}</T>
              <T size={9} w={800} lh={1.35} style={{ marginTop: 5, maxWidth: 115 }}>{t(`protocol.${card.k}C`)}</T>
              <View style={{ position: 'absolute', right: 7, bottom: 7, backgroundColor: 'rgba(255,255,255,0.68)', borderRadius: 10, paddingVertical: 3, paddingHorizontal: 6 }}>
                <T size={6.5} w={800} color="#1b2a4a">{t(`protocol.${card.k}Tag`)}</T>
              </View>
            </Card>
          </Animated.View>
        ))}
      </View>

      <View style={{ borderWidth: 1.5, borderColor: c.warnBorder, backgroundColor: c.warnBg, borderRadius: 14, minHeight: 47, marginTop: 7, padding: 8, flexDirection: 'row', gap: 8, alignItems: 'center' }}>
        <View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: c.warnDot, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T w={800} size={12} color="#1b2a4a">!</T></View>
        <View style={{ flex: 1 }}>
          <T size={9} w={800}>{t('protocol.warning')}</T>
          <T size={7} style={{ marginTop: 2 }}>{t('protocol.warningSub')}</T>
        </View>
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 9 }}>
        <Icon name="shield" size={14} color={c.trackText} />
        <T size={8} w={700} color={c.trackText}>{t('protocol.approved')}</T>
      </View>

      <T size={9} w={800} style={{ marginTop: 10, marginBottom: 6 }}>{t('protocol.modules')}</T>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5 }}>
        {list('protocol.chips').map(x => <Chip key={x} tone="blue">{x}</Chip>)}
      </View>

      <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
        <Button secondary style={{ width: '32%' }} onPress={() => navigation.goBack()}>{t('common.edit')}</Button>
        <Button style={{ flex: 1 }} onPress={completeOnboarding} size={12}>{t('protocol.confirm')}</Button>
      </View>
    </Screen>
  );
}
