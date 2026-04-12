/**
 * JoyVet Care — main app JS.
 * Loaded on every page. Initialises Alpine.js helpers, HTMX config,
 * and wires up offline/online events.
 */

// ── HTMX global config ─────────────────────────────────────────────────────

// Attach CSRF token to every HTMX request
document.addEventListener('htmx:configRequest', evt => {
  evt.detail.headers['X-CSRFToken'] = getCsrfToken();
});

// Show loading indicator during HTMX requests
document.addEventListener('htmx:beforeRequest', () => {
  document.body.classList.add('htmx-loading');
});
document.addEventListener('htmx:afterRequest', () => {
  document.body.classList.remove('htmx-loading');
});

// HTMX error handling
document.addEventListener('htmx:responseError', evt => {
  const status = evt.detail.xhr.status;
  if (status === 401 || status === 403) {
    showToast('Session expired — please log in again', 'error');
    setTimeout(() => window.location.href = '/accounts/login/', 2000);
  } else if (status === 500) {
    showToast('Server error — please try again', 'error');
  }
});

// ── Online / Offline events ────────────────────────────────────────────────

window.addEventListener('online', () => {
  showToast('Back online — syncing queued changes…', 'info');
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then(sw => {
      if ('sync' in sw) sw.sync.register('joyvet-offline-queue');
    });
  }
});

window.addEventListener('offline', () => {
  showToast('Offline mode — changes will sync when LAN is restored', 'warning');
});

// ── Utility functions ──────────────────────────────────────────────────────

function getCsrfToken() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))?.split('=')[1] ?? '';
}

/**
 * Format a number as IDR: formatIDR(1250000) → "Rp 1.250.000"
 */
function formatIDR(amount) {
  return 'Rp ' + parseInt(amount).toLocaleString('id-ID');
}

/**
 * Debounce a function call.
 */
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Alpine.js magic helpers ────────────────────────────────────────────────

document.addEventListener('alpine:init', () => {

  // $formatIDR magic — use in templates: x-text="$formatIDR(total)"
  Alpine.magic('formatIDR', () => formatIDR);

  // $confirm magic — use instead of window.confirm for consistency
  Alpine.magic('confirm', () => async (message) => {
    return window.confirm(message);
  });

});

// ── Dark mode persistence on page load ────────────────────────────────────

// Applied before Alpine loads to prevent flash
(function () {
  if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
  }
})();
