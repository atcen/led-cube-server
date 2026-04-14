/**
 * Hotkey-Editor: Erfasst Tastenkombinationen und speichert sie im pynput-Format.
 *
 * Verwendet in:
 *   - Settings-Modal (app.js)
 *   - Setup-Wizard Schritt 4 (wizard.js)
 *
 * Format in settings.json → hotkey_shortcuts:
 *   { enabled, stop, on, next, random, per_animation: { snake: "1", ... } }
 *
 * pynput-Syntax: "<ctrl>+<alt>+<right>", "r", "<f5>", usw.
 */

const BROWSER_TO_PYNPUT = {
  ArrowRight: '<right>', ArrowLeft:  '<left>',
  ArrowUp:    '<up>',    ArrowDown:  '<down>',
  Escape:     '<esc>',   Enter:      '<enter>',
  Backspace:  '<backspace>', Delete: '<delete>',
  Tab:        '<tab>',   ' ':        '<space>',
  PageUp:     '<page_up>', PageDown: '<page_down>',
  Home:       '<home>',  End:        '<end>',
};
for (let i = 1; i <= 12; i++) BROWSER_TO_PYNPUT[`F${i}`] = `<f${i}>`;

const PYNPUT_TO_DISPLAY = {
  '<right>':     '→',
  '<left>':      '←',
  '<up>':        '↑',
  '<down>':      '↓',
  '<esc>':       'Esc',
  '<enter>':     'Enter',
  '<backspace>': 'Backspace',
  '<delete>':    'Del',
  '<space>':     'Space',
  '<tab>':       'Tab',
  '<page_up>':   'PgUp',
  '<page_down>': 'PgDn',
  '<home>':      'Home',
  '<end>':       'End',
};
for (let i = 1; i <= 12; i++) PYNPUT_TO_DISPLAY[`<f${i}>`] = `F${i}`;

/**
 * Konvertiert ein browser KeyboardEvent in einen pynput-Key-String (einzelne Taste).
 * Gibt null zurück wenn ein Modifier gehalten wird oder nur ein Modifier gedrückt wurde.
 */
export function eventToPynput(e) {
  // Modifier-only → ignorieren
  if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return null;
  // Kombination mit Modifier → abweisen
  if (e.ctrlKey || e.altKey || e.metaKey) return null;

  const mapped = BROWSER_TO_PYNPUT[e.key] ?? (e.key.length === 1 ? e.key.toLowerCase() : null);
  return mapped ?? null;
}

/**
 * Konvertiert einen pynput-Combo-String in einen lesbaren Anzeigetext.
 */
export function pynputToDisplay(key) {
  if (!key) return '—';
  return PYNPUT_TO_DISPLAY[key] ?? key.toUpperCase();
}

const GLOBAL_ACTIONS = [
  { key: 'stop',   label: 'Alles aus' },
  { key: 'on',     label: 'Alles an (letzte Animation)' },
  { key: 'next',   label: 'Nächste Animation' },
  { key: 'random', label: 'Zufällige Animation' },
];

/**
 * Rendert den Hotkey-Editor in `container`.
 *
 * @param {HTMLElement} container  - Ziel-Element
 * @param {object}      shortcuts  - Aktuelle hotkey_shortcuts aus settings
 * @param {string[]}    animNames  - Alle (enabled) Animationsnamen
 * @returns {() => object}         - Getter für den aktuellen Zustand
 */
