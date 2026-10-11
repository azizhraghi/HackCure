import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Avatar, haptic, RoundButton, Screen } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useAlerts, useFollowedPatient } from '../../hooks/useBackend';
import { useT } from '../../i18n';
import { getCaregiverAlerts, getCaregiverTasks, getCaregiverTwin, getDigest, markTaskDone, usePoll } from '../../services/api';
import { initials } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';
import { FamilyCard, FamilyHeading, FamilyLoad, FamilyReadings, FamilySharing } from './FamilyShared';
import { useFamilyCopy } from './familyCopy';

export function CaregiverBanner() {
  const { c } = useTheme(); const copy = useFamilyCopy(); const { resetRole } = useAppState();
  return <View style={{flexDirection:'row',alignItems:'center',gap:6,paddingVertical:12}}>
    <Icon name="shield" size={13} color={c.primary} /><T size={9} color={c.primary} w={700} style={{flex:1}}>{copy.access}</T>
    <Pressable accessibilityRole="button" onPress={resetRole} hitSlop={8}><T size={9} color={c.muted}>{copy.switch} ↗</T></Pressable>
  </View>;
}
export function FamilyHomeScreen() {
  const { c } = useTheme(); const copy = useFamilyCopy(); const nav = useNavigation();
  const { apiUrl, session, demo } = useAppState(); const { patient } = useFollowedPatient();
  const alerts = usePoll(getCaregiverAlerts,4000); const tasks = usePoll(getCaregiverTasks,4000);
  const digest = usePoll(getDigest,30000); const twin = usePoll(getCaregiverTwin,4000);
  const { t } = useT();
  const deviceAlerts = useAlerts(digest.data?.shared_categories.includes('alerts') ? patient?.patient_id : undefined);
  const deviceAlert = deviceAlerts.data?.filter(a => a.status === 'OPEN' && Date.now() - Date.parse(a.created_at) < 6*3600*1000).sort((a,b) => b.severity-a.severity)[0];
  const [busy,setBusy] = useState<string | null>(null); const [notice,setNotice] = useState('');
  const name = patient?.full_name || (demo ? 'Sarah Miller' : '—');
  const me = session?.user.first_name || (demo ? 'Ahmed' : '');
  const urgent = alerts.data?.some(a => a.level === 'urgent') || (deviceAlert?.severity ?? 0) >= 3;
  const review = alerts.data?.some(a => a.level === 'attention') || !!deviceAlert;
  const statusReady = !!alerts.data && !!digest.data && (!patient?.patient_id || !digest.data.shared_categories.includes('alerts') || (!!deviceAlerts.data && !deviceAlerts.error));
  const alertsHidden = !!digest.data && !digest.data.shared_categories.includes('alerts');
  const title = alertsHidden ? copy.alertsHidden : urgent ? copy.urgent : review ? copy.review : statusReady ? copy.quiet : copy.unknown;
  const statusColor = urgent ? c.urgentText : review ? c.reviewText : c.primary;
  const done = async (id:string) => {
    if (busy) return; setBusy(id); setNotice('');
    try { await markTaskDone(apiUrl,id); haptic('notificationSuccess'); setNotice(copy.saved); await tasks.refresh(); }
    catch { setNotice(copy.failed); } finally { setBusy(null); }
  };
  return <Screen bg={c.bg}>
    <CaregiverBanner />
    <View style={{flexDirection:'row',alignItems:'center',gap:10,marginVertical:10}}><View style={{flex:1}}><T size={10} color={c.muted}>{copy.hello}{me ? `, ${me}` : ''}</T><T size={26} w={800} spacing={-1} style={{marginTop:7}}>{copy.title}</T></View><RoundButton icon="bell" size={40} onPress={() => nav.navigate('FamilyTabs',{screen:'Updates'})} /></View>
    <T size={11} color={c.muted} lh={1.6}>{copy.sub}</T>
    <FamilyCard bg={c.mint}>
      <View style={{flexDirection:'row',alignItems:'center',gap:11,paddingBottom:16,borderBottomWidth:1,borderBottomColor:c.line}}><Avatar initials={initials(name)} bg={c.pink} size={44} /><View style={{flex:1}}><T size={9} color={c.muted}>{copy.following}</T><T size={17} w={800} style={{marginTop:3}}>{name}</T></View>{demo && <T size={8} color={c.muted}>{copy.demo}</T>}</View>
      <View style={{paddingTop:17}}><T size={9} color={c.muted}>{copy.status}</T><View style={{flexDirection:'row',alignItems:'center',gap:8,marginTop:8}}><View style={{width:8,height:8,borderRadius:4,backgroundColor:statusColor}} /><T size={17} w={800} color={statusColor} style={{flex:1}}>{title}</T></View>
      <T size={10} color={c.muted} lh={1.6} style={{marginTop:9}}>{alertsHidden ? copy.alertsHiddenSub : urgent || review ? alerts.data?.find(a => a.level === (urgent ? 'urgent':'attention'))?.title || (deviceAlert ? t(`alerts.${deviceAlert.type}`):'') : statusReady ? copy.quietSub:copy.unknownSub}</T>
      <Pressable accessibilityRole="button" onPress={() => nav.navigate('FamilyTabs',{screen:'Updates'})} style={{marginTop:16,padding:12,borderRadius:15,borderWidth:1.5,borderColor:c.ink,boxShadow:`0px 3px 0px ${c.shadow}`,backgroundColor:c.primary,alignItems:'center'}}><T size={11} w={800} color={c.onPrimary}>{copy.seeUpdates} →</T></Pressable></View>
    </FamilyCard>
    {digest.data ? <FamilyCard bg={c.sky}><FamilyHeading title={copy.summary} sub={copy.ai} icon="sparkle" /><T size={12} lh={1.7}>{digest.data.digest.text}</T><T size={9} color={c.muted} style={{marginTop:12}}>{new Date(digest.data.digest.created_at).toLocaleString()}</T></FamilyCard> : <FamilyLoad online={digest.online} retry={digest.refresh} />}
    <FamilyCard bg={c.yellow}><FamilyHeading title={copy.help} sub={copy.helpSub} icon="heart" />
      {!tasks.data ? <T size={11} color={c.muted} lh={1.6}>{tasks.online === false ? copy.offline:copy.loading}</T> : !tasks.data.length ? <View style={{padding:16,backgroundColor:c.bg,borderRadius:12}}><Icon name="check" size={21} color={c.primary} /><T size={12} w={700} style={{marginTop:8}}>{copy.noTasks}</T><T size={10} color={c.muted} lh={1.6} style={{marginTop:5}}>{copy.noTasksSub}</T></View> : tasks.data.map(task => <View key={task.id} style={{paddingVertical:13,borderTopWidth:1,borderTopColor:c.line}}><T size={9} color={c.primary} w={700}>{copy.categories[task.category] || task.category}</T><T size={12} lh={1.6} style={{marginTop:6}}>{task.text}</T><Pressable accessibilityRole="button" disabled={!!busy} onPress={() => done(task.id)} style={{alignSelf:'flex-start',marginTop:10,paddingVertical:9,paddingHorizontal:14,borderRadius:9,backgroundColor:c.blue,opacity:busy ? .6:1}}><T size={10} color={c.primary} w={800}>{busy === task.id ? copy.saving:copy.done} ✓</T></Pressable></View>)}
      {!!notice && <T accessibilityRole="alert" size={10} color={c.muted} style={{marginTop:12}}>{notice}</T>}
    </FamilyCard>
    {twin.data && <FamilyReadings twin={twin.data} />}
    {digest.data && <FamilySharing categories={digest.data.shared_categories} />}
  </Screen>;
}
