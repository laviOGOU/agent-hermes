#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Inventaire LAN sans nmap (Windows/MSYS, bibliotheque standard uniquement).

Usage:
  python lan_discover.py                     # ping sweep du /24 local + ARP + ports + TTL
  python lan_discover.py 192.168.1.10 1.20   # hotes precis (numero seul = /24 courant)
  python lan_discover.py --ssdp              # + noms d'appareils UPnP/SSDP (TV, box)
  python lan_discover.py --airplay           # + nom/modele exact des appareils Apple
  python lan_discover.py --oui               # + constructeur depuis la MAC (API maclookup.app)

Sortie : JSON (une entree par hote) sur stdout + fichier lan_inventory.json
(chemin surchargeable via LAN_INVENTORY_OUT).
"""
import concurrent.futures as cf
import json
import os
import plistlib
import re
import socket
import subprocess
import sys
import time
import urllib.request

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP",
    88: "Kerberos", 135: "RPC", 139: "NetBIOS", 443: "HTTPS", 445: "SMB",
    515: "LPD (imprimante)", 548: "AFP (Mac)", 554: "RTSP (camera)",
    631: "IPP (imprimante)", 1883: "MQTT", 2049: "NFS", 3000: "dev",
    3306: "MySQL", 3389: "RDP", 5000: "AirPlay/UPnP", 5060: "SIP",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 7000: "AirPlay",
    7547: "TR-069 (box)", 7680: "DeliveryOptimization (Windows)", 8000: "HTTP alt",
    8008: "GoogleCast", 8009: "Chromecast", 8080: "HTTP alt", 8443: "HTTPS alt",
    8888: "HTTP alt", 9100: "JetDirect (imprimante)", 16642: "DLNA MediaRenderer",
    17500: "Dropbox LAN sync", 32400: "Plex", 49152: "UPnP/Apple",
    52869: "UPnP IGD (box)", 62078: "lockdownd (iPhone/iPad)",
}
PORTS = sorted(COMMON_PORTS)


def sh(cmd, timeout=180):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           errors="replace", timeout=timeout)
        return r.stdout or ""
    except Exception:
        return ""


def local_ipv4():
    """IP de l'interface qui porte le trafic Internet (= IP du LAN)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def ping(ip, wait_ms=400):
    """(vivant, ttl) — le TTL discrimine Windows (128) vs Linux/Android/Apple (64)."""
    out = sh(f"ping -n 1 -w {wait_ms} {ip}", timeout=15)
    m = re.search(r"TTL=(\d+)", out, re.I)
    if m:
        return True, int(m.group(1))
    return False, None


def os_guess(ttl):
    if ttl is None:
        return ""
    if ttl > 200:
        return "equipement reseau"
    if ttl > 100:
        return "Windows"
    return "Linux/Android/Apple/embarque"


def sweep(prefix):
    hosts = [f"{prefix}.{i}" for i in range(1, 255)]
    with cf.ThreadPoolExecutor(max_workers=80) as ex:
        return {ip: ttl for ip, (up, ttl) in zip(hosts, ex.map(lambda h: ping(h), hosts)) if up}


def read_arp(prefix):
    """MAC par IP, en ignorant broadcast/multicast/entrees statiques."""
    out = sh("arp -a", timeout=30)
    macs = {}
    for line in out.splitlines():
        m = re.match(r"\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})\s+(\S+)", line)
        if not m:
            continue
        ip, mac, kind = m.group(1), m.group(2).lower(), m.group(3).lower()
        if not ip.startswith(prefix + "."):
            continue
        if ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239."):
            continue
        if mac == "ff-ff-ff-ff-ff-ff" or kind.startswith("statique"):
            continue
        macs[ip] = mac
    return macs


def is_random_mac(mac):
    """Bit 'localement administre' : adresse Wi-Fi privee (pas de constructeur a chercher)."""
    try:
        return int(mac.split("-")[0], 16) & 0x02 == 0x02
    except Exception:
        return True


