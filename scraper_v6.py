import json
import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

CONFIGURATOR_URL = "https://app.nivoda.com/v2/live/jewellery/ring-configurator"
OUTPUT_FILE = "app1/data/nivoda_rings_v6.json"

def click_option(page: Page, prefix: str, value: str):
    try:
        btn = page.query_selector(f'button[data-automation-id="{prefix}{value}"]')
        if not btn: return False
        
        # Check if selected
        pressed = btn.get_attribute("aria-pressed") == "true"
        selected = "Mui-selected" in (btn.get_attribute("class") or "")
        if pressed or selected: return True
        
        # Check if disabled
        if btn.get_attribute("disabled") is not None or btn.get_attribute("aria-disabled") == "true":
            return False
            
        btn.scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        btn.click(force=True)
        page.wait_for_timeout(500)
        return True
    except:
        return False

def wait_for_image(page: Page):
    try:
        page.wait_for_function("""
        () => {
            const overlay = document.querySelector('[data-automation-id="loading-overlay"]');
            if (overlay && getComputedStyle(overlay).display !== 'none' && parseFloat(getComputedStyle(overlay).opacity) > 0.1) return false;
            
            const thumbs = [...document.querySelectorAll('[data-automation-id="thumbnail"]')];
            if (thumbs.length === 0) return false;
            
            return thumbs.every(img => img.src && !img.src.includes('loading') && img.naturalWidth > 0);
        }
        """, timeout=15000)
        return True
    except:
        return False

def build_seen_keys():
    if not os.path.exists(OUTPUT_FILE):
        return set(), []
    try:
        with open(OUTPUT_FILE, "r") as f:
            data = json.load(f)
            rings = data.get("rings", [])
            seen = set()
            for r in rings:
                c = r.get("combination", {})
                key = f"{c.get('stone_shape')}-{c.get('ring_head')}-{c.get('mounting')}-{c.get('side_setting')}-{c.get('mounting_color')}"
                seen.add(key)
            return seen, rings
    except Exception as e:
        print(f"Error loading {OUTPUT_FILE}: {e}")
        return set(), []

def scrape_all():
    seen_keys, results = build_seen_keys()
    print(f"Combinaciones ya scrapeadas en v6: {len(results)}")
    
    SHAPES = ['ROUND', 'OVAL', 'CUSHION', 'PRINCESS', 'PEAR', 'EMERALD', 'MARQUISE', 'RADIANT']
    HEADS = ['FOUR_PRONGS', 'BASKET', 'PEG_HEAD', 'PAVE', 'SINGLE_HALO', 'DOUBLE_HALO', 'CROWN', 'FLOWER_HALO']
    BANDS = ['SINGLE', 'DOUBLE', 'DOUBLE_TWIST', 'KNIFE_EDGE', 'SQUARE_EDGE', 'TAPERED', 'CONTEMPORARY', 'HIDDEN_HALO', 'SPLIT']
    SIDES = ['NONE', 'U_PAVE', 'CHANNEL', 'PRONG', 'BEAD', 'PAVE']
    COLORS = ['YELLOW_GOLD', 'WHITE_GOLD', 'ROSE_GOLD']
    
    combos_to_try = []
    for s in SHAPES:
        for h in HEADS:
            for b in BANDS:
                for sd in SIDES:
                    for c in COLORS:
                        key = f"{s}-{h}-{b}-{sd}-{c}"
                        if key not in seen_keys:
                            combos_to_try.append((s, h, b, sd, c))
                            
    print(f"Total de combinaciones pendientes por intentar: {len(combos_to_try)}")
    
    if not combos_to_try:
        print("¡El catálogo está completo!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(user_data_dir="./playwright_profile", headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        page.goto(CONFIGURATOR_URL, timeout=0)
        
        print("Por favor, navega manualmente al Cotizador de Anillos (Ring Configurator).")
        print("El agente está esperando a que aparezcan los botones de formas de diamantes...")
        
        while True:
            try:
                # Buscamos que haya al menos un botón de forma visible
                btn = page.query_selector('button[data-automation-id^="center-stone-shape-"]')
                if btn and btn.is_visible():
                    print("¡Cotizador detectado! Tomando el control...")
                    break
            except:
                pass
            page.wait_for_timeout(2000)
            
        page.wait_for_timeout(3000)
        
        # Close modal
        for sel in ['button:has-text("Entendido")', 'button:has-text("OK")']:
            try:
                b = page.query_selector(sel)
                if b and b.is_visible(): b.click()
            except: pass
            
        for i, (s, h, b, sd, c) in enumerate(combos_to_try, 1):
            print(f"[{i}/{len(combos_to_try)}] Intentando {s} + {h} + {b} + {sd} + {c}...")
            
            # Select Shape
            if not click_option(page, "center-stone-shape-", s.lower()): continue
            
            # Select Fixed properties to normalize
            click_option(page, "jewellery-configurator-center-stone-type-option-", "LABGROWN_DIAMOND")
            click_option(page, "jewellery-configurator-metal-type-option-", "GOLD")
            click_option(page, "jewellery-configurator-metal-quality-option-", "KT_18")
            
            # Set size
            try:
                page.query_selector('[data-automation-id="jewellery-configurator-center-stone-size"] input').fill("1ct")
                page.keyboard.press("Enter")
            except: pass
            
            # Select specific options
            if not click_option(page, "jewellery-configurator-ring-head-type-option-", h): continue
            if not click_option(page, "jewellery-configurator-mounting-type-option-", b): continue
            
            if sd != "NONE":
                if not click_option(page, "jewellery-configurator-side-setting-type-option-", sd): continue
            
            # Colors
            click_option(page, "jewellery-configurator-ring-head-metal-color-option-", c)
            click_option(page, "jewellery-configurator-mounting-metal-color-option-", c)
            
            # Wait for image update
            if wait_for_image(page):
                # Extract
                try:
                    sku = page.evaluate("() => document.querySelector('[data-automation-id=\"jewellery-configurator-nivoda-sku\"]')?.innerText.replace('Nivoda SKU:', '').trim()")
                    price = page.evaluate("() => document.querySelector('[data-automation-id=\"ring-configurator-footer-mount-price\"]')?.innerText.trim()")
                    images = page.evaluate("""() => {
                        return [...document.querySelectorAll('[data-automation-id="thumbnail"]')].map(img => img.src).filter(src => src && !src.includes('loading') && img.naturalWidth > 0);
                    }""")
                    
                    if sku and images:
                        results.append({
                            "sku": sku,
                            "url": page.url,
                            "price_mount": price,
                            "images": list(set(images))[:3],
                            "has_image": True,
                            "scraped_at": datetime.now().isoformat(),
                            "combination": {
                                "stone_shape": s,
                                "stone_type": "LABGROWN_DIAMOND",
                                "ring_head": h,
                                "mounting": b,
                                "side_setting": sd,
                                "ring_carving": "PLAIN" if sd == "NONE" else None,
                                "peekaboo": "NONE",
                                "metal_type": "GOLD",
                                "metal_quality": "KT_18",
                                "head_color": c,
                                "mounting_color": c,
                                "center_stone_size": "1ct"
                            }
                        })
                        print(f"  -> OK! SKU: {sku}")
                except Exception as e:
                    print(f"  -> Error: {e}")
                    
            if i % 10 == 0:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"rings": results}, f, indent=2)

        browser.close()
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"rings": results}, f, indent=2)
    print(f"¡Scraping quirúrgico terminado! Se recuperaron {len(results)} combinaciones en v6.")

if __name__ == "__main__":
    scrape_all()
