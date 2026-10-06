from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://app.nivoda.com/v2/live/jewellery/ring-configurator", wait_until="networkidle")
    time.sleep(3)
    ids = page.evaluate("() => [...document.querySelectorAll('button[data-automation-id]')].map(b => b.getAttribute('data-automation-id'))")
    with open("dom_ids.txt", "w") as f:
        f.write("\n".join(ids))
    browser.close()
