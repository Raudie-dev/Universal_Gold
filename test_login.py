import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(user_data_dir="./playwright_profile", headless=False)
    page = browser.new_page()
    page.goto("https://app.nivoda.com/v2/live/jewellery/ring-configurator", timeout=0)
    print("Esperando login...")
    try:
        page.wait_for_url("**/v2/live/search/**", timeout=120000)
        print("Login detectado. Redirigiendo...")
        page.goto("https://app.nivoda.com/v2/live/jewellery/ring-configurator", wait_until="domcontentloaded", timeout=60000)
    except:
        pass
    
    print("Esperando a que la pagina asiente...")
    page.wait_for_timeout(10000)
    page.screenshot(path="nivoda_debug.png", full_page=True)
    with open("nivoda_debug.html", "w") as f:
        f.write(page.content())
    print("Guardado.")
    browser.close()
