"""
worker.py — Nivoda Ring Scraper v5 (con pruning de combinaciones ya scrapeadas)
================================================================================
Cambio principal frente a la versión anterior:
  - Se pre-construye `seen_keys` con todas las combos ya guardadas.
  - Antes de entrar a cada nivel del loop, se verifica si TODAS las combinaciones
    de ese sub-árbol ya están cubiertas (subtree_done). Si es así, se salta el
    nivel completo sin tocar la UI — no se hace ningún click inútil.
  - La captura final también tiene el guard `if combo_key in seen_keys: continue`
    como seguro adicional.

Dimensiones que itera:
  - stone_shape    (fijada por argumento)
  - ring_head      (del DOM / configurator_map)
  - mounting       (del DOM / configurator_map)
  - side_setting   (del DOM)
  - peekaboo       (del DOM)
  - ring_carving   (del DOM, solo cuando side_setting == NONE)
  - head_color     (YELLOW_GOLD, WHITE_GOLD, ROSE_GOLD)
  - mounting_color (YELLOW_GOLD, WHITE_GOLD, ROSE_GOLD)

Fijo (no itera):
  - metal_type     = GOLD
  - metal_quality  = KT_18
  - stone_type     = LABGROWN_DIAMOND
  - center_stone_size = 1ct

Uso: python worker.py <SHAPE> <session.json> <configurator_map.json> <output_dir>
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page

CONFIGURATOR_URL = "https://app.nivoda.com/v2/live/jewellery/ring-configurator"
HEADLESS = False

# Valores fijos
FIXED_METAL_TYPE    = "GOLD"
FIXED_METAL_QUALITY = "KT_18"
FIXED_STONE_TYPE    = "LABGROWN_DIAMOND"
FIXED_STONE_SIZE    = "1ct"

# Colores que siempre iteramos (para oro)
HEAD_COLORS  = ["YELLOW_GOLD", "WHITE_GOLD", "ROSE_GOLD"]
MOUNT_COLORS = ["YELLOW_GOLD", "WHITE_GOLD", "ROSE_GOLD"]

PREFIXES = {
    "stone_type":       "jewellery-configurator-center-stone-type-option-",
    "ring_head":        "jewellery-configurator-ring-head-type-option-",
    "head_stones_type": "jewellery-configurator-head-stones-type-option-",
    "mounting":         "jewellery-configurator-mounting-type-option-",
    "side_setting":     "jewellery-configurator-side-setting-type-option-",
    "side_stones_type": "jewellery-configurator-side-stones-type-option-",
    "mounting_length":  "jewellery-configurator-side-stones-mounting-length-option-",
    "peekaboo":         "jewellery-configurator-peekaboo-stone-option-",
    "ring_carving":     "jewellery-configurator-ring-carving-type-option-",
    "metal_type":       "jewellery-configurator-metal-type-option-",
    "metal_quality":    "jewellery-configurator-metal-quality-option-",
    "head_color":       "jewellery-configurator-ring-head-metal-color-option-",
    "mounting_color":   "jewellery-configurator-mounting-metal-color-option-",
}

CONFIGURATOR_LOADED_JS = """
() => {
    const shapeButtons = document.querySelectorAll(
        'button[data-automation-id^="center-stone-shape-"]'
    );
    if (shapeButtons.length === 0) return false;

    const visible = [...shapeButtons].some(btn => {
        const rect = btn.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    });
    if (!visible) return false;

    const spinners = document.querySelectorAll(
        '[class*="skeleton"], [class*="Skeleton"], [role="progressbar"]'
    );
    for (const s of spinners) {
        const rect = s.getBoundingClientRect();
        if (rect.width > window.innerWidth * 0.5) return false;
    }

    return true;
}
"""


# ── Logging ───────────────────────────────────────────────────────────────────

_log_file: Path = None
_shape_label: str = ""

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][{_shape_label}] {msg}"
    safe = line.encode("ascii", errors="replace").decode("ascii")
    print(safe, flush=True)
    with open(_log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── Pruning helper ────────────────────────────────────────────────────────────

def make_combo_key(partial: dict) -> str:
    """Genera la clave canónica de una combinación (filtra Nones)."""
    return json.dumps({k: v for k, v in partial.items() if v}, sort_keys=True)


def subtree_done(seen_keys: set, partial: dict,
                 remaining_dims: list) -> bool:
    """
    Devuelve True si TODAS las combinaciones del sub-árbol definido por
    `partial` + expansión de `remaining_dims` ya están en `seen_keys`.

    `remaining_dims` es una lista de listas: cada elemento es la lista de
    valores posibles para la siguiente dimensión libre. El orden importa.

    Ejemplo:
        partial      = {stone_shape: ROUND, ring_head: FOUR_PRONG, mounting: SOLITAIRE}
        remaining_dims = [
            ["NONE", "PAVE"],           # side_setting
            ["PLAIN", "MILGRAIN"],      # carving (solo aplica si side=NONE)
            ["NONE", "SAPPHIRE"],       # peekaboo
            ["YELLOW_GOLD", ...],       # head_color
            ["YELLOW_GOLD", ...],       # mounting_color
        ]

    NOTA: Esta función evalúa el producto cartesiano completo de remaining_dims,
    lo que puede ser costoso si los dims son grandes. En la práctica los sub-árboles
    son pequeños (≤ 3×3 = 9 combos en el nivel más profundo), así que es seguro.
    Si un nivel tiene una sola opción None (placeholder), se trata como valor ausente.
    """
    if not remaining_dims:
        return make_combo_key(partial) in seen_keys

    current_dim_values, *rest = remaining_dims
    for val in current_dim_values:
        new_partial = dict(partial)
        if val is not None:
            # encontrar la key del partial que corresponde a este nivel
            # se pasa como tupla (key, value)
            pass
        # Los valores vienen ya como (dim_key, val) — ver cómo se llama abajo
        raise NotImplementedError("Usar subtree_done_kv en su lugar")


def subtree_done_kv(seen_keys: set, partial: dict,
                    remaining_dims: list[tuple[str, list]]) -> bool:
    """
    Versión correcta de subtree_done.
    `remaining_dims` es lista de (dim_key, [valores]) donde dim_key es la
    clave del dict de combinación y [valores] son sus posibles valores.

    Valores None dentro de la lista se tratan como ausencia de esa dimensión
    (la key no se añade al partial).

    Devuelve True si TODAS las combinaciones del sub-árbol ya están en seen_keys.
    Devuelve False en cuanto encuentra UNA combinación pendiente (cortocircuito).
    """
    if not remaining_dims:
        return make_combo_key(partial) in seen_keys

    (dim_key, dim_values), *rest = remaining_dims
    for val in dim_values:
        new_partial = dict(partial)
        if val is not None:
            new_partial[dim_key] = val
        if not subtree_done_kv(seen_keys, new_partial, rest):
            return False
    return True


# ── DOM helpers ───────────────────────────────────────────────────────────────

def get_available_options(page: Page, prefix: str) -> dict:
    try:
        return page.evaluate("""
        (prefix) => {
            const buttons = [...document.querySelectorAll(`button[data-automation-id^="${prefix}"]`)];
            const result = { selected: null, available: [], disabled: [] };
            for (const btn of buttons) {
                const id = btn.getAttribute('data-automation-id');
                const parts = id.split('-option-');
                const value = parts.length > 1 ? parts[1] : id.split('-').pop();
                const pressed  = btn.getAttribute('aria-pressed') === 'true'
                              || btn.classList.contains('Mui-selected');
                const disabled = btn.hasAttribute('disabled')
                              || btn.getAttribute('aria-disabled') === 'true';
                if (pressed)  result.selected = value;
                if (disabled) result.disabled.push(value);
                else          result.available.push(value);
            }
            return result;
        }
        """, prefix)
    except:
        return {"selected": None, "available": [], "disabled": []}


def click_button(page: Page, automation_id: str) -> bool:
    try:
        btn = page.query_selector(f'button[data-automation-id="{automation_id}"]')
        if not btn:
            return False
        pressed  = btn.get_attribute("aria-pressed") == "true"
        selected = "Mui-selected" in (btn.get_attribute("class") or "")
        if pressed or selected:
            return True
        disabled      = btn.get_attribute("disabled") is not None
        aria_disabled = btn.get_attribute("aria-disabled") == "true"
        if disabled or aria_disabled:
            return False
        btn.scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        btn.click(force=True)
        try:
            page.wait_for_function(f"""
            () => {{
                const b = document.querySelector('button[data-automation-id="{automation_id}"]');
                return b && (b.getAttribute('aria-pressed') === 'true' || b.classList.contains('Mui-selected'));
            }}
            """, timeout=2000)
        except:
            pass
        btn = page.query_selector(f'button[data-automation-id="{automation_id}"]')
        if not btn:
            return False
        return btn.get_attribute("aria-pressed") == "true" or "Mui-selected" in (btn.get_attribute("class") or "")
    except Exception as e:
        log(f"  click_button error ({automation_id}): {e}")
        return False


def set_autocomplete(page: Page, automation_id: str, value: str) -> bool:
    try:
        container = page.query_selector(f'[data-automation-id="{automation_id}"]')
        if not container:
            return False
        input_el = container.query_selector("input")
        if not input_el:
            return False
        current = input_el.get_attribute("value") or ""
        if current == value:
            return True
        input_el.click()
        page.wait_for_timeout(300)
        options = page.query_selector_all('[role="listbox"] [role="option"]')
        target = next((o for o in options if o.inner_text().strip() == value), None)
        if not target:
            page.keyboard.press("Escape")
            return False
        target.click()
        try:
            page.wait_for_function(f"""
            () => {{
                const el = document.querySelector('[data-automation-id="{automation_id}"] input');
                return el && el.value === '{value}';
            }}
            """, timeout=2000)
        except:
            pass
        return True
    except:
        return False


def get_active_shape(page: Page) -> str:
    try:
        return page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button[data-automation-id^="center-stone-shape-"]');
            for (const btn of btns) {
                const classes = Array.from(btn.classList);
                const pressed = btn.getAttribute('aria-pressed') === 'true'
                    || classes.includes('Mui-selected')
                    || classes.includes('Mui-active')
                    || classes.includes('selected')
                    || btn.getAttribute('aria-checked') === 'true'
                    || classes.some(c => c.includes('selected') || c.includes('active'));
                if (pressed) {
                    return btn.getAttribute('data-automation-id').replace('center-stone-shape-', '');
                }
            }
            return '';
        }
        """)
    except:
        return ""


