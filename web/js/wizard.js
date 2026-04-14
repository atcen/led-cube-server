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
      <button class="face-btn" data-face="${i}">${f}</button>`).join('');

    body.innerHTML = `
      <h3>Panel-Ausrichtung prüfen</h3>
      <p>Klicke auf eine Fläche, um das Ausrichtungs-Pattern zu aktivieren (Ecken=Rot, Rand=Blau, Mitte=Grün). Prüfe, ob die LEDs korrekt leuchten.</p>
      <div class="face-buttons" style="margin-bottom:12px">${btns}</div>
      <button class="btn btn-secondary" id="align-stop-btn">Ausrichtung stoppen</button>
    `;

    body.querySelectorAll('.face-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        body.querySelectorAll('.face-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this._alignActive = +btn.dataset.face;
        try { await api.alignFace(this._alignActive); } catch (e) { console.error(e); }
      });
    });

    body.querySelector('#align-stop-btn').addEventListener('click', async () => {
      body.querySelectorAll('.face-btn').forEach(b => b.classList.remove('active'));
      this._alignActive = null;
      try { await api.alignStop(); } catch (e) { console.error(e); }
    });
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
