/**
 * JoyVet Care — Offline-first IndexedDB layer using Dexie.js
 *
 * Architecture:
 *   - write_queue: HTMX form submissions captured when navigator.onLine === false
 *   - patient_cache: Local patient search index (refreshed on sync)
 *   - appointment_cache: Today's schedule (refreshed hourly)
 *   - consultation_drafts: Auto-saved SOAP note drafts
 *   - settings: Key-value store for device preferences
 *
 * When the server is reachable (LAN up), everything goes through Django normally.
 * When LAN is down (rare but possible), forms are queued and replayed on reconnect.
 */

import Dexie from 'https://cdn.jsdelivr.net/npm/dexie@3/dist/dexie.mjs';

const db = new Dexie('JoyVetOffline');

db.version(1).stores({
  write_queue:         '++id, url, method, timestamp, status',
  patient_cache:       'id, name, owner_name, phone, species, *searchTerms',
  appointment_cache:   'id, scheduled_at, patient_id, status, branch_id',
  consultation_drafts: 'id, patient_id, last_saved, [patient_id+id]',
  settings:            'key',
});

export default db;

// ── Offline form interception ──────────────────────────────────────────────

document.addEventListener('htmx:beforeRequest', async (evt) => {
  if (navigator.onLine) return; // LAN is up — let HTMX handle it normally

  evt.preventDefault();

  const elt = evt.detail.elt;
  const url = elt.action || evt.detail.pathInfo?.requestPath || window.location.pathname;
  const method = (evt.detail.verb || 'POST').toUpperCase();

  let body = {};
  if (elt instanceof HTMLFormElement) {
    body = Object.fromEntries(new FormData(elt));
  }

  await db.write_queue.add({
    url,
    method,
    data: body,
    timestamp: Date.now(),
    status: 'pending',
  });

  // Schedule a background sync for when LAN comes back
  if ('serviceWorker' in navigator) {
    const sw = await navigator.serviceWorker.ready;
    if ('sync' in sw) {
      await sw.sync.register('joyvet-offline-queue');
    }
  }

  showOfflineToast('Saved offline — will sync when connected');
});

// ── Consultation draft auto-save ───────────────────────────────────────────

let draftSaveTimer = null;

export function enableDraftAutoSave(consultationId, patientId) {
  const SOAP_FIELDS = ['subjective', 'objective', 'assessment', 'plan', 'internal_notes'];

  SOAP_FIELDS.forEach(field => {
    const el = document.getElementById(`id_${field}`);
    if (!el) return;

    el.addEventListener('input', () => {
      clearTimeout(draftSaveTimer);
      draftSaveTimer = setTimeout(() => saveDraft(consultationId, patientId), 2000);
    });
  });
}

async function saveDraft(consultationId, patientId) {
  const SOAP_FIELDS = ['subjective', 'objective', 'assessment', 'plan', 'internal_notes'];
  const data = {};
  SOAP_FIELDS.forEach(f => {
    const el = document.getElementById(`id_${f}`);
    if (el) data[f] = el.value;
  });

  await db.consultation_drafts.put({
    id: consultationId,
    patient_id: patientId,
    data,
    last_saved: Date.now(),
  });
}

export async function loadDraft(consultationId) {
  return db.consultation_drafts.get(consultationId);
}

// ── Patient cache refresh ──────────────────────────────────────────────────

export async function refreshPatientCache(branchId) {
  if (!navigator.onLine) return;

  try {
    const r = await fetch(`/api/v1/patients/?page_size=500`, {
      headers: { 'X-CSRFToken': getCsrfToken() },
    });
    const data = await r.json();
    const patients = data.results || [];

    await db.patient_cache.bulkPut(
      patients.map(p => ({
        id: p.id,
        name: p.name,
        owner_name: p.owner_name,
        phone: p.owner_phone,
        species: p.species,
        searchTerms: [
          p.name.toLowerCase(),
          p.owner_name.toLowerCase(),
          (p.owner_phone || '').replace(/\D/g, ''),
        ].filter(Boolean),
      }))
    );
  } catch (e) {
    console.warn('Patient cache refresh failed', e);
  }
}

export async function searchPatientCache(query) {
  const q = query.toLowerCase();
  return db.patient_cache
    .filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.owner_name.toLowerCase().includes(q) ||
      (p.phone || '').includes(q)
    )
    .limit(15)
    .toArray();
}

// ── Toast helper ───────────────────────────────────────────────────────────

function showOfflineToast(message) {
  if (typeof showToast === 'function') {
    showToast(message, 'warning');
  }
}

function getCsrfToken() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))?.split('=')[1] ?? '';
}
