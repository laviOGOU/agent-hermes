---
name: lan-device-discovery
description: "Use when inventorying LAN devices, ports, or local IPs."
version: 1.0.0
---

# Inventaire du réseau local et posture réseau de la machine

## Déclencheurs
- « combien de machines sont connectées à mon réseau ? », « donne leurs caractéristiques »
- inventaire / audit d'exposition d'un LAN domestique (quels services sont visibles par tout le réseau)
- « tu es connecté à quel port ? », « donne l'adresse IP de ma machine »

## Règles toujours actives
1. **Périmètre** : ne scanner que le réseau local de la machine de l'utilisateur (sa propre box). Si la cible n'est pas ce réseau, demander une autorisation explicite AVANT de lancer quoi que ce soit.
2. **Lecture seule uniquement** : ping, `connect()` sur des ports TCP, requêtes UPnP/DNS, fetch d'un endpoint d'identification. Jamais de scripts `vuln`/`exploit`/`brute` d'nmap sur un réseau domestique, jamais de modification de configuration.
3. **Compte rendu en français, en puces** (pas de tableaux sur Telegram), une ligne par appareil : `IP — nom/type identifié — preuves (MAC, ports, TTL)`. Ouvrir par le compte (« N machines actives en plus de la tienne »), pas par la méthode.
4. **Honnêteté sur les limites** : annoncer que la découverte repose sur ping + cache ARP, donc un appareil en veille profonde ou en isolation AP peut manquer, et que le compte est un instantané. Ne jamais présenter le nombre comme exhaustif.
5. **Pas d'hypothèse déguisée en fait** : MAC aléatoire + aucun port ouvert ⇒ « appareil mobile indéterminé », pas « le téléphone de X ». Écrire « adresse MAC aléatoire (adresse Wi-Fi privée) » et dire pourquoi c'est non identifiable.
6. **Services exposés** : qualifier (« exposé à tout le LAN », « sans authentification apparente ») et signaler le risque en une phrase ; ne pas affirmer « pas d'auth » sans l'avoir constaté.
7. **Finir par une offre d'action concrète** : rapport .docx, outil réutilisable rangé dans `D:\PYTHON\<projet>`, ou surveillance cron qui alerte à l'arrivée d'un nouvel appareil.

## Procédure

1. **Déterminer le réseau** : IP locale = socket UDP `connect(("8.8.8.8", 80))` puis `getsockname()` ; à défaut `ipconfig | grep -i IPv4`. Le /24 est le périmètre.
2. **Balayer en ping d'abord, lire ARP ensuite** — sans balayage préalable le cache ARP ne contient que les voisins récents :
   ```bash
   seq 1 254 | xargs -P 80 -I{} sh -c 'ping -n 1 -w 400 192.168.1.{} >/dev/null 2>&1'
   arp -a
   ```
   Parser en Python, pas à l'œil : filtrer `.255`, `224.x`/`239.x`, `255.255.255.255` et les cartes virtuelles locales.
