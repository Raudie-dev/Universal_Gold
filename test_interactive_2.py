import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(user_data_dir="./playwright_profile", headless=False)
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto("https://app.nivoda.com/v2/live/search/natural/diamond", timeout=0)
    print("Navega al cotizador. Imprimiré la URL cada 5 segundos...")
    for _ in range(60):
        try:
            print("URL ACTUAL:", page.url)
            ids = page.evaluate("() => [...document.querySelectorAll('button[data-automation-id]')].map(b => b.getAttribute('data-automation-id'))")
            shapes = [x for x in ids if 'shape' in x.lower()]
            colors = [x for x in ids if 'color' in x.lower()]
            if shapes: print("Formas encontradas:", shapes[:3])
            if colors: print("Colores encontrados:", colors[:3])
        except Exception as e:
            print("Error:", e)
        time.sleep(5)
    browser.close()
