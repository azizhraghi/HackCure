/** Account identity is verified by FastAPI against its configured account server. */
type Config = { apiUrl: string; token?: string; demo: boolean };
type Identity = { patient_id: string; member_id: string; role: 'patient' | 'caregiver' };
let config: Config = { apiUrl: '', demo: false };
let pending: Promise<Identity> | null = null;
export function configureAiIdentity(next: Config) {
  if (JSON.stringify(next) !== JSON.stringify(config)) { config = next; pending = null; }
}
export async function aiIdentity(): Promise<Identity> {
  if (config.demo) return { patient_id: 'sarah', member_id: 'ahmed', role: 'patient' };
  if (!config.token) throw new Error('Sign in or choose the fictional demo to connect AI features.');
  if (!pending) {
    const current = config;
    pending = fetch(`${current.apiUrl}/account/ai-context`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${current.token}` }, body: '{}',
    }).then(async res => {
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || 'AI account connection failed');
      if (current !== config) throw new Error('Account changed; retry the request.');
      return body as Identity;
    }).catch(e => { if (current === config) pending = null; throw e; });
  }
  return pending;
}
export async function aiRequest(path: string, body?: unknown) {
  const current = config;
  const identity = await aiIdentity();
  if (current !== config) throw new Error('Account changed; retry the request.');
  let mapped = path.replace('/patients/sarah/', `/patients/${identity.patient_id}/`)
    .replace('/caregiver/ahmed/', `/caregiver/${identity.member_id}/`)
    .replace('member_id=ahmed', `member_id=${identity.member_id}&patient_id=${identity.patient_id}`);
  if (/^\/requests\/[^/]+\/answer$/.test(mapped)) mapped += `?actor=${identity.patient_id}`;
  const payload = body && typeof body === 'object' ? { ...body } as Record<string, unknown> : body;
  if (payload && typeof payload === 'object') {
    const data = payload as Record<string, unknown>;
    if (data.patient_id === 'sarah' || path === '/chat') data.patient_id = identity.patient_id;
    if (data.actor === 'sarah') data.actor = identity.patient_id;
    if (data.actor === 'ahmed') data.actor = identity.member_id;
  }
  const headers: Record<string, string> = config.token ? { Authorization: `Bearer ${config.token}` } : {};
  return { path: mapped, body: payload, headers };
}
