import json
from pathlib import Path

SHAPES = ["CUSHION","EMERALD","MARQUISE","OVAL","PEAR","PRINCESS","RADIANT","ROUND"]

for shape in SHAPES:
    f = Path(f"results/results_{shape}.json")
    if not f.exists():
        print(f"{shape}: sin archivo")
        continue

    data = json.loads(f.read_text(encoding="utf-8"))
    total_antes = len(data["rings"])
    
    buenos = [r for r in data["rings"] if len(r.get("images", [])) == 3]

    data["rings"] = buenos
    data["total"] = len(buenos)
    data["partial"] = True
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"{shape:12} {total_antes:6} → {len(buenos):6} (eliminados: {total_antes - len(buenos)})")