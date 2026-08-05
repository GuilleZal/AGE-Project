/**
 * app.js — Global state, routing, toast, and session management.
 */
import { Auth } from './api.js';
import { initSalesView } from './views/sales.js';
import { initProductsView } from './views/products.js';
import { initCashView } from './views/cash.js';

// ── Session state ───────────────────────────────────────────────────────────
export const session = {
  user: null,
  permissions: null,

  set(user, permissions) {
    this.user = user;
    this.permissions = permissions;
    localStorage.setItem('pos_session', JSON.stringify({ user, permissions }));
  },

  load() {
    try {
      const raw = localStorage.getItem('pos_session');
      if (!raw) return false;
      const { user, permissions } = JSON.parse(raw);
      this.user = user;
      this.permissions = permissions;
      return true;
    } catch { return false; }
  },

  clear() {
    this.user = null;
    this.permissions = null;
    localStorage.removeItem('pos_session');
  },

  hasTab(tab) {
    return this.permissions?.allowed_tabs?.includes(tab) ?? false;
  },
};

// ── Toast ───────────────────────────────────────────────────────────────────
export function toast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      ${type === 'success' ? '<polyline points="20 6 9 17 4 12"/>'
        : type === 'error' ? '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
        : '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
    </svg>
    <span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 250ms';
    setTimeout(() => el.remove(), 250);
  }, duration);
}

// ── Router ───────────────────────────────────────────────────────────────────
const VIEW_MAP = {
  ventas:    '#view-ventas',
  productos: '#view-productos',
  caja:      '#view-caja',
  reportes:  '#view-reportes',
};

const NAV_TAB_MAP = {
  ventas:    'Ventas',
  productos: 'Productos',
  caja:      'Caja',
  reportes:  'Reportes',
};

let currentView = null;

export function navigateTo(viewId) {
  // Check permissions
  const tab = NAV_TAB_MAP[viewId];
  if (tab && !session.hasTab(tab)) {
    toast('No tienes permiso para acceder a esta sección.', 'error');
    return;
  }

  // Hide all views
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

  // Show the requested view
  const viewEl = document.querySelector(VIEW_MAP[viewId]);
  if (viewEl) {
    viewEl.classList.add('active');
    currentView = viewId;
  }

  // Highlight nav item
  document.querySelectorAll('.nav-item[data-view]').forEach(item => {
    item.classList.toggle('active', item.dataset.view === viewId);
  });
}

// ── Login view ───────────────────────────────────────────────────────────────
function initLoginView() {
  const loginView  = document.getElementById('view-login');
  const appShell   = document.getElementById('app');
  const form       = document.getElementById('login-form');
  const userInput  = document.getElementById('login-username');
  const passInput  = document.getElementById('login-password');
  const errDiv     = document.getElementById('login-error');
  const submitBtn  = document.getElementById('login-submit');

  async function doLogin(e) {
    e?.preventDefault();
    const username = userInput.value.trim();
    const password = passInput.value.trim();

    errDiv.classList.remove('visible');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Ingresando...';

    const res = await Auth.login(username, password);

    submitBtn.disabled = false;
    submitBtn.textContent = 'Ingresar';

    if (!res.success) {
      errDiv.textContent = res.error || 'Error desconocido';
      errDiv.classList.add('visible');
      passInput.value = '';
      passInput.focus();
      return;
    }

    session.set(res.data.user, res.data.permissions);
    showApp();
  }

  form.addEventListener('submit', doLogin);

  return { show() { loginView.style.display = 'flex'; appShell.style.display = 'none'; } };
}

// ── App Shell ─────────────────────────────────────────────────────────────────
function showApp() {
  document.getElementById('view-login').style.display = 'none';
  document.getElementById('app').style.display = 'flex';

  // Update user chip
  const u = session.user;
  document.getElementById('user-avatar-initials').textContent =
    (u.username?.[0] ?? '?').toUpperCase();
  document.getElementById('user-name-label').textContent = u.username;
  document.getElementById('user-role-label').textContent  = u.role;

  // Build nav items based on permissions
  buildNav();

  // Navigate to default tab
  const defaultTabs = ['ventas', 'caja', 'productos'];
  const firstAllowed = defaultTabs.find(t => session.hasTab(NAV_TAB_MAP[t]));
  navigateTo(firstAllowed ?? 'ventas');

  // Focus sales search
  setTimeout(() => {
    const searchInput = document.getElementById('barcode-search');
    if (searchInput) searchInput.focus();
  }, 100);
}

function buildNav() {
  const nav = document.getElementById('main-nav');
  nav.innerHTML = '';

  const items = [
    { id: 'ventas',    label: 'Ventas',    tab: 'Ventas',    icon: 'shopping-cart' },
    { id: 'productos', label: 'Productos', tab: 'Productos', icon: 'package' },
    { id: 'caja',      label: 'Caja',      tab: 'Caja',      icon: 'dollar-sign' },
    { id: 'reportes',  label: 'Reportes',  tab: 'Reportes',  icon: 'bar-chart-2' },
  ];

  items.forEach(({ id, label, tab, icon }) => {
    if (!session.hasTab(tab)) return;
    const li = document.createElement('li');
    li.className = 'nav-item';
    li.dataset.view = id;
    li.innerHTML = `${featherIcon(icon)}<span>${label}</span>`;
    li.addEventListener('click', () => navigateTo(id));
    nav.appendChild(li);
  });
}

// ── Logout ────────────────────────────────────────────────────────────────────
async function doLogout() {
  if (session.user?.id) await Auth.logout(session.user.id);
  session.clear();
  document.getElementById('app').style.display = 'none';
  document.getElementById('view-login').style.display = 'flex';
  document.getElementById('login-username').value = '';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').classList.remove('visible');
}

// ── Feather icon helper ───────────────────────────────────────────────────────
function featherIcon(name) {
  const icons = {
    'shopping-cart': `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>`,
    'package':       `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="16 16 12 12 8 16"/><path d="M12 12V3"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>`,
    'dollar-sign':   `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    'bar-chart-2':   `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  };
  return icons[name] ?? '';
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const login = initLoginView();

  // Restore session
  if (session.load()) {
    showApp();
  } else {
    login.show();
    document.getElementById('login-username').focus();
  }

  // Init views
  initSalesView();
  initProductsView();
  initCashView();

  // Logout button
  document.getElementById('logout-btn')?.addEventListener('click', doLogout);

  // Global keyboard shortcuts (F5/F6 for sales)
  document.addEventListener('keydown', (e) => {
    if (currentView !== 'ventas') return;
    if (e.key === 'F5') { e.preventDefault(); window._salesView?.handleF5(); }
    if (e.key === 'F6') { e.preventDefault(); window._salesView?.handleF6(); }
  });
});
