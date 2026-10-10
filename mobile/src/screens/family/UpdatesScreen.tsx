import React from 'react';
import { Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Muted, PageTitle, RoundButton, Screen, SectionRow, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { LockTone } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function UpdatesScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const nav = useNavigation();
  const toneBg = { track: c.green, review: '#ffe1b8', urgent: '#ffd3d3', private: c.grey };
  const updates: [string, IconName, keyof typeof toneBg, string, (() => void) | null][] = [
    ['10:18 AM', 'check', 'track', t('updates.u1'), () => nav.navigate('FamilyInfo')],
    ['9:42 AM', 'camera', 'review', t('updates.u2'), () => nav.navigate('FamilyAttention')],
    ['9:40 AM', 'thermo', 'review', t('updates.u3'), () => nav.navigate('FamilyAttention')],
    ['8:15 AM', 'activity', 'track', t('updates.u4'), null],
    ['7:30 AM', 'bell', 'urgent', t('updates.u5'), () => nav.navigate('FamilyAttention')],
    [t('updates.yesterday'), 'file', 'private', t('updates.u6'), null],
  ];
  const previews: [LockTone, string, string][] = [['info', t('lock.info'), c.sky], ['attention', t('lock.attention'), c.review], ['urgent', t('lock.urgent'), c.urgent]];

  return (
    <Screen>
      <TopBar title={t('updates.top')} back={false} action={<RoundButton icon="bell" onPress={() => nav.navigate('LockPreview', { tone: 'attention' })} />} />
      <PageTitle size={26}>{t('updates.title')}</PageTitle>
      <Muted>{t('updates.sub')}</Muted>
      <Card radius={19}>
        {updates.map(([time, icon, tone, text, onPress], i) => (
          <Pressable key={text} disabled={!onPress} onPress={onPress ?? undefined}
            style={({ pressed }) => ({ minHeight: 76, flexDirection: 'row', alignItems: 'center', padding: 9, borderBottomWidth: i < updates.length - 1 ? 1 : 0, borderBottomColor: c.line, opacity: pressed ? 0.7 : 1 })}>
            <T size={6.5} color={c.muted} style={{ width: 56 }}>{time}</T>
            <View style={{ width: 31, height: 31, marginRight: 10, borderRadius: 9, borderWidth: 1, borderColor: c.ink, backgroundColor: toneBg[tone], alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={icon} size={17} color={tone === 'private' ? '#7b8799' : '#1b2a4a'} />
            </View>
            <T size={8.5} w={700} lh={1.45} color={tone === 'private' ? c.muted : c.text} style={{ flex: 1, fontStyle: tone === 'private' ? 'italic' : 'normal' }}>{text}</T>
            {onPress && <T w={800}>›</T>}
          </Pressable>
        ))}
      </Card>

      <SectionRow title={t('updates.previewsSub')} kicker={t('updates.previews')} />
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {previews.map(([tone, label, bg]) => (
          <Pressable key={tone} style={{ flex: 1 }} onPress={() => nav.navigate('LockPreview', { tone })}>
            <Card bg={bg} radius={15} style={{ height: 70, padding: 10, justifyContent: 'space-between' }}>
              <Icon name={tone === 'info' ? 'check' : 'bell'} size={18} color="#1b2a4a" />
              <T size={8.5} w={800} color="#1b2a4a">{label}</T>
            </Card>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}