def probe(ip, port, timeout=0.7):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((ip, port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def banner(ip, port, timeout=1.2):
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
        data = s.recv(300).decode("utf-8", "replace")
        s.close()
        first = data.splitlines()[0].strip() if data else ""
        m = re.search(r"<title>(.*?)</title>", data, re.S | re.I)
        return (m.group(1).strip() if m else first)[:120]
    except Exception:
        return ""


def scan_ports(ip, ports=PORTS, workers=48):
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for p in ex.map(lambda p: p if probe(ip, p) else None, ports):
            if p:
                out.append({"port": p, "service": COMMON_PORTS.get(p, "?"), "banner": banner(ip, p)})
    return out


def reverse_dns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def ssdp(ip_local, seconds=8):
    """Noms d'appareils via UPnP/SSDP. DOIT etre lie a l'interface LAN sinon 0 reponse."""
    req = "\r\n".join(["M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
                       'MAN: "ssdp:discover"', "MX: 3", "ST: ssdp:all", "", ""]).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip_local))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    s.bind((ip_local, 0))
    s.settimeout(2)
    for _ in range(3):
        s.sendto(req, ("239.255.255.250", 1900))
        time.sleep(0.4)
    found = {}
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            data, addr = s.recvfrom(65535)
        except socket.timeout:
            continue
        txt = data.decode("utf-8", "replace")
        e = found.setdefault(addr[0], {"ip": addr[0], "server": "", "urls": []})
        m = re.search(r"SERVER:\s*(.+)", txt, re.I)
        if m and not e["server"]:
            e["server"] = m.group(1).strip()[:100]
        m = re.search(r"LOCATION:\s*(\S+)", txt, re.I)
        if m and m.group(1) not in e["urls"]:
            e["urls"].append(m.group(1))
    s.close()
    for e in found.values():
        e["details"] = [upnp_names(u) for u in e["urls"][:3]]
    return found


def upnp_names(url):
    try:
        xml = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "inv"}),
                                     timeout=3).read().decode("utf-8", "replace")
    except Exception as ex:
        return {"error": "impossible d'obtenir les details"}
    out = {}
    for tag in ("friendlyName", "modelName", "manufacturer", "deviceType"):
        m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), xml, re.S | re.I)
        if m:
            out[tag] = m.group(1).strip()[:90]
    return out


def airplay_info(ip):
    """Appareils Apple : /info renvoie un plist avec name + model exact."""
    for port in (7000, 5000, 49152):
        try:
            raw = urllib.request.urlopen(f"http://{ip}:{port}/info", timeout=4).read()
            d = plistlib.loads(raw)
            keep = {k: d[k] for k in ("name", "model", "deviceID", "macAddress", "osVersion",
                                      "sourceVersion", "protocolVersion") if k in d}
            return {"port": port, "info": keep}
        except Exception:
            continue
    return None


def oui(mac):
    if is_random_mac(mac):
        return ""
    prefix = mac.replace("-", "").upper()[:6]
    try:
        raw = urllib.request.urlopen(f"https://api.maclookup.app/v2/macs/{prefix}", timeout=8).read()
        d = json.loads(raw.decode("utf-8", "replace"))
        return d.get("company") or ""
    except Exception:
        return ""
    finally:
        time.sleep(1)  # respecter le debit de l'API gratuite


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    ip_local = local_ipv4()
    prefix = ".".join(ip_local.split(".")[:3])

    if args:
        hosts = [a if a.count(".") == 3 else f"{prefix}.{a}" for a in args]
    else:
        print(f"# ping sweep {prefix}.0/24 …", file=sys.stderr)
        hosts = list(sweep(prefix))

    macs = read_arp(prefix)
    macs.setdefault(ip_local, "")

    results = []
    for ip in sorted(set(hosts) | set(macs), key=lambda x: int(x.split(".")[-1])):
        up, ttl = ping(ip)
        if not up and ip not in macs:
            continue
        entry = {
            "ip": ip, "self": ip == ip_local, "reverse_dns": reverse_dns(ip),
            "mac": macs.get(ip, ""),
            "mac_random": is_random_mac(macs[ip]) if macs.get(ip) else None,
            "ttl": ttl, "os_guess": os_guess(ttl), "ports": scan_ports(ip),
        }
        if "--oui" in flags and entry["mac"]:
            entry["vendor"] = oui(entry["mac"])
        if "--airplay" in flags:
            entry["airplay"] = airplay_info(ip)
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)

    if "--ssdp" in flags:
        for e in ssdp(ip_local).values():
            print(json.dumps(e, ensure_ascii=False), flush=True)

    out = os.environ.get("LAN_INVENTORY_OUT", "lan_inventory.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"# {len(results)} hotes -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
