import React, { useState } from 'react';
import { ActivityIndicator, Linking, Pressable, TextInput, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { T } from '../../components/T';
import { Button, Card, haptic, IconBadge, Muted, PageTitle, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { answerRequest, getRequests, usePoll, type AnswerBody, type PatientRequest } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { fonts, fs } from '../../theme/tokens';

/** Questions, photo and measurement requests sent by the care-team agents (polled from the backend). */
export function RequestsScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const { data, online, refresh } = usePoll(getRequests, 3000);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [urgent, setUrgent] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});

  const send = async (r: PatientRequest, body: AnswerBody) => {
    haptic('selection');
    setBusyId(r.id);
    try {
      const res = await answerRequest(apiUrl, r.id, body);
      if (res.status === 'urgent') setUrgent(res.message || t('checkin.emergency'));
      else haptic('notificationSuccess');
    } catch {
      // stays in the list; the next poll shows the real state
    } finally {
      setBusyId(null);
      refresh();
    }
  };

  const requests = data ?? [];
  return (
    <Screen>
      <TopBar title={t('req.top')} />
      <PageTitle style={{ marginTop: 6 }}>{t('req.title')}</PageTitle>
      <Muted>{t('req.sub')}</Muted>

      {urgent && (
        <Pressable onPress={() => Linking.openURL('tel:112')}>
          <Card bg={c.urgent} radius={16} style={{ padding: 12, marginTop: 12, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
            <IconBadge icon="phone" bg="#fff" size={32} />
            <T size={9} w={800} color="#1b2a4a" lh={1.4} style={{ flex: 1 }}>{urgent}</T>
          </Card>
        </Pressable>
      )}

      {online === false && <Card bg={c.peach} radius={14} style={{ padding: 10, marginTop: 10 }}><T size={8.5}>{t('req.offline')}</T></Card>}
      {online && requests.length === 0 && !urgent && (
        <Animated.View entering={FadeIn}>
          <Card bg={c.green} radius={16} style={{ padding: 14, marginTop: 12 }}><T size={9.5} w={800}>✓ {t('req.none')}</T></Card>
        </Animated.View>
      )}
      {online === null && <ActivityIndicator style={{ marginTop: 20 }} />}

      {requests.map(r => (
        <Animated.View key={r.id} entering={FadeIn}>
          <Card bg={r.kind === 'photo' ? c.sky : c.lavender} radius={18} style={{ padding: 12, marginTop: 12 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <IconBadge icon={r.kind === 'photo' ? 'camera' : r.kind === 'measurement' ? 'sensor' : 'message'} bg={c.surface} size={28} />
              <T size={7} w={800} spacing={0.8} color={c.muted} style={{ flex: 1 }}>{t(`req.kind_${r.kind}`)}</T>
              {busyId === r.id && <ActivityIndicator size="small" />}
            </View>
            <T size={10.5} w={800} lh={1.4} style={{ marginTop: 8 }}>{r.prompt}</T>
            {!!r.reason && <T size={7.5} color={c.muted} style={{ marginTop: 3 }}>{r.reason}</T>}

            {r.kind === 'question' && r.options.map((o, i) => (
              <Pressable key={o} disabled={!!busyId} onPress={() => send(r, { option_index: i })}
                style={{ marginTop: 7, padding: 10, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.surface }}>
                <T size={9} w={700}>{o}</T>
              </Pressable>
            ))}

            {r.kind === 'photo' && (
              <Button style={{ marginTop: 10 }} height={44} size={11} icon="camera" onPress={busyId ? undefined : () => send(r, { photo_asset: 'day3' })}>
                {t('req.sendPhoto')}
              </Button>
            )}

            {r.kind === 'measurement' && (
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 10 }}>
                <TextInput keyboardType="decimal-pad" placeholder={r.metric ?? ''} placeholderTextColor={c.muted}
                  value={values[r.id] ?? ''} onChangeText={v => setValues(s => ({ ...s, [r.id]: v }))}
                  style={{ flex: 1, borderWidth: 1.2, borderColor: c.ink, borderRadius: 12, paddingHorizontal: 10, backgroundColor: c.surface, color: c.text, fontFamily: fonts[600], fontSize: fs(10) }} />
                <Button height={44} size={11} style={{ width: 110 }}
                  onPress={busyId || !values[r.id] ? undefined : () => send(r, { value: Number(values[r.id].replace(',', '.')) })}>
                  {t('req.send')}
                </Button>
              </View>
            )}
          </Card>
        </Animated.View>
      ))}
    </Screen>
  );
}
