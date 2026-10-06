import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(user_data_dir="./playwright_profile", headless=False)
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto("https://app.nivoda.com/v2/live/search/natural/diamond", timeout=0)
    print("Navega al cotizador de anillos manualmente y presiona Enter aquí en la terminal...")
    input()
    
    print("URL actual:", page.url)
    with open("nivoda_interactive.html", "w") as f:
        f.write(page.content())
    page.screenshot(path="nivoda_interactive.png", full_page=True)
    print("Guardado.")
    browser.close()