def ensure_shape(page: Page, shape: str, retries: int = 5) -> bool:
    automation_id = f"center-stone-shape-{shape}"
    for attempt in range(retries):
        if get_active_shape(page) == shape:
            return True
        log(f"  Re-seleccionando {shape} (intento {attempt+1})")
        try:
            btn = page.query_selector(f'button[data-automation-id="{automation_id}"]')
            if not btn:
                log(f"  Boton no encontrado — recargando configurador...")
                try:
                    page.goto(CONFIGURATOR_URL, wait_until="domcontentloaded", timeout=20000)
                    if "login.nivoda.com" in page.url:
                        log("  Redirigido a login")
                        return False
                    page.wait_for_timeout(3000)
                    for sel in ['button:has-text("Entendido")', 'button:has-text("OK")']:
                        try:
                            b = page.query_selector(sel)
                            if b and b.is_visible():
                                b.click()
                                page.wait_for_timeout(300)
                        except:
                            pass
                    page.wait_for_selector(
                        f'button[data-automation-id="{automation_id}"]',
                        timeout=30000
                    )
                except Exception as e:
                    log(f"  Error recargando: {e}")
                continue

            if btn.get_attribute("disabled") is not None or btn.get_attribute("aria-disabled") == "true":
                page.wait_for_timeout(800)
                continue
            btn.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            page.evaluate(f"""
            () => {{
                const btn = document.querySelector('button[data-automation-id="{automation_id}"]');
                if (btn) {{
                    btn.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true}}));
                    btn.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true}}));
                    btn.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
                }}
            }}
            """)
            page.wait_for_timeout(800)
        except Exception as e:
            log(f"  Error ensure_shape: {e}")
            if "closed" in str(e).lower():
                return False
    return get_active_shape(page) == shape


