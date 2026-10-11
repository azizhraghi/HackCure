import React, { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';
import { T } from '../components/T';
import { Card, haptic, IconBadge, ListRow, Screen, Switch, TopBar } from '../components/ui';
import { useAppState } from '../context/AppState';
import { setLanguage, useT, type Lang } from '../i18n';
import { useTheme } from '../theme/ThemeContext';
import { fonts } from '../theme/tokens';

function Label({ children }: { children: string }) {
  return <T size={6} w={800} spacing={0.8} style={{ marginTop: 14, marginBottom: 6, marginHorizontal: 2 }}>{children}</T>;
}

export function SettingsScreen() {
  const { c, isDark, setDark } = useTheme();
  const { t, lang } = useT();
  const { resetRole, apiUrl, setApiUrl } = useAppState();
  const [url, setUrl] = useState(apiUrl);

  const langs: [Lang, string][] = [['en', 'English'], ['fr', 'Français']];

  return (
    <Screen>
      <TopBar title={t('settings.top')} />
      <Label>{t('settings.appearance')}</Label>
      <Card radius={17}>
        <ListRow left={<IconBadge icon="moon" bg={c.lavender} />} title={t('settings.dark')} sub={t('settings.darkSub')} right={<Switch on={isDark} onToggle={() => setDark(!isDark)} />} last />
      </Card>

      <Label>{t('settings.language')}</Label>
      <Card radius={17} style={{ padding: 6, flexDirection: 'row', gap: 6 }}>
        {langs.map(([code, name]) => (
          <Pressable key={code} onPress={() => { haptic('selection'); setLanguage(code); }}
            style={{ flex: 1, height: 44, borderRadius: 12, borderWidth: lang === code ? 1.2 : 0, borderColor: c.ink, backgroundColor: lang === code ? c.primary : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
            <T size={11} w={800} color={lang === code ? '#fff' : c.text}>{name}</T>
          </Pressable>
        ))}
      </Card>

      <Label>{t('settings.server')}</Label>
      <Card radius={17} style={{ padding: 10 }}>
        <T size={7} color={c.muted} style={{ marginBottom: 6 }}>{t('settings.serverSub')}</T>
        <TextInput value={url} onChangeText={setUrl} onEndEditing={() => setApiUrl(url.trim())} autoCapitalize="none" autoCorrect={false} keyboardType="url"
          style={{ height: 44, borderWidth: 1.2, borderColor: c.ink, borderRadius: 12, paddingHorizontal: 12, color: c.text, fontFamily: fonts[600], backgroundColor: c.bg }} />
      </Card>

      <Label>{t('settings.account')}</Label>
      <Card radius={17}>
        <ListRow left={<IconBadge icon="rotate" bg={c.yellow} />} title={t('settings.switchRole')} sub={t('settings.switchRoleSub')} onPress={resetRole} last />
      </Card>

      <View style={{ marginTop: 22, alignItems: 'center', gap: 4 }}>
        <T size={8} w={800} color={c.muted}>{t('settings.about')}</T>
        <T size={7} color={c.muted} center>{t('settings.disclaimer')}</T>
      </View>
    </Screen>
  );
}
