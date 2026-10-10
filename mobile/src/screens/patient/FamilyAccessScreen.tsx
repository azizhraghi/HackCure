import React, { useState } from 'react';
import { Pressable, Share, View } from 'react-native';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Card, haptic, SectionRow, Screen, Switch, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

/** Stylised QR code (.qr-code) */
function QrMark() {
  const { c } = useTheme();
  const hollow = [1, 3, 7];
  return (
    <View style={{ width: 91, height: 113, backgroundColor: '#fff', borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, padding: 8, flexDirection: 'row', flexWrap: 'wrap', gap: 4 }}>
      {Array.from({ length: 9 }).map((_, i) => (
        <View key={i} style={{ width: 22, height: 28, borderRadius: 2, backgroundColor: hollow.includes(i) ? '#fff' : '#1b2a4a', borderWidth: hollow.includes(i) ? 2 : 0, borderColor: '#1b2a4a' }} />
      ))}
    </View>
  );
}

export function FamilyAccessScreen() {
  const { c } = useTheme();
  const { t, list } = useT();
  const [sharing, setSharing] = useState([true, true, true, true, true]);
  const [members, setMembers] = useState([
    { name: 'Ahmed Khan', rel: 'partner', bg: c.sky },
    { name: 'Emma Lee', rel: 'sister', bg: c.pink },
  ]);
  const icons: IconName[] = ['sensor', 'camera', 'checkin', 'pill', 'activity'];
  const items = list('access.items');

  return (
    <Screen>
      <TopBar title={t('access.top')} />
      <Card bg={c.sky} radius={20} style={{ padding: 11 }}>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1, justifyContent: 'space-between' }}>
            <View>
              <T size={6} spacing={0.8}>{t('access.secure')}</T>
              <T size={13} w={800} style={{ marginVertical: 5 }}>{t('access.invite')}</T>
              <T size={6.5} color={c.muted}>{t('access.expires')}</T>
            </View>
            <View>
              <T size={5.5} spacing={0.7}>{t('access.code')}</T>
              <T size={19} w={800} spacing={3} style={{ marginTop: 2 }}>482 916</T>
            </View>
          </View>
          <QrMark />
        </View>
        <Pressable onPress={() => { haptic(); Share.share({ message: t('access.shareMsg') }); }}
          style={({ pressed }) => ({ height: 35, marginTop: 8, borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, backgroundColor: c.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: pressed ? 0.7 : 1 })}>
          <Icon name="upload" size={15} /><T size={8} w={800}>{t('access.share')}</T>
        </Pressable>
      </Card>

      <SectionRow title={t('access.linked')} right={t('access.people', { n: members.length })} style={{ marginTop: 12, marginBottom: 6 }} />
      <Card radius={15}>
        {members.map((m, i) => (
          <View key={m.name} style={{ height: 48, paddingHorizontal: 8, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i < members.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
            <Avatar initials={m.name.split(' ').map(x => x[0]).join('')} size={31} bg={m.bg} />
            <View style={{ flex: 1 }}><T size={8} w={800}>{m.name}</T><T size={6} color={c.muted} style={{ marginTop: 2 }}>{t(`people.${m.rel}`)} · {t('access.viewOnly')}</T></View>
            <Pressable onPress={() => { haptic(); setMembers(v => v.filter(x => x.name !== m.name)); }} style={{ borderWidth: 1, borderColor: c.ink, borderRadius: 99, paddingVertical: 4, paddingHorizontal: 8 }}>
              <T size={6} w={800}>{t('common.remove')}</T>
            </Pressable>
          </View>
        ))}
      </Card>

      <SectionRow title={t('access.see')} kicker={undefined} right={<T size={7} color={c.muted}>{t('access.anytime')}</T>} style={{ marginTop: 12, marginBottom: 6 }} />
      <Card radius={15}>
        {items.map((title, i) => (
          <View key={title} style={{ height: 50, paddingHorizontal: 8, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i < items.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 27, borderRadius: 8, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name={icons[i]} size={15} /></View>
            <View style={{ flex: 1 }}><T size={8} w={800}>{title}</T><T size={6} color={c.muted} style={{ marginTop: 2 }}>{sharing[i] ? t('access.canSee') : t('access.hidden')}</T></View>
            <Switch on={sharing[i]} onToggle={() => setSharing(v => v.map((x, n) => (n === i ? !x : x)))} scale={0.9} />
          </View>
        ))}
      </Card>
    </Screen>
  );
}
