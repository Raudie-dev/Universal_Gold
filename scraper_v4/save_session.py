"""
Nivoda - Guardar sesión
========================
Corre este script UNA VEZ para guardar tu sesión.
Después inspect_configurator.py y scraper.py la reutilizan sin volver a hacer login.

Uso:
    python save_session.py
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

SESSION_FILE = Path(__file__).parent / "session.json"


def main():
    print("=" * 60)
    print("Nivoda - Guardar sesión")
    print("=" * 60)
    print()
    print("1. Se abrirá el browser")
    print("2. Haz login manualmente en Nivoda")
    print("3. El script detectará automáticamente cuando estés dentro")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="es-ES",
        )
        page = context.new_page()

        # Abrir Nivoda
        page.goto("https://app.nivoda.com/", wait_until="domcontentloaded")
        print("🌐 Browser abierto. Haz login en Nivoda...")

        # Esperar automáticamente hasta que el configurador sea accesible
        print("  ⏳ Esperando que completes el login...")
        page.wait_for_url("**/app.nivoda.com/**", timeout=120000)

        # Esperar que NO estemos en login
        while "login.nivoda.com" in page.url:
            page.wait_for_timeout(1000)

        print(f"  ✅ Login detectado. URL: {page.url}")

        # Navegar al configurador y esperar que cargue
        print("  ⏳ Navegando al configurador...")
        page.wait_for_timeout(2000)
        page.goto("https://app.nivoda.com/v2/live/jewellery/ring-configurator",
                  wait_until="domcontentloaded", timeout=30000)

        print("  ⏳ Esperando que el configurador cargue...")
        try:
            page.wait_for_selector(
                '[data-automation-id="center-stone-shape-ROUND"]',
                timeout=30000
            )
            print("  ✅ Configurador listo")
        except:
            print("  ⚠️  Configurador tardó pero continuamos")

        page.wait_for_timeout(2000)

        # Guardar sesión completa
        context.storage_state(path=str(SESSION_FILE))
        print(f"\n✅ Sesión guardada en: {SESSION_FILE}")
        print("   Ahora puedes correr scraper.py")

        browser.close()


if __name__ == "__main__":
    main()