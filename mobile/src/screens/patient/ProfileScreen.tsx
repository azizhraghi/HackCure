import React from 'react';
import { Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { T } from '../../components/T';
import { Avatar, Button, Card, Chip, IconBadge, ListRow, RoundButton, Screen, TopBar, toneColor } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useMyProfile } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { initials } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';

export function ProfileScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const { session, resetRole } = useAppState();
  const { data: profile } = useMyProfile();
  const name = session ? `${session.user.first_name} ${session.user.last_name}` : '';
  const family = profile?.family_members ?? [];
  const tones = ['sky', 'pink', 'yellow', 'lavender'] as const;

  return (
    <Screen>
      <TopBar title={t('profile.top')} back={false} action={<RoundButton icon="gear" onPress={() => nav.navigate('Settings')} />} />
      <Pressable accessibilityRole="button" accessibilityLabel={`${t('settings.switchRole')} — ${t('settings.switchRoleSub')}`} onPress={resetRole}
        style={{ paddingVertical:10, paddingHorizontal:12, borderWidth:1, borderColor:c.ink, borderRadius:12, backgroundColor:c.surface, flexDirection:'row', alignItems:'center', justifyContent:'space-between', gap:8 }}>
        <T size={10} w={700}>{t('settings.switchRole')}</T>
        <T size={8} color={c.muted}>{t('settings.switchRoleSub')} ↗</T>
      </Pressable>
      <View style={{ height: 78, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(name)} size={50} />
        <View style={{ flex: 1 }}>
          <T size={15} w={800}>{name}</T>
          <T size={8} color={c.muted} style={{ marginTop: 3 }}>{t('profile.dayOf')}</T>
        </View>
        <Pressable onPress={() => nav.navigate('Settings')} style={{ borderWidth: 1, borderColor: c.ink, backgroundColor: c.surface, borderRadius: 99, paddingVertical: 7, paddingHorizontal: 11 }}>
          <T size={8} w={800}>{t('common.edit')}</T>
        </Pressable>
      </View>

      <Card bg={c.ice} radius={21} style={{ padding: 11, marginBottom: 10 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <View><T size={6} spacing={1}>{t('profile.circle')}</T><T size={12} w={800} style={{ marginTop: 2 }}>{t('profile.caregivers')}</T></View>
          <Pressable onPress={() => nav.navigate('FamilyAccess')} style={{ borderWidth: 1, borderColor: c.ink, borderRadius: 99, backgroundColor: c.primary, paddingVertical: 7, paddingHorizontal: 11 }}>
            <T size={8} w={800} color="#fff">{t('profile.invite')}</T>
          </Pressable>
        </View>
        {family.length === 0 && <T size={8} color={c.muted} style={{ paddingVertical: 8 }}>{t('access.none')}</T>}
        {family.map((m, i) => (
          <View key={m.family_member_id} style={{ minHeight: 47, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: 1, borderBottomColor: c.lineSoft }}>
            <Avatar initials={initials(m.full_name)} size={31} bg={toneColor(c, tones[i % tones.length])} />
            <View style={{ flex: 1 }}><T size={8.5} w={800}>{m.full_name}</T><T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{m.relationship}</T></View>
            <Chip tone={m.is_primary_contact ? 'blue' : 'pink'}>{m.is_primary_contact ? t('access.primary') : t('people.family')}</Chip>
          </View>
        ))}
        <Pressable onPress={() => nav.navigate('FamilyAccess')} style={{ minHeight: 46, marginTop: 8, borderWidth: 1, borderStyle: 'dashed', borderColor: c.ink, backgroundColor: c.surface, borderRadius: 12, flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 8, paddingVertical: 5 }}>
          <T size={22}>▦</T>
          <View style={{ flex: 1 }}><T size={8} w={800}>{t('profile.shareTitle')}</T><T size={6} color={c.muted} style={{ marginTop: 2 }}>{t('profile.shareSub')}</T></View>
          <T w={800}>›</T>
        </Pressable>
      </Card>

      <Card bg={c.mint} radius={21} style={{ padding: 11, marginBottom: 10 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View><T size={6} spacing={1}>{t('profile.assigned')}</T><T size={12} w={800} style={{ marginTop: 2 }}>{t('profile.team')}</T></View>
          <Chip tone="green">{t('profile.connected')}</Chip>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 8, marginBottom: 10 }}>
          <Avatar initials="ER" portrait size={39} />
          <View>
            <T size={10} w={800}>Dr. Elena Ruiz</T>
            <T size={7} style={{ marginTop: 2 }}>{t('people.surgeon')}</T>
            <T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{t('people.hospital')}</T>
          </View>
        </View>
        <Button secondary icon="message" flat height={38} size={11} onPress={() => nav.navigate('AIAssistant')}>{t('profile.messageTeam')}</Button>
      </Card>

      <Card radius={17}>
        <ListRow left={<IconBadge icon="shield" border={false} />} title={t('profile.privacy')} onPress={() => nav.navigate('Consent')} />
        <ListRow left={<IconBadge icon="profile" border={false} bg={c.lavender} />} title={t('access.top')} onPress={() => nav.navigate('FamilyAccess')} />
        <ListRow left={<IconBadge icon="gear" border={false} bg={c.yellow} />} title={t('profile.settings')} onPress={() => nav.navigate('Settings')} last />
      </Card>
    </Screen>
  );
}
