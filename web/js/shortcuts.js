/**
 * Tastaturkürzel-Manager.
 */

export class ShortcutManager {
  constructor() {
    this._handlers = {};  // key → callback
    this._enabled  = true;

    document.addEventListener('keydown', (e) => this._onKey(e));
  }

  register(key, callback) {
    this._handlers[key] = callback;
  }

  unregister(key) {
    delete this._handlers[key];
  }

  loadFromSettings(shortcuts, animationNames, startAnimation) {
    this._handlers = {};
    if (!shortcuts || !shortcuts.enabled) return;

    if (shortcuts.next)   this.register(shortcuts.next,   () => startAnimation('__next__'));
    if (shortcuts.stop)   this.register(shortcuts.stop,   () => startAnimation('__stop__'));
    if (shortcuts.random) this.register(shortcuts.random, () => startAnimation('__random__'));

    const perAnim = shortcuts.per_animation || {};
    for (const [anim, key] of Object.entries(perAnim)) {
      if (animationNames.includes(anim)) {
        this.register(key, () => startAnimation(anim));
      }
    }
  }

  _onKey(e) {
    // Kein Trigger wenn ein Input-Feld fokussiert ist
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (!this._enabled) return;

    const cb = this._handlers[e.key];
    if (cb) {
      e.preventDefault();
      cb();
    }
  }

  setEnabled(v) { this._enabled = v; }
}
