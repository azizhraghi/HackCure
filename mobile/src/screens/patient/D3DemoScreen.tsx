import React, { useCallback, useEffect, useState } from 'react';
import { Linking, View } from 'react-native';
import { T } from '../../components/T';
import { Button, Card, PageTitle, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { acknowledgeDemoFollowup, createDemoInvestigation, getDemoFollowup, type DemoFollowup, type DemoInvestigation } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

export function D3DemoScreen({ route }: RootScreen<'D3Demo'>) {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const { event } = route.params;
  const [investigation, setInvestigation] = useState<DemoInvestigation | null>(null);
  const [followup, setFollowup] = useState<DemoFollowup | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  const refresh = useCallback(async () => {
    if (!event.followup_id) return;
    setBusy(true);
    setError(false);
    try {
      const [report, state] = await Promise.all([
        createDemoInvestigation(apiUrl, event.event_id),
        getDemoFollowup(apiUrl, event.followup_id),
      ]);
      setInvestigation(report);
      setFollowup(state);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }, [apiUrl, event.event_id, event.followup_id]);

  useEffect(() => { refresh(); }, [refresh]);

  const acknowledge = async () => {
    if (!event.followup_id || !followup || busy) return;
    setBusy(true);
    setError(false);
    try {
      setFollowup(await acknowledgeDemoFollowup(apiUrl, event.followup_id, followup.version));
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <TopBar title={t('d3Demo.top')} />
      <PageTitle>{t('d3Demo.title')}</PageTitle>
      <T size={9} color={c.muted} style={{ marginBottom: 12 }}>{t('d3Demo.intro')}</T>

      <Card bg={c.peach} radius={17} style={{ padding: 13, marginBottom: 11 }}>
        <T size={8} w={800} color={c.urgentText}>{t('d3Demo.safety')}</T>
        <T size={15} w={800} style={{ marginTop: 5 }}>{t(`d3Demo.outcome.${event.safety_decision.outcome}`)}</T>
        <T size={8.5} style={{ marginTop: 7 }}>{event.safety_decision.instruction ?? t('d3Demo.noInstruction')}</T>
        <T size={7} color={c.muted} style={{ marginTop: 8 }}>{t('d3Demo.rule')}: {event.safety_decision.matched_rule_ids.join(', ') || '—'} · {event.safety_decision.policy_version}</T>
      </Card>

      <Card radius={17} style={{ padding: 13, marginBottom: 11 }}>
        <T size={8} w={800}>{t('d3Demo.evidence')}</T>
        <T size={9} style={{ marginTop: 5 }}>{busy && !investigation ? t('d3Demo.loading') : investigation?.findings[0]?.statement ?? t('d3Demo.pending')}</T>
        {investigation && (
          <>
            <T size={7.5} color={c.muted} style={{ marginTop: 7 }}>{t('d3Demo.reportState')}: {investigation.state}</T>
            <T size={7.5} color={c.muted} style={{ marginTop: 4 }}>{t('d3Demo.sources')}: {investigation.evidence.map(x => x.evidence_id).join(', ')}</T>
            {investigation.missing_data.map(item => <T key={item} size={7.5} color={c.muted} style={{ marginTop: 4 }}>• {item}</T>)}
          </>
        )}
      </Card>

      <Card bg={c.ice} radius={17} style={{ padding: 13, marginBottom: 11 }}>
        <T size={8} w={800}>{t('d3Demo.followup')}</T>
        <T size={14} w={800} style={{ marginTop: 5 }}>{followup ? t(`d3Demo.stage.${followup.stage}`) : t('d3Demo.loading')}</T>
        <T size={7.5} color={c.muted} style={{ marginTop: 5 }}>{t('d3Demo.followupHint')}</T>
        {followup?.stage === 'open' && <Button onPress={acknowledge} style={{ marginTop: 10 }}>{t('d3Demo.acknowledge')}</Button>}
      </Card>

      {error && <T size={8} color={c.urgentText} style={{ marginBottom: 8 }}>{t('d3Demo.error')}</T>}
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Button secondary onPress={refresh} style={{ flex: 1 }}>{t('d3Demo.refresh')}</Button>
        <Button secondary onPress={() => Linking.openURL(`${apiUrl.replace(/\/$/, '')}/docs`)} style={{ flex: 1 }}>{t('d3Demo.api')}</Button>
      </View>
      <T size={7} color={c.muted} style={{ marginTop: 12 }}>{t('d3Demo.disclaimer')}</T>
    </Screen>
  );
}
