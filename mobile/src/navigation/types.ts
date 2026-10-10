import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { DemoEventResponse } from '../services/api';

export type PatientTabParams = { Home: undefined; CheckIn: undefined; Twin: undefined; Reports: undefined; Profile: undefined };
export type FamilyTabParams = { FamHome: undefined; Updates: undefined; FamRecovery: undefined; FamProfile: undefined };

export type LockTone = 'info' | 'attention' | 'urgent';

export type RootParams = {
  Role: undefined;
  Welcome: undefined;
  Upload: undefined;
  Protocol: undefined;
  PatientTabs: NavigatorScreenParams<PatientTabParams> | undefined;
  TwinDetail: undefined;
  WoundScan: undefined;
  SensingRequest: undefined;
  Escalation: undefined;
  D3Demo: { event: DemoEventResponse };
  Rehab: undefined;
  Medications: undefined;
  AIAssistant: { question?: string } | undefined;
  FamilyAccess: undefined;
  Consent: undefined;
  Settings: undefined;
  Join: undefined;
  FamilyTabs: NavigatorScreenParams<FamilyTabParams> | undefined;
  LockPreview: { tone: LockTone };
  FamilyInfo: undefined;
  FamilyAttention: undefined;
  FamilyUrgent: undefined;
};

export type RootScreen<K extends keyof RootParams> = NativeStackScreenProps<RootParams, K>;

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootParams {}
  }
}
