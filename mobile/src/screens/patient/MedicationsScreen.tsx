import React, { useState } from 'react';
import { Image, Pressable, View } from 'react-native';
import { ScoreRing } from '../../components/charts';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, haptic, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { getMedications, recordDose, uploadMedicationPhoto, usePoll, type ScheduledDose } from '../../services/api';
import { pickBrowserFile } from '../../services/filePicker';
import { useTheme } from '../../theme/ThemeContext';

export function MedicationsScreen({ navigation }: RootScreen<'Medications'>) {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const { data, online, refresh } = usePoll(getMedications, 5000);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const doses = data?.today ?? [];
  const taken = doses.filter(d => d.status === 'taken').length;
  const next = doses.find(d => d.status === 'due') ?? doses.find(d => d.status === 'upcoming');
  const slot = (d: ScheduledDose) => Number(d.scheduled_for.slice(11, 13)) < 12 ? 'morning' : Number(d.scheduled_for.slice(11, 13)) < 18 ? 'afternoon' : 'evening';
  const save = async (dose: ScheduledDose, status: 'taken' | 'not_taken' | 'postponed') => {
    if (busy) return;
    setBusy(true); setMessage(null);
    try {
      const result = await recordDose(apiUrl, dose, status);
      haptic('notificationSuccess'); setMessage(result.missed_dose_text ?? 'Your answer was saved.'); await refresh();
    } catch (e) { setMessage(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };
  const addPhoto = async (dose: ScheduledDose) => {
    if (busy) return;
    setBusy(true); setMessage(null);
    try {
      const file = await pickBrowserFile('image/jpeg,image/png,image/webp');
      if (file) { await uploadMedicationPhoto(apiUrl, dose.med_id, file); await refresh(); }
    } catch (e) { setMessage(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };
  return <Screen>
    <TopBar title={t('meds.top')} />
    <T size={9} w={800} spacing={1.5} color={c.primary} style={{ marginTop: 6 }}>TODAY · {new Set(doses.map(d => d.med_id)).size} SCHEDULED MEDICINES</T>
    <PageTitle style={{ marginTop: 6 }}>{t('meds.title')}</PageTitle>
    {online === false && <Card bg={c.warnBg} style={{ padding: 12 }}><T size={9}>Medication schedule unavailable. Reconnect to load your saved plan.</T></Card>}
    <View style={{ flexDirection: 'row', gap: 10 }}>
      <Card bg={c.sky} radius={19} style={{ flex: 1.1, padding: 12, minHeight: 128 }}>
        <T size={7.5} w={800}>{t('meds.next')}</T>
        {next ? <>
          <T size={26} w={800} style={{ marginTop: 6 }}>{next.scheduled_for.slice(11, 16)}</T>
          <T size={10} w={800}>{next.name} {next.dose}</T>
          <T size={8} style={{ marginTop: 3 }}>{next.status === 'due' ? 'Reminder: scheduled now' : 'Upcoming in your plan'}</T>
          {next.photo && <Image source={{ uri: next.photo.url }} accessibilityLabel={`${next.name} package photo`} resizeMode="contain" style={{ height: 100, marginTop: 8 }} />}
        </> : <T size={10} style={{ marginTop: 12 }}>{data ? 'No upcoming scheduled dose today.' : 'Loading your schedule…'}</T>}
      </Card>
      <Card bg={c.surface} radius={19} style={{ flex: 1, padding: 10, alignItems: 'center' }}>
        <T size={7.5} w={800}>{t('meds.adherence')}</T>
        <View style={{ marginTop: 6 }}><ScoreRing value={doses.length ? Math.round(taken / doses.length * 100) : 0} size={64} thickness={7} /></View>
        <T size={8} center style={{ marginTop: 5 }}>{taken}/{doses.length} doses reported taken today</T>
        <T size={7} color={c.muted} center style={{ marginTop: 4 }}>Unanswered does not mean taken.</T>
      </Card>
    </View>
    {message && <Card bg={c.ice} style={{ marginTop: 10, padding: 10 }}><T size={9}>{message}</T></Card>}
    {data && !doses.length && <T size={9} style={{ marginTop: 12 }}>No scheduled medicines in the active plan. As-needed medicines do not generate timed reminders.</T>}
    {(['morning', 'afternoon', 'evening'] as const).map(period => {
      const items = doses.filter(d => slot(d) === period);
      if (!items.length) return null;
      return <View key={period}>
        <SectionRow title={t(`meds.${period}`)} right={`${items.length}`} />
        <Card radius={17}>
          {items.map((d, i) => <View key={`${d.med_id}:${d.scheduled_for}`} style={{ padding: 12, borderBottomWidth: i < items.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
            <View style={{ flexDirection: 'row', gap: 9, alignItems: 'center' }}>
              {d.photo ? <Image source={{ uri: d.photo.url }} accessibilityLabel={`${d.name} package photo`} resizeMode="contain" style={{ width: 76, height: 76, borderRadius: 10 }} /> : <Icon name="pill" size={26} />}
              <View style={{ flex: 1 }}>
                <T size={12} w={800}>{d.name} {d.dose}</T>
                <T size={9} color={c.muted} style={{ marginTop: 3 }}>{d.scheduled_for.slice(11, 16)} · {d.purpose}</T>
                <View style={{ alignSelf: 'flex-start', marginTop: 5 }}><Chip tone={d.status === 'taken' ? 'green' : 'white'}>{d.status.replace('_', ' ')}</Chip></View>
              </View>
            </View>
            <Pressable disabled={busy} onPress={() => addPhoto(d)} style={{ paddingVertical: 10 }}>
              <T size={9} w={700} color={c.primary}>{d.photo ? 'Replace package photo' : 'Add a photo of this medicine’s package'}</T>
            </Pressable>
            {d.status !== 'upcoming' && <View style={{ gap: 7 }}>
              <Button onPress={!busy ? () => save(d, 'taken') : undefined}>{t('meds.take')}</Button>
              <View style={{ flexDirection: 'row', gap: 7 }}>
                <Button secondary style={{ flex: 1 }} onPress={!busy ? () => save(d, 'not_taken') : undefined}>Not taken</Button>
                <Button secondary style={{ flex: 1 }} onPress={!busy ? () => save(d, 'postponed') : undefined}>Postponed</Button>
              </View>
            </View>}
          </View>)}
        </Card>
      </View>;
    })}
    <T size={8} color={c.muted} lh={1.5} style={{ marginTop: 12 }}>Add a photo only after checking the medicine name and strength against your plan. The photo helps recognition; it does not identify the medicine or confirm that you took it.</T>
    <Button icon="sparkle" secondary style={{ marginTop: 14 }} onPress={() => navigation.navigate('AIAssistant', { question: 'Help me understand the medicines in my care plan.' })}>{t('meds.ask')}</Button>
  </Screen>;
}
