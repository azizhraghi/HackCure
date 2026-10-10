import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { Brand } from '../../components/Brand';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, haptic, Muted, PageTitle, Screen } from '../../components/ui';
import { useAppState, type Role } from '../../context/AppState';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';

function Person({ heart }: { heart?: boolean }) {
  const { c } = useTheme();
  return (
    <View style={{ width: 88, height: 112, borderWidth: 1.3, borderColor: c.ink, borderTopLeftRadius: 44, borderTopRightRadius: 44, borderBottomLeftRadius: 18, borderBottomRightRadius: 18, backgroundColor: 'rgba(255,255,255,0.48)', overflow: 'hidden' }}>
      <View style={{ position: 'absolute', width: 60, height: 68, left: 13, top: 50, borderWidth: 1.5, borderColor: '#1b2a4a', borderTopLeftRadius: 28, borderTopRightRadius: 28, borderBottomLeftRadius: 4, borderBottomRightRadius: 4, backgroundColor: heart ? '#f7faff' : '#fff' }} />
      <View style={{ position: 'absolute', width: 34, height: 38, left: 26, top: 15, borderWidth: 1.5, borderColor: '#1b2a4a', borderRadius: 20, backgroundColor: '#f0c7ad' }} />
      <View style={{ position: 'absolute', top: 70, left: 0, right: 0, alignItems: 'center' }}>
        {heart ? <Icon name="heart" size={22} color="#ff6b6b" strokeWidth={2.4} /> : <Icon name="activity" size={24} color="#1b2a4a" strokeWidth={2} />}
      </View>
    </View>
  );
}

function RoleCard({ selected, onPress, bg, title, sub, heart }: { selected: boolean; onPress: () => void; bg: string; title: string; sub: string; heart?: boolean }) {
  const { c } = useTheme();
  return (
    <Pressable onPress={() => { haptic('selection'); onPress(); }}
      style={{ height: 156, marginTop: 12, borderWidth: selected ? 2.5 : 1.5, borderColor: selected ? c.primary : c.ink, borderRadius: 23, padding: 16, backgroundColor: bg, flexDirection: 'row', alignItems: 'center', gap: 14 }}>
      <Person heart={heart} />
      <View style={{ flex: 1 }}>
        <T size={14} w={800} lh={1.35}>{title}</T>
        <T size={8} color={c.muted} style={{ marginTop: 7 }}>{sub}</T>
      </View>
      <T size={19} w={800}>→</T>
      <View style={{ position: 'absolute', top: 11, right: 12, width: 24, height: 24, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: selected ? c.primary : 'rgba(255,255,255,0.6)', alignItems: 'center', justifyContent: 'center' }}>
        {selected && <Icon name="check" size={15} color="#fff" />}
      </View>
    </Pressable>
  );
}

export function RoleSelectionScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const { setRole } = useAppState();
  const [role, setLocal] = useState<Role>('patient');
  return (
    <Screen style={{ paddingHorizontal: 23, paddingTop: 13 }}>
      <Brand />
      <View style={{ height: 50 }} />
      <T size={9} w={800} spacing={1.7} color={c.primary}>{t('role.kicker')}</T>
      <PageTitle size={34} style={{ marginTop: 6 }}>{t('role.title')}</PageTitle>
      <Muted>{t('role.sub')}</Muted>
      <RoleCard selected={role === 'patient'} onPress={() => setLocal('patient')} bg={c.sky} title={t('role.patient')} sub={t('role.patientSub')} heart />
      <RoleCard selected={role === 'family'} onPress={() => setLocal('family')} bg={c.lavender} title={t('role.family')} sub={t('role.familySub')} />
      <View style={{ flexDirection: 'row', gap: 9, alignItems: 'center', marginVertical: 17, marginHorizontal: 7 }}>
        <Icon name="shield" size={16} color={c.trackText} />
        <View>
          <T size={8} w={800}>{t('role.privateTitle')}</T>
          <T size={7} color={c.muted} style={{ marginTop: 2 }}>{t('role.privateSub')}</T>
        </View>
      </View>
      <Button onPress={() => setRole(role)}>{t('common.continue')}  →</Button>
    </Screen>
  );
}
