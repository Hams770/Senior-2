// Shared navigation template injected into every page
function renderShell(pageTitle, pageSubtitle = '') {
  const pages = [
    { href: 'index.html', icon: '⊞', label: 'Dashboard' },
    { href: 'candidates.html', icon: '👥', label: 'Candidates', badge: '24' },
    { href: 'screening.html', icon: '🔍', label: 'CV Screening' },
    { href: 'scoring.html', icon: '📊', label: 'Scoring Engine' },
    { href: 'verification.html', icon: '✅', label: 'Skill Verification' },
    { href: 'jobs.html', icon: '💼', label: 'Job Postings' },
    { href: 'feedback.html', icon: '💬', label: 'AI Feedback' },
    { href: 'analytics.html', icon: '📈', label: 'Analytics' },
    { href: 'learning.html', icon: '🔄', label: 'Learning Loop' },
    { href: 'settings.html', icon: '⚙️', label: 'Settings' },
  ];
  const navHTML = pages.map(p => `
    <a href="${p.href}" class="nav-item">
      <span class="nav-icon">${p.icon}</span>
      <span>${p.label}</span>
      ${p.badge ? `<span class="nav-badge">${p.badge}</span>` : ''}
    </a>
  `).join('');

  const shell = document.getElementById('app-root');
  if (!shell) return;

  shell.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar-logo">
          <div class="logo-mark">
            <div class="logo-icon">🧠</div>
            <div>
              <div class="logo-text">Smart<span>Recruit</span></div>
              <div class="tagline">AI Recruitment Platform</div>
            </div>
          </div>
        </div>
        <nav class="sidebar-nav">
          <div class="nav-section-label">Platform</div>
          ${navHTML}
        </nav>
        <div class="sidebar-footer">
          <div class="user-card">
            <div class="avatar" style="width:34px;height:34px;font-size:13px">HR</div>
            <div class="user-info">
              <div class="user-name">HR Manager</div>
              <div class="user-role">Administrator</div>
            </div>
            <span style="margin-left:auto;font-size:16px;color:var(--mist)">⋯</span>
          </div>
        </div>
      </aside>
      <div class="main-content">
        <header class="topbar">
          <div class="topbar-title">${pageTitle}${pageSubtitle ? ` <span>${pageSubtitle}</span>` : ''}</div>
          <div class="search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" placeholder="Search candidates, jobs…">
          </div>
          <div class="topbar-actions">
            <a href="screening.html" class="icon-btn" title="New Screening">➕</a>
            <div class="icon-btn" title="Notifications">
              🔔
              <span class="notif-dot"></span>
            </div>
            <div class="icon-btn" title="Help">❓</div>
          </div>
        </header>
        <main class="page-content" id="page-body"></main>
      </div>
    </div>
    <div class="toast-container"></div>
  `;
  initNav();
}