export function renderHotkeysEditor(container, shortcuts, animNames) {
  const sc = {
    enabled: true,
    stop:    null,
    on:      null,
    next:    null,
    random:  null,
    per_animation: {},
    ...shortcuts,
  };
  if (!sc.per_animation) sc.per_animation = {};

  // --- HTML aufbauen ---
  const globalRows = GLOBAL_ACTIONS.map(({ key, label }) => `
    <div class="shortcut-row">
      <span class="shortcut-label">${label}</span>
      <span class="key-capture" data-action="${key}">${pynputToDisplay(sc[key])}</span>
      <button class="key-clear" data-action="${key}" title="Löschen">✕</button>
    </div>`).join('');

  const animRows = animNames.map(name => {
    const combo = sc.per_animation[name] || null;
    return `
      <div class="shortcut-row">
        <span class="shortcut-label anim-label">${name}</span>
        <span class="key-capture" data-anim="${name}">${pynputToDisplay(combo)}</span>
        <button class="key-clear" data-anim="${name}" title="Löschen">✕</button>
      </div>`;
  }).join('');

  container.innerHTML = `
    <label class="hk-toggle-label">
      <input type="checkbox" id="hk-enabled" ${sc.enabled !== false ? 'checked' : ''}>
      <span>Hotkeys aktiviert</span>
    </label>

    <div class="shortcut-section-title">Globale Aktionen</div>
    ${globalRows}

    ${animNames.length ? `
      <div class="shortcut-section-title" style="margin-top:16px">Pro Animation</div>
      ${animRows}
    ` : ''}

    <p class="hk-hint">Klicke auf ein Feld und drücke eine einzelne Taste (z.B. F1–F12, Ziffern, Pfeiltasten). Keine Modifier (Ctrl/Alt/Shift).</p>
  `;

  // --- Key-Capture-Logik ---
  let captureEl   = null;
  let captureHdl  = null;

  function startCapture(el) {
    if (captureEl) {
      captureEl.classList.remove('capturing');
      captureEl.textContent = pynputToDisplay(getCombo(captureEl)) || '—';
    }
    if (captureHdl) document.removeEventListener('keydown', captureHdl, true);

    captureEl = el;
    el.classList.add('capturing');
    el.textContent = '…';

    captureHdl = (e) => {
      // Modifier-only → warten
      if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return;
      e.preventDefault();
      e.stopPropagation();

      // Kombination mit Modifier → visuelles Feedback, weiter warten
      if (e.ctrlKey || e.altKey || e.metaKey) {
        captureEl.textContent = 'Nur einzelne Taste!';
        setTimeout(() => { if (captureEl) captureEl.textContent = '…'; }, 900);
        return;
      }

      const key = eventToPynput(e);
      if (!key) return;

      setCombo(captureEl, key);
      captureEl.textContent = pynputToDisplay(key);
      captureEl.classList.remove('capturing');
      captureEl = null;
      document.removeEventListener('keydown', captureHdl, true);
      captureHdl = null;
    };
    document.addEventListener('keydown', captureHdl, true);
  }

  function getCombo(el) {
    if (el.dataset.action) return sc[el.dataset.action];
    if (el.dataset.anim)   return sc.per_animation[el.dataset.anim] || null;
    return null;
  }

  function setCombo(el, combo) {
    if (el.dataset.action) {
      sc[el.dataset.action] = combo;
    } else if (el.dataset.anim) {
      sc.per_animation[el.dataset.anim] = combo;
    }
  }

  function clearCombo(btn) {
    if (btn.dataset.action) {
      sc[btn.dataset.action] = null;
      const cap = container.querySelector(`.key-capture[data-action="${btn.dataset.action}"]`);
      if (cap) cap.textContent = '—';
    } else if (btn.dataset.anim) {
      delete sc.per_animation[btn.dataset.anim];
      const cap = container.querySelector(`.key-capture[data-anim="${btn.dataset.anim}"]`);
      if (cap) cap.textContent = '—';
    }
  }

  container.querySelectorAll('.key-capture').forEach(el => {
    el.addEventListener('click', () => startCapture(el));
  });
  container.querySelectorAll('.key-clear').forEach(btn => {
    btn.addEventListener('click', () => clearCombo(btn));
  });

  // Getter
  return () => ({
    ...sc,
    enabled: container.querySelector('#hk-enabled')?.checked ?? true,
  });
}
