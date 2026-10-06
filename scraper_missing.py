import json
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Page

CONFIGURATOR_URL = "https://app.nivoda.com/v2/live/jewellery/ring-configurator"

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

def scrape_missing():
    with open("missing_combos.json", "r") as f:
        missing = json.load(f)
        
    print(f"Total combinaciones faltantes a intentar: {len(missing)}")
    results = []
    
    SHAPE_MAP = {'round': 'ROUND', 'oval': 'OVAL', 'cushion': 'CUSHION', 'princess': 'PRINCESS', 'pear': 'PEAR', 'emerald': 'EMERALD', 'marquise': 'MARQUISE', 'radiant': 'RADIANT'}
    HEAD_MAP = {'4prong': 'FOUR_PRONGS', 'basket': 'BASKET', 'bezel': 'PEG_HEAD', 'pave': 'PAVE', 'halo': 'SINGLE_HALO', 'doublehalo': 'DOUBLE_HALO', 'crown': 'CROWN', 'flowerhalo': 'FLOWER_HALO'}
    BAND_MAP = {'single': 'SINGLE', 'double': 'DOUBLE', 'twisted': 'DOUBLE_TWIST', 'knife': 'KNIFE_EDGE', 'flat': 'SQUARE_EDGE', 'tapered': 'TAPERED', 'modern': 'CONTEMPORARY', 'hidden': 'HIDDEN_HALO', 'split': 'SPLIT'}
    SIDE_MAP = {'none': 'NONE', 'upave': 'U_PAVE', 'channel': 'CHANNEL', 'prong': 'PRONG', 'grain': 'BEAD', 'pave': 'PAVE'}
    COLOR_MAP = {'yellow': 'YELLOW_GOLD', 'white': 'WHITE_GOLD', 'rose': 'ROSE_GOLD'}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(CONFIGURATOR_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        
        # Close modal
        for sel in ['button:has-text("Entendido")', 'button:has-text("OK")']:
            try:
                b = page.query_selector(sel)
                if b and b.is_visible(): b.click()
            except: pass
            
        for i, m in enumerate(missing, 1):
            s = SHAPE_MAP.get(m['shape'])
            h = HEAD_MAP.get(m['head'])
            b = BAND_MAP.get(m['band'])
            sd = SIDE_MAP.get(m['side'])
            c = COLOR_MAP.get(m['metalcolor'])
            
            print(f"[{i}/{len(missing)}] Intentando {s} + {h} + {b} + {sd} + {c}...")
            
            # Select Shape
            if not click_option(page, "center-stone-shape-", s): continue
            
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
                with open("rescued_rings.json", "w") as f:
                    json.dump(results, f, indent=2)

        browser.close()
        
    with open("rescued_rings.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"¡Scraping quirúrgico terminado! Se recuperaron {len(results)} combinaciones.")

if __name__ == "__main__":
    scrape_missing()
