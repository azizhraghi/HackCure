import React, { useState } from 'react';
import { View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { T } from '../../components/T';
import { Avatar, Button, Card, IconBadge, ListRow, RoundButton, Screen, Switch, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useFollowedPatient } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { initials } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';

export function FamilyProfileScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const { resetRole, session } = useAppState();
  const { patient } = useFollowedPatient();
  const name = session ? `${session.user.first_name} ${session.user.last_name}` : '';
  const [toggles, setToggles] = useState([true, true, true, true]);
  const rows: [string, string][] = [[t('famProfile.n1'), t('famProfile.n1s')], [t('famProfile.n2'), t('famProfile.n2s')], [t('famProfile.n3'), t('famProfile.n3s')], [t('famProfile.n4'), t('famProfile.n4s')]];
  const icons = ['checkin', 'profile', 'bell', 'calendar'] as const;

  return (
    <Screen>
      <TopBar title={t('famProfile.top')} back={false} action={<RoundButton icon="gear" onPress={() => nav.navigate('Settings')} />} />
      <View style={{ height: 78, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(name)} size={50} bg={c.sky} />
        <View style={{ flex: 1 }}>
          <T size={15} w={800}>{name}</T>
          <T size={8} color={c.muted} style={{ marginTop: 3 }}>{patient ? `${t('people.caregiver')} · ${patient.relationship}` : t('people.caregiver')}</T>
        </View>
      </View>

      <Card bg={c.ice} radius={19} style={{ padding: 11, flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Avatar initials={initials(patient?.full_name ?? '?')} size={41} />
        <View style={{ flex: 1 }}>
          <T size={6} spacing={1}>{t('famProfile.following')}</T>
          <T size={11} w={800} style={{ marginTop: 2 }}>{patient?.full_name ?? t('fam.noPatient')}</T>
          <T size={7} color={c.muted} style={{ marginTop: 2 }}>{patient?.is_primary_contact ? t('access.primary') : ''}{patient?.whatsapp_opt_in ? ' · WhatsApp' : ''}</T>
        </View>
      </Card>

      <T size={6} w={800} spacing={0.8} style={{ marginTop: 14, marginBottom: 6, marginHorizontal: 2 }}>{t('famProfile.notif')}</T>
      <Card radius={17}>
        {rows.map(([title, sub], i) => (
          <ListRow key={title} left={<IconBadge icon={icons[i]} />} title={title} sub={sub} last={i === rows.length - 1}
            right={<Switch on={toggles[i]} onToggle={() => setToggles(v => v.map((x, n) => (n === i ? !x : x)))} />} />
        ))}
      </Card>

      <Card radius={17} style={{ marginTop: 10 }}>
        <ListRow left={<IconBadge icon="gear" bg={c.yellow} />} title={t('profile.settings')} onPress={() => nav.navigate('Settings')} last />
      </Card>
      <Button secondary style={{ marginTop: 14 }} onPress={resetRole}>{t('famProfile.leave')}</Button>
    </Screen>
  );
}
