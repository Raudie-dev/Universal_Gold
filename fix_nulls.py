import json

path = "app1/data/nivoda_rings_v5.json"
print("Leyendo JSON...")
data = json.load(open(path, encoding="utf-8"))

fixed_count = 0
for r in data.get("rings", []):
    c = r.get("combination", {})
    if c:
        if c.get("peekaboo") is None:
            c["peekaboo"] = "NONE"
            fixed_count += 1
        if c.get("ring_carving") is None:
            c["ring_carving"] = "PLAIN"
            fixed_count += 1
        if c.get("head_stones_type") is None:
            c["head_stones_type"] = "NONE"
            fixed_count += 1
        if c.get("mounting_length") is None:
            c["mounting_length"] = "HALF"
            fixed_count += 1

print(f"Valores nulos corregidos: {fixed_count}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("JSON actualizado y guardado.")
