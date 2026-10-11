import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, View } from 'react-native';
import { Icon } from '../../components/Icon';
export { Corners } from '../../components/Corners';
import { T } from '../../components/T';
import { Button, Chip, Screen, TopBar, RoundButton } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { getToday, getWoundPhotos, uploadWoundPhoto, type Today, type WoundPhoto } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { WoundAnalysis } from '../../components/WoundAnalysis';

/** Browser build: the phone's camera opens through a file input (capture=environment); same backend measurement. */
function pickImage(): Promise<File | null> {
  const doc = (globalThis as { document?: any }).document;
  return new Promise(resolve => {
    const input = doc.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.setAttribute('capture', 'environment');
    input.onchange = () => resolve(input.files?.[0] ?? null);
    input.click();
  });
}

function PhotoHalf({ uri, label, divider }: { uri?: string; label: string; divider?: boolean }) {
  return (
    <View style={{ flex: 1, backgroundColor: '#273748', borderLeftWidth: divider ? 1 : 0, borderLeftColor: '#fff' }}>
      {uri ? <Image source={{ uri }} style={StyleSheet.absoluteFill} resizeMode="cover" /> : null}
      <T size={6} w={800} color="#fff" style={{ position: 'absolute', top: 6, left: 6 }}>{label}</T>
    </View>
  );
}

export function WoundScanScreen({ navigation }: RootScreen<'WoundScan'>) {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localUri, setLocalUri] = useState<string | null>(null);
  const [result, setResult] = useState<WoundPhoto | null>(null);
  const [reference, setReference] = useState<WoundPhoto | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [window_, setWindow] = useState<Today['wound_photo'] | null>(null);
  const abs = useCallback((path?: string | null) => (path ? `${apiUrl.replace(/\/$/, '')}${path}` : undefined), [apiUrl]);

  useEffect(() => {
    getWoundPhotos(apiUrl).then(r => setReference(r.reference)).catch(() => setReference(null));
    getToday(apiUrl).then(r => setWindow(r.wound_photo)).catch(() => setWindow(null));
  }, [apiUrl]);

  const [picked, setPicked] = useState<File | null>(null);
  const capture = async () => {
    const file = await pickImage();
    if (!file) return;
    setError(null);
    setResult(null);
    setPicked(file);
    setLocalUri(URL.createObjectURL(file));
  };
  const send = async () => {
    if (!picked || busy) return;
    if (!confirmed) { setError(t('scan.confirm')); return; }
    setBusy(true);
    setError(null);
    try {
      setResult(await uploadWoundPhoto(apiUrl, picked, confirmed));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const cmp = result?.comparison;
  const problems = result?.analysis?.problems ?? [];
  return (
    <Screen>
      <TopBar title={t('scan.top')} action={<RoundButton icon="close" onPress={() => navigation.goBack()} />} />
      <View style={{ height: 300, marginHorizontal: -16, backgroundColor: '#1b2533', alignItems: 'center', justifyContent: 'center' }}>
        {localUri ? <Image source={{ uri: localUri }} style={StyleSheet.absoluteFill} resizeMode="cover" /> : (
          <View style={{ alignItems: 'center', padding: 24 }}>
            <Icon name="camera" size={34} color="#fff" />
            <T size={9} color="#fff" center style={{ marginTop: 8 }}>{t('scan.align')}</T>
          </View>
        )}
        <Pressable disabled={busy || !!result} onPress={capture}
          style={{ position: 'absolute', bottom: 16, flexDirection: 'row', gap: 8, alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 99, borderWidth: 2, borderColor: '#fff', backgroundColor: c.primary, opacity: busy || result ? 0.5 : 1 }}>
          {busy ? <ActivityIndicator color="#fff" /> : <Icon name="camera" size={20} color="#fff" />}
          <T size={10} w={800} color="#fff">{busy ? t('scan.captured') : t('scan.pick')}</T>
        </Pressable>
      </View>

      <View style={{ backgroundColor: c.surface, marginHorizontal: -16, paddingHorizontal: 16, paddingVertical: 10 }}>
        {!result && window_ && !window_.permitted && (
          <T size={8.5} w={700} color={c.muted} style={{ marginBottom: 6 }}>{t('scan.outsideWindow')}</T>
        )}
        {!result && (
          <Pressable onPress={() => setConfirmed(v => !v)} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 9 }}>
            <View style={{ width: 20, height: 20, borderRadius: 5, borderWidth: 1.4, borderColor: c.ink, backgroundColor: confirmed ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {confirmed && <Icon name="check" size={14} />}
            </View>
            <T size={8.5} w={700} style={{ flex: 1 }}>{t('scan.confirm')}</T>
          </Pressable>
        )}
        <T size={6} spacing={1} color={c.muted}>{t('scan.measuredBy')}</T>
        <T size={14} w={800} style={{ marginTop: 2, marginBottom: 8 }}>{t('scan.progress')}</T>
        <View style={{ height: 120, flexDirection: 'row', borderWidth: 1.3, borderColor: c.ink, borderRadius: 15, overflow: 'hidden' }}>
          <PhotoHalf uri={abs(reference?.url)} label={t('scan.day1')} />
          <PhotoHalf uri={localUri ?? undefined} label={t('scan.today')} divider />
        </View>
        {picked && !result && (
          <Button onPress={send} style={{ marginTop: 10, opacity: confirmed && !busy ? 1 : 0.5 }}>{busy ? t('scan.captured') : t('scan.analyse')}</Button>
        )}
        {error && <T size={8.5} color={c.urgentText} style={{ marginTop: 8 }}>{t('scan.failed')} ({error})</T>}
        {problems.length > 0 && <T size={8.5} w={700} color={c.reviewText} style={{ marginTop: 8 }}>⚠ {problems.join(' · ')}: {t('scan.retakeHint')}</T>}
        {result && (
          <View style={{ gap: 5, marginVertical: 8 }}>
            {cmp?.available
              ? <Chip tone={cmp.trend === 'up' ? 'yellow' : 'pink'}><T size={9} w={800}>{t('scan.redness')}  {cmp.redness_area_ref_pct}% → {cmp.redness_area_now_pct}%</T></Chip>
              : <Chip tone="blue"><T size={9} w={800}>{t('scan.notCompared')}</T></Chip>}
            <Chip tone="white"><T size={8.5} w={800}>{t('scan.swelling')} · {t('scan.discharge')}: {t('scan.notMeasured')}</T></Chip>
          </View>
        )}
        {result && <WoundAnalysis apiUrl={apiUrl} photo={result} />}
        <T size={7} color={c.muted} style={{ marginVertical: 6 }}>{t('scan.disclaimer')}</T>
        <Button onPress={() => navigation.goBack()}>{result ? t('scan.saved') : t('common.close')}</Button>
      </View>
    </Screen>
  );
}
