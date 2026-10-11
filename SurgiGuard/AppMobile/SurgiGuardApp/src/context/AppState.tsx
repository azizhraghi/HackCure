import React, { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createApi, type Api, type Session } from '../services/backend';

export type Role = 'patient' | 'family';

/** Public ngrok tunnel to the API (Backend/API, port 8080). Free tunnels change URL on restart: edit it in Settings or on the login screen. */
export const DEFAULT_API_URL = 'https://03f9-196-176-231-29.ngrok-free.app';

// Emulator-only addresses saved by previous versions of the app
const LEGACY_URLS = ['http://10.0.2.2:8000', 'http://localhost:8000'];

type Persisted = { role: Role | null; onboardedRoles: Role[]; apiUrl: string; session: Session | null };

type AppStateValue = {
  role: Role | null;
  onboarded: boolean;
  apiUrl: string;
  session: Session | null;
  api: Api;
  ready: boolean;
  /** Demo link between the two roles: family acknowledged the patient's alert (kept in memory across role switches) */
  familyAck: boolean;
  setFamilyAck: (v: boolean) => void;
  setRole: (r: Role | null) => void;
  completeOnboarding: () => void;
  setApiUrl: (url: string) => void;
  /** The account's role (from the server) decides which side of the app opens */
  signIn: (session: Session, onboarded: boolean) => void;
  /** Signs out and goes back to role selection */
  resetRole: () => void;
};

const KEY = 'sg.appState.v2';
const initial: Persisted = { role: null, onboardedRoles: [], apiUrl: DEFAULT_API_URL, session: null };

const Ctx = createContext<AppStateValue | null>(null);

function restore(raw: string): Persisted {
  const saved: Persisted = { ...initial, ...JSON.parse(raw) };
  if (LEGACY_URLS.includes(saved.apiUrl)) saved.apiUrl = DEFAULT_API_URL;
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
    const signOut = () => update(p => ({ ...p, role: null, session: null }));
    return {
      role: state.role,
      onboarded: !!state.role && state.onboardedRoles.includes(state.role),
      apiUrl: state.apiUrl,
      session: state.session,
      api: createApi({ apiUrl: state.apiUrl, token: state.session?.token, onUnauthorized: signOut }),
      ready,
      familyAck,
      setFamilyAck,
      setRole: role => update(p => ({ ...p, role })),
      completeOnboarding: () => update(p => (p.role && !p.onboardedRoles.includes(p.role) ? { ...p, onboardedRoles: [...p.onboardedRoles, p.role] } : p)),
      setApiUrl: apiUrl => update(p => ({ ...p, apiUrl })),
      signIn: (session, onboarded) => update(p => {
        const role: Role = session.user.role === 'FAMILY_MEMBER' ? 'family' : 'patient';
        const others = p.onboardedRoles.filter(r => r !== role);
        return { ...p, session, role, onboardedRoles: onboarded ? [...others, role] : others };
      }),
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
