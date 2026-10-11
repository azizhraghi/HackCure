import React from 'react';
import { View } from 'react-native';
import { Card } from './ui';
import { T } from './T';
import { useT } from '../i18n';
import { useTheme } from '../theme/ThemeContext';
import type { InvestigationProgress as Progress } from '../services/api';

export function InvestigationProgress({ progress }: { progress?: Progress | null }) {
  const { c } = useTheme();
  const { t } = useT();
  if (!progress) return null;
  const steps = [
    ['context', progress.context_collected], ['evidence', progress.report_ready],
    ['report', progress.report_ready], ['followup', progress.closed],
  ] as const;
  return <Card bg={c.ice} radius={16} style={{ padding: 12, marginBottom: 10, marginTop: 10 }}>
    <T size={7} w={800} spacing={0.8} color={c.muted}>{t('investigation.title')}</T>
    <T size={9} w={700} lh={1.4} style={{ marginTop: 5 }}>{t(`investigation.${progress.phase}`)}</T>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7, marginTop: 9 }}>
      {steps.map(([key, done], i) => <View key={key} style={{ backgroundColor: done ? c.green : c.surface, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 5 }}>
        <T size={7.5} w={600}>{done ? '✓' : `${i + 1}.`} {t(`investigation.step_${key}`)}</T>
      </View>)}
    </View>
    {progress.report_incomplete && <T size={7.5} lh={1.4} style={{ marginTop: 7 }}>{t('investigation.incomplete')}</T>}
  </Card>;
}