3. **Résoudre les noms / identifier les appareils** (tables dans `references/identifying-devices.md`) : reverse DNS (`socket.gethostbyaddr`), puis UPnP/SSDP (noms commerciaux des TV et box), puis AirPlay `/info` (nom + modèle exact des appareils Apple), puis bannière HTTP des ports ouverts.
4. **Scanner les ports** : `scripts/lan_discover.py` (pool de threads, timeout 0,6–0,8 s, ~150 ports ; un LAN de 16 hôtes se termine en moins d'une minute). N'élargir qu'aux hôtes encore non identifiés après l'étape 3.
5. **Fingerprint TTL** par ping (`ping -n 1 <ip>` → `TTL=`): 128 Windows, 64 Linux/Android/embarqué/Apple, 255 équipement réseau. Gratuit et discriminant quand aucun port n'est ouvert.
6. **Rédiger le rapport** selon les règles ci-dessus : compte total, ligne par appareil, section « ce que ça dit concrètement » (répartition PC/TV/mobiles + points d'attention sécurité), puis « limites de la méthode ».
7. **Vérifier le compte avant d'annoncer** : énumérer les entrées retenues en Python et comparer au nombre écrit dans la réponse. Mentionner les appareils vus dans un relevé puis disparus dans le suivant (un LAN domestique bouge en quelques minutes).

## Pitfalls

- **`nbtstat -A <ip>` interroge le premier adaptateur de la liste et échoue sur les autres** (cartes VMware) → ne pas en dépendre pour les noms NetBIOS ; passer par reverse DNS, UPnP/SSDP, AirPlay `/info` ou la bannière HTTP.
- **`net view \\<ip>` renvoie « erreur système 1702 » quand RPC n'est pas joignable** : ne pas l'utiliser comme méthode d'identification.
- **SSDP renvoie 0 hôte si le socket n'est pas lié à l'interface LAN** : poser `IP_MULTICAST_IF` sur l'IP locale **et** `bind((ip_locale, 0))` avant le M-SEARCH, puis relire 8 s.
- **Deux IP partageant une MAC = la même machine** (double bail) ou un répéteur : le signaler, ne pas la compter comme deux appareils distincts.
- **Ne pas compter les cartes virtuelles** (VMware host-only/NAT, Hyper-V, VPN) comme des machines du réseau : `192.168.163.1`, `192.168.116.1` etc. sont locales à la machine auditée.
- **Bit « localement administré »** : 2ᵉ chiffre hexadécimal de la MAC ∈ {2,6,A,E} ⇒ adresse aléatoire (iOS/Android/macOS « adresse Wi-Fi privée ») — chercher un constructeur n'a aucun sens, dire « indéterminé ».
- **Sorties de commandes Windows illisibles pour grep** : `tasklist`/`wmic` déclenchent « Binary file matches » → toujours `grep -a`.
- **`tasklist /FI "PID eq N"` peut revenir vide sous MSYS** : filtrer `tasklist /FO CSV /NH | grep -a` ou le faire en Python.
- **Lignes de commande des processus** : `wmic process get ...` peut revenir vide ; utiliser `powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"ProcessId=x or ProcessId=y\" | Select ProcessId,CommandLine | Format-List"`.
- **Ne pas boucler sur une identification incertaine** : après 2–3 sondes, écrire « indéterminé » avec la preuve disponible plutôt que d'enchaîner les techniques.

## Posture réseau de la machine (« sur quel port / mon IP »)

- Distinguer **entrant** et **sortant** : Hermes n'écoute rien depuis Internet. Il tient des connexions **sortantes TCP 443** (serveurs Telegram, API/CDN) et éventuellement un port local interne. Le dire explicitement, puis donner les preuves :
  ```bash
  netstat -ano | grep -a -E " (PID)$"        # LISTENING + ESTABLISHED du processus
  ```
- **PID → processus** : `tasklist /FO CSV /NH | grep -a` et la ligne de commande via `Get-CimInstance Win32_Process` ; le gateway Hermes se repère à `hermes_cli.main gateway run`.
- **IP locale** : `ipconfig | grep -i -E "IPv4|Carte"` (libellés français « Adresse IPv4 » / « Carte ») — annoncer la carte Ethernet comme LA bonne adresse, les autres étant virtuelles.
- **IP publique** : `curl -s --max-time 8 https://api.ipify.org` (v4) et `https://ifconfig.co/json` (pays, région, ASN) — utile comme contrôle de cohérence.
- Si un service local (dashboard Flask, API de dev) n'apparaît pas dans `netstat | grep LISTENING`, dire qu'il **n'est pas démarré** au lieu de supposer son état.

## Fichiers d'appui
- `scripts/lan_discover.py` — balayage ping, ARP, ports, TTL, reverse DNS, SSDP, AirPlay `/info`, lookup OUI ; sortie JSON. Options `--ssdp`, `--airplay`, `--oui` pour les modules coûteux.
- `references/identifying-devices.md` — tables TTL / port→type d'appareil / constructeurs, champs utiles d'AirPlay `/info`, tags des XML UPnP.
