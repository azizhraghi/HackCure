import React, { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Button, Card, Chip, Muted, PageTitle, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import { confirmPlanDraft, getPlanDraft, type PlanDraft } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';

/** Review of the plan drafted from the patient's documents (Developer 2 compiler + code grounding). */
function DraftReview({ draft, onBack, onConfirmed }: { draft: PlanDraft; onBack: () => void; onConfirmed: () => void }) {
  const { c } = useTheme();
  const { t } = useT();
  const { apiUrl } = useAppState();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const plan = draft.plan;
  const info = plan?.document_info;
  const profile = plan?.clinical_profile ?? {};
  const levels = { high: 0, medium: 1, low: 2 } as const;
  const warnings = [...draft.warnings].sort((a, b) => levels[a.level] - levels[b.level]);
  const facts = ([
    ['patient_age', 'Age'], ['asa_score', 'ASA'], ['bmi_kg_m2', 'BMI'], ['smoking_status', 'Smoking'],
    ['diabetes', 'Diabetes'], ['anesthesia_type', 'Anesthesia'], ['hospital_name', 'Hospital'],
  ] as const).filter(([k]) => profile[k] !== null && profile[k] !== undefined && profile[k] !== '');

  const confirm = async () => {
    setSaving(true);
    setError(null);
    try { await confirmPlanDraft(apiUrl, draft.id); onConfirmed(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); setSaving(false); }
  };

  return (
    <>
      <PageTitle>{t('protocol.reviewTitle')}</PageTitle>
      <Muted>{t('protocol.reviewSub')}</Muted>
      <Card bg={c.green} style={{ padding: 11, marginTop: 4, marginBottom: 9 }}>
        <T size={7} w={700} spacing={0.8}>{t('protocol.detected')}</T>
        <T size={11} w={800} style={{ marginVertical: 3 }}>{plan?.pathway || info?.surgery || '—'}</T>
        <T size={8}>{[info?.surgery_date, info?.surgeon, info?.allergies?.length ? `⚠ ${info.allergies.join(', ')}` : ''].filter(Boolean).join(' · ')}</T>
      </Card>

      <T size={7.5} w={800} spacing={0.8} style={{ marginBottom: 5 }}>{t('protocol.meds')}</T>
      {(plan?.medications ?? []).map((m, i) => (
        <Animated.View key={m.id} entering={FadeInDown.delay(i * 60)}>
          <Card bg={c.pink} radius={14} style={{ padding: 9, marginBottom: 6 }}>
            <T size={9.5} w={800}>{m.name} {m.dose}</T>
            <T size={8} style={{ marginTop: 2 }}>
              {m.times.length ? m.times.join(' · ') : t('protocol.noTimes')}{m.duration_days ? ` · ${m.duration_days} d` : ''}{m.purpose ? ` · ${m.purpose}` : ''}
            </T>
            {m.times_inferred && <T size={7.5} w={800} color={c.reviewText} style={{ marginTop: 2 }}>⚠ {t('protocol.proposed')}</T>}
          </Card>
        </Animated.View>
      ))}

      {!!info?.activity_restrictions?.length && (
        <Card bg={c.yellow} radius={14} style={{ padding: 9, marginBottom: 6 }}>
          <T size={7.5} w={800} spacing={0.8}>{t('protocol.restrictions')}</T>
          {info.activity_restrictions.map(r => <T key={r} size={8.5} style={{ marginTop: 3 }}>• {r}</T>)}
        </Card>
      )}

      {facts.length > 0 && (
        <>
          <T size={7.5} w={800} spacing={0.8} style={{ marginTop: 6, marginBottom: 5 }}>{t('protocol.profile')}</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginBottom: 6 }}>
            {facts.map(([k, label]) => <Chip key={k} tone="lavender">{`${label}: ${String(profile[k])}`}</Chip>)}
          </View>
        </>
      )}

      <T size={7.5} w={800} spacing={0.8} style={{ marginTop: 6, marginBottom: 5 }}>{t('protocol.checks')}</T>
      {warnings.length === 0 && <T size={8.5} color={c.muted}>{t('protocol.noChecks')}</T>}
      {warnings.map((w, i) => (
        <View key={i} style={{ borderWidth: 1.2, borderColor: w.level === 'high' ? c.urgentText : c.warnBorder, backgroundColor: w.level === 'low' ? c.surface : c.warnBg, borderRadius: 12, padding: 8, marginBottom: 5 }}>
          <T size={8.5} w={800}>{w.level === 'high' ? '⚠ ' : ''}{w.item}</T>
          <T size={8} style={{ marginTop: 2 }}>{w.message}</T>
        </View>
      ))}

      {error && <T size={8.5} color={c.urgentText} style={{ marginTop: 6 }}>{error}</T>}
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
        <Button secondary style={{ width: '32%' }} onPress={onBack}>{t('common.edit')}</Button>
        <Button style={{ flex: 1 }} onPress={saving ? undefined : confirm} size={12}>{saving ? t('protocol.confirming') : t('protocol.confirmPlan')}</Button>
      </View>
      <T size={7} color={c.muted} center style={{ marginTop: 8 }}>{draft.mode}</T>
    </>
  );
}

