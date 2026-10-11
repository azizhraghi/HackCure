import React from 'react';
import { View } from 'react-native';
import { T } from '../../components/T';
import { Screen } from '../../components/ui';
import { useT } from '../../i18n';
import { getCaregiverTwin, getDigest, usePoll } from '../../services/api';
import { useTheme } from '../../theme/ThemeContext';
import { CaregiverBanner } from './FamilyHomeScreen';
import { FamilyCard, FamilyHeading, FamilyLoad, FamilyReadings, FamilySharing } from './FamilyShared';
import { useFamilyCopy } from './familyCopy';

export function FamilyRecoveryScreen() {
  const { c } = useTheme(); const copy = useFamilyCopy(); const { t } = useT();
  const twin = usePoll(getCaregiverTwin,4000); const digest = usePoll(getDigest,30000);
  const checkin = twin.data?.checkins;
  return <Screen bg={c.bg}><CaregiverBanner />
    <T size={26} w={800} spacing={-1} style={{marginTop:12}}>{copy.recovery}</T>
    <T size={11} color={c.muted} lh={1.6} style={{marginTop:9}}>{copy.recoverySub}</T>
    {!twin.data ? <FamilyLoad online={twin.online} retry={twin.refresh} /> : <>
      <FamilyReadings twin={twin.data} />
      {checkin && <FamilyCard bg={c.mint}><FamilyHeading title={copy.checkin} sub={copy.score} icon="checkin" />
        {checkin.latest ? <><View style={{flexDirection:'row',gap:8}}>{Object.entries(checkin.latest.scores_1_to_5).map(([key,value]) => <View key={key} style={{flex:1,backgroundColor:c.bg,padding:10,borderRadius:10}}><T size={9} color={c.muted}>{t(`checkin.${key}`)}</T><T size={23} w={800} style={{marginTop:8}}>{value}<T size={10}>/5</T></T></View>)}</View><T size={9} color={c.muted} style={{marginTop:12}}>{new Date(checkin.latest.at).toLocaleString()}</T>{checkin.status !== 'ok' && <T size={10} color={c.reviewText} style={{marginTop:8}}>{copy.noCheckin}</T>}</> : <T size={11} color={c.muted}>{copy.noCheckin}</T>}
      </FamilyCard>}
      {twin.data.medications && <FamilyCard bg={c.yellow}><FamilyHeading title={copy.medication} sub={copy.medicationSub} icon="pill" />
        {([['taken',copy.taken],['not_taken',copy.notTaken],['postponed',copy.postponed],['unknown',copy.unanswered]] as const).map(([key,label]) => <View key={key} style={{flexDirection:'row',justifyContent:'space-between',paddingVertical:9,borderTopWidth:1,borderTopColor:c.line}}><T size={11} color={c.muted}>{label}</T><T size={12} w={800}>{twin.data?.medications?.last_48h[key] ?? 0}</T></View>)}
      </FamilyCard>}
      {twin.data.wound && <FamilyCard bg={c.lilacBg}><FamilyHeading title={copy.photos} sub={copy.photosSub} icon="camera" /><T size={12} w={700}>{twin.data.wound.photos.length ? `${twin.data.wound.photos.length} · ${copy.photosCount}`:copy.noPhotos}</T>{twin.data.wound.photos[0] && <T size={10} color={c.muted} style={{marginTop:9}}>{new Date(twin.data.wound.photos[0].at).toLocaleString()}</T>}</FamilyCard>}
    </>}
    {digest.data && <FamilySharing categories={digest.data.shared_categories} />}
  </Screen>;
}
