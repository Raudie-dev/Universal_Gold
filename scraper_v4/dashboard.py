"""
dashboard.py — Nivoda Scraper Dashboard v5
=========================================
Interfaz web para lanzar, monitorear y reanudar workers.

Uso:
    python dashboard.py

Abre automaticamente el browser en http://localhost:5555
"""

import json
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR      = Path(__file__).parent
SESSION_FILE  = BASE_DIR / "session.json"
MAP_FILE      = BASE_DIR / "configurator_map.json"
WORKER_SCRIPT = BASE_DIR / "worker.py"
OUTPUT_DIR    = BASE_DIR / "results"
FINAL_OUTPUT  = BASE_DIR / "nivoda_rings_v5.json"
PORT          = 5556

SHAPES = ["CUSHION","EMERALD","MARQUISE","OVAL","PEAR","PRINCESS","RADIANT","ROUND"]

active_procs: dict[str, subprocess.Popen] = {}
proc_lock = threading.Lock()


def get_shape_status(shape: str) -> dict:
    out_file  = OUTPUT_DIR / f"results_{shape}.json"
    log_file  = OUTPUT_DIR / f"worker_{shape}.log"
    total    = 0
    partial  = True
    last_sku = ""
    last_line= ""
    if out_file.exists():
        try:
            data    = json.loads(out_file.read_text(encoding="utf-8"))
            total   = data.get("total", 0)
            partial = data.get("partial", True)
            rings   = data.get("rings", [])
            if rings:
                last_sku = rings[-1].get("sku", "")
        except:
            pass
    if log_file.exists():
        try:
            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                last_line = lines[-1]
        except:
            pass
    with proc_lock:
        running = shape in active_procs and active_procs[shape].poll() is None
    status = (
        "running" if running else
        ("done"    if not partial and total > 0 else
        ("partial" if total > 0 else "idle"))
    )
    return {
        "shape":    shape,
        "total":    total,
        "partial":  partial,
        "status":   status,
        "last_sku": last_sku,
        "last_log": last_line,
    }


def launch_worker(shape: str) -> dict:
    with proc_lock:
        if shape in active_procs and active_procs[shape].poll() is None:
            return {"ok": False, "msg": f"{shape} ya esta corriendo"}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_out = OUTPUT_DIR / f"worker_{shape}.stdout"
    cmd = [
        sys.executable, str(WORKER_SCRIPT),
        shape,
        str(SESSION_FILE),
        str(MAP_FILE),
        str(OUTPUT_DIR),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=open(log_out, "w"),
        stderr=subprocess.STDOUT,
        text=True,
    )
    with proc_lock:
        active_procs[shape] = proc
    return {"ok": True, "msg": f"{shape} lanzado (PID {proc.pid})", "pid": proc.pid}


def stop_worker(shape: str) -> dict:
    with proc_lock:
        proc = active_procs.get(shape)
        if not proc or proc.poll() is not None:
            return {"ok": False, "msg": f"{shape} no esta corriendo"}
        proc.terminate()
        del active_procs[shape]
    return {"ok": True, "msg": f"{shape} detenido"}


def reset_shape(shape: str) -> dict:
    """Borra results_SHAPE.json, worker_SHAPE.log y worker_SHAPE.stdout."""
    with proc_lock:
        if shape in active_procs and active_procs[shape].poll() is None:
            return {"ok": False, "msg": f"{shape} esta corriendo — detenerlo primero"}
    deleted = []
    for pattern in [f"results_{shape}.json", f"worker_{shape}.log", f"worker_{shape}.stdout"]:
        f = OUTPUT_DIR / pattern
        if f.exists():
            f.unlink()
            deleted.append(pattern)
    if deleted:
        return {"ok": True, "msg": f"{shape} reseteado ({len(deleted)} archivos borrados)"}
    return {"ok": True, "msg": f"{shape} ya estaba limpio"}


