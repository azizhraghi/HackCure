import React, { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createApi, type Api, type Session } from '../services/backend';

export type Role = 'patient' | 'family';

/** AI backend (FastAPI: agents, care plan, check-in, assistant). In the browser it is the server that serves /app;
 * the Android emulator reaches the host machine through 10.0.2.2. A phone needs the PC's address (Settings). */
const webOrigin = (globalThis as { location?: { origin?: string } }).location?.origin;
export const DEFAULT_API_URL = Platform.OS === 'web' && webOrigin ? webOrigin
  : Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

/** SurgiGuard API (.NET + MongoDB: accounts, ESP32 telemetry, device alerts) through a public ngrok tunnel.
 * Free tunnels change URL on restart: edit it in Settings or on the sign-in screen. */
export const DEFAULT_ACCOUNT_URL = 'https://03f9-196-176-231-29.ngrok-free.app';

type Persisted = {
  role: Role | null; onboardedRoles: Role[]; apiUrl: string; accountUrl: string; session: Session | null;
  /** Using the app without a SurgiGuard API account (demo patient Sarah / family member Ahmed) */
  demo: boolean;
};

type AppStateValue = {
  role: Role | null;
  onboarded: boolean;
  apiUrl: string;
  accountUrl: string;
  session: Session | null;
  demo: boolean;
  /** Client of the SurgiGuard API (accounts, ESP32 telemetry, device alerts) */
  api: Api;
  ready: boolean;
  /** Demo link between the two roles: family acknowledged the patient's alert (kept in memory across role switches) */
  familyAck: boolean;
  setFamilyAck: (v: boolean) => void;
  setRole: (r: Role | null) => void;
  completeOnboarding: () => void;
  setApiUrl: (url: string) => void;
  setAccountUrl: (url: string) => void;
  /** The account's role (from the server) decides which side of the app opens */
  signIn: (session: Session, onboarded: boolean) => void;
  /** Continue without an account: the AI backend's demo patient and family member */
  continueAsDemo: () => void;
  /** Signs out and goes back to role selection */
  resetRole: () => void;
};

// v3: one app for both backends (v2 stored the SurgiGuard API address in apiUrl)
const KEY = 'sg.appState.v3';
const initial: Persisted = { role: null, onboardedRoles: [], apiUrl: DEFAULT_API_URL, accountUrl: DEFAULT_ACCOUNT_URL, session: null, demo: false };

const Ctx = createContext<AppStateValue | null>(null);

function restore(raw: string): Persisted {
  const saved: Persisted = { ...initial, ...JSON.parse(raw) };
  if (Platform.OS === 'web') saved.apiUrl = DEFAULT_API_URL; // the page's own server
  if (saved.session && Date.parse(saved.session.expiresAt) <= Date.now()) saved.session = null;
  return saved;
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Persisted>(initial);
  const [ready, setReady] = useState(false);
  const [familyAck, setFamilyAck] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then(raw => { if (raw) setState(restore(raw)); })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AppStateValue>(() => {
    const update = (fn: (p: Persisted) => Persisted) => setState(prev => {
      const next = fn(prev);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
    const signOut = () => update(p => ({ ...p, role: null, session: null, demo: false }));
    return {
      role: state.role,
      onboarded: !!state.role && state.onboardedRoles.includes(state.role),
      apiUrl: state.apiUrl,
      accountUrl: state.accountUrl,
      session: state.session,
      demo: state.demo,
      api: createApi({ apiUrl: state.accountUrl, token: state.session?.token, onUnauthorized: signOut }),
      ready,
      familyAck,
      setFamilyAck,
      setRole: role => update(p => ({ ...p, role })),
      completeOnboarding: () => update(p => (p.role && !p.onboardedRoles.includes(p.role) ? { ...p, onboardedRoles: [...p.onboardedRoles, p.role] } : p)),
      setApiUrl: apiUrl => update(p => ({ ...p, apiUrl })),
      setAccountUrl: accountUrl => update(p => ({ ...p, accountUrl })),
      signIn: (session, onboarded) => update(p => {
        const role: Role = session.user.role === 'FAMILY_MEMBER' ? 'family' : 'patient';
        const others = p.onboardedRoles.filter(r => r !== role);
        return { ...p, session, demo: false, role, onboardedRoles: onboarded ? [...others, role] : others };
      }),
      continueAsDemo: () => update(p => ({ ...p, demo: true, session: null })),
      resetRole: signOut,
    };
  }, [state, ready, familyAck]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAppState must be used inside AppStateProvider');
  return v;
}

export const useApi = () => useAppState().api;