# ── Carga robusta del configurador ────────────────────────────────────────────

def load_configurator(page: Page, shape: str, out_dir: Path, max_attempts: int = 5) -> bool:
    for attempt in range(1, max_attempts + 1):
        log(f"Cargando configurador (intento {attempt}/{max_attempts})...")
        try:
            page.goto(CONFIGURATOR_URL, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            log(f"  goto falló: {e}")
            page.wait_for_timeout(5000)
            continue

        if "login.nivoda.com" in page.url or "auth" in page.url:
            log("  Sesion expirada — redirigido a login")
            return False

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass

        try:
            page.wait_for_function(CONFIGURATOR_LOADED_JS, timeout=30000, polling=500)
            log("  UI del configurador detectada")
        except:
            body_len = page.evaluate("() => document.body?.innerHTML?.length || 0")
            log(f"  Timeout esperando UI (body={body_len}). Reintentando en 10s...")
            page.screenshot(path=str(out_dir / f"debug_load_{shape}_attempt{attempt}.png"))
            page.wait_for_timeout(10000)
            continue

        for selector in [
            'button:has-text("Entendido")',
            'button:has-text("Accept")',
            'button:has-text("OK")',
            '[data-automation-id="modal-close"]',
            '[aria-label="Close"]',
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(400)
            except:
                pass

        try:
            page.wait_for_function(CONFIGURATOR_LOADED_JS, timeout=10000)
        except:
            log("  UI desapareció tras cerrar modal — reintentando...")
            continue

        log(f"  Configurador listo en intento {attempt}")
        return True

    page.screenshot(path=str(out_dir / f"debug_load_{shape}_FINAL.png"))
    log(f"FALLO TOTAL: configurador no cargo tras {max_attempts} intentos")
    return False


# ── Espera de imagen reactiva ─────────────────────────────────────────────────

def wait_for_image(page: Page, required: int = 3, timeout_ms: int = 20000) -> bool:
    try:
        try:
            page.wait_for_function("""
            () => {
                const overlay = document.querySelector('[data-automation-id="loading-overlay"]');
                if (!overlay) return true;
                const style = getComputedStyle(overlay);
                return style.display === 'none'
                    || style.visibility === 'hidden'
                    || parseFloat(style.opacity || '1') < 0.1;
            }
            """, timeout=6000)
        except:
            pass

        page.wait_for_function(f"""
        () => {{
            const thumbs = document.querySelectorAll('[data-automation-id="thumbnail"]');
            return thumbs.length >= {required};
        }}
        """, timeout=timeout_ms)

        page.wait_for_function(f"""
        () => {{
            const thumbs = [...document.querySelectorAll('[data-automation-id="thumbnail"]')];
            if (thumbs.length < {required}) return false;

            const targets = thumbs.slice(0, {required});
            return targets.every(img =>
                img.src
                && !img.src.includes('loading')
                && img.naturalWidth > 0
                && img.naturalHeight > 0
            );
        }}
        """, timeout=timeout_ms)

        page.wait_for_timeout(500)
        return True

    except Exception as e:
        log(f"  wait_for_image timeout o error: {e}")
        try:
            count = page.evaluate("""
            () => [...document.querySelectorAll('[data-automation-id="thumbnail"]')]
                    .filter(img => img.naturalWidth > 0).length
            """)
            log(f"  Rescate: {count} thumbnail(s) visibles")
            return count > 0
        except:
            return False


# ── Captura ───────────────────────────────────────────────────────────────────

def capture_state(page: Page, combo: dict) -> dict | None:
    try:
        if "login.nivoda.com" in page.url:
            return None
    except:
        return None

    wait_for_image(page)
    page.wait_for_timeout(300)

    if "ring-configurator" not in page.url:
        return None

    sku_url = re.search(r'sku=([^&]+)', page.url)
    sku_url = sku_url.group(1) if sku_url else ""

    try:
        images = page.evaluate("""
        () => {
            const imgs = [];
            document.querySelectorAll('[data-automation-id="thumbnail"]').forEach(img => {
                const src = img.src || img.getAttribute('data-src') || '';
                if (src && !src.includes('loading') && img.naturalWidth > 0) imgs.push(src);
            });
            document.querySelectorAll('img[alt="preview"]').forEach(img => {
                if (img.src && img.naturalWidth > 0 && !imgs.includes(img.src)) imgs.push(img.src);
            });
            if (imgs.length === 0) {
                document.querySelectorAll('img').forEach(img => {
                    if (img.naturalWidth > 200 && img.src
                        && !img.src.includes('logo')
                        && !img.src.includes('icon')
                        && !img.src.includes('loading')) {
                        imgs.push(img.src);
                    }
                });
            }
            return [...new Set(imgs)].slice(0, 3);
        }
        """)
    except:
        images = []

    try:
        sku_page = page.evaluate("""
        () => {
            const el = document.querySelector('[data-automation-id="jewellery-configurator-nivoda-sku"]');
            return el ? el.innerText.replace('Nivoda SKU:', '').trim() : '';
        }
        """)
    except:
        sku_page = ""

    try:
        price_mount = page.evaluate("""
        () => {
            const el = document.querySelector('[data-automation-id="ring-configurator-footer-mount-price"]');
            return el ? el.innerText.trim() : '';
        }
        """)
    except:
        price_mount = ""

    try:
        title = page.evaluate("""
        () => {
            const el = document.querySelector('[data-automation-id="jewellery-configurator-title"]');
            return el ? el.innerText.trim() : '';
        }
        """)
    except:
        title = ""

    return {
        "sku":         sku_url or sku_page,
        "url":         page.url,
        "title":       title,
        "price_mount": price_mount,
        "images":      images,
        "has_image":   len(images) > 0,
        "combination": combo,
        "scraped_at":  datetime.now().isoformat(),
    }


# ── Setup fijos ───────────────────────────────────────────────────────────────

def setup_fixed_options(page: Page, shape: str) -> bool:
    log(f"  Configurando fijos: {FIXED_METAL_TYPE} / {FIXED_METAL_QUALITY} / {FIXED_STONE_TYPE} / {FIXED_STONE_SIZE}")

    if not ensure_shape(page, shape):
        return False

    if not click_button(page, f"{PREFIXES['stone_type']}{FIXED_STONE_TYPE}"):
        log(f"  WARN: no se pudo seleccionar stone_type={FIXED_STONE_TYPE}")
    page.wait_for_timeout(400)

    if not ensure_shape(page, shape):
        return False
    metal_state = get_available_options(page, PREFIXES["metal_type"])
    if FIXED_METAL_TYPE in metal_state["available"]:
        click_button(page, f"{PREFIXES['metal_type']}{FIXED_METAL_TYPE}")
        page.wait_for_timeout(400)
    else:
        log(f"  WARN: GOLD no disponible en metal_type: {metal_state}")

    if not ensure_shape(page, shape):
        return False
    qual_state = get_available_options(page, PREFIXES["metal_quality"])
    if FIXED_METAL_QUALITY in qual_state["available"]:
        click_button(page, f"{PREFIXES['metal_quality']}{FIXED_METAL_QUALITY}")
        page.wait_for_timeout(300)
    else:
        log(f"  WARN: KT_18 no disponible en metal_quality: {qual_state}")

    set_autocomplete(page, "jewellery-configurator-center-stone-size", FIXED_STONE_SIZE)
    page.wait_for_timeout(400)

    log("  Fijos configurados OK")
    return True


# ── Loop principal con pruning ────────────────────────────────────────────────

def scrape_shape(page: Page, shape: str, shape_data: dict,
                 seen_keys: set, results: list, out_file: Path) -> bool:
    """
    Loop principal con pruning de sub-árboles ya scrapeados.

    Antes de hacer cualquier click, se evalúa si TODAS las combinaciones
    del sub-árbol correspondiente ya están en seen_keys. Si es así, se
    salta el nivel completo sin tocar la UI.

    Esto garantiza que en una reanudación el worker no navegue por
    combinaciones ya capturadas — solo hace clicks para las pendientes.
    """
    idx = 0
    fixed_ok = False

    ring_heads = [h for h in shape_data.get("ring_head", []) if h in {'FOUR_PRONGS', 'BASKET', 'PEG_HEAD', 'PAVE', 'SINGLE_HALO', 'DOUBLE_HALO', 'CROWN', 'FLOWER_HALO'}]
    mountings  = [m for m in shape_data.get("mounting", []) if m in {'SINGLE', 'DOUBLE', 'DOUBLE_TWIST', 'SQUARE_EDGE', 'TAPERED', 'CONTEMPORARY', 'HIDDEN_HALO', 'SPLIT'}]

    # Partial base que siempre incluimos (fijos que no varían)
    BASE = {
        "stone_shape":       shape,
        "stone_type":        FIXED_STONE_TYPE,
        "metal_type":        FIXED_METAL_TYPE,
        "metal_quality":     FIXED_METAL_QUALITY,
        "center_stone_size": FIXED_STONE_SIZE,
    }

    def save():
        out_file.write_text(json.dumps({
            "shape":      shape,
            "scraped_at": datetime.now().isoformat(),
            "total":      len(results),
            "partial":    True,
            "rings":      results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def ensure_fixed(page, shape):
        nonlocal fixed_ok
        if not fixed_ok:
            if not setup_fixed_options(page, shape):
                return False
            fixed_ok = True
        return True

    if not ensure_fixed(page, shape):
        return False

    for ring_head in ring_heads:

        # ── Pruning nivel ring_head ───────────────────────────────────────────
        # Para calcular el sub-árbol del ring_head necesitamos conocer los
        # mountings, pero los side_settings/carvings/peekaboos los leeremos
        # del DOM — no los conocemos a priori. Solo podemos hacer un pruning
        # exacto en los niveles que SÍ conocemos de antemano: head_color y
        # mounting_color (siempre 3×3). Para los niveles DOM-driven hacemos
        # un pruning parcial: contamos cuántas combos con este ring_head ya
        # están en seen_keys y comparamos con un estimado mínimo razonable.
        #
        # Pruning conservador: si NINGUNA combo de este ring_head falta, skip.
        # Se hace verificando que para TODOS los mountings conocidos y TODOS
        # los colores (3×3), al menos una combinación con cualquier
        # side_setting/carving/peekaboo falta. Si el sub-árbol mínimo
        # (solo colores, sin dims DOM) está completo, skipeamos.
        #
        # Estrategia práctica:
        #   - Para dims conocidas (ring_head, mounting, head_color, mount_color)
        #     hacemos pruning exacto.
        #   - Para dims DOM (side_setting, carving, peekaboo) leemos del DOM
        #     en el momento en que llegamos — si todas las combos de ese nivel
        #     están en seen_keys, skipeamos sin más clicks.

        partial_head = {**BASE, "ring_head": ring_head}

        # Pruning rápido de ring_head: ¿algún mounting con algún color falta?
        # Usamos solo los mountings conocidos del map + colores fijos.
        # Si para todos los mountings y todos los colores ya tenemos datos
        # con AL MENOS un (side_setting, carving, peekaboo) cualquiera → skip.
        # Como no conocemos los DOM-dims, hacemos un check más simple:
        # buscamos en seen_keys si hay ALGUNA key que contenga este ring_head.
        head_has_pending = any(
            f'"ring_head": "{ring_head}"' in k
            and k not in seen_keys  # esta key aún no está (imposible por definición)
            for k in seen_keys  # lo que buscamos es lo contrario:
        )
        # Reescrito correctamente:
        head_count_done = sum(
            1 for k in seen_keys
            if f'"ring_head": "{ring_head}"' in k
        )
        # Si no hay ninguna done todavía, claramente hay pendientes.
        # Si hay algunas, verificamos más finamente en los niveles internos.
        # Solo skipeamos a nivel ring_head si sabemos con certeza que están
        # TODAS — lo cual solo podemos saber en los niveles inferiores.
        # Así que NO skipeamos a nivel ring_head todavía; lo haremos en mounting.

        if not ensure_shape(page, shape):
            return False
        fixed_ok = False
        if not ensure_fixed(page, shape):
            return False

        head_state = get_available_options(page, PREFIXES["ring_head"])
        if ring_head not in head_state["available"]:
            log(f"  SKIP ring_head={ring_head} (no disponible en DOM)")
            continue

        click_button(page, f"{PREFIXES['ring_head']}{ring_head}")
        page.wait_for_timeout(400)

        for mounting in mountings:

            partial_mount = {**partial_head, "mounting": mounting}

            # ── Pruning exacto nivel mounting × colores ───────────────────────
            # En este nivel ya podemos construir el sub-árbol de colores (3×3=9)
            # sin necesidad de conocer los DOM-dims, porque si TODOS los combos
            # de colores con CUALQUIER side_setting/carving/peekaboo ya están
            # capturados, el nivel está completo.
            #
            # Pero como no conocemos los DOM-dims a priori, usamos este criterio:
            # Si para cada (head_color, mounting_color) existe AL MENOS UNA
            # entrada en seen_keys con este (ring_head, mounting), asumimos que
            # al menos ese color-combo fue cubierto. No es pruning completo, pero
            # sí evita re-navegar monturas completamente procesadas.
            #
            # Pruning estricto: skip si para TODOS los (hc, mc) ya hay ≥1 combo.
            color_combos_done = set()
            for k in seen_keys:
                if (f'"ring_head": "{ring_head}"' in k
                        and f'"mounting": "{mounting}"' in k):
                    for hc in HEAD_COLORS:
                        for mc in MOUNT_COLORS:
                            if (f'"head_color": "{hc}"' in k
                                    and f'"mounting_color": "{mc}"' in k):
                                color_combos_done.add((hc, mc))

            all_color_combos = {(hc, mc) for hc in HEAD_COLORS for mc in MOUNT_COLORS}
            if color_combos_done >= all_color_combos:
                log(f"  SKIP mounting={mounting} (todos los colores ya capturados)")
                continue

            if not ensure_shape(page, shape):
                return False
            mount_state = get_available_options(page, PREFIXES["mounting"])
            if mounting not in mount_state["available"]:
                continue

            click_button(page, f"{PREFIXES['mounting']}{mounting}")
            page.wait_for_timeout(400)

            # ── side_setting — leer del DOM ───────────────────────────────────
            side_state    = get_available_options(page, PREFIXES["side_setting"])
            side_settings = [s for s in (side_state["available"] or ["NONE"]) if s in {'NONE', 'U_PAVE', 'CHANNEL', 'PRONG', 'BEAD', 'PAVE'}]

            for side_setting in side_settings:

                partial_side = {**partial_mount, "side_setting": side_setting}

                # Pruning nivel side_setting
                side_color_done = set()
                for k in seen_keys:
                    if (f'"ring_head": "{ring_head}"' in k
                            and f'"mounting": "{mounting}"' in k
                            and f'"side_setting": "{side_setting}"' in k):
                        for hc in HEAD_COLORS:
                            for mc in MOUNT_COLORS:
                                if (f'"head_color": "{hc}"' in k
                                        and f'"mounting_color": "{mc}"' in k):
                                    side_color_done.add((hc, mc))

                if side_color_done >= all_color_combos:
                    log(f"  SKIP side_setting={side_setting} (todos los colores ya capturados)")
                    continue

                if not ensure_shape(page, shape):
                    return False
                if not click_button(page, f"{PREFIXES['side_setting']}{side_setting}"):
                    continue
                page.wait_for_timeout(300)

                # ring_carving solo cuando side_setting == NONE
                if side_setting == "NONE":
                    carv_state = get_available_options(page, PREFIXES["ring_carving"])
                    carvings   = ["PLAIN"]
                else:
                    carvings = [None]

                # peekaboo — leer del DOM
                peek_state = get_available_options(page, PREFIXES["peekaboo"])
                peekaboos  = ["NONE"]

                for carving in carvings:

                    partial_carv = dict(partial_side)
                    if carving:
                        partial_carv["ring_carving"] = carving

                    # Pruning nivel carving
                    carv_color_done = set()
                    for k in seen_keys:
                        carv_match = (
                            f'"ring_carving": "{carving}"' in k if carving
                            else '"ring_carving"' not in k
                        )
                        if (f'"ring_head": "{ring_head}"' in k
                                and f'"mounting": "{mounting}"' in k
                                and f'"side_setting": "{side_setting}"' in k
                                and carv_match):
                            for hc in HEAD_COLORS:
                                for mc in MOUNT_COLORS:
                                    if (f'"head_color": "{hc}"' in k
                                            and f'"mounting_color": "{mc}"' in k):
                                        carv_color_done.add((hc, mc))

                    if carv_color_done >= all_color_combos:
                        log(f"  SKIP carving={carving} (todos los colores ya capturados)")
                        continue

                    if carving:
                        if not ensure_shape(page, shape):
                            return False
                        if not click_button(page, f"{PREFIXES['ring_carving']}{carving}"):
                            continue
                        page.wait_for_timeout(300)

                    for peekaboo in peekaboos:

                        partial_peek = dict(partial_carv)
                        if peekaboo and peekaboo != "NONE":
                            partial_peek["peekaboo"] = peekaboo

                        # Pruning nivel peekaboo × colores (exacto — conocemos todos los valores)
                        remaining_color_dims = [
                            ("head_color",     HEAD_COLORS),
                            ("mounting_color", MOUNT_COLORS),
                        ]
                        if subtree_done_kv(seen_keys, partial_peek, remaining_color_dims):
                            log(
                                f"  SKIP peekaboo={peekaboo} | "
                                f"{ring_head} | {mounting} | {side_setting} | {carving} "
                                f"(todos los colores ya capturados)"
                            )
                            continue

                        if peekaboo and peekaboo != "NONE":
                            if not ensure_shape(page, shape):
                                return False
                            if not click_button(page, f"{PREFIXES['peekaboo']}{peekaboo}"):
                                continue
                            page.wait_for_timeout(300)

                        # ── head_color × mounting_color ───────────────────────
                        for hcolor in HEAD_COLORS:

                            mcolor = hcolor  # Solo colores identicos para la cabeza y montura
                            partial_hc = {**partial_peek, "head_color": hcolor}

                            # Pruning nivel head_color
                            if subtree_done_kv(
                                seen_keys, partial_hc,
                                [("mounting_color", [mcolor])]
                            ):
                                log(f"  SKIP head_color={hcolor} (ya capturado)")
                                continue

                            if not ensure_shape(page, shape):
                                return False
                            if not click_button(page, f"{PREFIXES['head_color']}{hcolor}"):
                                log(f"  WARN head_color={hcolor} no clickeable")
                                continue
                            page.wait_for_timeout(200)

                            combo = {
                                **BASE,
                                "ring_head":      ring_head,
                                "mounting":       mounting,
                                "side_setting":   side_setting,
                                "ring_carving":   carving,
                                "peekaboo":       peekaboo,
                                "head_color":     hcolor,
                                "mounting_color": mcolor,
                            }
                            combo_key = make_combo_key(combo)

                            # Guard final — no debería llegar aquí si el pruning funcionó
                            if combo_key in seen_keys:
                                continue

                            if not ensure_shape(page, shape):
                                return False
                            if not click_button(page, f"{PREFIXES['mounting_color']}{mcolor}"):
                                log(f"  WARN mounting_color={mcolor} no clickeable")
                                continue
                            page.wait_for_timeout(200)

                                idx += 1
                                state = capture_state(page, combo)
                                if state is None:
                                    log("Sesion expirada")
                                    return False

                                seen_keys.add(combo_key)
                                results.append(state)
                                imgs = len(state["images"])
                                log(
                                    f"[{idx}] {'OK' if imgs else 'NO-IMG'} "
                                    f"{state['sku'][:20]} | {ring_head} | {mounting} | "
                                    f"{side_setting} | {carving} | {peekaboo} | "
                                    f"{hcolor} | {mcolor} | imgs:{imgs}"
                                )

                                if len(results) % 20 == 0:
                                    save()

    save()
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def run(shape: str, session_file: str, map_file: str, output_dir: str):
    global _log_file, _shape_label
    _shape_label = shape
    out_dir  = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _log_file = out_dir / f"worker_{shape}.log"
    out_file  = out_dir / f"results_{shape}.json"
    _log_file.write_text("", encoding="utf-8")

    config_map = json.loads(Path(map_file).read_text(encoding="utf-8"))
    shape_data = config_map["availability_by_shape"].get(shape, {}).get("breakdown", {})

    # ── Reanudación ───────────────────────────────────────────────────────────
    seen_keys: set = set()
    results: list  = []
    if out_file.exists():
        try:
            prev = json.loads(out_file.read_text(encoding="utf-8"))
            results   = prev.get("rings", [])
            seen_keys = {
                make_combo_key(r["combination"])
                for r in results
            }
            log(f"Retomando: {len(results)} ya scrapeados, {len(seen_keys)} seen_keys cargadas")
        except Exception as e:
            log(f"Error cargando resultados previos: {e}")

    global_file = Path(__file__).parent / "nivoda_rings_v4.json"
    if global_file.exists():
        try:
            g_data = json.loads(global_file.read_text(encoding="utf-8"))
            g_rings = g_data.get("rings", [])
            added = 0
            for r in g_rings:
                if r["combination"].get("stone_shape") == shape:
                    key = make_combo_key(r["combination"])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(r)
                        added += 1
            if added > 0:
                log(f"Agregadas {added} combinaciones desde JSON global maestro.")
        except Exception as e:
            log(f"Error cargando global maestro: {e}")

    log(f"Iniciando worker para {shape}")
    log(f"Fijos: metal={FIXED_METAL_TYPE} quality={FIXED_METAL_QUALITY} stone={FIXED_STONE_TYPE} size={FIXED_STONE_SIZE}")

    positions = {
        "CUSHION":  (0,    0),   "EMERALD":  (390,  0),
        "MARQUISE": (780,  0),   "OVAL":     (1170, 0),
        "PEAR":     (0,    480), "PRINCESS": (390,  480),
        "RADIANT":  (780,  480), "ROUND":    (1170, 480),
    }
    px, py = positions.get(shape, (0, 0))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=0,
            args=[
                f"--window-position={px},{py}",
                "--window-size=380,460",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            storage_state=session_file,
            viewport={"width": 1380, "height": 860},
            locale="es-ES",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        if not load_configurator(page, shape, out_dir):
            browser.close()
            return

        page.wait_for_timeout(1500)

        if shape != "ROUND":
            log("Seleccionando ROUND como base...")
            try:
                round_btn = page.query_selector('button[data-automation-id="center-stone-shape-ROUND"]')
                if round_btn:
                    round_btn.click(force=True)
                    page.wait_for_timeout(1500)
            except:
                pass

        if not ensure_shape(page, shape):
            log(f"No se pudo seleccionar {shape}")
            browser.close()
            return

        log(f"Forma {shape} activa. Comenzando scrape...")
        ok = scrape_shape(page, shape, shape_data, seen_keys, results, out_file)
        browser.close()

    out_file.write_text(json.dumps({
        "shape":      shape,
        "scraped_at": datetime.now().isoformat(),
        "total":      len(results),
        "partial":    not ok,
        "rings":      results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    status = "COMPLETO" if ok else "PARCIAL (sesion expiro)"
    log(f"{status} — {len(results)} resultados guardados en {out_file}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Uso: python worker.py <SHAPE> <session.json> <configurator_map.json> <output_dir>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])