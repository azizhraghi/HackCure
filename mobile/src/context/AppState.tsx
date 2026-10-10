import React, { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type Role = 'patient' | 'family';

// Android emulator reaches the host machine through 10.0.2.2
export const DEFAULT_API_URL = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

type Persisted = { role: Role | null; onboardedRoles: Role[]; apiUrl: string };

type AppStateValue = {
  role: Role | null;
  onboarded: boolean;
  apiUrl: string;
  ready: boolean;
  /** Demo link between the two roles: family acknowledged the patient's alert (kept in memory across role switches) */
  familyAck: boolean;
  setFamilyAck: (v: boolean) => void;
  setRole: (r: Role | null) => void;
  completeOnboarding: () => void;
  setApiUrl: (url: string) => void;
  resetRole: () => void;
};

const KEY = 'sg.appState.v2';
const initial: Persisted = { role: null, onboardedRoles: [], apiUrl: DEFAULT_API_URL };

const Ctx = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Persisted>(initial);
  const [ready, setReady] = useState(false);
  const [familyAck, setFamilyAck] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then(raw => { if (raw) setState({ ...initial, ...JSON.parse(raw) }); })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AppStateValue>(() => {
    const update = (fn: (p: Persisted) => Persisted) => setState(prev => {
      const next = fn(prev);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
    return {
      role: state.role,
      onboarded: !!state.role && state.onboardedRoles.includes(state.role),
      apiUrl: state.apiUrl,
      ready,
      familyAck,
      setFamilyAck,
      setRole: role => update(p => ({ ...p, role })),
      completeOnboarding: () => update(p => (p.role && !p.onboardedRoles.includes(p.role) ? { ...p, onboardedRoles: [...p.onboardedRoles, p.role] } : p)),
      setApiUrl: apiUrl => update(p => ({ ...p, apiUrl })),
      resetRole: () => update(p => ({ ...p, role: null })),
    };
  }, [state, ready, familyAck]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAppState must be used inside AppStateProvider');
  return v;
}
