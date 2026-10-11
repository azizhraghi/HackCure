import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Button, Card, Chip, haptic, Muted, PageTitle, Screen, Switch, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function ConsentScreen({ navigation }: RootScreen<'Consent'>) {
  const { c } = useTheme();
  const { t } = useT();
  const [enabled, setEnabled] = useState([true, true, true, false]);
  const [saved, setSaved] = useState(false);
  const items: [IconName, string, string, string][] = [
    ['camera', t('consent.i1'), t('consent.i1s'), c.sky],
    ['sensor', t('consent.i2'), t('consent.i2s'), c.green],
    ['checkin', t('consent.i3'), t('consent.i3s'), c.yellow],
    ['activity', t('consent.i4'), t('consent.i4s'), c.lavender],
  ];
  return (
    <Screen>
      <TopBar title={t('consent.top')} />
      <View style={{ width: 187, height: 88, alignSelf: 'center', marginTop: 16, marginBottom: 7, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View style={{ position: 'absolute', left: 47, right: 47, borderTopWidth: 2, borderStyle: 'dashed', borderColor: '#8ca1b7' }} />
        <Avatar initials="SM" size={55} />
        <Avatar initials="ER" size={55} portrait />
        <View style={{ position: 'absolute', left: 75, top: 23, width: 38, height: 42, alignItems: 'center', justifyContent: 'center' }}>
          <View style={{ position: 'absolute', width: 34, height: 38, borderRadius: 10, backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center', borderBottomLeftRadius: 17, borderBottomRightRadius: 17 }}>
            <Icon name="check" size={19} color="#fff" />
          </View>
        </View>
      </View>
      <PageTitle center>{t('consent.title')}</PageTitle>
      <Muted center style={{ paddingHorizontal: 17 }}>{t('consent.intro')}</Muted>
      <Card bg={c.mint} radius={16} style={{ height: 61, padding: 8, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <Avatar initials="ER" size={39} portrait />
        <View style={{ flex: 1 }}><T size={8.5} w={800}>Dr. Elena Ruiz</T><T size={6} style={{ marginTop: 2 }}>{t('consent.specialty')}</T></View>
        <Chip tone="green">{t('consent.verified')}</Chip>
      </Card>
      <Card radius={18} style={{ marginTop: 10 }}>
        {items.map(([icon, title, sub, bg], i) => (
          <View key={title} style={{ minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 6, paddingHorizontal: 10, borderBottomWidth: i < 3 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 30, height: 30, borderRadius: 9, borderWidth: 1, borderColor: c.ink, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}><Icon name={icon} size={18} /></View>
            <View style={{ flex: 1 }}><T size={8.5} w={800}>{title}</T><T size={6} color={c.muted} style={{ marginTop: 3 }}>{sub}</T></View>
            <Switch on={enabled[i]} onToggle={() => setEnabled(v => v.map((x, n) => (n === i ? !x : x)))} />
          </View>
        ))}
      </Card>
      <View style={{ marginVertical: 11, marginHorizontal: 5, flexDirection: 'row', gap: 7, alignItems: 'center' }}>
        <Icon name="check" size={15} color={c.trackText} />
        <T size={6.5} color={c.muted} style={{ flex: 1 }}>{t('consent.foot')}</T>
      </View>
      <Button onPress={() => { haptic('notificationSuccess'); setSaved(true); setTimeout(() => navigation.goBack(), 800); }}>{saved ? t('consent.saved') : t('consent.confirm')}</Button>
      <Pressable onPress={() => navigation.goBack()} style={{ alignSelf: 'center', marginTop: 18 }}>
        <T size={12} w={700} style={{ textDecorationLine: 'underline' }}>{t('common.notNow')}</T>
      </Pressable>
    </Screen>
  );
}
