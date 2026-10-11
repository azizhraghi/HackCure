import React from 'react';
import { Pressable, View } from 'react-native';
import { Icon, type IconName } from '../../components/Icon';
import { T } from '../../components/T';
import { Card } from '../../components/ui';
import type { CaregiverTwin } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { useFamilyCopy } from './familyCopy';

export function FamilyCard({ children, bg }: { children: React.ReactNode; bg?: string }) {
  const { c } = useTheme();
  return <Card bg={bg} radius={20} style={{ padding:18, marginTop:14 }}>{children}</Card>;
}
export function FamilyHeading({ title, sub, icon }: { title:string; sub?:string; icon?:IconName }) {
  const { c } = useTheme();
  return <View style={{ flexDirection:'row', gap:10, alignItems:'center', marginBottom:12 }}>
    {icon && <View style={{ width:32, height:32, borderRadius:10, backgroundColor:c.blue, alignItems:'center', justifyContent:'center' }}><Icon name={icon} size={17} color={c.primary} /></View>}
    <View style={{flex:1}}><T size={14} w={800}>{title}</T>{sub && <T size={10} color={c.muted} lh={1.5} style={{marginTop:4}}>{sub}</T>}</View>
  </View>;
}
export function FamilyLoad({ online, retry }: { online:boolean | null; retry:()=>void }) {
  const { c } = useTheme(); const copy = useFamilyCopy();
  return <FamilyCard><T size={11} lh={1.6} color={c.muted}>{online === false ? copy.offline : copy.loading}</T>{online === false && <Pressable accessibilityRole="button" onPress={retry} style={{marginTop:12}}><T size={11} w={800} color={c.primary}>{copy.retry} ↗</T></Pressable>}</FamilyCard>;
}
export function FamilyReadings({ twin }: { twin:CaregiverTwin }) {
  const { c } = useTheme(); const copy = useFamilyCopy();
  if (!twin.vitals) return null;
  return <FamilyCard><FamilyHeading title={copy.readings} sub={copy.readingSub} icon="sensor" />
    <View style={{flexDirection:'row', gap:8}}>{([['hr',copy.hr,'bpm'],['temp',copy.temp,'°C'],['spo2',copy.spo2,'%']] as const).map(([key,label,unit]) => {
      const reading = twin.vitals?.[key]; const value = reading?.value?.value;
      const simulated = reading?.series?.find(o => o.observation_id === reading.observation_id)?.simulated;
      return <View key={key} style={{flex:1, backgroundColor:({hr:c.pink,temp:c.yellow,spo2:c.green})[key], borderWidth:1.5, borderColor:c.ink, padding:10, borderRadius:16, minHeight:100}}>
        <T size={9} color={c.muted}>{label}</T><T size={22} w={800} style={{marginTop:9}}>{value ?? '—'}<T size={9}> {unit}</T></T>
        <T size={8} color={c.muted} style={{marginTop:7}}>{reading?.at ? new Date(reading.at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : copy.noReading}</T>
        {simulated && <T size={8} color={c.primary} style={{marginTop:4}}>{copy.simulated}</T>}
        {reading?.status !== 'ok' && <T size={8} color={c.reviewText} lh={1.4} style={{marginTop:4}}>{reading?.reason || copy.noReading}</T>}
      </View>;
    })}</View></FamilyCard>;
}
export function FamilySharing({ categories }: { categories:string[] }) {
  const { c } = useTheme(); const copy = useFamilyCopy();
  return <FamilyCard bg={c.lilacBg}><FamilyHeading title={copy.privacy} icon="shield" />
    <View style={{flexDirection:'row',flexWrap:'wrap',gap:6}}>{categories.map(key => <View key={key} style={{paddingVertical:6,paddingHorizontal:9,borderRadius:99,borderWidth:1,borderColor:c.ink,backgroundColor:c.surface}}><T size={9} w={600} color={c.primary}>{copy.categories[key] || key}</T></View>)}</View>
    {!categories.length && <T size={11} color={c.muted}>{copy.noSharing}</T>}
    <T size={10} color={c.muted} lh={1.6} style={{marginTop:12}}>{copy.privacySub}</T>
  </FamilyCard>;
}
