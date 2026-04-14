/**
 * Haupt-App: Dashboard, WebSocket, UI-Steuerung.
 */

import api from './api.js';
import { Cube3D } from './cube3d.js';
import { Wizard } from './wizard.js';
import { ShortcutManager } from './shortcuts.js';
import { renderHotkeysEditor, pynputToDisplay } from './hotkeys_editor.js';

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
const paramsBar    = document.getElementById('params-bar');
const cubeCanvas   = document.getElementById('cube-canvas');
const toastCont    = document.getElementById('toast-container');
const wizardEl     = document.getElementById('wizard-overlay');
const settingsEl   = document.getElementById('settings-overlay');
const settingsBody = document.getElementById('settings-body');

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
  brightnessEl.value      = bri;
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

  document.getElementById('btn-wizard').addEventListener('click', () => wizard.show());

  // Ausrichtungs-Button
  let alignActive = false;
  const btnAlign = document.getElementById('btn-align');
  btnAlign.addEventListener('click', () => {
    if (alignActive) {
      fetch('/align/stop', { method: 'POST' }).catch(console.error);
      btnAlign.textContent = 'Ausrichten';
      btnAlign.classList.remove('active');
      alignActive = false;
    } else {
      fetch('/align/all', { method: 'POST' }).catch(console.error);
      btnAlign.textContent = 'Ausrichten ✕';
      btnAlign.classList.add('active');
      alignActive = true;
    }
  });

  // Settings-Button
  document.getElementById('btn-settings').addEventListener('click', openSettings);
  document.getElementById('settings-close').addEventListener('click', closeSettings);
  document.getElementById('settings-cancel').addEventListener('click', closeSettings);
  document.getElementById('settings-save').addEventListener('click', saveSettings);
  settingsEl.addEventListener('click', (e) => {
    if (e.target === settingsEl) closeSettings();
  });

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

  document.getElementById('btn-next').addEventListener('click', () => {
    api.nextAnimation().then(r => {
      if (r.animation) setActive(r.animation, false);
    }).catch(console.error);
  });

  // Aktuellen Status abfragen
  api.status().then(s => {
    setActive(s.animation, s.preview ?? true);
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

    const combo = settings.hotkey_shortcuts?.per_animation?.[name] || null;
    const scLabel = combo ? pynputToDisplay(combo) : '';
    li.innerHTML = `
      <span class="anim-name">${name}</span>
      <div class="anim-actions">
        ${scLabel ? `<span class="anim-shortcut">${scLabel}</span>` : ''}
        <button class="btn-icon btn-play" title="Auf Hardware abspielen">&#9654;</button>
      </div>
    `;
    li.querySelector('.anim-name').addEventListener('click', () => startAnimation(name));
    li.querySelector('.btn-play').addEventListener('click', (e) => {
      e.stopPropagation();
      fetch(`/animation/${name}`, { method: 'POST' })
        .then(() => setActive(name, false))
        .catch(console.error);
    });
    animList.appendChild(li);
  }
}

function setActive(name, preview = true) {
  activeAnim = name;
  animList.querySelectorAll('.anim-item').forEach(el => {
    el.classList.toggle('active', el.dataset.name === name);
  });
  if (name === 'none') {
    statusPill.textContent = 'Gestoppt';
    statusPill.className   = 'status-pill stopped';
  } else if (preview) {
    statusPill.textContent = `${name} ▸ Preview`;
    statusPill.className   = 'status-pill preview';
  } else {
    statusPill.textContent = name;
    statusPill.className   = 'status-pill running';
  }
  renderParams(name);
}

// ---- Animation starten ----
async function startAnimation(name) {
  try {
    const saved = settings.animation_params?.[name];
    if (saved && Object.keys(saved).length > 0) {
      await api.startWithParams(name, saved);
    } else {
      await api.startAnimation(name);
    }
    setActive(name);
  } catch (e) {
    showToast(`Fehler: ${e.message}`, 'error');
  }
}

// ---- Params ----
function renderParams(name) {
  paramsBar.innerHTML = '';
  paramsBar.classList.add('hidden');
  if (name === 'none' || !animations[name]) return;

  const params = animations[name].params || {};
  if (Object.keys(params).length === 0) return;

  paramsBar.classList.remove('hidden');

  const savedParams = settings.animation_params?.[name] || {};

  for (const [pName, pInfo] of Object.entries(params)) {
    const type  = pInfo.type || 'float';
    const def   = savedParams[pName] ?? pInfo.default ?? 0;
    const label = pInfo.label || pName;

    const group = document.createElement('div');
    group.className = 'param-group';

    if (type === 'hue') {
      const hue360 = Math.round(def * 360);
      group.innerHTML = `
        <label>${label}</label>
        <div class="hue-picker">
          <input type="range" class="hue-slider" min="0" max="360" step="1" value="${hue360}"
                 data-param="${pName}" data-type="hue">
          <div class="hue-preview" style="background:hsl(${hue360},100%,50%)"></div>
        </div>
      `;
      const input   = group.querySelector('input');
      const preview = group.querySelector('.hue-preview');
      input.addEventListener('input', () => {
        preview.style.background = `hsl(${input.value},100%,50%)`;
      });
      input.addEventListener('change', _onParamChange.bind(null, name));
    } else if (type === 'str') {
      group.innerHTML = `
        <label>${label}</label>
        <input type="text" class="param-text" value="${def}" data-param="${pName}" data-type="str">
      `;
      group.querySelector('input').addEventListener('change', _onParamChange.bind(null, name));
    } else {
      const min  = pInfo.min  ?? 0;
      const max  = pInfo.max  ?? (typeof def === 'number' ? Math.max(20, def * 2) : 20);
      const step = pInfo.step ?? (type === 'int' ? 1 : 0.05);
      const disp = _fmtVal(def, step);
      group.innerHTML = `
        <label>${label}</label>
        <input type="range" min="${min}" max="${max}" step="${step}" value="${def}"
               data-param="${pName}" data-type="${type}">
        <span class="param-val">${disp}</span>
      `;
      const input = group.querySelector('input');
      const val   = group.querySelector('.param-val');
      input.addEventListener('input', () => { val.textContent = _fmtVal(input.value, step); });
      input.addEventListener('change', _onParamChange.bind(null, name));
    }

    paramsBar.appendChild(group);
  }
}

