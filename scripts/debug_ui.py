"""
Playwright-Debug-Skript für die WLED Cube Web-UI.

Voraussetzungen:
  - Server läuft: uvicorn server.server:app --host 0.0.0.0 --port 8000
  - Chrome: /Applications/Google Chrome.app

Aufruf:
  python scripts/debug_ui.py
"""

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright, ConsoleMessage

BASE_URL    = "http://localhost:8000"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOT_DIR = Path("debug_screenshots")


async def main():
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    errors   = []
    warnings = []
    requests = []
    failed_requests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=False,           # sichtbar zum Debugging
            slow_mo=200,
            args=["--auto-open-devtools-for-tabs"],
        )
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()

        # ---- Konsole abfangen ----
        def on_console(msg: ConsoleMessage):
            line = f"[{msg.type.upper()}] {msg.text}"
            print(line)
            if msg.type == "error":
                errors.append(msg.text)
            elif msg.type == "warning":
                warnings.append(msg.text)

        page.on("console", on_console)

        # ---- Netzwerk-Fehler abfangen ----
        def on_request_failed(req):
            entry = f"FAIL  {req.method} {req.url}"
            print(entry)
            failed_requests.append(entry)

        async def on_response(resp):
            if resp.status >= 400:
                entry = f"HTTP {resp.status}  {resp.url}"
                print(entry)
                failed_requests.append(entry)

        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        # ---- Seite laden ----
        print(f"\n{'='*60}")
        print(f"Öffne {BASE_URL} ...")
        print(f"{'='*60}\n")

        try:
            await page.goto(BASE_URL, wait_until="networkidle", timeout=10_000)
        except Exception as e:
            print(f"\n[FEHLER] Konnte Seite nicht laden: {e}")
            print("→ Läuft der Server?  uvicorn server.server:app --host 0.0.0.0 --port 8000")
            await browser.close()
            sys.exit(1)

        # ---- Screenshot: Initialzustand ----
        await page.screenshot(path=SCREENSHOT_DIR / "01_initial.png", full_page=True)
        print(f"\n[Screenshot] {SCREENSHOT_DIR}/01_initial.png")

        # ---- DOM-Inspektion ----
        print("\n--- DOM-Check ---")

        checks = {
            "#anim-list":      "Animations-Liste",
            "#ctrl-list":      "Controller-Liste",
            "#cube-canvas":    "3D-Canvas",
            "#ws-status":      "WebSocket-Status",
            "#status-pill":    "Status-Pill",
            "#params-panel":   "Params-Panel",
        }

        for selector, label in checks.items():
            el = page.locator(selector)
            count = await el.count()
            if count == 0:
                print(f"  ✗ FEHLT    {label} ({selector})")
                continue

            text    = (await el.inner_text()).strip()[:80]
            visible = await el.is_visible()
            print(f"  {'✓' if visible else '~'} {'OK' if visible else 'HIDDEN'}     {label}: {repr(text)}")

        # ---- API-Endpoints testen ----
        print("\n--- API-Check ---")
        for path in ["/", "/status", "/animations", "/settings", "/controllers/status"]:
            result = await page.evaluate(f"""
                fetch('{path}')
                  .then(r => r.status + ' ' + r.statusText)
                  .catch(e => 'ERROR: ' + e.message)
            """)
            status_char = "✓" if result.startswith("2") else "✗"
            print(f"  {status_char} {path:35s}  {result}")

        # ---- Auf Animationsliste warten und klicken ----
        print("\n--- Animations-Test ---")
        anim_items = page.locator(".anim-item")
        count = await anim_items.count()
        print(f"  Gefundene Animationen: {count}")

        if count > 0:
            # Checkerboard: ganze Würfelfläche mit 2 Farben — besser sichtbar als Snake
            chk = page.locator('.anim-item[data-name="checkerboard"]')
            anim_name = "checkerboard" if await chk.count() > 0 else await anim_items.first.get_attribute("data-name")
            print(f"  Klicke auf: {anim_name}")
            if await chk.count() > 0:
                await chk.click()
            else:
                await anim_items.first.click()

            # Mehrere Screenshots über 3 Sekunden — prüft ob Animation läuft
            for i, delay in enumerate([500, 1000, 2000, 3000], start=2):
                await page.wait_for_timeout(500)
                shot = SCREENSHOT_DIR / f"0{i}_t{delay}ms.png"
                await page.screenshot(path=shot, full_page=True)
                print(f"  [Screenshot] {shot}")

            pill_text = await page.locator("#status-pill").inner_text()
            print(f"  Status-Pill: {pill_text!r}")

            # WS-Frame-Zähler aus dem Cube3D-Objekt auslesen
            frames = await page.evaluate("window.__cube3d_frames || (window.cube3d && cube3d._framesReceived) || 'N/A'")
            print(f"  Empfangene WS-Frames: {frames}")

            # WebSocket-Typ prüfen
            ws_check = await page.evaluate("""
                (() => {
                    const ws_inst = window._ws_debug;
                    return {
                        readyState: ws_inst ? ws_inst.readyState : 'no ref',
                        binaryType: ws_inst ? ws_inst.binaryType : 'no ref'
                    };
                })()
            """)
            print(f"  WS-State: {ws_check}")

        # ---- WebSocket-Status prüfen ----
        print("\n--- WebSocket-Check ---")
        await page.wait_for_timeout(2000)
        ws_text = await page.locator("#ws-status").inner_text()
        print(f"  WS-Status: {ws_text!r}")

        # ---- Controller-Liste ----
        print("\n--- Controller-Status ---")
        ctrl_items = page.locator(".ctrl-item")
        ctrl_count = await ctrl_items.count()
        if ctrl_count == 0:
            raw = await page.locator("#ctrl-list").inner_html()
            print(f"  Keine Controller-Einträge. HTML: {raw[:200]}")
        else:
            for i in range(ctrl_count):
                text = (await ctrl_items.nth(i).inner_text()).replace("\n", " ")
                print(f"  Controller {i+1}: {text}")

        # ---- Abschluss-Screenshot ----
        await page.screenshot(path=SCREENSHOT_DIR / "03_final.png", full_page=True)

        # ---- Zusammenfassung ----
        print(f"\n{'='*60}")
        print("ZUSAMMENFASSUNG")
        print(f"{'='*60}")
        print(f"  JS-Fehler:          {len(errors)}")
        print(f"  JS-Warnungen:       {len(warnings)}")
        print(f"  Fehlgeschl. Reqs:   {len(failed_requests)}")

        if errors:
            print("\n  JS-Fehler:")
            for e in errors:
                print(f"    • {e}")
        if failed_requests:
            print("\n  Fehlgeschlagene Requests:")
            for r in failed_requests:
                print(f"    • {r}")

        print(f"\n  Screenshots: {SCREENSHOT_DIR}/")
        print("\nBrowser bleibt 10 Sekunden offen …")
        await page.wait_for_timeout(10_000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
