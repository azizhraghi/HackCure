import React from 'react';
import { Pressable, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { Brand } from '../../components/Brand';
import { BodyFigure } from '../../components/figures';
import { T } from '../../components/T';
import { Button, Muted, Screen } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

export function WelcomeScreen({ navigation }: RootScreen<'Welcome'>) {
  const { c } = useTheme();
  const { t } = useT();
  const { completeOnboarding } = useAppState();
  return (
    <Screen style={{ paddingHorizontal: 24, paddingTop: 12 }}>
      <Brand />
      <LinearGradient colors={['#dff7f2', '#bde8fb', '#d8cbf8']} locations={[0, 0.56, 1]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
        style={{ height: 328, marginTop: 13, borderWidth: 1.5, borderColor: c.ink, borderRadius: 28, overflow: 'hidden', alignItems: 'center' }}>
        <View style={{ position: 'absolute', width: 280, height: 280, top: 15, borderRadius: 140, borderWidth: 1, borderColor: 'rgba(27,42,74,0.16)', backgroundColor: 'rgba(255,255,255,0.2)' }} />
        <View style={{ position: 'absolute', width: 210, height: 210, top: 50, borderRadius: 105, borderWidth: 1, borderColor: 'rgba(27,42,74,0.16)', backgroundColor: 'rgba(255,255,255,0.2)' }} />
        <View style={{ position: 'absolute', width: 260, height: 45, bottom: -20, borderRadius: 130, backgroundColor: 'rgba(255,255,255,0.48)' }} />
        <View style={{ marginTop: 15 }}><BodyFigure /></View>
        <View style={{ position: 'absolute', right: 16, top: 197, flexDirection: 'row', alignItems: 'center' }}>
          <View style={{ width: 40, borderTopWidth: 1, borderColor: '#1b2a4a' }} />
          <View style={{ backgroundColor: '#fff', borderWidth: 1.3, borderColor: '#1b2a4a', borderRadius: 12, paddingVertical: 8, paddingHorizontal: 10, flexDirection: 'row', alignItems: 'center', gap: 5 }}>
            <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: '#ff715e' }} />
            <T size={8} w={800} color="#1b2a4a">{t('welcome.siteLabel')}</T>
          </View>
        </View>
      </LinearGradient>
      <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 22, marginBottom: 8 }}>{t('welcome.eyebrow')}</T>
      <T size={31} w={800} spacing={-1.4} color={c.title} style={{ lineHeight: 34 }}>
        {t('welcome.t1')}{'\n'}{t('welcome.t2')}{'\n'}<T size={31} w={800} color={c.primary}>{t('welcome.t3')}</T>
      </T>
      <Muted style={{ marginTop: 11, marginBottom: 16, width: '92%' }}>{t('welcome.lead')}</Muted>
      <Button onPress={() => navigation.navigate('Upload')}>{t('welcome.start')}  →</Button>
      <Pressable onPress={completeOnboarding} style={{ marginTop: 18, alignSelf: 'center' }}>
        <T size={12} w={700} style={{ textDecorationLine: 'underline' }}>{t('welcome.account')}</T>
      </Pressable>
    </Screen>
  );
}
