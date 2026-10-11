/** Client of the .NET backend (Backend/API), reached through the ngrok tunnel. Payloads are snake_case. */

export type ApiRole = 'PATIENT' | 'FAMILY_MEMBER' | 'NURSE' | 'DOCTOR';

export type User = {
  id: string;
  email: string;
  role: ApiRole;
  first_name: string;
  last_name: string;
  phone: string | null;
  whatsapp_number: string | null;
};

export type AuthResponse = { access_token: string; token_type: string; expires_at: string; user: User; profile_id: string | null };

export type Session = { token: string; expiresAt: string; user: User; profileId: string | null };

export type Telemetry = {
  timestamp: string;
  device_id: string | null;
  bpm: number | null;
  spo2: number | null;
  room_temp: number | null;
  room_humidity: number | null;
  motion_state: string | null;
  fall_detected: boolean;
};

export type LinkedFamilyMember = {
  family_member_id: string;
  full_name: string;
  phone: string | null;
  relationship: string;
  is_primary_contact: boolean;
  whatsapp_opt_in: boolean;
};

export type PatientProfile = {
  id: string;
  user: User;
  date_of_birth: string | null;
  gender: string | null;
  device_id: string | null;
  link_code: string;
  family_members: LinkedFamilyMember[];
};

export type FollowedPatient = {
  patient_id: string;
  full_name: string;
  date_of_birth: string | null;
  device_id: string | null;
  relationship: string;
  is_primary_contact: boolean;
  whatsapp_opt_in: boolean;
  linked_at: string;
  latest_telemetry: Telemetry | null;
};

export type AlertType = 'FALL' | 'TACHYCARDIA' | 'BRADYCARDIA' | 'HYPOXIA';

export type Alert = {
  id: string;
  patient_id: string;
  type: AlertType;
  severity: 1 | 2 | 3;
  message: string;
  source: string | null;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  created_at: string;
};

export type RegisterBody = {
  email: string;
  password: string;
  role: 'PATIENT' | 'FAMILY_MEMBER';
  first_name: string;
  last_name: string;
  phone?: string;
  device_id?: string;
};

export type ChatMessage = { role: 'user' | 'assistant'; content: string };
export type ChatReply = { reply: string; escalate: boolean };

/** status 0 = server unreachable (tunnel down, no network, timeout) */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

type Config = { apiUrl: string; token?: string | null; onUnauthorized?: () => void };

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    // ASP.NET validation errors: { errors: { field: ["message"] } }
    const first = body?.errors && Object.values(body.errors as Record<string, string[]>)[0]?.[0];
    return first || body?.title || `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

async function request<T>(cfg: Config, path: string, init: { method?: string; body?: unknown; timeoutMs?: number } = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), init.timeoutMs ?? 15000);
  try {
    const res = await fetch(`${cfg.apiUrl.trim().replace(/\/+$/, '')}${path}`, {
      method: init.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        // Without it, free ngrok tunnels may answer with an HTML warning page
        'ngrok-skip-browser-warning': 'true',
        ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(cfg.token ? { Authorization: `Bearer ${cfg.token}` } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: controller.signal,
    });
    if (res.status === 401 && cfg.token) cfg.onUnauthorized?.();
    if (!res.ok) throw new ApiError(await errorMessage(res), res.status);
    if (res.status === 204) return null as T;
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError('network', 0);
  } finally {
    clearTimeout(timer);
  }
}

export function createApi(cfg: Config) {
  return {
    register: (body: RegisterBody) => request<AuthResponse>(cfg, '/api/auth/register', { method: 'POST', body }),
    login: (email: string, password: string) => request<AuthResponse>(cfg, '/api/auth/login', { method: 'POST', body: { email, password } }),

    me: () => request<PatientProfile>(cfg, '/api/patients/me'),
    latestTelemetry: (patientId: string) => request<Telemetry | null>(cfg, `/api/patients/${patientId}/telemetry/latest`),
    alerts: (patientId: string, limit = 30) => request<Alert[]>(cfg, `/api/patients/${patientId}/alerts?limit=${limit}`),

    linkPatient: (linkCode: string, relationship: string, whatsappOptIn: boolean) =>
      request<FollowedPatient>(cfg, '/api/family/link-patient', {
        method: 'POST',
        body: { link_code: linkCode, relationship, whatsapp_opt_in: whatsappOptIn, is_primary_contact: false },
      }),
    followedPatients: () => request<FollowedPatient[]>(cfg, '/api/family/patients'),

    /** Recovery assistant, relayed by the API to the FastAPI/Mistral service */
    chat: (messages: ChatMessage[], lang: string) => request<ChatReply>(cfg, '/chat', { method: 'POST', body: { messages, lang }, timeoutMs: 30000 }),
  };
}

export type Api = ReturnType<typeof createApi>;

export const toSession = (r: AuthResponse): Session => ({ token: r.access_token, expiresAt: r.expires_at, user: r.user, profileId: r.profile_id });

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]!.toUpperCase()).join('');
