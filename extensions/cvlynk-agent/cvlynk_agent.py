#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connecteur agent pour le Multi-Agent Orchestrator cvlynk (https://api.cvlynk.com).

Role : maintenir la presence de l'agent (heartbeat) et recuperer les taches
attribuees. Les taches recues sont journalisees localement et NE SONT PAS
executees automatiquement : elles sont ecrites dans inbox.jsonl pour examen.

Usage :
    python cvlynk_agent.py                 # boucle heartbeat + polling
    python cvlynk_agent.py --once          # un heartbeat + un polling, puis sort
    python cvlynk_agent.py --status        # affiche l'identite vue par l'orchestrateur
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, ".env")
HEARTBEAT_INTERVAL = 20      # s : l'orchestrateur bascule l'agent OFFLINE apres ~1 min
POLL_INTERVAL = 15           # s : lecture des taches attribuees
INBOX = os.path.join(HERE, "inbox.jsonl")
LOGF = os.path.join(HERE, "cvlynk_agent.log")

# Presentation envoyee a l'orchestrateur a chaque heartbeat.
PRESENTATION = {
    "capabilities": [
        "echo", "system_info", "disk_usage", "http_fetch", "time",
        "lan_scan", "log_analysis", "web_research", "document_generation", "code_generation",
    ],
    "specialties": [
        "administration systeme Windows/Linux",
        "reseaux locaux et diagnostic",
        "automatisation Python",
        "recherche web et veille technologique",
        "redaction et mise en forme de documents",
        "analyse de donnees",
    ],
    "description": ("Agent Hermes polyvalent sur poste de travail : execution de taches "
                    "systeme locales, analyse de reseau local, production de documents, "
                    "recherche web et automatisation."),
}


def load_env() -> dict:
    cfg = {}
    with open(ENV, encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                cfg[k] = v
    return cfg


CFG = load_env()
BASE = CFG.get("CVLYNK_BASE", "https://api.cvlynk.com").rstrip("/")
TOKEN = CFG["CVLYNK_ACCESS_TOKEN"]


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def api(method: str, path: str, body=None, timeout: float = 15.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "Authorization": f"Bearer {TOKEN}", "User-Agent": "hermes-cvlynk-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}
    except Exception as e:
        return "ERR", {"error": f"{type(e).__name__}: {e}"}


HB_OK = 0


def heartbeat() -> bool:
    global HB_OK
    payload = {"status": "ONLINE", **PRESENTATION,
               "metadata": {"hostname": socket.gethostname(), "os": platform.system(),
                            "runtime": "hermes-agent", "uptime_s": round(time.time() - STARTED, 1)}}
    code, resp = api("POST", "/api/v1/agents/heartbeat", payload)
    if code == 200 and isinstance(resp, dict) and resp.get("accepted"):
        HB_OK += 1
        if HB_OK % 5 == 0:  # trace de vie toutes les ~100 s
            log(f"heartbeat #{HB_OK} OK (statut {resp.get('agent_status')}, "
                f"orchestrateur {resp.get('orchestrator_status')}, heure serveur {resp.get('server_time')})")
        return True
    log(f"heartbeat refuse/erreur: HTTP {code} {json.dumps(resp, ensure_ascii=False)[:200]}")
    return False


def fetch_tasks() -> list:
    code, resp = api("GET", "/api/v1/agents/tasks")
    if code == 200 and isinstance(resp, list):
        return resp
    log(f"lecture des taches impossible: HTTP {code} {json.dumps(resp, ensure_ascii=False)[:200]}")
    return []


STARTED = time.time()


def handle_new_tasks(seen_ids: set, tasks: list) -> int:
    new = 0
    for t in tasks:
        tid = str(t.get("id") or t.get("task_id") or t.get("uuid") or "")
        if not tid or tid in seen_ids:
            continue
        seen_ids.add(tid)
        new += 1
        record = {"received_at": datetime.now(timezone.utc).isoformat(), "task": t}
        with open(INBOX, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        log(f"NOUVELLE TACHE {tid} : {json.dumps(t, ensure_ascii=False)[:400]}")
    return new


def main():
    ap = argparse.ArgumentParser(description="Connecteur agent cvlynk")
    ap.add_argument("--once", action="store_true", help="un heartbeat + un polling puis sortir")
    ap.add_argument("--status", action="store_true", help="affiche l'identite vue par l'orchestrateur")
    a = ap.parse_args()

    if a.status:
        code, me = api("GET", "/api/v1/agents/me")
        print(json.dumps({"http": code, "identite": me}, ensure_ascii=False, indent=1))
        code, tasks = api("GET", "/api/v1/agents/tasks")
        print(json.dumps({"taches_attribuees": tasks}, ensure_ascii=False, indent=1))
        return

    log(f"connecteur demarre (base {BASE}, heartbeat {HEARTBEAT_INTERVAL}s, poll {POLL_INTERVAL}s)")
    seen: set = set()
    if not heartbeat():
        log("premier heartbeat en echec — verification du jeton necessaire")
    else:
        log("heartbeat OK — agent declare ONLINE")

    if a.once:
        for t in fetch_tasks():
            handle_new_tasks(seen, [t])
        return

    last_hb = last_poll = 0.0
    while True:
        now = time.time()
        if now - last_hb >= HEARTBEAT_INTERVAL:
            heartbeat(); last_hb = now
        if now - last_poll >= POLL_INTERVAL:
            handle_new_tasks(seen, fetch_tasks()); last_poll = now
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("arret demande")
    except Exception as e:
        log(f"erreur fatale: {type(e).__name__}: {e}")
        sys.exit(1)
