/* ============================================================
   MediWallet – API Client
   All calls use fetch() with session cookies (credentials:include).
   Non-2xx responses throw an APIError with .status and .message.
   ============================================================ */

const API_BASE = '/api';

class APIError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'APIError';
    this.status = status;
  }
}

/**
 * Core request function.
 * @param {string} method   HTTP method
 * @param {string} path     Path appended to /api
 * @param {*}      body     Object (JSON) or FormData
 * @param {boolean} isForm  True for multipart uploads
 */
async function req(method, path, body = null, isForm = false) {
  const opts = {
    method,
    credentials: 'include',
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = isForm ? body : JSON.stringify(body);

  let res;
  try {
    res = await fetch(API_BASE + path, opts);
  } catch (e) {
    throw new APIError('Network error — please check your connection.', 0);
  }

  let json = {};
  try { json = await res.json(); } catch (_) { /* empty body */ }

  if (!res.ok) {
    throw new APIError(json.error || `Request failed (${res.status})`, res.status);
  }
  return json;
}

/* ── Auth ─────────────────────────────────────────────────── */
const auth = {
  register: (d)  => req('POST', '/auth/register', d),
  login:    (d)  => req('POST', '/auth/login', d),
  logout:   ()   => req('POST', '/auth/logout'),
  me:       ()   => req('GET',  '/auth/me'),
  changePassword: (d) => req('POST', '/auth/change-password', d),
};

/* ── Profile ──────────────────────────────────────────────── */
const profile = {
  get:          ()  => req('GET',  '/profile/'),
  update:       (d) => req('PUT',  '/profile/', d),
  completeness: ()  => req('GET',  '/profile/completeness'),
};

/* ── Records ──────────────────────────────────────────────── */
const records = {
  upload: (formData) => req('POST', '/records/upload', formData, true),

  list: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    ).toString();
    return req('GET', `/records/${qs ? '?' + qs : ''}`);
  },

  get:     (id)      => req('GET',    `/records/${id}`),
  update:  (id, d)   => req('PATCH',  `/records/${id}`, d),
  delete:  (id)      => req('DELETE', `/records/${id}`),
  medicineHistory: () => req('GET', '/records/history/medicines'),

  /** Health folder categorization endpoints */
  healthFolders: () => req('GET', '/records/health-folders'),
  healthFolder:  (category) => req('GET', `/records/health-folders/${encodeURIComponent(category)}`),
  folderNames:   () => req('GET', '/records/folders/names'),
  recategorize:  (id)       => req('POST', `/records/${id}/recategorize`),

  /** Returns a direct URL (no fetch — used for <a> download links) */
  downloadUrl: (id) => `${API_BASE}/records/${id}/download`,
};

/* ── Sharing ──────────────────────────────────────────────── */
const share = {
  create:  (d)     => req('POST',   '/share/create', d),
  view:    (token) => req('GET',    `/share/view/${token}`),
  list:    ()      => req('GET',    '/share/'),
  revoke:  (id)    => req('DELETE', `/share/${id}/revoke`),
  history: (id)    => req('GET',    `/share/${id}/history`),
  downloadUrl: (token, recordId) => `${API_BASE}/share/view/${token}/download/${recordId}`,
};

/* ── Emergency ────────────────────────────────────────────── */
const emergency = {
  summary: () => req('GET', '/emergency-summary'),
};

window.api = { auth, profile, records, share, emergency, APIError };

/* ── Session helpers ──────────────────────────────────────── */

/**
 * Fetch the current user.  Returns null if unauthenticated (401).
 * Any other error is re-thrown.
 */
async function getCurrentUser() {
  try {
    const data = await auth.me();
    return data.user;
  } catch (e) {
    if (e.status === 401) return null;
    throw e;
  }
}

/**
 * Redirect to /login if not authenticated.
 * Call at the top of every protected page.
 */
async function requireAuth() {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = '/login';
    return null;
  }
  return user;
}

/**
 * Redirect authenticated users away from the login/register page.
 */
async function redirectIfAuthenticated(to = '/dashboard') {
  const user = await getCurrentUser();
  if (user) window.location.href = to;
}

window.requireAuth = requireAuth;
window.getCurrentUser = getCurrentUser;
window.redirectIfAuthenticated = redirectIfAuthenticated;

/* ── UI helpers ───────────────────────────────────────────── */

function toast(message, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.getElementById('toast-container')
    || (() => {
      const el = document.createElement('div');
      el.id = 'toast-container';
      document.body.appendChild(el);
      return el;
    })();

  const el = document.createElement('div');
  el.className = `toast t-${type}`;
  el.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-text">${message}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
  container.appendChild(el);

  setTimeout(() => {
    el.style.animation = 'toastOut .3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('open'); document.body.style.overflow = 'hidden'; }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('open'); document.body.style.overflow = ''; }
}

/** Close modal when clicking the overlay backdrop */
document.addEventListener('click', e => {
  if (e.target.classList.contains('overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

function setLoading(btn, loading, text = '') {
  if (!btn) return;
  if (loading) {
    btn.dataset.origText = btn.innerHTML;
    btn.innerHTML = `<div class="spinner spinner-sm"></div>${text ? ' ' + text : ''}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.origText || text;
    btn.disabled = false;
  }
}

/** Format a date string nicely */
function fmtDate(str) {
  if (!str) return '—';
  try { return new Date(str).toLocaleDateString('en-IN', { year:'numeric', month:'short', day:'numeric' }); }
  catch { return str; }
}

/** Format a datetime string */
function fmtDatetime(str) {
  if (!str) return '—';
  try { return new Date(str).toLocaleString('en-IN', { year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }); }
  catch { return str; }
}

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/** Get initials from a name */
function initials(name = '') {
  return name.trim().split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

/** Return icon + colour for a document type */
function docTypeMeta(type) {
  const map = {
    prescription: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/></svg>',
      label: 'Prescription',
      cls: 'rec-prescription'
    },
    blood_test: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/></svg>',
      label: 'Blood Test',
      cls: 'rec-blood_test'
    },
    scan: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary-deep)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>',
      label: 'Medical Scan',
      cls: 'rec-scan'
    },
    discharge: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--primary-deep)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>',
      label: 'Discharge Summary',
      cls: 'rec-discharge'
    },
    diagnosis: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M15 2H9a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1Z"/><path d="M9 12h6"/><path d="M9 16h6"/></svg>',
      label: 'Diagnosis',
      cls: 'rec-diagnosis'
    },
    other: {
      icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--taupe)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>',
      label: 'Document',
      cls: 'rec-other'
    },
  };
  return map[type] || map.other;
}

window.toast      = toast;
window.openModal  = openModal;
window.closeModal = closeModal;
window.setLoading = setLoading;
window.fmtDate    = fmtDate;
window.fmtDatetime = fmtDatetime;
window.formatBytes = formatBytes;
window.initials   = initials;
window.docTypeMeta = docTypeMeta;
