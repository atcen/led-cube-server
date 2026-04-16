/**
 * Setup-Wizard (7 Schritte).
 */

import api from './api.js';
import { renderHotkeysEditor } from './hotkeys_editor.js';

const STEPS = [
  'Willkommen',
  'Controller-Discovery',
  'Panel-Ausrichtung',
  'Animationen',
  'Shortcuts',
  'Fertig',
];

export class Wizard {
  constructor(overlayEl, onComplete) {
    this.overlay    = overlayEl;
    this.onComplete = onComplete;
    this.step       = 0;
    this.settings   = {};
    this.animations = {};
    this._alignActive = null;

    this._build();
  }

  show() {
    this.overlay.classList.remove('hidden');
    this._renderStep();
  }

  hide() {
    this.overlay.classList.add('hidden');
  }

  // --- Build ---
  _build() {
    this.overlay.innerHTML = `
      <div class="wizard-box">
        <div class="wizard-header">
          <h2 id="wiz-title">Setup</h2>
          <div class="wizard-steps" id="wiz-dots"></div>
        </div>
        <div class="wizard-body" id="wiz-body"></div>
        <div class="wizard-footer">
          <button class="btn btn-secondary" id="wiz-back">Zurück</button>
          <button class="btn btn-primary"   id="wiz-next">Weiter</button>
        </div>
      </div>
    `;
    this.overlay.querySelector('#wiz-back').addEventListener('click', () => this._prev());
    this.overlay.querySelector('#wiz-next').addEventListener('click', () => this._next());
  }

  _renderDots() {
    const el = this.overlay.querySelector('#wiz-dots');
    el.innerHTML = STEPS.map((_, i) => {
      const cls = i < this.step ? 'done' : i === this.step ? 'active' : '';
      return `<div class="wizard-step-dot ${cls}"></div>`;
    }).join('');
  }

  async _renderStep() {
    const body = this.overlay.querySelector('#wiz-body');
    const title = this.overlay.querySelector('#wiz-title');
    const btnBack = this.overlay.querySelector('#wiz-back');
    const btnNext = this.overlay.querySelector('#wiz-next');

    title.textContent = STEPS[this.step];
    btnBack.style.display = this.step === 0 ? 'none' : '';
    btnNext.textContent = this.step === STEPS.length - 1 ? 'Abschließen' : 'Weiter';

    this._renderDots();
    body.innerHTML = '<p style="color:var(--text-dim)">Lädt…</p>';

    switch (this.step) {
      case 0: this._renderWelcome(body);      break;
      case 1: await this._renderDiscovery(body);  break;
      case 2: this._renderAlign(body);        break;
      case 3: await this._renderAnimations(body); break;
      case 4: await this._renderShortcuts(body);  break;
      case 5: this._renderDone(body);         break;
    }
  }

  // Step 0: Willkommen
  _renderWelcome(body) {
    body.innerHTML = `
      <h3>Willkommen beim WLED Cube Setup</h3>
      <p>Dieser Assistent hilft dir, deinen LED-Würfel einzurichten.</p>
      <p>Du wirst folgende Schritte durchlaufen:</p>
      <ul style="margin-left:20px;color:var(--text-dim);line-height:2">
        <li>Controller-Verbindung prüfen</li>
        <li>Panel-Ausrichtung verifizieren</li>
        <li>Animationen & Playlist konfigurieren</li>
        <li>Tastaturkürzel einrichten</li>
      </ul>
    `;
  }

  // Step 1: Controller Discovery
  async _renderDiscovery(body) {
    body.innerHTML = '<p>Verbinde mit Controllern…</p>';
    let controllers;
    try {
      controllers = await api.controllers();
    } catch (e) {
      body.innerHTML = `<p style="color:var(--danger)">Fehler: ${e.message}</p>`;
      return;
    }

    const rows = controllers.map(c => `
      <tr>
        <td>${c.face}</td>
        <td><code>${c.ip}</code></td>
        <td><span class="badge badge-${c.online ? 'online' : 'offline'}">${c.online ? 'Online' : 'Offline'}</span></td>
        <td>${c.name || '-'}</td>
        <td>${c.version || '-'}</td>
        <td>${c.leds || '-'}</td>
      </tr>`).join('');

    body.innerHTML = `
      <h3>Controller-Status</h3>
      <table class="ctrl-table">
        <thead><tr>
          <th>Fläche</th><th>IP</th><th>Status</th><th>Name</th><th>Version</th><th>LEDs</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p style="margin-top:12px">Offline-Controller können trotzdem konfiguriert werden, solange die IPs stimmen.</p>
    `;
  }