function _fmtVal(v, step) {
  return parseFloat(step) < 1 ? parseFloat(v).toFixed(2) : parseInt(v, 10);
}

function _onParamChange(name) {
  const currentParams = collectParams(name);
  if (!settings.animation_params) settings.animation_params = {};
  settings.animation_params[name] = currentParams;
  api.saveSettings({ animation_params: settings.animation_params }).catch(() => {});
}

function collectParams(name) {
  const result = {};
  paramsBar.querySelectorAll('input[data-param]').forEach(input => {
    const key  = input.dataset.param;
    const type = input.dataset.type || 'float';
    if (type === 'hue') {
      result[key] = Math.round(parseFloat(input.value)) / 360;
    } else if (type === 'int') {
      result[key] = parseInt(input.value, 10);
    } else if (type === 'str') {
      result[key] = input.value;
    } else {
      result[key] = parseFloat(input.value);
    }
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
        <button class="btn-icon btn-reset" data-id="${c.face_id}" title="Reset">&#8635;</button>
      </li>`).join('');
      
    ctrlList.querySelectorAll('.btn-reset').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (confirm(`Controller ${id} wirklich neustarten?`)) {
          api.resetController(id).then(() => {
            showToast(`Reset für Controller ${id} gesendet`, 'success');
            setTimeout(loadControllers, 5000);
          }).catch(err => showToast(`Reset fehlgeschlagen: ${err}`, 'error'));
        }
      });
    });
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
  window._ws_debug = ws;

  ws.onopen = () => {
    wsStatusEl.textContent = '● Live';
    wsStatusEl.className   = 'connected';
  };

  ws.onmessage = (ev) => {
    if (cube3d && ev.data instanceof ArrayBuffer) {
      cube3d.setFrame(ev.data);
    }
  };

  ws.onclose = ws.onerror = () => {
    wsStatusEl.textContent = '○ Getrennt';
    wsStatusEl.className   = 'disconnected';
    wsRetryTimer = setTimeout(connectWS, 3000);
  };
}

// ---- Settings-Modal ----
let _getHotkeyValues = null;

function openSettings() {
  const enabledKeys = settings.enabled_animations || Object.keys(animations);
  const animNames   = Object.keys(animations).filter(n => enabledKeys.includes(n));

  settingsBody.innerHTML = `
    <div class="settings-section-title">Hotkeys (Raspberry Pi Daemon)</div>
    <p class="settings-hint">
      Diese Tastenkürzel werden vom Daemon auf dem Raspberry Pi ausgeführt —
      das Web UI muss dafür <strong>nicht</strong> geöffnet sein.
    </p>
    <div id="hk-editor"></div>
  `;

  const editorEl = settingsBody.querySelector('#hk-editor');
  _getHotkeyValues = renderHotkeysEditor(
    editorEl,
    settings.hotkey_shortcuts || {},
    animNames,
  );

  settingsEl.classList.remove('hidden');
}

function closeSettings() {
  settingsEl.classList.add('hidden');
  _getHotkeyValues = null;
}

async function saveSettings() {
  if (!_getHotkeyValues) return;
  const hotkeys = _getHotkeyValues();
  try {
    settings = await api.saveSettings({ hotkey_shortcuts: hotkeys });
    renderAnimList();  // Shortcut-Labels in der Sidebar aktualisieren
    showToast('Einstellungen gespeichert', 'success');
    closeSettings();
  } catch (e) {
    showToast('Fehler beim Speichern', 'error');
  }
}

// ---- Web-UI Shortcuts ----
function handleShortcut(action) {
  const keys     = Object.keys(animations);
  const enabled  = settings.enabled_animations || keys;
  const available = keys.filter(k => enabled.includes(k));

  if (action === '__stop__') {
    api.stop().then(() => setActive('none')).catch(() => {});
    return;
  }
  if (action === '__next__') {
    const idx  = available.indexOf(activeAnim);
    const next = available[(idx + 1) % available.length];
    if (next) startAnimation(next);
    return;
  }
  if (action === '__random__') {
    const pick = available[Math.floor(Math.random() * available.length)];
    if (pick) startAnimation(pick);
    return;
  }
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
