import React, { useState } from 'react';
import { Pressable, Share, View } from 'react-native';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, Card, haptic, SectionRow, Screen, Switch, TopBar } from '../../components/ui';
import { useMyProfile } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { initials } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';
import { useAppState } from '../../context/AppState';
import { getSharing, updateSharing, usePoll } from '../../services/api';

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
  const { apiUrl } = useAppState();
  const { data, refresh } = usePoll(getSharing, 15000);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { data: profile } = useMyProfile();
  const members = data ?? [];
  const selected = members.find(m => m.id === selectedId) ?? members[0];
  const code = profile?.link_code ?? '······';
  const tones = [c.sky, c.pink, c.yellow, c.lavender];
  const icons: IconName[] = ['sensor', 'camera', 'checkin', 'pill', 'activity', 'bell', 'calendar'];
  const categories = ['vitals', 'wound', 'symptoms', 'medications', 'rehab', 'alerts', 'appointments'];
  const items = [...list('access.items'), 'Care-team alerts', 'Appointments'];
  const toggle = async (category: string) => {
    if (!selected || busy) return;
    setBusy(true); setError(null);
    try { await updateSharing(apiUrl, selected, category); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

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
              <T size={19} w={800} spacing={3} style={{ marginTop: 2 }}>{`${code.slice(0, 3)} ${code.slice(3)}`}</T>
            </View>
          </View>
          <QrMark />
        </View>
        <Pressable onPress={() => { haptic(); if (profile) Share.share({ message: t('access.shareMsg', { code: profile.link_code }) }); }}
          style={({ pressed }) => ({ height: 35, marginTop: 8, borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, backgroundColor: c.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: pressed ? 0.7 : 1 })}>
          <Icon name="upload" size={15} /><T size={8} w={800}>{t('access.share')}</T>
        </Pressable>
      </Card>

      <SectionRow title={t('access.linked')} right={t('access.people', { n: members.length })} style={{ marginTop: 12, marginBottom: 6 }} />
      <Card radius={15}>
        {members.length === 0 && <T size={8} color={c.muted} style={{ padding: 10 }}>{t('access.none')}</T>}
        {members.map((m, i) => (
          <Pressable key={m.id} onPress={() => setSelectedId(m.id)} style={{ height: 48, paddingHorizontal: 8, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i < members.length - 1 ? 1 : 0, borderBottomColor: c.line, backgroundColor: m.id === selected?.id ? c.ice : c.surface }}>
            <Avatar initials={initials(m.name)} size={31} bg={tones[i % tones.length]} />
            <View style={{ flex: 1 }}>
              <T size={8} w={800}>{m.name}</T>
              <T size={6} color={c.muted} style={{ marginTop: 2 }}>{m.relation} · {m.id === selected?.id ? 'Selected' : 'Tap to manage sharing'}</T>
            </View>
          </Pressable>
        ))}
      </Card>

      <SectionRow title={t('access.see')} kicker={undefined} right={<T size={7} color={c.muted}>{t('access.anytime')}</T>} style={{ marginTop: 12, marginBottom: 6 }} />
      <Card radius={15}>
        {selected && <T size={8} style={{ padding: 10 }}>Sharing with {selected.name}</T>}
        {error && <T size={8} color={c.urgentText} style={{ padding: 10 }}>{error}</T>}
        {items.map((title, i) => (
          <View key={title} style={{ height: 50, paddingHorizontal: 8, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i < items.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 27, borderRadius: 8, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name={icons[i]} size={15} /></View>
            <View style={{ flex: 1 }}><T size={8} w={800}>{title}</T><T size={6} color={c.muted} style={{ marginTop: 2 }}>{selected?.categories[categories[i]] ? t('access.canSee') : t('access.hidden')}</T></View>
            <Switch on={!!selected?.categories[categories[i]]} onToggle={() => toggle(categories[i])} scale={0.9} />
          </View>
        ))}
      </Card>
    </Screen>
  );
}
