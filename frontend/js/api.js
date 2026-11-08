// ── HireMind — connection to the backend API ──────────────────────────────
// Pages are served by the backend (http://127.0.0.1:8000/...), so the API is on the same origin.
const API = '';
const Auth = {
  get token() { try { return localStorage.getItem('hm_token'); } catch { return null; } },
  set token(t) { try { t ? localStorage.setItem('hm_token', t) : localStorage.removeItem('hm_token'); } catch {} },
  user: null,
};

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function api(path, { method = 'GET', body, form, raw } = {}) {
  const headers = {};
  if (Auth.token) headers['Authorization'] = 'Bearer ' + Auth.token;
  let payload;
  if (form) payload = form;                              // FormData (file upload) or URLSearchParams (login)
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401 && !path.startsWith('/api/auth/login')) { Auth.token = null; location.href = 'login.html'; throw new Error('Signed out'); }
  if (raw) return res;
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const d = data && data.detail;
    const msg = Array.isArray(d) ? d.map(e => (e.loc ? e.loc.slice(-1)[0] + ': ' : '') + e.msg).join('; ') : (d || res.statusText);
    throw new Error(msg);
  }
  return data;
}

// Run a page action and show its error as a toast instead of failing silently
async function act(fn, okMessage) {
  try { const r = await fn(); if (okMessage) showToast(okMessage, 'success'); return r; }
  catch (e) { showToast(esc(e.message), 'error', 5000); throw e; }
}

// Every page except login calls this first: it loads the signed-in user or sends them to login
async function requireUser(roles) {
  if (!Auth.token) { location.href = 'login.html'; return new Promise(() => {}); }
  Auth.user = await api('/api/auth/me');
  if (roles && !roles.includes(Auth.user.role)) {
    location.href = Auth.user.role === 'candidate' ? 'portal.html' : 'index.html';
    return new Promise(() => {});
  }
  return Auth.user;
}

function logout() { Auth.token = null; location.href = 'login.html'; }

function fmtScore(s) { return s === null || s === undefined ? '—' : Math.round(s); }
function fmtDate(d) { return d ? new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'; }
function statusBadge(s) {
  const map = { draft: 'badge-violet', published: 'badge-teal', closed: 'badge-rose', submitted: 'badge-sky', assessment: 'badge-amber',
    decided: 'badge-violet', hired: 'badge-emerald', not_hired: 'badge-rose', withdrawn: 'badge-rose', parsed: 'badge-teal',
    failed: 'badge-rose', corrected: 'badge-amber', advance: 'badge-emerald', hold: 'badge-amber', reject: 'badge-rose',
    provisional: 'badge-amber', final: 'badge-teal', graded: 'badge-teal', expired: 'badge-rose', assigned: 'badge-sky',
    in_progress: 'badge-amber', approved: 'badge-teal', released: 'badge-emerald', discarded: 'badge-rose' };
  return `<span class="badge ${map[s] || 'badge-sky'}">${esc(String(s || '—').replace('_', ' '))}</span>`;
}

// Job picker shared by the HR screens; remembers the last job chosen
async function jobPicker(containerId, onChange) {
  const jobs = await api('/api/jobs');
  const el = document.getElementById(containerId);
  if (!jobs.length) { el.innerHTML = '<span style="color:var(--mist);font-size:13px">No jobs yet — create one in Job Postings.</span>'; return null; }
  let saved; try { saved = Number(localStorage.getItem('hm_job')); } catch {}
  const current = jobs.find(j => j.id === saved) ? saved : jobs[0].id;
  el.innerHTML = `<select class="form-select" style="min-width:260px">${jobs.map(j =>
    `<option value="${j.id}" ${j.id === current ? 'selected' : ''}>${esc(j.title)} (${esc(j.status)})</option>`).join('')}</select>`;
  el.querySelector('select').onchange = e => { try { localStorage.setItem('hm_job', e.target.value); } catch {} onChange(Number(e.target.value)); };
  onChange(current);
  return current;
}

function modal(html) {
  let m = document.getElementById('hm-modal');
  if (!m) {
    m = document.createElement('div'); m.id = 'hm-modal'; m.className = 'hm-modal';
    m.onclick = e => { if (e.target === m) closeModal(); };
    document.body.appendChild(m);
  }
  m.innerHTML = `<div class="hm-modal-box">${html}</div>`; m.classList.add('open');
  return m;
}
function closeModal() { const m = document.getElementById('hm-modal'); if (m) m.classList.remove('open'); }