def get_logs(shape: str, lines: int = 200) -> dict:
    """Retorna las ultimas N lineas del log de una forma."""
    log_file    = OUTPUT_DIR / f"worker_{shape}.log"
    stdout_file = OUTPUT_DIR / f"worker_{shape}.stdout"
    target = log_file if log_file.exists() else stdout_file
    if not target.exists():
        return {"ok": True, "lines": [], "file": str(target), "total": 0}
    try:
        content   = target.read_text(encoding="utf-8", errors="replace")
        all_lines = content.strip().splitlines()
        return {
            "ok":    True,
            "lines": all_lines[-lines:],
            "file":  target.name,
            "total": len(all_lines),
        }
    except Exception as e:
        return {"ok": False, "lines": [], "error": str(e)}


def merge_results() -> dict:
    all_rings = []
    summary   = {}
    for shape in SHAPES:
        f = OUTPUT_DIR / f"results_{shape}.json"
        if not f.exists():
            continue
        try:
            data  = json.loads(f.read_text(encoding="utf-8"))
            rings = data.get("rings", [])
            all_rings.extend(rings)
            summary[shape] = {"total": len(rings), "partial": data.get("partial", True)}
        except:
            pass
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
    django_output = BASE_DIR.parent / "app1" / "data" / "nivoda_rings_v5.json"
    django_output.parent.mkdir(parents=True, exist_ok=True)
    FINAL_OUTPUT.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    django_output.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "total": len(all_rings), "file": f"Guardado en {django_output.name} (Django)"}

