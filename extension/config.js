// Where the extension delivers the captured Aztek session.
//
// Local development defaults to the dev server on port 8000. Before sharing the
// extension for a real deployment, change BACKEND_ORIGIN to your Render URL
// (for example "https://all-for-cabal.onrender.com"), add that same origin to
// "host_permissions" in manifest.json, then reload the extension from
// chrome://extensions. This file holds only the backend origin — nothing private.
const BACKEND_ORIGIN = 'http://localhost:8000';
