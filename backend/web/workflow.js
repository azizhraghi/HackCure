/* Public workflow actions and source references, not hidden model reasoning. */
window.renderInvestigationWorkflow = function (inv) {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const w = inv.workflow || {};
  const f = w.followup;
  const milestones = [['Context collected', w.context_collected], ['Evidence checked', w.report_ready],
    ['Clinician report prepared', w.report_ready], ['Follow-up verified and closed', f?.closed]];
  const sources = (w.context_sources || []).map(s => `<li>${esc(s.kind)} · <code>${esc(s.id)}</code> · ${esc(s.at)}</li>`).join('');
  const d1 = (inv.summary?.supplementary_findings || []).map(x => `<li>${esc(x.summary || x.kind)} · <code>${esc(x.observation_id)}</code> · ${esc(x.at)}${x.simulated ? ' · SIMULATED' : ''}<br>${esc(x.note)}</li>`).join('');
  const events = (w.events || []).slice(-12).map(e => `<li>${esc(e.at.slice(11,19))} · ${esc(e.label)}</li>`).join('');
  return `<div class="card" style="margin:10px 0;border:1px solid var(--line);padding:12px;border-radius:14px;background:var(--surface)">
    <h3 style="margin:0 0 8px">Investigation workflow · ${esc(w.engine || 'legacy')}</h3>
    <div style="display:flex;gap:8px;flex-wrap:wrap">${milestones.map(([label, done], i) => `<span style="border:1px solid ${done ? '#218d65' : '#8a96ab'};border-radius:10px;padding:6px 9px">${done ? '✓' : i+1+'.'} ${esc(label)}</span>`).join('')}</div>
    <p><b>${esc(w.label || inv.status)}</b>${inv.status === 'incomplete' ? ' · Available evidence sent for review; report incomplete.' : ''}</p>
    <p>${esc(f?.label || (inv.status === 'aborted_urgent' ? 'Investigation stopped for the urgent alert.' : 'Clinical follow-up starts after the evidence handover.'))}</p>
    ${w.report_ready && !f?.closed ? '<p style="font-size:13px">Report preparation does not close the case. A clinician must record action, assess new follow-up evidence, and close it.</p>' : ''}
    <details><summary>Evidence actions and context sources</summary><ul>${events || '<li>Workflow trace unavailable for this older investigation.</li>'}</ul><h4>Context sources</h4><ul>${sources || '<li>No context snapshot recorded.</li>'}</ul>
    ${d1 ? `<h4>Supplementary D1 findings</h4><ul>${d1}</ul>` : ''}</details>
  </div>`;
};
