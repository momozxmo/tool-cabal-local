// Shared plumbing for the tool pages.
//
// Item Code and Event are the same console around a different form: the same
// top bar, the same server picker, the same queue kept in this browser, the
// same log. That part lives here so each page is only its own form.
//
// index.html and bundles.html predate this and still carry their own copies.

const $ = id => document.getElementById(id);
// One chosen server across every page: what is built here is created on the
// server the ids came from.
const GAME_KEY = 'afc.game';

async function apiFetch(url, options) {
  const response = await fetch(url, Object.assign({credentials: 'same-origin'}, options || {}));
  if (response.status === 401) { window.location.replace('/login'); throw new Error('เซสชันหมดอายุ'); }
  return response;
}

function log(message, level = 'INFO') {
  const line = document.createElement('div'); line.className = level;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  $('log').appendChild(line); $('log').scrollTop = $('log').scrollHeight;
}

function paintAztek(status) {
  const badge = $('aztekStatus');
  if (status === 'active') { badge.textContent = 'Aztek: เชื่อมแล้ว'; badge.style.background = '#163b31'; badge.style.color = '#69e0b5'; }
  else if (status === 'expired') { badge.textContent = 'Aztek: หมดอายุ — เชื่อมใหม่'; badge.style.background = '#4a1f24'; badge.style.color = 'var(--red)'; }
  else { badge.textContent = 'Aztek: ยังไม่ได้เชื่อม'; badge.style.background = '#3a2f14'; badge.style.color = 'var(--yellow)'; }
}

// Aztek only takes lowercase, digits and hyphens, so a Thai name cannot become
// a slug on its own — the operator is asked for one instead of being handed a
// silently empty field.
function slugify(text) {
  return String(text || '').trim().toLowerCase()
    .replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

// 'YYYY-MM-DDTHH:MM(:SS)' as the browser's datetime-local gives it, padded to
// seconds because the Aztek picker has a seconds box and 00 is a real answer.
function withSeconds(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  return /T\d{2}:\d{2}$/.test(text) ? text + ':00' : text;
}

function nextKey(prefix) {
  return prefix + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
}

/** A list of half-built things kept in this browser. */
class Queue {
  constructor(storageKey) { this.storageKey = storageKey; this.items = []; this.active = ''; }
  load() {
    try {
      const raw = localStorage.getItem(this.storageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      this.items = Array.isArray(parsed) ? parsed : [];
    } catch (e) { this.items = []; }
  }
  save() { try { localStorage.setItem(this.storageKey, JSON.stringify(this.items)); } catch (e) {} }
  current() { return this.items.find(entry => entry.key === this.active) || null; }
  add(entry) { this.items.push(entry); this.active = entry.key; return entry; }
  removeActive() {
    this.items = this.items.filter(entry => entry.key !== this.active);
    this.active = this.items.length ? this.items[0].key : '';
  }
  clear() { this.items = []; this.active = ''; }
  /** A name nobody else in the queue is using. */
  uniqueName(name) {
    const taken = new Set(this.items.map(entry => entry.name || ''));
    let out = name || 'ใหม่', n = 2;
    while (taken.has(out)) { out = `${name} (${n})`; n++; }
    return out;
  }
}

/** Fill the top bar and the server picker; returns the games on offer. */
async function loadShell(pendingGame) {
  $('btnClearLog').onclick = () => $('log').replaceChildren();
  $('btnLogout').onclick = async () => {
    $('btnLogout').disabled = true;
    try { await fetch('/api/auth/logout', {method: 'POST'}); }
    finally { window.location.replace('/login'); }
  };
  $('game').addEventListener('change', () => {
    try { localStorage.setItem(GAME_KEY, $('game').value); } catch (e) {}
  });
  try {
    const me = await apiFetch('/api/auth/me').then(r => r.json());
    $('currentUser').textContent = me.username ? `ผู้ใช้: ${me.username}` : '';
  } catch (e) {}
  let games = [];
  try {
    const data = await apiFetch('/api/games').then(r => r.json());
    games = data.games || [];
    games.forEach(name => {
      const option = document.createElement('option');
      option.value = option.textContent = name;
      $('game').appendChild(option);
    });
    let want = pendingGame;
    if (!want) try { want = localStorage.getItem(GAME_KEY) || ''; } catch (e) {}
    if (want && games.includes(want)) $('game').value = want;
    try { localStorage.setItem(GAME_KEY, $('game').value); } catch (e) {}
  } catch (e) {}
  try {
    const status = await apiFetch('/api/aztek/status').then(r => r.json());
    paintAztek(status.status);
  } catch (e) { paintAztek('disconnected'); }
  return games;
}

/** Show a full-page screenshot of what was filled in, when there is one. */
function showShot(base64) {
  $('shot').replaceChildren();
  if (!base64) return;
  const img = document.createElement('img');
  img.src = 'data:image/png;base64,' + base64;
  img.style.cssText = 'max-width:100%;border:1px solid var(--edge);border-radius:8px';
  $('shot').appendChild(img);
}

/** Bundles created on the Create Bundle page, waiting to be turned into
 *  something. One-way and consumed once, so a refresh cannot re-add them. */
function drainBundleIds() {
  try {
    const raw = sessionStorage.getItem('afc.codeHandoff');
    if (!raw) return null;
    sessionStorage.removeItem('afc.codeHandoff');
    const payload = JSON.parse(raw);
    return (payload && Array.isArray(payload.rows)) ? payload : null;
  } catch (e) { return null; }
}
