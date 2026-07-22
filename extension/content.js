// Injected only into Aztek pages (see manifest content_scripts.matches).
// Returns this tab's localStorage entries when the popup asks for them. The
// popup — not this script — is what sends anything to the backend.
'use strict';

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== 'afc-read-local-storage') {
    return false;
  }
  const entries = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const name = localStorage.key(index);
    if (name !== null) {
      entries.push({ name: name, value: localStorage.getItem(name) });
    }
  }
  sendResponse({ origin: location.origin, localStorage: entries });
  return true;
});
