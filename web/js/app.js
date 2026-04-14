/**
 * Haupt-App: Dashboard, WebSocket, UI-Steuerung.
 */

import api from './api.js';
import { Cube3D } from './cube3d.js';
import { Wizard } from './wizard.js';
import { ShortcutManager } from './shortcuts.js';

// ---- State ----
let cube3d       = null;
let ws           = null;
let wsRetryTimer = null;
let animations   = {};
let settings     = {};
let activeAnim   = 'none';
const shortcuts  = new ShortcutManager();

// ---- DOM refs ----
const animList     = document.getElementById('anim-list');
const ctrlList     = document.getElementById('ctrl-list');
const brightnessEl = document.getElementById('brightness');
const brightValEl  = document.getElementById('brightness-val');
const statusPill   = document.getElementById('status-pill');
const wsStatusEl   = document.getElementById('ws-status');
const btnStop      = document.getElementById('btn-stop');
const paramsPanel  = document.getElementById('params-panel');
const cubeCanvas   = document.getElementById('cube-canvas');
const toastCont    = document.getElementById('toast-container');
const wizardEl     = document.getElementById('wizard-overlay');

// ---- Init ----
async function init() {
  // LED-Mapping laden
  let mapping;
  try {
    const r = await fetch('/ui/js/led_mapping.json');
    mapping = await r.json();
  } catch (e) {
    console.error('LED-Mapping nicht gefunden:', e);
    mapping = { mapping: Array(480).fill([0, 0]), width: 32, height: 15 };
  }

  // 3D-Würfel init
  cube3d = new Cube3D(cubeCanvas, mapping);

  // Daten laden
  [animations, settings] = await Promise.all([
    api.animations().catch(() => ({})),
    api.getSettings().catch(() => ({})),
  ]);

  // Brightness initialisieren
  const bri = settings.brightness ?? 128;
  brightnessEl.value   = bri;
  brightValEl.textContent = bri;

  // Animations-Liste rendern
  renderAnimList();

  // Controller-Status laden
  loadControllers();

  // Shortcuts laden
  shortcuts.loadFromSettings(
    settings.keyboard_shortcuts,
    Object.keys(animations),
    handleShortcut,
  );

  // WebSocket verbinden
  connectWS();

  // Wizard — falls Setup nicht abgeschlossen
  const wizard = new Wizard(wizardEl, async (newSettings) => {
    settings = newSettings;
    renderAnimList();
    shortcuts.loadFromSettings(
      settings.keyboard_shortcuts,
      Object.keys(animations),
      handleShortcut,
    );
    showToast('Setup abgeschlossen!', 'success');
  });

  if (!settings.setup_complete) {
    wizard.show();
  }

  // Wizard über Einstellungs-Button erneut öffnen
  document.getElementById('btn-wizard').addEventListener('click', () => wizard.show());

  // Event-Listener
  brightnessEl.addEventListener('input', () => {
    brightValEl.textContent = brightnessEl.value;
  });
  brightnessEl.addEventListener('change', () => {
    api.brightness(+brightnessEl.value).catch(console.error);
  });

  btnStop.addEventListener('click', () => {
    api.stop().then(() => setActive('none')).catch(console.error);
  });

  // Aktuellen Status abfragen
  api.status().then(s => {
    setActive(s.animation);
    if (s.brightness != null) {
      brightnessEl.value      = s.brightness;
      brightValEl.textContent = s.brightness;
    }
  }).catch(() => {});
}

// ---- Animations-Liste ----
function renderAnimList() {
  const enabled = settings.enabled_animations;
  animList.innerHTML = '';

  for (const [name] of Object.entries(animations)) {
    if (enabled && !enabled.includes(name)) continue;

    const li = document.createElement('li');
    li.className = 'anim-item' + (name === activeAnim ? ' active' : '');
    li.dataset.name = name;

    const sc = settings.keyboard_shortcuts?.per_animation?.[name] || '';
    li.innerHTML = `
      <span class="anim-name">${name}</span>
      ${sc ? `<span class="anim-shortcut">${sc}</span>` : ''}
    `;
    li.addEventListener('click', () => startAnimation(name));
    animList.appendChild(li);
  }
}

