// Collects the current Aztek browser session and hands it to the backend using
// a one-time pairing token. The user's Aztek login credentials are never read,
// stored, or transmitted — only the resulting cookies and localStorage.
'use strict';

const AZTEK_ORIGIN = 'https://aztek-tools.combo-interactive.com';
const AZTEK_COOKIE_DOMAIN = 'aztek-tools.combo-interactive.com';

function setStatus(message, kind) {
  const el = document.getElementById('status');
  el.textContent = message;
  el.dataset.kind = kind || '';
}

function toPlaywrightSameSite(value) {
  // chrome.cookies sameSite -> Playwright storage_state sameSite
  switch (value) {
    case 'strict':
      return 'Strict';
    case 'no_restriction':
      return 'None';
    case 'lax':
      return 'Lax';
    default:
      return 'Lax';
  }
}

function toPlaywrightCookie(cookie) {
  const converted = {
    name: cookie.name,
    value: cookie.value,
    domain: cookie.domain,
    path: cookie.path || '/',
    httpOnly: Boolean(cookie.httpOnly),
    secure: Boolean(cookie.secure),
    sameSite: toPlaywrightSameSite(cookie.sameSite),
  };
  if (cookie.session === false && typeof cookie.expirationDate === 'number') {
    converted.expires = Math.round(cookie.expirationDate);
  } else {
    converted.expires = -1;
  }
  return converted;
}

async function findActiveAztekTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab || !tab.url) {
    return null;
  }
  try {
    return new URL(tab.url).origin === AZTEK_ORIGIN ? tab : null;
  } catch (error) {
    return null;
  }
}

async function readLocalStorage(tabId) {
  try {
    const response = await chrome.tabs.sendMessage(
      tabId, { type: 'afc-read-local-storage' });
    if (response && Array.isArray(response.localStorage)) {
      return response.localStorage;
    }
  } catch (error) {
    // Content script not ready on this page; proceed with cookies only.
  }
  return [];
}

async function connect() {
  const button = document.getElementById('connect');
  const tokenInput = document.getElementById('token');
  const labelInput = document.getElementById('label');
  const token = tokenInput.value.trim();
  if (!token) {
    setStatus('กรุณาวางรหัสจับคู่ก่อน', 'error');
    return;
  }

  button.disabled = true;
  setStatus('กำลังเชื่อมต่อ…', '');
  try {
    const tab = await findActiveAztekTab();
    if (!tab) {
      setStatus('เปิดแท็บ Aztek ที่ล็อกอินแล้วให้อยู่หน้าปัจจุบัน แล้วลองใหม่', 'error');
      return;
    }

    const cookies = await chrome.cookies.getAll({ domain: AZTEK_COOKIE_DOMAIN });
    if (!cookies.length) {
      setStatus('ไม่พบคุกกี้ Aztek — กรุณาล็อกอิน Aztek ก่อน', 'error');
      return;
    }

    const localStorageEntries = await readLocalStorage(tab.id);
    const payload = {
      pairing_token: token,
      account_label: labelInput.value.trim(),
      storage_state: {
        cookies: cookies.map(toPlaywrightCookie),
        origins: localStorageEntries.length
          ? [{ origin: AZTEK_ORIGIN, localStorage: localStorageEntries }]
          : [],
      },
    };

    const response = await fetch(BACKEND_ORIGIN + '/api/aztek/pair', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      const body = await response.json().catch(() => ({}));
      const label = body && body.account_label ? ' (' + body.account_label + ')' : '';
      setStatus('เชื่อมต่อสำเร็จ' + label, 'ok');
      tokenInput.value = '';
    } else if (response.status === 404) {
      setStatus('ไม่พบรหัสจับคู่ — ตรวจสอบว่าคัดลอกครบถ้วน', 'error');
    } else if (response.status === 410) {
      setStatus('รหัสจับคู่หมดอายุหรือถูกใช้ไปแล้ว — ขอรหัสใหม่จากหน้า /account', 'error');
    } else if (response.status === 422) {
      setStatus('เซสชัน Aztek ไม่ถูกต้อง — ลองล็อกอิน Aztek ใหม่แล้วเชื่อมอีกครั้ง', 'error');
    } else if (response.status === 429) {
      setStatus('พยายามบ่อยเกินไป — รอสักครู่แล้วลองใหม่', 'error');
    } else {
      setStatus('เชื่อมต่อไม่สำเร็จ (สถานะ ' + response.status + ')', 'error');
    }
  } catch (error) {
    setStatus('เชื่อมต่อ backend ไม่ได้ — ตรวจสอบ BACKEND_ORIGIN และว่าเซิร์ฟเวอร์เปิดอยู่', 'error');
  } finally {
    button.disabled = false;
  }
}

document.getElementById('connect').addEventListener('click', connect);
