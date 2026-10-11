import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, View } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { Camera, useCameraDevice, useCameraDevices, useCameraPermission, usePhotoOutput } from 'react-native-vision-camera';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Chip, haptic, RoundButton, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { getToday, getWoundPhotos, uploadWoundPhoto, type Today, type WoundPhoto } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { WoundAnalysis } from '../../components/WoundAnalysis';

import { Corners } from '../../components/Corners';
export { Corners };

/** One half of the comparison: a real photo (reference or today), or an empty slot. */
function PhotoHalf({ uri, label, divider }: { uri?: string; label: string; divider?: boolean }) {
  return (
    <View style={{ flex: 1, backgroundColor: '#273748', borderLeftWidth: divider ? 1 : 0, borderLeftColor: '#fff' }}>
      {uri ? <Image source={{ uri }} style={StyleSheet.absoluteFill} resizeMode="cover" /> : null}
      <T size={6} w={800} color="#fff" style={{ position: 'absolute', top: 6, left: 6, textShadowColor: '#000', textShadowRadius: 3 }}>{label}</T>
    </View>
  );
}

export function WoundScanScreen({ navigation }: RootScreen<'WoundScan'>) {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const focused = useIsFocused();
  const { hasPermission, canRequestPermission, requestPermission } = useCameraPermission();
  const devices = useCameraDevices();
  const device = useCameraDevice('back') ?? devices[0];
  const photoOutput = usePhotoOutput({ qualityPrioritization: 'balanced' });
  const [torch, setTorch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localUri, setLocalUri] = useState<string | null>(null);
  const [result, setResult] = useState<WoundPhoto | null>(null);
  const [reference, setReference] = useState<WoundPhoto | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [window_, setWindow] = useState<Today['wound_photo'] | null>(null);

  const abs = useCallback((path?: string | null) => (path ? `${apiUrl.replace(/\/$/, '')}${path}` : undefined), [apiUrl]);

  useEffect(() => {
    if (!hasPermission && canRequestPermission) requestPermission();
  }, [hasPermission, canRequestPermission, requestPermission]);

  useEffect(() => {
    getWoundPhotos(apiUrl).then(r => setReference(r.reference)).catch(() => setReference(null));
    getToday(apiUrl).then(r => setWindow(r.wound_photo)).catch(() => setWindow(null));
  }, [apiUrl]);

  const capture = async () => {
    if (busy) return;
    haptic('impactMedium');
    setBusy(true);
    setError(null);
    try {
      const file = await photoOutput.capturePhotoToFile({ flashMode: torch ? 'on' : 'off' }, {});
      const uri = file.filePath.startsWith('file://') ? file.filePath : `file://${file.filePath}`;
      setLocalUri(uri);
      const res = await uploadWoundPhoto(apiUrl, uri, confirmed);
      setResult(res);
      haptic(res.analysis?.problems?.length ? 'impactMedium' : 'notificationSuccess');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const cmp = result?.comparison;
  const problems = result?.analysis?.problems ?? [];
  const trendChip = !cmp?.available
    ? null
    : cmp.trend === 'up' ? { tone: 'yellow' as const, label: t('scan.trendUp') }
      : cmp.trend === 'down' ? { tone: 'green' as const, label: t('scan.trendDown') }
        : { tone: 'blue' as const, label: t('scan.trendStable') };

  return (
    <Screen>
      <TopBar title={t('scan.top')} action={<RoundButton icon="close" onPress={() => navigation.goBack()} />} />
      <View style={{ height: 407, marginHorizontal: -16, backgroundColor: '#1b2533', overflow: 'hidden', alignItems: 'center' }}>
        {hasPermission && device ? (
          localUri && (busy || result)
            ? <Image source={{ uri: localUri }} style={StyleSheet.absoluteFill} resizeMode="cover" />
            : <Camera style={StyleSheet.absoluteFill} device={device} isActive={focused && !result} outputs={[photoOutput]}
                torchMode={torch ? 'on' : 'off'} resizeMode="cover" />
        ) : (
          <View style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center', padding: 30 }]}>
            <Icon name="camera" size={34} color="#fff" />
            <T size={10} w={800} color="#fff" center style={{ marginTop: 10 }}>
              {!hasPermission ? t('scan.permission') : t('scan.noCamera', { n: devices.length })}
            </T>
            <Pressable onPress={requestPermission} style={{ marginTop: 12, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1, borderColor: '#fff' }}>
              <T size={9} w={800} color="#fff">{!hasPermission ? t('scan.allow') : t('scan.retry')}</T>
            </Pressable>
          </View>
        )}
        <View style={{ position: 'absolute', top: 50 }}><Corners /></View>
        <Chip tone="dark" style={{ position: 'absolute', top: 294, alignSelf: 'center' }}>
          {busy ? t('scan.captured') : result ? t('scan.measured') : t('scan.align')}
        </Chip>
        <View style={{ position: 'absolute', left: 31, right: 31, bottom: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Pressable onPress={() => { setResult(null); setLocalUri(null); setError(null); }}>
            <T size={8} color="#fff">{result ? t('scan.retake') : t('scan.auto')}</T>
          </Pressable>
          <Pressable disabled={!hasPermission || !device || busy || !!result || !confirmed} onPress={capture}
            style={({ pressed }) => ({ width: 61, height: 61, borderRadius: 31, borderWidth: 4, borderColor: '#fff', backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center', opacity: !device || result || !confirmed ? 0.5 : 1, transform: [{ scale: pressed ? 0.94 : 1 }] })}>
            {busy ? <ActivityIndicator color="#fff" /> : <Icon name="camera" size={26} color="#fff" />}
          </Pressable>
          <Pressable onPress={() => setTorch(v => !v)}><T size={8} color="#fff">{torch ? t('scan.flashOn') : t('scan.flashOff')}</T></Pressable>
        </View>
      </View>

      <View style={{ backgroundColor: c.surface, marginHorizontal: -16, paddingHorizontal: 16, paddingVertical: 10 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 9 }}>
          <View style={{ flex: 1 }}>
            <T size={6} spacing={1} color={c.muted}>{t('scan.measuredBy')}</T>
            <T size={14} w={800} style={{ marginTop: 2 }}>{t('scan.progress')}</T>
          </View>
          {trendChip && <Chip tone={trendChip.tone}>{trendChip.label}</Chip>}
        </View>
        <View style={{ height: 120, flexDirection: 'row', borderWidth: 1.3, borderColor: c.ink, borderRadius: 15, overflow: 'hidden' }}>
          <PhotoHalf uri={abs(reference?.url)} label={t('scan.day1')} />
          <PhotoHalf uri={localUri ?? undefined} label={t('scan.today')} divider />
        </View>

        {!result && window_ && !window_.permitted && (
          <T size={8.5} w={700} color={c.reviewText} style={{ marginTop: 8 }}>{t('scan.notNow')} {window_.reason}</T>
        )}
        {!result && (
          <Pressable onPress={() => setConfirmed(v => !v)} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 }}>
            <View style={{ width: 20, height: 20, borderRadius: 5, borderWidth: 1.4, borderColor: c.ink, backgroundColor: confirmed ? c.green : c.surface, alignItems: 'center', justifyContent: 'center' }}>
              {confirmed && <Icon name="check" size={14} />}
            </View>
            <T size={8.5} w={700} style={{ flex: 1 }}>{t('scan.confirm')}</T>
          </Pressable>
        )}
        {error && <T size={8.5} color={c.urgentText} style={{ marginTop: 8 }}>{t('scan.failed')} ({error})</T>}
        {problems.length > 0 && <T size={8.5} w={700} color={c.reviewText} style={{ marginTop: 8 }}>⚠ {problems.join(' · ')}: {t('scan.retakeHint')}</T>}

        {result && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginVertical: 8 }}>
            {cmp?.available ? (
              <Chip tone={cmp.trend === 'up' ? 'yellow' : 'pink'} style={{ flexGrow: 1 }}>
                <T size={9} w={800}>{t('scan.redness')}  {cmp.redness_area_ref_pct}% → {cmp.redness_area_now_pct}%{cmp.redness_area_change_pct != null ? `  (${cmp.redness_area_change_pct > 0 ? '+' : ''}${cmp.redness_area_change_pct}%)` : ''}</T>
              </Chip>
            ) : (
              <Chip tone="blue" style={{ flexGrow: 1 }}><T size={9} w={800}>{t('scan.notCompared')}</T></Chip>
            )}
            <Chip tone="white" style={{ flexGrow: 1, alignSelf: 'stretch', width: '100%' }}>
              <T size={8.5} w={800}>{t('scan.swelling')} · {t('scan.discharge')}: {t('scan.notMeasured')}</T>
            </Chip>
          </View>
        )}
        {result && <WoundAnalysis apiUrl={apiUrl} photo={result} />}
        <T size={7} color={c.muted} style={{ marginVertical: 6 }}>{t('scan.disclaimer')}</T>
        <Button onPress={() => navigation.goBack()}>{result ? t('scan.saved') : t('common.close')}</Button>
      </View>
    </Screen>
  );
}
