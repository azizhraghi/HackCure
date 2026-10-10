import React from 'react';
import { Pressable, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { WoundThumb } from '../../components/charts';
import { KneeFigure } from '../../components/figures';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, RoundButton, Screen, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function TwinDetailScreen({ navigation }: RootScreen<'TwinDetail'>) {
  const { c } = useTheme();
  const { t } = useT();
  const items: [string, string, string, IconName][] = [
    [t('twinDetail.temperature'), '36.9°C', c.yellow, 'thermo'],
    [t('twinDetail.moisture'), '42%', c.pink, 'drop'],
    [t('twinDetail.redness'), t('twinDetail.low'), c.pink, 'activity'],
    [t('twinDetail.kneeAngle'), '92°', c.yellow, 'rotate'],
  ];
  return (
    <Screen>
      <TopBar title={t('twinDetail.top')} back={false} action={<RoundButton icon="close" onPress={() => navigation.goBack()} />} />
      <LinearGradient colors={['#f8fcff', '#dbeef9']} style={{ height: 278, borderWidth: 1.5, borderColor: c.ink, borderRadius: 24, overflow: 'hidden' }}>
        <KneeFigure />
        <Chip tone="green" style={{ position: 'absolute', top: 12, left: 12 }}>{t('twinDetail.healing')}</Chip>
        <T size={8} w={800} color="#1b2a4a" style={{ position: 'absolute', right: 12, top: 15 }}>{t('common.day')} 6</T>
      </LinearGradient>

      <View style={{ backgroundColor: c.surface, borderWidth: 1.5, borderColor: c.ink, borderTopLeftRadius: 27, borderTopRightRadius: 27, marginTop: -17, marginHorizontal: -16, paddingHorizontal: 16, paddingTop: 13, paddingBottom: 30 }}>
        <View style={{ width: 42, height: 4, borderRadius: 5, backgroundColor: '#cbd2de', alignSelf: 'center', marginBottom: 12 }} />
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <T size={7} spacing={1}>{t('twinDetail.kicker')}</T>
            <T size={20} w={800} style={{ marginTop: 2 }}>{t('twinDetail.top')}</T>
          </View>
          <Chip tone="green">{t('common.onTrack')}</Chip>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
          {items.map(([label, value, bg, icon]) => (
            <Card key={label} bg={bg} radius={17} style={{ width: '48.5%', height: 87, padding: 10 }}>
              <View style={{ position: 'absolute', right: 10, top: 10 }}><Icon name={icon} size={18} /></View>
              <T size={8} w={700}>{label}</T>
              <T size={22} w={800} style={{ marginTop: 12 }}>{value}</T>
            </Card>
          ))}
          <View pointerEvents="box-none" style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' }}>
            <Pressable onPress={() => navigation.navigate('PatientTabs', { screen: 'Reports' })} style={{ borderWidth: 1.3, borderColor: c.ink, borderRadius: 99, backgroundColor: c.primary, paddingVertical: 8, paddingHorizontal: 13 }}>
              <T size={8} w={800} color="#fff">{t('twinDetail.viewMore')}</T>
            </Pressable>
          </View>
        </View>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 14, marginBottom: 8, marginHorizontal: 2 }}>
          <T size={11} w={800}>{t('twinDetail.lastPhoto')}</T>
          <T size={7} color={c.muted}>{t('twinDetail.when')}</T>
        </View>
        <Card bg={c.iceBlue} radius={15} style={{ height: 67, padding: 7, flexDirection: 'row', alignItems: 'center', gap: 9 }}>
          <WoundThumb dashed />
          <View style={{ flex: 1 }}>
            <T size={8} w={800}>{t('twinDetail.normal')}</T>
            <T size={6.5} style={{ marginTop: 3 }}>{t('twinDetail.reduced')}</T>
          </View>
          <Pressable onPress={() => navigation.navigate('WoundScan')} style={{ borderWidth: 1, borderColor: c.ink, backgroundColor: c.surface, borderRadius: 99, paddingVertical: 6, paddingHorizontal: 9 }}>
            <T size={7} w={800}>{t('twinDetail.compare')}</T>
          </Pressable>
        </Card>
        <Button icon="camera" style={{ marginTop: 14 }} onPress={() => navigation.navigate('WoundScan')}>{t('twinDetail.scanNow')}</Button>
      </View>
    </Screen>
  );
}
