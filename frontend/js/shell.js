// Shared navigation, built for the signed-in user's role
function renderShell(pageTitle, pageSubtitle = '') {
  const role = (Auth.user && Auth.user.role) || 'hr';
  const hrPages = [
    { href: 'index.html', icon: '⊞', label: 'Dashboard' },
    { href: 'jobs.html', icon: '💼', label: 'Job Postings' },
    { href: 'candidates.html', icon: '👥', label: 'Candidates' },
    { href: 'screening.html', icon: '🔍', label: 'CV Screening' },
    { href: 'scoring.html', icon: '📊', label: 'Scoring & Ranking' },
    { href: 'verification.html', icon: '✅', label: 'Skill Verification' },
    { href: 'feedback.html', icon: '💬', label: 'Feedback' },
    { href: 'analytics.html', icon: '📈', label: 'Analytics' },
    { href: 'learning.html', icon: '🔄', label: 'Learning Loop', future: true },
    { href: 'settings.html', icon: '⚙️', label: 'Settings' },
  ];
  const candPages = [{ href: 'portal.html', icon: '🏠', label: 'My Applications' }];
  const pages = role === 'candidate' ? candPages : hrPages;
  const navHTML = pages.map(p => `
    <a href="${p.href}" class="nav-item"><span class="nav-icon">${p.icon}</span><span>${p.label}</span>
    ${p.future ? '<span class="nav-badge" style="background:rgba(255,255,255,0.08);color:var(--mist)">future</span>' : ''}</a>`).join('');
  const u = Auth.user || { full_name: '', email: '', role };
  const name = u.full_name || u.email;
  const initials = (name || '?').split(/[\s@.]+/).filter(Boolean).slice(0, 2).map(s => s[0].toUpperCase()).join('');
  const roleLabel = { admin: 'Administrator', hr: 'HR Manager', candidate: 'Candidate' }[role];

  const shell = document.getElementById('app-root');
  if (!shell) return;
  shell.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar-logo"><div class="logo-mark"><div class="logo-icon"><img src="img/logo.svg" alt=""></div>
          <div><div class="logo-text">HireMind</div><div class="tagline">AI-assisted, HR-led recruitment</div></div></div></div>
        <nav class="sidebar-nav"><div class="nav-section-label">${role === 'candidate' ? 'Candidate' : 'Platform'}</div>${navHTML}</nav>
        <div class="sidebar-footer"><div class="user-card">
          <div class="avatar" style="width:34px;height:34px;font-size:13px">${esc(initials)}</div>
          <div class="user-info"><div class="user-name">${esc(name)}</div><div class="user-role">${roleLabel}</div></div>
          <button onclick="logout()" title="Sign out" style="margin-left:auto;background:none;border:none;color:var(--mist);cursor:pointer;font-size:12px">Sign out</button>
        </div></div>
      </aside>
      <div class="main-content">
        <header class="topbar">
          <div class="topbar-title">${pageTitle}${pageSubtitle ? ` <span>${pageSubtitle}</span>` : ''}</div>
          <div class="topbar-actions" id="topbar-actions"></div>
        </header>
        <main class="page-content" id="page-body"></main>
      </div>
    </div>
    <div class="toast-container"></div>`;
  initNav();
}

// Standard page start: sign-in check, shell, then the page's own loader
async function startPage(title, subtitle, roles, load) {
  await requireUser(roles);
  renderShell(title, subtitle);
  try { await load(document.getElementById('page-body')); }
  catch (e) { showToast(esc(e.message), 'error', 6000); }
}
