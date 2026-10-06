"""
scraper_v5.py — Orchestrator simplificado
==========================================
Lanza workers paralelos (1 por forma) con las dimensiones simplificadas.

Dimensiones activas:  stone_shape, ring_head, mounting, side_setting,
                      ring_carving, peekaboo, head_color, mounting_color
Fijo:                 metal_type=GOLD, metal_quality=KT_18,
                      stone_type=LABGROWN_DIAMOND, center_stone_size=1ct

Uso:
    python scraper_v5.py

Requiere en el mismo directorio:
    - session.json
    - configurator_map.json
    - worker.py

Genera:
    - results/results_SHAPE.json  (1 por forma)
    - results/worker_SHAPE.log    (1 por forma)
    - nivoda_rings_v5.json        (union final)
"""

import json
import subprocess
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

BASE_DIR      = Path(__file__).parent
SESSION_FILE  = BASE_DIR / "session.json"
MAP_FILE      = BASE_DIR / "configurator_map.json"
WORKER_SCRIPT = BASE_DIR / "worker.py"
OUTPUT_DIR    = BASE_DIR / "results"
FINAL_OUTPUT  = BASE_DIR / "nivoda_rings_v5.json"

MAX_PARALLEL  = 1   # cuántos browsers simultáneos
DELAY_BETWEEN = 25  # segundos entre lanzamientos dentro del mismo lote
DELAY_LOTE    = 30  # segundos de pausa entre lotes

SHAPES = [
    "CUSHION",
    "EMERALD",
    "MARQUISE",
    "OVAL",
    "PEAR",
    "PRINCESS",
    "RADIANT",
    "ROUND",
]


def print_header():
    print("=" * 65)
    print("  Nivoda Ring Scraper v5 — simplificado")
    print("  Fijo: GOLD / KT_18 / LABGROWN / 1ct")
    print("  Itera: head x mounting x side x carving x peekaboo x colores")
    print("=" * 65)
    print(f"  Session : {SESSION_FILE}")
    print(f"  Output  : {OUTPUT_DIR}")
    print(f"  Formas  : {', '.join(SHAPES)}")
    print("=" * 65)
    print()


def monitor_progress(output_dir: Path, shapes: list, interval: int = 30):
    counts = {s: 0 for s in shapes}
    while True:
        time.sleep(interval)
        parts = []
        for shape in shapes:
            f = output_dir / f"results_{shape}.json"
            if f.exists():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    n = len(data.get("rings", []))
                    delta = n - counts[shape]
                    counts[shape] = n
                    parts.append(f"{shape}:{n}(+{delta})")
                except:
                    parts.append(f"{shape}:?")
            else:
                parts.append(f"{shape}:0")
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] PROGRESO — {' | '.join(parts)}", flush=True)


def merge_results(output_dir: Path, final_output: Path, shapes: list):
    all_rings = []
    summary   = {}
    print("\n  Uniendo resultados...\n")
    for shape in shapes:
        f = output_dir / f"results_{shape}.json"
        if not f.exists():
            print(f"  WARN: Sin resultados para {shape}")
            continue
        try:
            data  = json.loads(f.read_text(encoding="utf-8"))
            rings = data.get("rings", [])
            all_rings.extend(rings)
            summary[shape] = {"total": len(rings), "partial": data.get("partial", True)}
            print(f"  {shape:12} -> {len(rings):,} combinaciones")
        except Exception as e:
            print(f"  ERROR leyendo {f}: {e}")

    final = {
        "scraped_at":     datetime.now().isoformat(),
        "total":          len(all_rings),
        "shapes_summary": summary,
        "fixed": {
            "metal_type":        "GOLD",
            "metal_quality":     "KT_18",
            "stone_type":        "LABGROWN_DIAMOND",
            "center_stone_size": "1ct",
        },
        "rings": all_rings,
    }
    final_output.write_text(
        json.dumps(final, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n  Total unificado: {len(all_rings):,} combinaciones")
    print(f"  Archivo: {final_output}")


def main():
    print_header()

    for f, name in [
        (SESSION_FILE,  "session.json"),
        (MAP_FILE,      "configurator_map.json"),
        (WORKER_SCRIPT, "worker.py"),
    ]:
        if not f.exists():
            print(f"ERROR: No se encontro {name} en {BASE_DIR}")
            sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    monitor_thread = threading.Thread(
        target=monitor_progress,
        args=(OUTPUT_DIR, SHAPES, 30),
        daemon=True
    )
    monitor_thread.start()

    start_time   = time.time()
    shape_queue  = list(SHAPES)

    print("-" * 65)

    while shape_queue:
        lote       = shape_queue[:MAX_PARALLEL]
        shape_queue = shape_queue[MAX_PARALLEL:]

        print(f"\n  Lanzando lote: {lote}\n")

        lote_procs = {}
        for shape in lote:
            cmd = [
                sys.executable, str(WORKER_SCRIPT),
                shape,
                str(SESSION_FILE),
                str(MAP_FILE),
                str(OUTPUT_DIR),
            ]
            log_out = OUTPUT_DIR / f"worker_{shape}.stdout"
            proc = subprocess.Popen(
                cmd,
                stdout=open(log_out, "w"),
                stderr=subprocess.STDOUT,
                text=True,
            )
            lote_procs[shape] = proc
            elapsed = time.time() - start_time
            print(f"  >> {shape:12} PID={proc.pid} ({elapsed/60:.1f} min)")
            time.sleep(DELAY_BETWEEN)

        print(f"\n  Esperando que termine el lote...\n")
        for shape, proc in lote_procs.items():
            proc.wait()
            elapsed = time.time() - start_time
            print(f"  OK {shape} termino ({elapsed/60:.1f} min)")

        if shape_queue:
            print(f"\n  Pausa {DELAY_LOTE}s antes del siguiente lote: {shape_queue[:MAX_PARALLEL]}\n")
            time.sleep(DELAY_LOTE)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 65}")
    print(f"  Todos los workers terminaron en {elapsed/60:.1f} minutos")
    print(f"{'=' * 65}\n")

    merge_results(OUTPUT_DIR, FINAL_OUTPUT, SHAPES)

    print(f"\n{'=' * 65}")
    print(f"  Scrape completo en {elapsed/60:.1f} minutos")
    print(f"  Archivo final: {FINAL_OUTPUT}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()