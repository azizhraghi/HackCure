import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';
import { Stepper } from '../../components/charts';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, haptic, Muted, PageTitle, Screen, SectionRow, TopBar } from '../../components/ui';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { useTheme } from '../../theme/ThemeContext';

type FileItem = { key: string; size: string; state: 'done' | 'wait' };

export function UploadScreen({ navigation }: RootScreen<'Upload'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const [files, setFiles] = useState<FileItem[]>([
    { key: 'upload.discharge', size: '2.4 MB', state: 'done' },
    { key: 'upload.operative', size: '1.8 MB', state: 'done' },
    { key: 'upload.labs', size: '', state: 'wait' },
    { key: 'upload.meds', size: '', state: 'done' },
  ]);
  const [analyzing, setAnalyzing] = useState(false);

  // Lab results finish "processing" after a moment
  useEffect(() => {
    const id = setTimeout(() => setFiles(f => f.map(x => (x.state === 'wait' ? { ...x, state: 'done', size: '0.9 MB' } : x))), 2500);
    return () => clearTimeout(id);
  }, []);

  const analyze = () => {
    setAnalyzing(true);
    setTimeout(() => { setAnalyzing(false); navigation.navigate('Protocol'); }, 1600);
  };

  const UploadBtn = ({ icon, label, flex }: { icon: IconName; label: string; flex?: boolean }) => (
    <Pressable onPress={() => haptic()} style={({ pressed }) => ({ flex: flex ? 1 : undefined, minHeight: 34, borderWidth: 1.2, borderColor: c.ink, borderRadius: 10, backgroundColor: c.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: pressed ? 0.7 : 1 })}>
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
        <View style={{ alignSelf: 'stretch' }}><UploadBtn icon="camera" label={t('upload.scan')} /></View>
        <View style={{ flexDirection: 'row', gap: 7, marginTop: 7, alignSelf: 'stretch' }}>
          <UploadBtn icon="file" label={t('upload.pdf')} flex />
          <UploadBtn icon="image" label={t('upload.gallery')} flex />
        </View>
      </Card>
      <SectionRow title={t('upload.files')} right={t('upload.count', { n: files.length })} />
      <Card radius={18} style={{ paddingHorizontal: 11, paddingVertical: 2, marginBottom: 12 }}>
        {files.map((f, i) => (
          <View key={f.key} style={{ height: 50, flexDirection: 'row', alignItems: 'center', gap: 8, borderBottomWidth: i === files.length - 1 ? 0 : 1, borderBottomColor: c.line }}>
            <View style={{ width: 27, height: 29, borderRadius: 7, borderWidth: 1, borderColor: c.ink, backgroundColor: c.iceBlue, alignItems: 'center', justifyContent: 'center' }}><Icon name="file" size={17} /></View>
            <View style={{ flex: 1 }}>
              <T size={9.5} w={800}>{t(f.key)}</T>
              <T size={7.5} color={c.muted} style={{ marginTop: 2 }}>{f.state === 'wait' ? t('upload.processing') : f.size || t('upload.ready')}</T>
            </View>
            <View style={{ width: 20, height: 20, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: f.state === 'done' ? c.green : c.yellow }}>
              {f.state === 'done' ? <Icon name="check" size={14} /> : <ActivityIndicator size="small" color={c.text} style={{ transform: [{ scale: 0.6 }] }} />}
            </View>
          </View>
        ))}
      </Card>
      <Button onPress={analyze}>{analyzing ? t('upload.analyzing') : `${t('upload.analyze')}  →`}</Button>
    </Screen>
  );
}
