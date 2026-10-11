import React from 'react';
import { View } from 'react-native';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Screen } from '../../components/ui';
import { getCaregiverAlerts, getDigest, usePoll } from '../../services/api';
import { useAlerts, useFollowedPatient } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { useTheme } from '../../theme/ThemeContext';
import { CaregiverBanner } from './FamilyHomeScreen';
import { FamilyCard, FamilyLoad } from './FamilyShared';
import { useFamilyCopy } from './familyCopy';

export function UpdatesScreen() {
  const { c } = useTheme(); const copy = useFamilyCopy(); const alerts = usePoll(getCaregiverAlerts,4000);
  const digest = usePoll(getDigest,30000); const { patient } = useFollowedPatient(); const { t } = useT();
  const deviceAlerts = useAlerts(digest.data?.shared_categories.includes('alerts') ? patient?.patient_id : undefined);
  const openDevice = deviceAlerts.data?.filter(a => a.status === 'OPEN') || [];
  const iotPending = !!patient?.patient_id && !!digest.data?.shared_categories.includes('alerts') && (!deviceAlerts.data || !!deviceAlerts.error);
  const stages:Record<string,string> = { created:copy.assigned,assigned:copy.assigned,acknowledged:copy.acknowledged,patient_contacted:copy.patient_contacted,action_taken:copy.action_taken,verified:copy.verified,resolved:copy.resolved };
  return <Screen bg={c.bg}><CaregiverBanner /><T size={26} w={800} spacing={-1} style={{marginTop:12}}>{copy.updates}</T><T size={11} color={c.muted} lh={1.6} style={{marginTop:9}}>{copy.updatesSub}</T>
    {iotPending && <FamilyLoad online={deviceAlerts.error ? false:null} retry={deviceAlerts.refresh} />}
    {!alerts.data ? <FamilyLoad online={alerts.online} retry={alerts.refresh} /> : !alerts.data.length && !openDevice.length && !iotPending ? <FamilyCard><Icon name="bell" size={22} color={c.primary} /><T size={12} color={c.muted} lh={1.6} style={{marginTop:10}}>{copy.noAlerts}</T></FamilyCard> : [...alerts.data].sort((a,b) => Date.parse(b.created_at)-Date.parse(a.created_at)).map(a => <FamilyCard key={a.id} bg={a.level === 'urgent' ? c.warnBg : c.peach}>
      <View style={{flexDirection:'row',alignItems:'center',gap:8}}><Icon name="bell" size={17} color={a.level === 'urgent' ? c.urgentText:c.primary} /><T size={10} color={c.muted}>{new Date(a.created_at).toLocaleString()}</T></View>
      <T size={16} w={800} lh={1.4} style={{marginTop:12}}>{a.title}</T><T size={11} color={a.level === 'urgent' ? c.urgentText:c.muted} style={{marginTop:7}}>{a.level === 'urgent' ? copy.urgent:a.level === 'attention' ? copy.review:copy.updates}</T>
      <View style={{marginTop:14,padding:11,backgroundColor:c.bg,borderRadius:10}}><T size={9} color={c.muted}>{copy.stage}</T><T size={12} w={700} style={{marginTop:5}}>{stages[a.state] || a.state}</T></View>
    </FamilyCard>)}
    {openDevice.map(a => <FamilyCard key={`device-${a.id}`} bg={c.lilacBg}><View style={{flexDirection:'row',alignItems:'center',gap:8}}><Icon name="sensor" size={17} color={c.primary} /><T size={10} color={c.muted}>{new Date(a.created_at).toLocaleString()}</T></View><T size={16} w={800} style={{marginTop:12}}>{t(`alerts.${a.type}`)}</T><T size={12} lh={1.6} style={{marginTop:8}}>{a.message}</T><T size={11} color={a.severity >= 3 ? c.urgentText:c.reviewText} style={{marginTop:10}}>{a.severity >= 3 ? copy.urgent:copy.review}</T></FamilyCard>)}
  </Screen>;
}