  // Step 2: Ausrichtung
  _renderAlign(body) {
    const faces = ['FRONT (0)', 'BACK (1)', 'LEFT (2)', 'RIGHT (3)', 'TOP (4)', 'BOTTOM (5)'];
    const btns  = faces.map((f, i) => `
      <button class="face-btn ${this._alignActive === i ? 'active' : ''}" data-face="${i}">${f}</button>`).join('');

    body.innerHTML = `
      <h3>Cube-Montage & Ausrichtung</h3>
      <p>Bringe die Panels in die richtige Position. Jede Kante hat einen eindeutigen Farbcode (X-Y-X), der an beiden anliegenden Panels identisch sein muss.</p>
      
      <div style="margin-bottom:16px; display:flex; gap:10px">
        <button class="btn btn-primary" id="align-all-btn" style="flex:1">Alle Flächen: Montage-Modus</button>
        <button class="btn btn-secondary" id="align-stop-btn">Aus</button>
      </div>

      <div style="display:flex; flex-direction:column; align-items:center; background:#111; padding:15px; border-radius:8px; border:1px solid #333; margin-bottom:16px">
        <div style="margin-bottom:10px"><strong>Montage-Guide (Netz-Ansicht):</strong></div>
        ${this._generateNetHTML()}
        <div style="margin-top:10px; font-size:0.85em; color:#aaa">Gleiche Farbcodes treffen an den Kanten aufeinander. Weißer Punkt = Front oben links.</div>
      </div>

      <p style="font-size:0.9em">Einzelne Fläche prüfen & korrigieren (Software-Rotation):</p>
      <div class="face-buttons" style="margin-bottom:16px">${btns}</div>

      <div class="align-ui ${this._alignActive === null ? 'hidden' : ''}">
        <div class="align-container" style="display:flex; gap:20px; align-items:center; background:#111; padding:15px; border-radius:8px; border:1px solid #444">
          <div id="align-pattern-guide" style="width:100px; height:100px; background:#000; border:2px solid #555; display:grid; grid-template-columns: repeat(5, 1fr); gap:1px; padding:2px">
            ${this._generatePatternHTML()}
          </div>
          <div class="align-controls" style="flex:1">
            <div style="display:flex; gap:5px; flex-direction:column">
              <button class="btn btn-secondary btn-sm" id="align-rotate-btn">↻ 90° Drehen</button>
              <button class="btn btn-secondary btn-sm" id="align-flip-btn">↔ Spiegeln</button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Event Listeners
    body.querySelector('#align-all-btn').addEventListener('click', async () => {
      this._alignActive = 'all';
      body.querySelectorAll('.face-btn').forEach(b => b.classList.remove('active'));
      try { await api.alignAll(); } catch (e) { console.error(e); }
    });

    body.querySelectorAll('.face-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        this._alignActive = +btn.dataset.face;
        this._renderAlign(body);
        try { await api.alignFace(this._alignActive); } catch (e) { console.error(e); }
      });
    });

    if (typeof this._alignActive === 'number') {
      body.querySelector('#align-rotate-btn').addEventListener('click', async () => {
        try { await api.alignRotate(this._alignActive); } catch (e) { console.error(e); }
      });
      body.querySelector('#align-flip-btn').addEventListener('click', async () => {
        try { await api.alignFlip(this._alignActive); } catch (e) { console.error(e); }
      });
    }

    body.querySelector('#align-stop-btn').addEventListener('click', async () => {
      this._alignActive = null;
      this._renderAlign(body);
      try { await api.alignStop(); } catch (e) { console.error(e); }
    });
  }

  _generateNetHTML() {
    // Einfache Netz-Darstellung (T-Shape)
    //       [TOP]
    // [LEFT][FRONT][RIGHT][BACK]
    //       [BOTTOM]
    
    const C1="#f00", C2="#0f0", C3="#00f", C4="#ff0", C5="#f0f", C6="#0ff", C7="#f80", C8="#fff", _="#222";
    
    // Mini-Faces 5x5 Grid
    const f = (id, label) => {
      let grid = '';
      for(let r=0; r<5; r++) {
        for(let c=0; c<5; c++) {
          let col = _;
          
          // Corner colors mapping
          if (r===0 && c===0) { // Top-Left of face
            if (id===0) col=C1; if (id===1) col=C6; if (id===2) col=C5; if (id===3) col=C2; if (id===4) col=C5; if (id===5) col=C3;
          }
          if (r===0 && c===4) { // Top-Right of face
            if (id===0) col=C2; if (id===1) col=C5; if (id===2) col=C1; if (id===3) col=C6; if (id===4) col=C6; if (id===5) col=C4;
          }
          if (r===4 && c===0) { // Bottom-Left of face
            if (id===0) col=C3; if (id===1) col=C8; if (id===2) col=C7; if (id===3) col=C4; if (id===4) col=C1; if (id===5) col=C7;
          }
          if (r===4 && c===4) { // Bottom-Right of face
            if (id===0) col=C4; if (id===1) col=C7; if (id===2) col=C3; if (id===3) col=C8; if (id===4) col=C2; if (id===5) col=C8;
          }

          grid += `<div style="background:${col}; width:100%; height:100%"></div>`;
        }
      }
      return `
        <div class="net-face" style="width:60px; height:60px; background:#000; display:grid; grid-template-columns:repeat(5,1fr); gap:1px; border:1px solid #444; position:relative">
          ${grid}
          <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-size:10px; color:#fff; text-shadow:1px 1px 2px #000; pointer-events:none">${label}</div>
        </div>
      `;
    };

    return `
      <div style="display:grid; grid-template-columns: repeat(4, 62px); grid-template-rows: repeat(3, 62px); gap:2px">
        <div style="grid-column:2">${f(4, 'TOP')}</div>
        <div style="grid-column:1; grid-row:2">${f(2, 'LEFT')}</div>
        <div style="grid-column:2; grid-row:2">${f(0, 'FRONT')}</div>
        <div style="grid-column:3; grid-row:2">${f(3, 'RIGHT')}</div>
        <div style="grid-column:4; grid-row:2">${f(1, 'BACK')}</div>
        <div style="grid-column:2; grid-row:3">${f(5, 'BOTTOM')}</div>
      </div>
    `;
  }

  _generatePatternHTML() {
    let html = '';
    for (let r = 0; r < 5; r++) {
      for (let c = 0; c < 5; c++) {
        let color = '#000';
        if (r === 0 && c === 0) color = '#fff';
        else if (r === 0) color = '#f00';
        else if (c === 0) color = '#0f0';
        else if (r === 4 || c === 4) color = '#00f';
        else if (r === 2 && c === 2) color = '#333';
        html += `<div style="background:${color}; width:100%; height:100%"></div>`;
      }
    }
    return html;
  }

  // Step 3: Animationen
  async _renderAnimations(body) {
    if (!Object.keys(this.animations).length) {
      try { this.animations = await api.animations(); } catch (e) { /* ignore */ }
    }
    const saved   = this.settings.enabled_animations || Object.keys(this.animations);
    const animKeys = Object.keys(this.animations);

    const items = animKeys.map(name => `
      <li class="anim-toggle-item">
        <input type="checkbox" id="anim-${name}" data-name="${name}"
               ${saved.includes(name) ? 'checked' : ''}>
        <label for="anim-${name}">${name}</label>
      </li>`).join('');

    body.innerHTML = `
      <h3>Animationen aktivieren</h3>
      <p>Wähle, welche Animationen verfügbar sein sollen.</p>
      <ul class="anim-toggle-list">${items}</ul>
    `;

    body.querySelectorAll('input[type=checkbox]').forEach(cb => {
      cb.addEventListener('change', () => this._saveEnabledAnimations(body));
    });
  }

  _saveEnabledAnimations(body) {
    const enabled = [...body.querySelectorAll('input[type=checkbox]:checked')]
      .map(cb => cb.dataset.name);
    this.settings.enabled_animations = enabled;
  }

  // Step 4: Shortcuts
  async _renderShortcuts(body) {
    if (!Object.keys(this.animations).length) {
      try { this.animations = await api.animations(); } catch (e) { /* ignore */ }
    }
    if (!this.settings.hotkey_shortcuts) {
      try {
        const s = await api.getSettings();
        this.settings = { ...this.settings, ...s };
      } catch (e) { /* ignore */ }
    }

    const enabledKeys = this.settings.enabled_animations || Object.keys(this.animations);
    const animNames   = Object.keys(this.animations).filter(n => enabledKeys.includes(n));

    body.innerHTML = `
      <h3>Hotkeys (Raspberry Pi Daemon)</h3>
      <p>Diese Kürzel steuern den Würfel direkt vom Pi — das Web UI muss nicht offen sein.</p>
      <div id="wiz-hk-editor"></div>
    `;

    this._getHotkeyValues = renderHotkeysEditor(
      body.querySelector('#wiz-hk-editor'),
      this.settings.hotkey_shortcuts || {},
      animNames,
    );
  }

  // Step 5: Fertig
  _renderDone(body) {
    body.innerHTML = `
      <h3>Setup abgeschlossen!</h3>
      <p>Dein WLED-Würfel ist konfiguriert. Du kannst den Wizard jederzeit über das Einstellungsmenü erneut aufrufen.</p>
      <p style="margin-top:16px;color:var(--success)">✓ Einstellungen wurden gespeichert.</p>
    `;
  }

  // --- Navigation ---
  async _next() {
    if (this._alignActive !== null) {
      await api.alignStop().catch(() => {});
      this._alignActive = null;
    }

    if (this.step === STEPS.length - 1) {
      await this._finish();
    } else {
      this.step++;
      this._renderStep();
    }
  }

  _prev() {
    if (this.step > 0) {
      this.step--;
      this._renderStep();
    }
  }

  async _finish() {
    this.settings.setup_complete = true;
    // Hotkey-Werte aus dem Editor übernehmen (falls Schritt 4 besucht wurde)
    if (this._getHotkeyValues) {
      this.settings.hotkey_shortcuts = this._getHotkeyValues();
    }
    try {
      await api.saveSettings(this.settings);
    } catch (e) {
      console.error('Settings speichern fehlgeschlagen:', e);
    }
    this.hide();
    this.onComplete(this.settings);
  }
}
