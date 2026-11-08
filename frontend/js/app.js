// ── SmartRecruit AI — shared utilities ──────────────────────────────────────

// Mark active nav item based on current page
function initNav() {
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href') || '';
    if (href === current || (current === 'index.html' && href === 'index.html')) {
      item.classList.add('active');
    }
  });
}

// Toast notifications
function showToast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size:18px;flex-shrink:0">${icons[type]||icons.info}</span>
    <div>
      <div style="font-size:13px;font-weight:600;margin-bottom:2px">${type.charAt(0).toUpperCase()+type.slice(1)}</div>
      <div style="font-size:12px;color:var(--mist)">${message}</div>
    </div>
    <button onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;color:var(--mist);cursor:pointer;font-size:16px;padding:0 0 0 8px">×</button>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.style.opacity = '0', duration - 400);
  setTimeout(() => toast.remove(), duration);
}

// Animate numbers counting up
function animateCount(el, target, duration = 1200, suffix = '') {
  const start = Date.now();
  const update = () => {
    const elapsed = Date.now() - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// Animate progress bars
function animateBars() {
  document.querySelectorAll('.progress-fill[data-width]').forEach(bar => {
    const w = bar.dataset.width;
    setTimeout(() => bar.style.width = w, 100);
  });
}

// Animate score rings (SVG)
function animateRings() {
  document.querySelectorAll('.score-ring').forEach(ring => {
    const circle = ring.querySelector('.ring-progress');
    if (!circle) return;
    const score = parseInt(ring.dataset.score || 0);
    const r = parseFloat(circle.getAttribute('r') || 40);
    const circ = 2 * Math.PI * r;
    circle.style.strokeDasharray = circ;
    circle.style.strokeDashoffset = circ;
    setTimeout(() => {
      circle.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)';
      circle.style.strokeDashoffset = circ - (score / 100) * circ;
    }, 200);
  });
}

// Chart mini-sparkline (canvas-free SVG)
function renderSparkline(container, data, color = '#00d4b4') {
  const w = container.offsetWidth || 200, h = 48;
  const max = Math.max(...data), min = Math.min(...data);
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * (h - 8) - 4;
    return `${x},${y}`;
  }).join(' ');
  container.innerHTML = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="width:100%;height:${h}px">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <polyline points="0,${h} ${pts} ${w},${h}" fill="url(#sg)" opacity="0.2"/>
    <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}"/><stop offset="100%" stop-color="${color}" stop-opacity="0"/>
    </linearGradient></defs>
  </svg>`;
}

// Upload zone drag-and-drop
function initUploadZone(zone, onFile) {
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    if (onFile) onFile(e.dataTransfer.files[0]);
  });
  zone.addEventListener('click', () => {
    const inp = document.createElement('input'); inp.type = 'file'; inp.accept = '.pdf,.doc,.docx';
    inp.onchange = () => { if (onFile && inp.files[0]) onFile(inp.files[0]); };
    inp.click();
  });
}

// Simulate AI processing stages
function simulateAIProcessing(steps, onStep, onComplete, delay = 900) {
  let i = 0;
  const run = () => {
    if (i < steps.length) { onStep(steps[i], i); i++; setTimeout(run, delay); }
    else if (onComplete) onComplete();
  };
  run();
}

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  animateBars();
  animateRings();
});
