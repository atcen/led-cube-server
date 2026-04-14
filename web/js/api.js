/**
 * API-Wrapper für den WLED Cube Server.
 */

const API_BASE = window.location.origin;

async function apiFetch(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(API_BASE + path, opts);
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status}`);
  return r.json();
}

const api = {
  status:           ()         => apiFetch('GET',  '/status'),
  animations:       ()         => apiFetch('GET',  '/animations'),
  // Preview: läuft im Server, kein UDP an die Controller
  startAnimation:   (name)     => apiFetch('POST', `/preview/${name}`),
  startWithParams:  (name, p)  => apiFetch('POST', `/preview/${name}/params`, p),
  // Hardware: sendet direkt an die Controller (für Hotkeys)
  hardwareStart:    (name)     => apiFetch('POST', `/animation/${name}`),
  stop:             ()         => apiFetch('POST', '/stop'),
  brightness:       (v)        => apiFetch('POST', `/brightness/${v}`),
  getSettings:      ()         => apiFetch('GET',  '/settings'),
  saveSettings:     (data)     => apiFetch('POST', '/settings', data),
  controllers:      ()         => apiFetch('GET',  '/controllers/status'),
  alignFace:        (id)       => apiFetch('POST', `/align/${id}`),
  alignStop:        ()         => apiFetch('POST', '/align/stop'),
};

export default api;
