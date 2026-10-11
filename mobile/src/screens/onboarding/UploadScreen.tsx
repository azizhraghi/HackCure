import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, View } from 'react-native';
import { Stepper } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, haptic, Muted, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { addSampleDocument, getDocuments, getPlanDraft, startPlanDraft, uploadDocument, type UploadedDocument } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

/** Browser only: native file picking needs a document-picker library (not installed yet). */
function pickFileOnWeb(): Promise<File | null> {
  const doc = (globalThis as { document?: any }).document;
  if (Platform.OS !== 'web' || !doc) return Promise.resolve(null);
  return new Promise(resolve => {
    const input = doc.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.txt,image/*';
    input.onchange = () => resolve(input.files?.[0] ?? null);
    input.click();
  });
}

export function UploadScreen({ navigation }: RootScreen<'Upload'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const { apiUrl } = useAppState();
  const [docs, setDocs] = useState<UploadedDocument[]>([]);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => getDocuments(apiUrl).then(setDocs).catch(e => setError(String(e.message ?? e))), [apiUrl]);
  useEffect(() => { refresh(); }, [refresh]);

  const run = async (fn: () => Promise<unknown>) => {
    haptic();
    setBusy(true);
    setError(null);
    try { await fn(); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };

  const addSample = () => run(() => addSampleDocument(apiUrl));
  const pick = () => run(async () => { const f = await pickFileOnWeb(); if (f) await uploadDocument(apiUrl, f); });

  /** Developer 2's compiler reads the documents; the draft is reviewed on the next screen. */
  const analyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      let draft = await startPlanDraft(apiUrl, docs.filter(d => d.status === 'ready').map(d => d.id));
      for (let i = 0; i < 90 && draft.status === 'analyzing'; i++) {
        await new Promise<void>(r => setTimeout(() => r(), 2000));
        draft = await getPlanDraft(apiUrl, draft.id);
      }
      navigation.navigate('Protocol', { draftId: draft.id });
    } catch (e) {
      setError(`${t('upload.failed')}: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const UploadBtn = ({ icon, label, flex, onPress, disabled }: { icon: IconName; label: string; flex?: boolean; onPress: () => void; disabled?: boolean }) => (
    <Pressable disabled={disabled || busy} onPress={onPress} style={({ pressed }) => ({ flex: flex ? 1 : undefined, minHeight: 34, borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, backgroundColor: c.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: disabled ? 0.45 : pressed ? 0.7 : 1 })}>
      <Icon name={icon} size={18} /><T size={9} w={800}>{label}</T>
    </Pressable>
  );
  const ready = docs.filter(d => d.status === 'ready');

  return (
    <Screen>
      <TopBar title={t('upload.top')} />
      <Stepper steps={list('upload.steps')} current={0} />
      <PageTitle>{t('upload.title')}</PageTitle>
      <Muted>{t('upload.sub')}</Muted>
      <Card bg={c.sky} radius={21} dashed style={{ padding: 14, alignItems: 'center' }}>
        <View style={{ width: 43, height: 43, borderRadius: 22, borderWidth: 1.4, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>
          {busy ? <ActivityIndicator color={c.text} /> : <Icon name="upload" size={25} />}
        </View>
        <T size={13} w={800}>{t('upload.card')}</T>
        <T size={8.5} color={c.muted} style={{ marginTop: 3, marginBottom: 10 }}>{t('upload.cardSub')}</T>
        <View style={{ alignSelf: 'stretch' }}><UploadBtn icon="file" label={t('upload.sample')} onPress={addSample} /></View>
        <View style={{ flexDirection: 'row', gap: 7, marginTop: 7, alignSelf: 'stretch' }}>
          <UploadBtn icon="upload" label={t('upload.pick')} flex onPress={pick} disabled={Platform.OS !== 'web'} />
        </View>
      </Card>
      <SectionRow title={t('upload.files')} right={t('upload.count', { n: docs.length })} />
      <Card radius={18} style={{ paddingHorizontal: 11, paddingVertical: 2, marginBottom: 12 }}>
        {docs.length === 0 && <T size={9} color={c.muted} style={{ paddingVertical: 14 }}>{t('upload.none')}</T>}
        {docs.map((d, i) => (
          <View key={d.id} style={{ minHeight: 50, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i === docs.length - 1 ? 0 : 1, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 29, borderRadius: 7, borderWidth: 1, borderColor: c.ink, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name="file" size={17} /></View>
            <View style={{ flex: 1 }}>
              <T size={9.5} w={800} numberOfLines={1}>{d.filename}</T>
              <T size={7.5} color={d.status === 'ready' ? c.muted : c.urgentText} style={{ marginTop: 2 }}>
                {d.status === 'ready' ? t('upload.chars', { n: d.chars }) : `${t('upload.unreadable')}: ${d.error ?? ''}`}
              </T>
            </View>
            <View style={{ width: 20, height: 20, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: d.status === 'ready' ? c.green : c.yellow }}>
              <Icon name={d.status === 'ready' ? 'check' : 'close'} size={14} />
            </View>
          </View>
        ))}
      </Card>
      {error && <T size={8.5} color={c.urgentText} style={{ marginBottom: 8 }}>{error}</T>}
      <Button onPress={ready.length && !analyzing ? analyze : undefined} style={{ opacity: ready.length ? 1 : 0.5 }}>
        {analyzing ? t('upload.analyzing') : `${t('upload.analyze')}  →`}
      </Button>
    </Screen>
  );
}
