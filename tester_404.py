import urllib.request
import urllib.parse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

URL = "http://127.0.0.1:8000/api/ring-config/"

SHAPES = ['round', 'oval', 'cushion', 'princess', 'pear', 'emerald', 'marquise', 'radiant']
HEADS = ['4prong', 'basket', 'bezel', 'pave', 'halo', 'doublehalo', 'crown', 'flowerhalo']
BANDS = ['single', 'double', 'twisted', 'knife', 'flat', 'tapered', 'modern', 'hidden', 'split']
SIDES = ['none', 'upave', 'channel', 'prong', 'grain', 'pave']
COLORS = ['yellow', 'white', 'rose']

def test_combo(shape, head, band, side, color):
    params = {
        'shape': shape,
        'head': head,
        'band': band,
        'side': side,
        'metalcolor': color
    }
    query = urllib.parse.urlencode(params)
    try:
        req = urllib.request.urlopen(f"{URL}?{query}", timeout=2)
        return (params, req.getcode())
    except urllib.error.HTTPError as e:
        return (params, e.code)
    except Exception as e:
        return (params, 0)

def main():
    combos = []
    for s in SHAPES:
        for h in HEADS:
            for b in BANDS:
                for sd in SIDES:
                    for c in COLORS:
                        combos.append((s, h, b, sd, c))
    
    print(f"Probando {len(combos)} combinaciones locales...")
    missing = []
    success = 0
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(test_combo, *c): c for c in combos}
        
        for i, future in enumerate(as_completed(futures), 1):
            params, status = future.result()
            if status == 404:
                missing.append(params)
            elif status == 200:
                success += 1
            
            if i % 1000 == 0:
                print(f"  Progreso: {i}/{len(combos)} | Encontrados 404: {len(missing)}")
                
    elapsed = time.time() - start
    print(f"\nFinalizado en {elapsed:.1f}s")
    print(f"Exitosos: {success}")
    print(f"Faltantes (404): {len(missing)}")
    
    with open("missing_combos.json", "w", encoding="utf-8") as f:
        json.dump(missing, f, indent=2)

if __name__ == "__main__":
    main()
