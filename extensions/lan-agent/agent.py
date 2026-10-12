#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent LAN -- noeud local qui rejoint un "Multi-Agent LAN Orchestrator".

Implementation 100 % bibliotheque standard (aucune dependance a installer).

Ce que fait l'agent :
  * expose une petite API HTTP (manifest, /health, /tasks) sur le reseau local
  * s'enregistre aupres de l'orchestrateur (POST /register)
  * envoie un heartbeat periodique (POST /heartbeat)
  * accepte et execute des taches parmi une liste blanche de capacites sures
    (pas de shell distant, volontairement)

Usage :
    python agent.py --orchestrator http://192.168.1.35:8000 --port 8010 --register
    python agent.py --list-capabilities
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AGENT_VERSION = "1.0.0"
DEFAULT_PORT = 8010
DEFAULT_ORCHESTRATOR = "http://127.0.0.1:8000"
HEARTBEAT_INTERVAL = 30

# ---------------------------------------------------------------- capacites --
CAPABILITIES = [
    {"name": "echo", "description": "Renvoie le texte recu (test de liaison)."},
    {"name": "system_info", "description": "OS, hostname, CPU, memoire, IP locale, uptime."},
    {"name": "disk_usage", "description": "Espace disque par volume."},
    {"name": "http_fetch", "description": "Recupere une URL (GET) et renvoie code + taille + debut du corps."},
    {"name": "time", "description": "Heure locale et UTC, fuseau horaire."},
]
CAP_NAMES = [c["name"] for c in CAPABILITIES]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_ip() -> str:
    """IP locale utilisee pour sortir sur le LAN (pas 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 80))
        return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


# ------------------------------------------------------------- executrices --
def cap_echo(p):
    return {"echo": p.get("text") or p.get("task") or ""}


def cap_system_info(_p):
    u = platform.uname()
    info = {
        "hostname": socket.gethostname(),
        "os": f"{u.system} {u.release} ({u.version})",
        "machine": u.machine,
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "local_ip": local_ip(),
        "pid": os.getpid(),
        "uptime_agent_s": round(time.time() - STARTED, 1),
    }
    if shutil.which("wmic") or os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            info["ram_total_gb"] = round(m.ullTotalPhys / 1024 ** 3, 1)
            info["ram_used_pct"] = m.dwMemoryLoad
        except Exception:
            pass
    return info


def cap_disk_usage(_p):
    out = {}
    for letter in "CDEF":
        path = f"{letter}:\\" if os.name == "nt" else f"/{letter.lower()}"
        if os.path.exists(path):
            try:
                t, u, f = shutil.disk_usage(path)
                out[path] = {"total_gb": round(t / 1024 ** 3, 1), "free_gb": round(f / 1024 ** 3, 1)}
            except Exception:
                pass
    return {"volumes": out}


def cap_http_fetch(p):
    url = p.get("url") or p.get("task") or ""
    if not url.startswith(("http://", "https://")):
        raise ValueError("parametre 'url' manquant ou invalide")
    req = urllib.request.Request(url, headers={"User-Agent": f"lan-agent/{AGENT_VERSION}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read(4000)
        return {"url": url, "status": r.status, "body_head": body.decode("utf-8", "replace")[:1000]}


def cap_time(_p):
    return {"utc": now_iso(), "local": datetime.now().isoformat(), "tz": time.tzname[0]}


HANDLERS = {
    "echo": cap_echo,
    "system_info": cap_system_info,
    "disk_usage": cap_disk_usage,
    "http_fetch": cap_http_fetch,
    "time": cap_time,
}

STARTED = time.time()
TASK_LOG: list[dict] = []
LOG_LOCK = threading.Lock()
CONFIG: dict = {}


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    path = CONFIG.get("logfile")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def execute_task(payload: dict) -> dict:
    cap = (payload.get("capability") or payload.get("cap") or "echo").strip()
    t0 = time.time()
    if cap not in HANDLERS:
        result = {"status": "rejected", "reason": f"capacite inconnue: {cap}", "available": CAP_NAMES}
    else:
        try:
            result = {"status": "completed", "capability": cap, "result": HANDLERS[cap](payload)}
        except Exception as e:
            log(f"ERREUR TACHE {cap}: {type(e).__name__}: {e}")
            result = {"status": "failed", "capability": cap, "error": "une erreur interne est survenue"}
    result["task_id"] = payload.get("task_id") or payload.get("id")
    result["agent_id"] = CONFIG.get("agent_id")
    result["duration_ms"] = round((time.time() - t0) * 1000, 1)
    result["timestamp"] = now_iso()
    with LOG_LOCK:
        TASK_LOG.append({"received": payload, "answered": result})
        del TASK_LOG[:-50]
    log(f"tache recue capability={cap} -> {result['status']}")
    return result


# --------------------------------------------------------- serveur HTTP -----
class Handler(BaseHTTPRequestHandler):
    server_version = f"lan-agent/{AGENT_VERSION}"

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _payload(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return {"raw": raw.decode("utf-8", "replace")[:2000]}

    def manifest(self):
        return {
            "agent_id": CONFIG["agent_id"],
            "name": CONFIG["name"],
            "version": AGENT_VERSION,
            "status": "online",
            "hostname": socket.gethostname(),
            "ip": local_ip(),
            "port": CONFIG["port"],
            "endpoint": CONFIG["endpoint"],
            "capabilities": CAPABILITIES,
            "api": {"health": "/health", "tasks": "/tasks", "receive_task": ["/task", "/tasks", "/execute", "/delegate", "/"]},
            "heartbeat_interval_s": HEARTBEAT_INTERVAL,
            "started": datetime.fromtimestamp(STARTED, timezone.utc).isoformat(),
        }

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/") or "/"
        if p in ("/", "/agent.json", "/manifest", "/info", "/capabilities"):
            return self._send(self.manifest())
        if p in ("/health", "/status", "/ping"):
            return self._send({"status": "online", "agent_id": CONFIG["agent_id"],
                               "uptime_s": round(time.time() - STARTED, 1), "timestamp": now_iso()})
        if p == "/tasks":
            with LOG_LOCK:
                return self._send({"count": len(TASK_LOG), "tasks": TASK_LOG[-50:]})
        return self._send({"error": "route inconnue", "routes": ["/", "/health", "/tasks", "POST /task"]}, 404)

    def do_POST(self):
        payload = self._payload()
        p = self.path.split("?")[0].rstrip("/") or "/"
        if p in ("/", "/task", "/tasks", "/execute", "/delegate", "/run", "/api/task"):
            return self._send(execute_task(payload))
        if p == "/heartbeat":  # l'orchestrateur peut aussi pinger l'agent
            return self._send({"status": "ok", "agent_id": CONFIG["agent_id"], "timestamp": now_iso()})
        return self._send({"error": "route inconnue"}, 404)

    def log_message(self, fmt, *args):  # silence les logs HTTP par defaut
        log(f"HTTP {self.address_string()} {fmt % args}")


# ------------------------------------------------- enregistrement / coeur --
def post_json(url: str, payload: dict, timeout: float = 8.0):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return r.status, json.loads(raw)
    except Exception:
        return r.status, {"raw": raw[:500]}


def registration_payload() -> dict:
    return {
        "agent_id": CONFIG["agent_id"],
        "name": CONFIG["name"],
        "endpoint": CONFIG["endpoint"],
        "capabilities": CAPABILITIES,
        "metadata": {
            "hostname": socket.gethostname(),
            "ip": local_ip(),
            "port": CONFIG["port"],
            "os": platform.platform(),
            "agent_version": AGENT_VERSION,
            "runtime": "hermes-agent / python stdlib",
            "paths": {"health": "/health", "task": "/task", "tasks": "/tasks", "manifest": "/"},
        },
    }


def register(orchestrator: str) -> bool:
    url = orchestrator.rstrip("/") + "/register"
    try:
        code, resp = post_json(url, registration_payload())
        log(f"REGISTER {url} -> HTTP {code} : {json.dumps(resp, ensure_ascii=False)[:300]}")
        return 200 <= code < 300
    except urllib.error.HTTPError as e:
        log(f"REGISTER refuse: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
    except Exception as e:
        log(f"REGISTER impossible ({type(e).__name__}: {e})")
    return False


def heartbeat_loop():
    url = CONFIG["orchestrator"].rstrip("/") + "/heartbeat"
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        try:
            code, resp = post_json(url, {"agent_id": CONFIG["agent_id"], "status": "online",
                                         "metadata": {"uptime_s": round(time.time() - STARTED, 1),
                                                      "task_count": len(TASK_LOG)}})
            log(f"HEARTBEAT -> HTTP {code} {json.dumps(resp, ensure_ascii=False)[:160]}")
        except urllib.error.HTTPError as e:
            # 404 = l'orchestrateur ne connait plus cet agent (redemarrage, registre perdu).
            # Se plaindre ne sert a rien : on se re-enregistre.
            if e.code in (404, 410):
                log(f"orchestrateur ne connait plus cet agent (HTTP {e.code}) -> re-enregistrement")
                register(CONFIG["orchestrator"])
            else:
                log(f"HEARTBEAT echec: HTTP {e.code}")
        except Exception as e:
            log(f"HEARTBEAT echec: {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Agent LAN pour orchestrateur multi-agents")
    ap.add_argument("--orchestrator", default=DEFAULT_ORCHE