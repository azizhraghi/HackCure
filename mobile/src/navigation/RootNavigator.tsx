import React from 'react';
import { DarkTheme, DefaultTheme, NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAppState } from '../context/AppState';
import { useT } from '../i18n';
import { useTheme } from '../theme/ThemeContext';
import { BottomNav } from './BottomNav';
import type { FamilyTabParams, PatientTabParams, RootParams } from './types';

import { RoleSelectionScreen } from '../screens/onboarding/RoleSelectionScreen';
import { WelcomeScreen } from '../screens/onboarding/WelcomeScreen';
import { UploadScreen } from '../screens/onboarding/UploadScreen';
import { ProtocolScreen } from '../screens/onboarding/ProtocolScreen';
import { HomeScreen } from '../screens/patient/HomeScreen';
import { CheckInScreen } from '../screens/patient/CheckInScreen';
import { TwinScreen } from '../screens/patient/TwinScreen';
import { ReportsScreen } from '../screens/patient/ReportsScreen';
import { ProfileScreen } from '../screens/patient/ProfileScreen';
import { TwinDetailScreen } from '../screens/patient/TwinDetailScreen';
import { WoundScanScreen } from '../screens/patient/WoundScanScreen';
import { SensingRequestScreen } from '../screens/patient/SensingRequestScreen';
import { EscalationScreen } from '../screens/patient/EscalationScreen';
import { RehabScreen } from '../screens/patient/RehabScreen';
import { MedicationsScreen } from '../screens/patient/MedicationsScreen';
import { AIAssistantScreen } from '../screens/patient/AIAssistantScreen';
import { FamilyAccessScreen } from '../screens/patient/FamilyAccessScreen';
import { ConsentScreen } from '../screens/patient/ConsentScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { JoinPatientScreen } from '../screens/family/JoinPatientScreen';
import { FamilyHomeScreen } from '../screens/family/FamilyHomeScreen';
import { UpdatesScreen } from '../screens/family/UpdatesScreen';
import { FamilyRecoveryScreen } from '../screens/family/FamilyRecoveryScreen';
import { FamilyProfileScreen } from '../screens/family/FamilyProfileScreen';
import { FamilyAttentionScreen, FamilyInfoScreen, FamilyUrgentScreen, LockPreviewScreen } from '../screens/family/AlertScreens';

const Stack = createNativeStackNavigator<RootParams>();
const PatientTab = createBottomTabNavigator<PatientTabParams>();
const FamilyTab = createBottomTabNavigator<FamilyTabParams>();

function PatientTabs() {
  const { t } = useT();
  return (
    <PatientTab.Navigator screenOptions={{ headerShown: false }}
      tabBar={props => <BottomNav {...props} icons={{ Home: 'home', CheckIn: 'checkin', Twin: 'twin', Reports: 'report', Profile: 'profile' }} />}>
      <PatientTab.Screen name="Home" component={HomeScreen} options={{ title: t('tabs.home') }} />
      <PatientTab.Screen name="CheckIn" component={CheckInScreen} options={{ title: t('tabs.checkin') }} />
      <PatientTab.Screen name="Twin" component={TwinScreen} options={{ title: t('tabs.twin') }} />
      <PatientTab.Screen name="Reports" component={ReportsScreen} options={{ title: t('tabs.reports') }} />
      <PatientTab.Screen name="Profile" component={ProfileScreen} options={{ title: t('tabs.profile') }} />
    </PatientTab.Navigator>
  );
}

function FamilyTabs() {
  const { t } = useT();
  return (
    <FamilyTab.Navigator screenOptions={{ headerShown: false }}
      tabBar={props => <BottomNav {...props} icons={{ FamHome: 'home', Updates: 'bell', FamRecovery: 'twin', FamProfile: 'profile' }} />}>
      <FamilyTab.Screen name="FamHome" component={FamilyHomeScreen} options={{ title: t('tabs.home') }} />
      <FamilyTab.Screen name="Updates" component={UpdatesScreen} options={{ title: t('tabs.updates') }} />
      <FamilyTab.Screen name="FamRecovery" component={FamilyRecoveryScreen} options={{ title: t('tabs.recovery') }} />
      <FamilyTab.Screen name="FamProfile" component={FamilyProfileScreen} options={{ title: t('tabs.profile') }} />
    </FamilyTab.Navigator>
  );
}

export function RootNavigator() {
  const { c, isDark } = useTheme();
  const { role, onboarded } = useAppState();
  const base = isDark ? DarkTheme : DefaultTheme;
  const navTheme = { ...base, colors: { ...base.colors, background: c.bg, card: c.bg, text: c.text, primary: c.primary, border: c.navLine } };

  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'slide_from_right', contentStyle: { backgroundColor: c.bg } }}>
        {role === null && <Stack.Screen name="Role" component={RoleSelectionScreen} options={{ animation: 'fade' }} />}

        {role === 'patient' && !onboarded && (
          <Stack.Group>
            <Stack.Screen name="Welcome" component={WelcomeScreen} />
            <Stack.Screen name="Upload" component={UploadScreen} />
            <Stack.Screen name="Protocol" component={ProtocolScreen} />
          </Stack.Group>
        )}

        {role === 'patient' && onboarded && (
          <Stack.Group>
            <Stack.Screen name="PatientTabs" component={PatientTabs} options={{ animation: 'fade' }} />
            <Stack.Screen name="TwinDetail" component={TwinDetailScreen} options={{ animation: 'slide_from_bottom' }} />
            <Stack.Screen name="WoundScan" component={WoundScanScreen} options={{ animation: 'slide_from_bottom' }} />
            <Stack.Screen name="SensingRequest" component={SensingRequestScreen} options={{ presentation: 'transparentModal', animation: 'fade' }} />
            <Stack.Screen name="Escalation" component={EscalationScreen} />
            <Stack.Screen name="Rehab" component={RehabScreen} />
            <Stack.Screen name="Medications" component={MedicationsScreen} />
            <Stack.Screen name="AIAssistant" component={AIAssistantScreen} />
            <Stack.Screen name="FamilyAccess" component={FamilyAccessScreen} />
            <Stack.Screen name="Consent" component={ConsentScreen} />
          </Stack.Group>
        )}

        {role === 'family' && !onboarded && <Stack.Screen name="Join" component={JoinPatientScreen} />}

        {role === 'family' && onboarded && (
          <Stack.Group>
            <Stack.Screen name="FamilyTabs" component={FamilyTabs} options={{ animation: 'fade' }} />
            <Stack.Screen name="LockPreview" component={LockPreviewScreen} options={{ animation: 'fade' }} />
            <Stack.Screen name="FamilyInfo" component={FamilyInfoScreen} />
            <Stack.Screen name="FamilyAttention" component={FamilyAttentionScreen} />
            <Stack.Screen name="FamilyUrgent" component={FamilyUrgentScreen} options={{ presentation: 'fullScreenModal', animation: 'slide_from_bottom' }} />
          </Stack.Group>
        )}

        {role !== null && onboarded && <Stack.Screen name="Settings" component={SettingsScreen} />}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
