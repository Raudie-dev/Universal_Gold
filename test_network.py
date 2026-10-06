from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        def handle_response(response):
            if "graphql" in response.url or "api" in response.url:
                print(f"API Call: {response.url}")
        
        page.on("response", handle_response)
        page.goto("https://app.nivoda.com/v2/live/jewellery/ring-configurator", wait_until="networkidle")
        browser.close()

main()