function setActive(name) {
  activeAnim = name;
  animList.querySelectorAll('.anim-item').forEach(el => {
    el.classList.toggle('active', el.dataset.name === name);
  });
  statusPill.textContent = name === 'none' ? 'Gestoppt' : name;
  statusPill.className   = 'status-pill ' + (name === 'none' ? 'stopped' : 'running');
  renderParams(name);
}

// ---- Animation starten ----
async function startAnimation(name) {
  try {
    await api.startAnimation(name);
    setActive(name);
  } catch (e) {
    showToast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Params ----
function renderParams(name) {
  paramsPanel.innerHTML = '';
  if (name === 'none' || !animations[name]) return;

  const params = animations[name].params || {};
  if (Object.keys(params).length === 0) return;

  const savedParams = settings.animation_params?.[name] || {};

  for (const [pName, pInfo] of Object.entries(params)) {
    const def = savedParams[pName] ?? pInfo.default ?? 0;
    const isFloat = typeof def === 'number' && !Number.isInteger(def);

    const group = document.createElement('div');
    group.className = 'param-group';

    const min  = 0;
    const max  = isFloat ? 1 : 20;
    const step = isFloat ? 0.01 : 1;

    group.innerHTML = `
      <label>${pName}</label>
      <input type="range" min="${min}" max="${max}" step="${step}" value="${def}" data-param="${pName}">
      <span class="param-val">${def}</span>
    `;

    const input = group.querySelector('input');
    const val   = group.querySelector('.param-val');

    input.addEventListener('input', () => {
      val.textContent = input.value;
    });

    input.addEventListener('change', () => {
      const currentParams = collectParams(name);
      api.startWithParams(name, currentParams).catch(console.error);

      // Param-Einstellungen speichern
      if (!settings.animation_params) settings.animation_params = {};
      settings.animation_params[name] = currentParams;
      api.saveSettings({ animation_params: settings.animation_params }).catch(() => {});
    });

    paramsPanel.appendChild(group);
  }
}

function collectParams(name) {
  const result = {};
  paramsPanel.querySelectorAll('input[data-param]').forEach(input => {
    const key = input.dataset.param;
    const val = input.step && parseFloat(input.step) < 1
      ? parseFloat(input.value)
      : parseInt(input.value, 10);
    result[key] = val;
  });
  return result;
}

// ---- Controller-Status ----
async function loadControllers() {
  ctrlList.innerHTML = '<li style="color:var(--text-dim);font-size:12px">Lädt…</li>';
  try {
    const ctrls = await api.controllers();
    ctrlList.innerHTML = ctrls.map(c => `
      <li class="ctrl-item">
        <span class="ctrl-dot ${c.online ? 'online' : 'offline'}"></span>
        <span class="ctrl-face">${c.face}</span>
        <span class="ctrl-ip">${c.ip}</span>
      </li>`).join('');
  } catch (e) {
    ctrlList.innerHTML = '<li style="color:var(--danger);font-size:12px">Fehler</li>';
  }
}

// ---- WebSocket ----
function connectWS() {
  if (wsRetryTimer) clearTimeout(wsRetryTimer);
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    wsStatusEl.textContent = '● Live';
    wsStatusEl.className   = 'connected';
  };

  ws.onmessage = (ev) => {
    if (cube3d && ev.data instanceof ArrayBuffer) {
      cube3d.updateFrame(ev.data);
    }
  };

  ws.onclose = ws.onerror = () => {
    wsStatusEl.textContent = '○ Getrennt';
    wsStatusEl.className   = 'disconnected';
    wsRetryTimer = setTimeout(connectWS, 3000);
  };
}

// ---- Shortcuts ----
function handleShortcut(action) {
  const keys = Object.keys(animations);
  const enabled = settings.enabled_animations || keys;
  const available = keys.filter(k => enabled.includes(k));

  if (action === '__stop__') {
    api.stop().then(() => setActive('none')).catch(() => {});
    return;
  }
  if (action === '__next__') {
    const idx = available.indexOf(activeAnim);
    const next = available[(idx + 1) % available.length];
    if (next) startAnimation(next);
    return;
  }
  if (action === '__random__') {
    const pick = available[Math.floor(Math.random() * available.length)];
    if (pick) startAnimation(pick);
    return;
  }
  // Direkte Animation
  if (available.includes(action)) {
    startAnimation(action);
  }
}

// ---- Toast ----
function showToast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  toastCont.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ---- Start ----
document.addEventListener('DOMContentLoaded', init);