def run_login() -> dict:
    cmd = [sys.executable, str(BASE_DIR / "save_session.py")]
    subprocess.Popen(cmd)
    return {"ok": True, "msg": "Abriendo ventana para Login..."}


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nivoda Scraper v5</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0f0f0f;--surface:#1a1a1a;--border:#2a2a2a;
    --text:#e8e6e0;--muted:#6b6962;--accent:#7c6af7;
    --green:#22c55e;--amber:#f59e0b;--red:#ef4444;
    --font:'DM Mono',ui-monospace,monospace;
  }
  body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:13px;min-height:100vh;padding:2rem}
  h1{font-size:11px;letter-spacing:.12em;color:var(--muted);text-transform:uppercase;margin-bottom:.4rem;font-weight:400}
  .subtitle{font-size:10px;color:var(--muted);opacity:.6;margin-bottom:2rem;letter-spacing:.06em}
  .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:2rem}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;transition:border-color .2s}
  .card.running{border-color:var(--accent)44}
  .card.done{border-color:var(--green)44}
  .card.partial{border-color:var(--amber)33}
  .card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
  .shape{font-size:11px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--border);flex-shrink:0}
  .dot.running{background:var(--accent);box-shadow:0 0 8px var(--accent)}
  .dot.done{background:var(--green)}
  .dot.partial{background:var(--amber)}
  .count{font-size:28px;font-weight:500;color:var(--text);letter-spacing:-.02em;margin-bottom:2px}
  .meta{font-size:11px;color:var(--muted);margin-bottom:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .btn-full{width:100%;padding:7px;border-radius:6px;border:1px solid var(--border);background:transparent;
            color:var(--muted);cursor:pointer;font-family:var(--font);font-size:10px;letter-spacing:.04em;
            transition:all .15s;margin-bottom:6px}
  .btn-full:hover:not(:disabled){background:#ffffff08;border-color:#ffffff22;color:var(--text)}
  .btn-full.primary{border-color:var(--accent)66;color:var(--accent)}
  .btn-full.primary:hover{background:var(--accent)11}
  .btn-full.stop{border-color:var(--red)44;color:var(--red)99}
  .btn-full.stop:hover{background:var(--red)11;color:var(--red)}
  .btn-row{display:flex;gap:6px}
  .btn{flex:1;padding:6px 4px;border-radius:6px;border:1px solid var(--border);background:transparent;
       color:var(--muted);cursor:pointer;font-family:var(--font);font-size:10px;letter-spacing:.04em;transition:all .15s}
  .btn:hover:not(:disabled){background:#ffffff08;border-color:#ffffff22;color:var(--text)}
  .btn.danger{border-color:var(--red)33;color:var(--red)55}
  .btn.danger:hover:not(:disabled){background:var(--red)11;border-color:var(--red)55;color:var(--red)}
  .btn:disabled{opacity:.22;cursor:default}
  .footer{display:flex;gap:12px;align-items:center;padding:16px;background:var(--surface);
          border:1px solid var(--border);border-radius:10px;margin-bottom:1.5rem}
  .total-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
  .total-count{font-size:22px;font-weight:500;color:var(--text);margin-left:12px}
  .spacer{flex:1}
  .footer-btn{padding:8px 18px;border-radius:6px;background:transparent;cursor:pointer;
              font-family:var(--font);font-size:11px;letter-spacing:.05em;transition:all .15s}
  .footer-btn.accent{border:1px solid var(--accent)44;color:var(--accent)}
  .footer-btn.accent:hover{background:var(--accent)11}
  .footer-btn.green{border:1px solid var(--green)44;color:var(--green)}
  .footer-btn.green:hover{background:var(--green)11}
  .log{background:var(--surface);border:1px solid var(--border);border-radius:10px;
       padding:14px;max-height:140px;overflow-y:auto}
  .log-line{font-size:11px;color:var(--muted);line-height:1.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .log-line.ok{color:var(--green)cc}
  .log-line.err{color:var(--red)cc}
  .log-line.info{color:var(--accent)cc}
  .toast{position:fixed;bottom:2rem;right:2rem;background:var(--surface);border:1px solid var(--border);
         border-radius:8px;padding:12px 18px;font-size:12px;color:var(--text);
         opacity:0;transform:translateY(8px);transition:all .25s;pointer-events:none;z-index:200}
  .toast.show{opacity:1;transform:translateY(0)}

  /* Modal logs */
  .modal-backdrop{position:fixed;inset:0;background:#000000bb;z-index:100;
                  display:none;align-items:center;justify-content:center}
  .modal-backdrop.open{display:flex}
  .modal{background:var(--surface);border:1px solid var(--border);border-radius:12px;
         width:min(860px,94vw);max-height:82vh;display:flex;flex-direction:column;overflow:hidden}
  .modal-header{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--border)}
  .modal-title{font-size:11px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase}
  .modal-shape-tag{font-size:12px;font-weight:500;color:var(--accent)}
  .modal-file{font-size:10px;color:var(--muted);opacity:.55;margin-left:4px}
  .modal-auto{font-size:10px;color:var(--accent);opacity:.7;margin-left:auto}
  .modal-close{background:transparent;border:1px solid var(--border);color:var(--muted);
               border-radius:6px;padding:4px 12px;cursor:pointer;font-family:var(--font);
               font-size:11px;transition:all .15s;margin-left:10px}
  .modal-close:hover{border-color:#ffffff22;color:var(--text)}
  .modal-body{flex:1;overflow-y:auto;padding:14px 18px;font-size:11px;line-height:1.85}
  .log-modal-line{white-space:pre-wrap;word-break:break-all;color:var(--muted)}
  .log-modal-line.ok-line{color:#22c55eaa}
  .log-modal-line.err-line{color:#ef4444aa}
  .log-modal-line.warn-line{color:#f59e0baa}
  .modal-footer{padding:10px 18px;border-top:1px solid var(--border);
                display:flex;align-items:center;font-size:10px;color:var(--muted)}

  /* Confirm */
  .confirm-backdrop{position:fixed;inset:0;background:#000000cc;z-index:150;
                    display:none;align-items:center;justify-content:center}
  .confirm-backdrop.open{display:flex}
  .confirm-box{background:var(--surface);border:1px solid var(--border);border-radius:10px;
               padding:26px 28px;width:310px;text-align:center}
  .confirm-title{font-size:12px;color:var(--text);margin-bottom:8px;letter-spacing:.04em}
  .confirm-sub{font-size:11px;color:var(--muted);margin-bottom:22px;line-height:1.65}
  .confirm-btns{display:flex;gap:10px;justify-content:center}
  .confirm-ok{padding:8px 22px;border-radius:6px;border:1px solid var(--red)55;background:transparent;
              color:var(--red);cursor:pointer;font-family:var(--font);font-size:11px;transition:all .15s}
  .confirm-ok:hover{background:var(--red)11}
  .confirm-cancel{padding:8px 22px;border-radius:6px;border:1px solid var(--border);background:transparent;
                  color:var(--muted);cursor:pointer;font-family:var(--font);font-size:11px;transition:all .15s}
  .confirm-cancel:hover{color:var(--text)}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>

<h1>Nivoda Ring Scraper v5</h1>
<p class="subtitle">Fijo: GOLD / KT_18 / LABGROWN / 1ct &nbsp;·&nbsp; Itera: head · mounting · side · carving · peekaboo · head_color · mount_color</p>

<div class="grid" id="grid"></div>

<div class="footer">
  <span class="total-label">Total</span>
  <span class="total-count" id="total">0</span>
  <div class="spacer"></div>
  <button class="footer-btn accent" onclick="doLogin()">Guardar Sesión</button>
  <button class="footer-btn accent" onclick="launchAll()">Lanzar todos</button>
  <button class="footer-btn green"  onclick="doMerge()">Merge final</button>
</div>

<div class="log" id="log"></div>
<div class="toast" id="toast"></div>

<!-- Modal de logs -->
<div class="modal-backdrop" id="logModal" onclick="closeLogModal(event)">
  <div class="modal">
    <div class="modal-header">
      <span class="modal-title">log</span>
      <span class="modal-shape-tag" id="modalShape"></span>
      <span class="modal-file" id="modalFile"></span>
      <span class="modal-auto">● live</span>
      <button class="modal-close" onclick="closeLogModalDirect()">Cerrar</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
    <div class="modal-footer" id="modalCount"></div>
  </div>
</div>

<!-- Confirm reset -->
<div class="confirm-backdrop" id="confirmModal">
  <div class="confirm-box">
    <div class="confirm-title">¿Resetear <span id="confirmShape"></span>?</div>
    <div class="confirm-sub">Se borrarán el JSON de resultados y los archivos de log.<br>Esta acción no se puede deshacer.</div>
    <div class="confirm-btns">
      <button class="confirm-cancel" onclick="closeConfirm()">Cancelar</button>
      <button class="confirm-ok" id="confirmOkBtn">Resetear</button>
    </div>
  </div>
</div>

<script>
const SHAPES = ['CUSHION','EMERALD','MARQUISE','OVAL','PEAR','PRINCESS','RADIANT','ROUND'];
let state = {};
let logModalShape = null;
let logModalTimer = null;

function ts(){ return new Date().toLocaleTimeString('es') }

function addLog(msg, cls=''){
  const el = document.getElementById('log');
  const d  = document.createElement('div');
  d.className   = 'log-line ' + cls;
  d.textContent = '[' + ts() + '] ' + msg;
  el.appendChild(d);
  el.scrollTop = el.scrollHeight;
  if(el.children.length > 80) el.removeChild(el.firstChild);
}

function showToast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 2800);
}

function renderGrid(){
  let totalAll = 0;
  const html = SHAPES.map(shape => {
    const s         = state[shape] || {total:0, status:'idle', last_sku:'', last_log:''};
    totalAll       += s.total;
    const dotClass  = s.status;
    const cardClass = ['running','done','partial'].includes(s.status) ? s.status : '';
    const meta      = s.last_sku
      ? s.last_sku.slice(0,22)+'...'
      : (s.last_log ? s.last_log.slice(-34) : 'sin datos');
    const isRunning = s.status === 'running';
    const isDone    = s.status === 'done';
    const hasData   = s.total > 0;

    let mainBtn;
    if(isRunning){
      mainBtn = `<button class="btn-full stop" onclick="stop('${shape}')">Detener</button>`;
    } else if(isDone){
      mainBtn = `<button class="btn-full" onclick="launch('${shape}')">Relanzar</button>`;
    } else {
      const label = hasData ? 'Reanudar' : 'Lanzar';
      mainBtn = `<button class="btn-full primary" onclick="launch('${shape}')">${label}</button>`;
    }

    const resetDis = isRunning ? 'disabled' : '';

    return `<div class="card ${cardClass}" id="card-${shape}">
      <div class="card-header">
        <span class="shape">${shape}</span>
        <div class="dot ${dotClass}"></div>
      </div>
      <div class="count">${s.total.toLocaleString()}</div>
      <div class="meta" title="${s.last_sku || s.last_log}">${meta}</div>
      ${mainBtn}
      <div class="btn-row">
        <button class="btn" onclick="openLogModal('${shape}')">Logs</button>
        <button class="btn danger" onclick="askReset('${shape}')" ${resetDis}>Reset</button>
      </div>
    </div>`;
  }).join('');

  document.getElementById('grid').innerHTML = html;
  document.getElementById('total').textContent = totalAll.toLocaleString();
}

async function fetchStatus(){
  try{
    const r    = await fetch('/api/status');
    const data = await r.json();
    state = {};
    data.forEach(s => state[s.shape] = s);
    renderGrid();
  }catch(e){}
}

async function launch(shape){
  addLog('Lanzando ' + shape + '...', 'info');
  try{
    const r = await fetch('/api/launch?shape=' + shape);
    const d = await r.json();
    addLog(d.msg, d.ok ? 'ok' : 'err');
    showToast(d.msg);
    setTimeout(fetchStatus, 1500);
  }catch(e){ addLog('Error: '+e,'err'); }
}

async function stop(shape){
  addLog('Deteniendo ' + shape + '...', 'info');
  try{
    const r = await fetch('/api/stop?shape=' + shape);
    const d = await r.json();
    addLog(d.msg, d.ok ? 'ok' : 'err');
    showToast(d.msg);
    setTimeout(fetchStatus, 800);
  }catch(e){ addLog('Error: '+e,'err'); }
}

async function launchAll(){
  addLog('Lanzando todos con 20s entre cada uno...', 'info');
  const idle = SHAPES.filter(s => { const st = state[s]; return !st || st.status !== 'running'; });
  for(const shape of idle){
    await launch(shape);
    await new Promise(r => setTimeout(r, 1000));
  }
  addLog('Todos lanzados.', 'ok');
}

async function doMerge(){
  addLog('Generando merge final...', 'info');
  try{
    const r = await fetch('/api/merge');
    const d = await r.json();
    addLog('Merge OK — ' + d.total + ' combos -> ' + d.file, 'ok');
    showToast('Merge: ' + d.total.toLocaleString() + ' combos. ' + d.file);
  }catch(e){ addLog('Error: '+e,'err'); }
}

async function doLogin(){
  addLog('Lanzando proceso de Login (abre navegador)...', 'info');
  try{
    const r = await fetch('/api/login');
    const d = await r.json();
    addLog(d.msg, d.ok ? 'ok' : 'err');
    showToast(d.msg);
  }catch(e){ addLog('Error: '+e,'err'); }
}

// ── Reset ─────────────────────────────────────────────────────────────────────

let pendingResetShape = null;

function askReset(shape){
  pendingResetShape = shape;
  document.getElementById('confirmShape').textContent = shape;
  document.getElementById('confirmOkBtn').onclick = doReset;
  document.getElementById('confirmModal').classList.add('open');
}

function closeConfirm(){
  document.getElementById('confirmModal').classList.remove('open');
  pendingResetShape = null;
}

async function doReset(){
  const shape = pendingResetShape;
  closeConfirm();
  if(!shape) return;
  addLog('Reseteando ' + shape + '...', 'info');
  try{
    const r = await fetch('/api/reset?shape=' + shape);
    const d = await r.json();
    addLog(d.msg, d.ok ? 'ok' : 'err');
    showToast(d.msg);
    setTimeout(fetchStatus, 600);
  }catch(e){ addLog('Error: '+e,'err'); }
}

// ── Modal logs ────────────────────────────────────────────────────────────────

async function openLogModal(shape){
  logModalShape = shape;
  document.getElementById('modalShape').textContent = shape;
  document.getElementById('logModal').classList.add('open');
  await refreshLogModal();
  logModalTimer = setInterval(refreshLogModal, 2000);
}

function escHtml(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

async function refreshLogModal(){
  if(!logModalShape) return;
  try{
    const r = await fetch('/api/logs?shape=' + logModalShape);
    const d = await r.json();
    if(!d.ok) return;

    document.getElementById('modalFile').textContent  = d.file ? '· ' + d.file : '';
    document.getElementById('modalCount').textContent =
      (d.total || d.lines.length) + ' líneas totales · mostrando últimas ' + d.lines.length;

    const body    = document.getElementById('modalBody');
    const newLast = d.lines[d.lines.length - 1] || '';
    const curLast = body.lastElementChild?.textContent || '';
    if(curLast === newLast && body.children.length > 0) return;

    const atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 50;
    body.innerHTML = d.lines.map(line => {
      let cls = '';
      const u = line.toUpperCase();
      if(u.includes('OK') || u.includes('COMPLETO') || u.includes('CONFIGURADOS OK')) cls = 'ok-line';
      else if(u.includes('ERROR') || u.includes('FALLO') || u.includes('EXPIRADA')) cls = 'err-line';
      else if(u.includes('WARN') || u.includes('SKIP') || u.includes('PARCIAL')) cls = 'warn-line';
      return `<div class="log-modal-line ${cls}">${escHtml(line)}</div>`;
    }).join('');

    if(atBottom) body.scrollTop = body.scrollHeight;
  }catch(e){}
}

function closeLogModal(e){
  if(e.target === document.getElementById('logModal')) closeLogModalDirect();
}

function closeLogModalDirect(){
  document.getElementById('logModal').classList.remove('open');
  if(logModalTimer){ clearInterval(logModalTimer); logModalTimer = null; }
  logModalShape = null;
}

// ── Init ──────────────────────────────────────────────────────────────────────
addLog('Dashboard listo — v5 (GOLD / KT18 / LAB / 1ct).', 'info');
fetchStatus();
setInterval(fetchStatus, 5000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self.send_html(HTML)
        elif path == "/api/status":
            self.send_json([get_shape_status(s) for s in SHAPES])
        elif path == "/api/launch":
            shape = qs.get("shape", [None])[0]
            if shape not in SHAPES:
                self.send_json({"ok": False, "msg": "Shape invalido"}, 400); return
            self.send_json(launch_worker(shape))
        elif path == "/api/stop":
            shape = qs.get("shape", [None])[0]
            if shape not in SHAPES:
                self.send_json({"ok": False, "msg": "Shape invalido"}, 400); return
            self.send_json(stop_worker(shape))
        elif path == "/api/reset":
            shape = qs.get("shape", [None])[0]
            if shape not in SHAPES:
                self.send_json({"ok": False, "msg": "Shape invalido"}, 400); return
            self.send_json(reset_shape(shape))
        elif path == "/api/logs":
            shape = qs.get("shape", [None])[0]
            if shape not in SHAPES:
                self.send_json({"ok": False, "msg": "Shape invalido"}, 400); return
            lines = int(qs.get("lines", ["200"])[0])
            self.send_json(get_logs(shape, lines))
        elif path == "/api/merge":
            self.send_json(merge_results())
        elif path == "/api/login":
            self.send_json(run_login())
        else:
            self.send_response(404); self.end_headers()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for f, name in [
        (SESSION_FILE,  "session.json"),
        (MAP_FILE,      "configurator_map.json"),
        (WORKER_SCRIPT, "worker.py"),
    ]:
        if not f.exists():
            print(f"ERROR: No se encontro {name}")
            sys.exit(1)

    server = HTTPServer(("localhost", PORT), Handler)
    url    = f"http://localhost:{PORT}"
    print("=" * 50)
    print(f"  Nivoda Scraper Dashboard v5")
    print(f"  {url}")
    print("=" * 50)
    print("  Ctrl+C para cerrar\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Dashboard cerrado.")
        with proc_lock:
            for shape, proc in active_procs.items():
                if proc.poll() is None:
                    proc.terminate()
                    print(f"  Worker {shape} detenido.")

if __name__ == "__main__":
    main()