export function ProtocolScreen({ navigation, route }: RootScreen<'Protocol'>) {
  const { c } = useTheme();
  const { t, list } = useT();
  const { apiUrl, completeOnboarding } = useAppState();
  const draftId = route.params?.draftId;
  const [draft, setDraft] = useState<PlanDraft | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (draftId) getPlanDraft(apiUrl, draftId).then(setDraft).catch(e => setLoadError(String(e.message ?? e)));
  }, [apiUrl, draftId]);

  const cards = [
    { k: 'med', bg: c.pink }, { k: 'act', bg: c.yellow }, { k: 'reh', bg: c.lavender }, { k: 'fol', bg: c.sky },
  ];

  if (draftId) {
    return (
      <Screen>
        <TopBar title={t('protocol.top')} />
        {!draft && !loadError && <View style={{ padding: 40, alignItems: 'center' }}><ActivityIndicator color={c.text} /><T size={9} style={{ marginTop: 8 }}>{t('protocol.loading')}</T></View>}
        {(loadError || draft?.status === 'failed') && (
          <Card bg={c.warnBg} style={{ padding: 12 }}>
            <T size={11} w={800}>{t('protocol.failed')}</T>
            <T size={8.5} style={{ marginTop: 4 }}>{loadError ?? draft?.error}</T>
            <Button secondary style={{ marginTop: 10 }} onPress={() => navigation.goBack()}>{t('protocol.back')}</Button>
          </Card>
        )}
        {draft && draft.status !== 'failed' && (
          <DraftReview draft={draft} onBack={() => navigation.goBack()} onConfirmed={completeOnboarding} />
        )}
      </Screen>
    );
  }

  return (
    <Screen>
      <TopBar title={t('protocol.top')} />
      <View style={{ width: 48, height: 48, borderRadius: 24, borderWidth: 1.5, borderColor: c.ink, backgroundColor: c.green, alignItems: 'center', justifyContent: 'center', alignSelf: 'center', marginTop: 5, marginBottom: 6 }}>
        <Icon name="check" size={25} />
      </View>
      <PageTitle center>{t('protocol.title')}</PageTitle>
      <Muted center>{t('protocol.sub')}</Muted>

      <Card bg={c.green} style={{ minHeight: 75, padding: 11, flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4, marginBottom: 9 }}>
        <View style={{ width: 39, height: 39, borderRadius: 20, backgroundColor: c.surface, borderWidth: 1.2, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T size={22}>◒</T></View>
        <View style={{ flex: 1 }}>
          <T size={7} w={700} spacing={0.8}>{t('protocol.detected')}</T>
          <T size={11} w={800} style={{ marginVertical: 3 }}>{t('protocol.surgery')}</T>
          <T size={8}>{t('protocol.surgerySub')}</T>
        </View>
        <Icon name="check" size={19} />
      </Card>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 7 }}>
        {cards.map((card, i) => (
          <Animated.View key={card.k} entering={FadeInDown.delay(i * 80)} style={{ width: '48.7%' }}>
            <Card bg={card.bg} radius={15} style={{ minHeight: 80, padding: 10 }}>
              <T size={7.5} w={800} upper>{t(`protocol.${card.k}T`)}</T>
              <T size={9} w={800} lh={1.35} style={{ marginTop: 5, maxWidth: 115 }}>{t(`protocol.${card.k}C`)}</T>
              <View style={{ position: 'absolute', right: 7, bottom: 7, backgroundColor: 'rgba(255,255,255,0.68)', borderRadius: 10, paddingVertical: 3, paddingHorizontal: 6 }}>
                <T size={6.5} w={800} color="#1b2a4a">{t(`protocol.${card.k}Tag`)}</T>
              </View>
            </Card>
          </Animated.View>
        ))}
      </View>

      <View style={{ borderWidth: 1.5, borderColor: c.warnBorder, backgroundColor: c.warnBg, borderRadius: 14, minHeight: 47, marginTop: 7, padding: 8, flexDirection: 'row', gap: 8, alignItems: 'center' }}>
        <View style={{ width: 26, height: 26, borderRadius: 13, backgroundColor: c.warnDot, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><T w={800} size={12} color="#1b2a4a">!</T></View>
        <View style={{ flex: 1 }}>
          <T size={9} w={800}>{t('protocol.warning')}</T>
          <T size={7} style={{ marginTop: 2 }}>{t('protocol.warningSub')}</T>
        </View>
      </View>

      <T size={9} w={800} style={{ marginTop: 10, marginBottom: 6 }}>{t('protocol.modules')}</T>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 5 }}>
        {list('protocol.chips').map(x => <Chip key={x} tone="blue">{x}</Chip>)}
      </View>

      <View style={{ flexDirection: 'row', gap: 8, marginTop: 14 }}>
        <Button secondary style={{ width: '32%' }} onPress={() => navigation.goBack()}>{t('common.edit')}</Button>
        <Button style={{ flex: 1 }} onPress={completeOnboarding} size={12}>{t('protocol.confirm')}</Button>
      </View>
    </Screen>
  );
}
