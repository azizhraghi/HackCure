import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';
import { Stepper } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, haptic, Muted, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';
import { useAppState } from '../../context/AppState';
import { getDocuments, uploadDocument, addSampleDocument, startPlanDraft, type UploadedDocument } from '../../services/api';
import { pickBrowserFile } from '../../services/filePicker';

export function UploadScreen({ navigation }: RootScreen<'Upload'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const { apiUrl, demo } = useAppState();
  const [files, setFiles] = useState<UploadedDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    getDocuments(apiUrl).then(setFiles).catch(e => setError(e.message));
  }, [apiUrl]);

  const analyze = async () => {
    if (analyzing) return;
    setAnalyzing(true);
    setError(null);
    try {
      const draft = await startPlanDraft(apiUrl, files.filter(f => f.status === 'ready').map(f => f.id));
      navigation.navigate('Protocol', { draftId: draft.id });
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setAnalyzing(false); }
  };

  const add = async (kind: 'pdf' | 'gallery' | 'scan' | 'sample') => {
    if (analyzing) return;
    setError(null);
    try {
      if (kind === 'sample') await addSampleDocument(apiUrl);
      else {
        const file = await pickBrowserFile(kind === 'pdf' ? '.pdf,.txt' : 'image/*', kind === 'scan');
        if (!file) return;
        await uploadDocument(apiUrl, file);
      }
      setFiles(await getDocuments(apiUrl));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  const UploadBtn = ({ icon, label, flex, kind }: { icon: IconName; label: string; flex?: boolean; kind: 'pdf' | 'gallery' | 'scan' }) => (
    <Pressable onPress={() => { haptic(); add(kind); }} style={({ pressed }) => ({ flex: flex ? 1 : undefined, minHeight: 34, borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, backgroundColor: c.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: pressed ? 0.7 : 1 })}>
      <Icon name={icon} size={18} /><T size={9} w={800}>{label}</T>
    </Pressable>
  );

  return (
    <Screen>
      <TopBar title={t('upload.top')} />
      <Stepper steps={list('upload.steps')} current={0} />
      <PageTitle>{t('upload.title')}</PageTitle>
      <Muted>{t('upload.sub')}</Muted>
      <Card bg={c.sky} radius={21} dashed style={{ padding: 14, alignItems: 'center' }}>
        <View style={{ width: 43, height: 43, borderRadius: 22, borderWidth: 1.4, borderColor: c.ink, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>
          <Icon name="upload" size={25} />
        </View>
        <T size={13} w={800}>{t('upload.card')}</T>
        <T size={8.5} color={c.muted} style={{ marginTop: 3, marginBottom: 10 }}>{t('upload.cardSub')}</T>
        <View style={{ alignSelf: 'stretch' }}><UploadBtn kind="scan" icon="camera" label={t('upload.scan')} /></View>
        <View style={{ flexDirection: 'row', gap: 7, marginTop: 7, alignSelf: 'stretch' }}>
          <UploadBtn kind="pdf" icon="file" label={t('upload.pdf')} flex />
          <UploadBtn kind="gallery" icon="image" label={t('upload.gallery')} flex />
        </View>
      </Card>
      <SectionRow title={t('upload.files')} right={t('upload.count', { n: files.length })} />
      <Card radius={18} style={{ paddingHorizontal: 11, paddingVertical: 2, marginBottom: 12 }}>
        {files.map((f, i) => (
          <View key={f.id} style={{ minHeight: 50, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i === files.length - 1 ? 0 : 1, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 29, borderRadius: 7, borderWidth: 1, borderColor: c.ink, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name="file" size={17} /></View>
            <View style={{ flex: 1 }}>
              <T size={9.5} w={800}>{f.filename}</T>
              <T size={7.5} color={c.muted} style={{ marginTop: 2 }}>{f.error ?? `${Math.ceil(f.size / 1024)} KB · ${f.chars} characters read`}</T>
            </View>
            <View style={{ width: 20, height: 20, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: f.status === 'ready' ? c.green : c.yellow }}>
              <Icon name={f.status === 'ready' ? 'check' : 'file'} size={14} />
            </View>
          </View>
        ))}
      </Card>
      {demo && <Button secondary onPress={() => add('sample')} style={{ marginBottom: 8 }}>Use fictional sample document</Button>}
      {error && <T size={9} color={c.urgentText} style={{ marginBottom: 8 }}>{error}</T>}
      <Button onPress={files.some(f => f.status === 'ready') && !analyzing ? analyze : undefined}>{analyzing ? t('upload.analyzing') : `${t('upload.analyze')}  →`}</Button>
    </Screen>
  );
}
