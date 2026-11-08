// HireMind — small shared helpers used by every page

// Mark the menu item of the current page
function initNav() {
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-item').forEach(item => {
    if ((item.getAttribute('href') || '') === current) item.classList.add('active');
  });
}

// Short confirmation or error message in the corner
function showToast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
  toast.innerHTML = `<div>${message}</div>
    <button aria-label="Dismiss" onclick="this.parentElement.remove()" style="margin-left:auto;background:none;border:none;color:inherit;cursor:pointer;font-size:16px;padding:0 0 0 8px">×</button>`;
  container.appendChild(toast);
  setTimeout(() => (toast.style.opacity = '0'), duration - 300);
  setTimeout(() => toast.remove(), duration);
}

document.addEventListener('DOMContentLoaded', initNav);
