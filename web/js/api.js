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
  previewAnimationParams: (name, p) => apiFetch('POST', `/preview/${name}/params`, p),
  nextAnimation:    ()         => apiFetch('POST', '/animation/next'),
  stop:             ()         => apiFetch('POST', '/stop'),
  brightness:       (v)        => apiFetch('POST', `/brightness/${v}`),
  getSettings:      ()         => apiFetch('GET',  '/settings'),
  saveSettings:     (data)     => apiFetch('POST', '/settings', data),
  controllers:      ()         => apiFetch('GET',  '/controllers/status'),
  resetController:  (id)       => apiFetch('POST', `/controllers/${id}/reset`),

  alignAll:         ()         => apiFetch('POST', '/align/all'),
  alignFace:        (id)       => apiFetch('POST', `/align/${id}`),
  alignStop:        ()         => apiFetch('POST', '/align/stop'),
  alignRotate:      (id)       => apiFetch('POST', `/align/${id}/rotate`),
  alignFlip:        (id)       => apiFetch('POST', `/align/${id}/flip`),
};

export default api;
