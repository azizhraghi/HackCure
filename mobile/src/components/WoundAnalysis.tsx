import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, View } from 'react-native';
import { T } from './T';
import { Chip } from './ui';
import { useT } from '../i18n';
import { getWoundPhoto, type WoundPhoto } from '../services/api';
import { useTheme } from '../theme/ThemeContext';

/**
 * D1-F result for one dressing-change photo: the area the code outlined (so the patient sees what was measured),
 * photo quality, the comparison with the reference photo, and the AI's plain description once it arrives.
 * Wording stays descriptive: the care team reviews; nothing here is a diagnosis.
 */
export function WoundAnalysis({ apiUrl, photo }: { apiUrl: string; photo: WoundPhoto }) {
  const { c } = useTheme();
  const { t } = useT();
  const [p, setP] = useState<WoundPhoto>(photo);
  const abs = (path?: string | null) => (path ? `${apiUrl.replace(/\/$/, '')}${path}` : undefined);

  useEffect(() => {
    setP(photo);
    if (photo.vision_review) return;
    let alive = true;
    let tries = 0;
    const id = setInterval(async () => {
      tries += 1;
      try {
        const next = await getWoundPhoto(apiUrl, photo.observation_id);
        if (!alive) return;
        setP(next);
        if (next.vision_review || tries > 20) clearInterval(id);
      } catch {
        if (tries > 20) clearInterval(id);
      }
    }, 2000);
    return () => { alive = false; clearInterval(id); };
  }, [apiUrl, photo]);

  const d = p.d1;
  if (!d) return null;
  const q = d.quality;
  const cmp = d.comparison;
  const v = p.vision_review;
  return (
    <View style={{ marginTop: 8, borderWidth: 1.3, borderColor: c.ink, borderRadius: 15, padding: 10, backgroundColor: c.surface }}>
      <T size={6} spacing={1} color={c.muted}>{t('scan.d1Title')}</T>
      {d.overlay_url ? (
        <Image source={{ uri: abs(d.overlay_url) }} style={{ width: '100%', aspectRatio: 4 / 3, borderRadius: 10, marginTop: 6 }} resizeMode="contain" />
      ) : null}
      <T size={8} color={c.muted} style={{ marginTop: 4 }}>{d.segmentation.found ? t('scan.d1Outlined') : `${t('scan.d1NotFound')} (${d.segmentation.reason ?? ''})`}</T>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginTop: 6 }}>
        <Chip tone={q.status === 'good' ? 'pink' : 'yellow'}><T size={8.5} w={800}>{t('scan.d1Quality')}: {q.status}</T></Chip>
        {cmp ? (
          <Chip tone={cmp.available ? (cmp.trend === 'more_red' ? 'yellow' : 'pink') : 'blue'}>
            <T size={8.5} w={800}>{cmp.available ? cmp.summary : `${t('scan.notCompared')}`}</T>
          </Chip>
        ) : <Chip tone="blue"><T size={8.5} w={800}>{t('scan.d1Reference')}</T></Chip>}
      </View>
      {q.problems && q.problems.length > 0 && (
        <T size={8.5} w={700} color={c.reviewText} style={{ marginTop: 6 }}>⚠ {q.problems.join(' · ')}: {t('scan.retakeHint')}</T>
      )}
      <View style={{ marginTop: 8 }}>
        <T size={8.5} w={800}>{t('scan.d1Ai')}</T>
        {!v ? (
          <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center', marginTop: 4 }}>
            <ActivityIndicator size="small" color={c.primary} /><T size={8} color={c.muted}>{t('scan.d1AiPending')}</T>
          </View>
        ) : v.available ? (
          <View style={{ marginTop: 4, gap: 2 }}>
            {v.findings.length ? v.findings.map((f, i) => (
              <T key={i} size={8.5}>• {f.finding} <T size={7.5} color={c.muted}>({f.confidence})</T></T>
            )) : <T size={8} color={c.muted}>{t('scan.d1AiNothing')}</T>}
            {v.mode !== 'live' && <T size={7.5} color={c.muted}>{v.uncertainty}</T>}
          </View>
        ) : <T size={8} color={c.muted} style={{ marginTop: 4 }}>{v.reason}</T>}
      </View>
      <T size={8.5} w={700} style={{ marginTop: 8 }}>{p.review_alert_id ? t('scan.d1Review') : t('scan.d1Received')}</T>
    </View>
  );
}
