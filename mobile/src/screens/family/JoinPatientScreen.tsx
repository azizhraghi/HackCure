import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, TextInput, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { CameraPreview } from '../../components/CameraPreview';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, haptic, Muted, PageTitle, Screen, Toggle, TopBar } from '../../components/ui';
import { useApi, useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { ApiError, type FollowedPatient } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';
import { Corners } from '../patient/WoundScanScreen';
import { useFamilyCopy } from './familyCopy';

export function JoinPatientScreen() {
  const { c } = useTheme();
  const { t, list } = useT();
  const api = useApi();
  const { session, demo, completeOnboarding, resetRole } = useAppState();
  const copy = useFamilyCopy();
  const relations = list('join.relations');
  const [relation, setRelation] = useState(relations[0]!);
  const [code, setCode] = useState('');
  const [scanning, setScanning] = useState(false);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState<FollowedPatient | null>(null);
  const input = useRef<React.ComponentRef<typeof TextInput>>(null);

  const link = async (value: string) => {
    setLinking(true);
    setError(null);
    try {
      // WhatsApp alerts only if the account has a number (the API refuses opt-in otherwise)
      setJoined(await api.linkPatient(value, relation, !!session?.user.whatsapp_number));
      haptic('notificationSuccess');
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        // Already linked: just show the patient
        setJoined((await api.followedPatients())[0] ?? null);
      } else {
        setError(e instanceof ApiError && e.status !== 0 ? e.message : t('auth.network'));
      }
    } finally {
      setLinking(false);
    }
  };

  useEffect(() => {
    if (code.length === 6 && !joined && !linking) link(code);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  const onQr = (value: string) => {
    const match = value.replace(/\D/g, '').match(/\d{6}/);
    if (match) {
      haptic('notificationSuccess');
      setCode(match[0]);
      setScanning(false);
    }
  };

  if (demo) return <Screen><TopBar title={copy.space} onBack={resetRole} /><PageTitle>{copy.demo}</PageTitle><Muted>{copy.demoIntro}</Muted><Button onPress={completeOnboarding} style={{marginTop:20}}>{copy.openDemo} →</Button></Screen>;

  const wrong = !!error;

  return (
    <Screen>
      <TopBar title={t('join.top')} onBack={resetRole} />
      <View style={{ alignItems: 'center' }}>
        <View style={{ width: 56, height: 56, marginTop: 4, borderRadius: 17, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.lavender, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="scan" size={30} />
        </View>
        <PageTitle center style={{ marginTop: 10 }}>{t('join.title')}</PageTitle>
        <Muted center>{t('join.sub')}</Muted>
      </View>

      <Pressable onPress={() => { haptic(); setScanning(s => !s); }}
        style={{ height: 205, borderWidth: 1.5, borderStyle: 'dashed', borderColor: c.ink, borderRadius: 22, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        {scanning ? (
          <>
            <CameraPreview onQr={onQr} fallback={<View style={{ flex: 1, backgroundColor: '#273748' }} />} permissionLabel={t('join.permission')} />
            <Corners color="#1e88e5" size={30} width={150} height={150} />
            <View style={{ position: 'absolute', bottom: 10, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 99, backgroundColor: 'rgba(27,42,74,0.86)' }}>
              <T size={8} w={800} color="#fff">{t('join.scanning')}</T>
            </View>
          </>
        ) : (
          <>
            <View style={{ width: 104, height: 104, borderRadius: 15, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' }}>
              <View style={{ position: 'absolute', top: 8, left: 8 }}><Corners color="#1e88e5" size={26} width={88} height={88} /></View>
              <Icon name="camera" size={25} color="#1b2a4a" />
            </View>
            <T size={11} w={800} style={{ marginTop: 9 }}>{t('join.scan')}</T>
            <T size={7} color={c.muted} style={{ marginTop: 3 }}>{t('join.scanSub')}</T>
          </>
        )}
      </Pressable>

      <T size={7} w={800} spacing={0.8} style={{ marginTop: 14, marginBottom: 6 }}>{t('join.relation')}</T>
      <Toggle options={relations} value={relation} onChange={setRelation} />

      <View style={{ height: 37, flexDirection: 'row', alignItems: 'center', gap: 7 }}>
        <View style={{ flex: 1, borderTopWidth: 1, borderColor: '#ccd3de' }} />
        <T size={6.5} color={c.muted}>{t('join.or')}</T>
        <View style={{ flex: 1, borderTopWidth: 1, borderColor: '#ccd3de' }} />
      </View>

      <Pressable onPress={() => input.current?.focus()} style={{ flexDirection: 'row', gap: 6 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <View key={i} style={{ flex: 1, height: 47, borderWidth: code.length === i ? 2 : 1.3, borderColor: wrong ? c.urgent : code.length === i ? c.primary : c.ink, borderRadius: 11, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}>
            <T size={16} w={800}>{code[i] ?? ''}</T>
          </View>
        ))}
      </Pressable>
      <TextInput ref={input} value={code} editable={!joined && !linking}
        onChangeText={v => { setError(null); setCode(v.replace(/\D/g, '').slice(0, 6)); }} keyboardType="number-pad" maxLength={6}
        style={{ position: 'absolute', opacity: 0, height: 1, width: 1 }} />
      {linking && <ActivityIndicator color={c.primary} style={{ marginTop: 10 }} />}
      {wrong && <T size={8} w={700} color={c.urgentText} style={{ marginTop: 6 }}>{error}</T>}

      {joined && (
        <Animated.View entering={FadeInDown} style={{ minHeight: 96, marginTop: 12, borderWidth: 1.4, borderColor: c.ink, borderRadius: 18, backgroundColor: c.green, padding: 11, flexDirection: 'row', gap: 10 }}>
          <View style={{ width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}><Icon name="check" size={22} /></View>
          <View style={{ flex: 1 }}>
            <T size={5.5} spacing={0.7}>{t('join.connected')}</T>
            <T size={10} w={800} style={{ marginVertical: 3 }}>{t('join.following', { name: joined.full_name })}</T>
            <T size={6.5} lh={1.4}>{t('join.followingSub')}</T>
          </View>
        </Animated.View>
      )}
      <Button style={{ marginTop: 12, opacity: joined ? 1 : 0.5 }} onPress={() => (joined ? completeOnboarding() : input.current?.focus())}>{t('join.go')}  →</Button>
    </Screen>
  );
}
