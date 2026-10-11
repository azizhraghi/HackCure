import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import type { TFunction } from 'i18next';
import { useLatestTelemetry } from '../hooks/useBackend';
import { useT } from '../i18n';
import type { AlertType } from '../services/backend';
import { useTheme } from '../theme/ThemeContext';
import { Icon, type IconName } from './Icon';
import { T } from './T';
import { Card } from './ui';

const STALE_AFTER_S = 120;

export function formatAgo(t: TFunction, iso: string) {
  const s = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
  if (s < 60) return t('live.secondsAgo', { n: s });
  if (s < 3600) return t('live.minutesAgo', { n: Math.round(s / 60) });
  return t('live.at', { time: new Date(iso).toLocaleString([], { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) });
}

export const alertIcon = (type: AlertType): IconName =>
  type === 'FALL' ? 'activity' : type === 'HYPOXIA' ? 'drop' : 'heart';

function Tile({ icon, label, value, unit, bg }: { icon: IconName; label: string; value: string; unit: string; bg: string }) {
  return (
    <View style={{ flex: 1, minHeight: 74, borderRadius: 14, borderWidth: 1, borderColor: '#1b2a4a', backgroundColor: bg, padding: 9 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
        <Icon name={icon} size={14} color="#1b2a4a" />
        <T size={7} w={800} spacing={0.6} color="#1b2a4a">{label}</T>
      </View>
      <T size={24} w={800} spacing={-1} color="#1b2a4a" style={{ marginTop: 4 }}>
        {value}<T size={10} w={800} color="#1b2a4a">{unit}</T>
      </T>
    </View>
  );
}

const fmt = (v: number | null | undefined, decimals = 0) => (v === null || v === undefined ? '--' : v.toFixed(decimals));

/** Latest ESP32 measurement for a patient, refreshed every 5 s. */
export function LiveVitalsCard({ patientId }: { patientId: string | null | undefined }) {
  const { c } = useTheme();
  const { t } = useT();
  const { data, error, loading } = useLatestTelemetry(patientId);

  const age = data ? (Date.now() - Date.parse(data.timestamp)) / 1000 : null;
  const live = !error && age !== null && age < STALE_AFTER_S;
  const dot = error ? c.urgent : live ? c.track : c.switchOff;

  return (
    <Card radius={20} style={{ padding: 11, marginBottom: 10 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <T size={7.5} w={800} spacing={0.8}>{t('live.kicker')}</T>
        <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: dot, borderWidth: 1, borderColor: c.ink }} />
      </View>

      {loading && !data ? (
        <ActivityIndicator color={c.primary} style={{ marginVertical: 18 }} />
      ) : error && !data ? (
        <T size={9} w={700} color={c.urgentText}>{t('live.offline')}</T>
      ) : !data ? (
        <T size={9} color={c.muted}>{t('live.noData')}</T>
      ) : (
        <>
          {data.fall_detected && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7, padding: 8, marginBottom: 8, borderRadius: 12, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.urgent }}>
              <Icon name="activity" size={16} color="#fff" />
              <T size={9} w={800} color="#fff">{t('live.fall')}</T>
            </View>
          )}
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Tile icon="heart" label={t('live.bpm')} value={fmt(data.bpm)} unit=" bpm" bg={c.pink} />
            <Tile icon="drop" label={t('live.spo2')} value={fmt(data.spo2)} unit=" %" bg={c.sky} />
          </View>
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
            <Tile icon="thermo" label={t('live.roomTemp')} value={fmt(data.room_temp, 1)} unit=" °C" bg={c.yellow} />
            <Tile icon="sensor" label={t('live.humidity')} value={fmt(data.room_humidity)} unit=" %" bg={c.green} />
          </View>
          <T size={7} color={error ? c.urgentText : c.muted} style={{ marginTop: 8 }}>
            {error ? t('live.offline') : t(live ? 'live.updated' : 'live.stale', { ago: formatAgo(t, data.timestamp) })}
          </T>
        </>
      )}
    </Card>
  );
}
