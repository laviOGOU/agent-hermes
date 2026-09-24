# Identifier et qualifier un appareil du LAN

## TTL (via `ping -n 1 <ip>`)
- 128 → Windows
- 64 → Linux, Android, iOS/macOS, équipements embarqués (box, TV, imprimante réseau)
- 255 → équipement réseau (switch/routeur géré)

Le TTL est le signal le moins cher qui reste quand l'hôte n'expose aucun port : un hôte à TTL 128 sans port ouvert est un **PC Windows au pare-feu strict**, pas un mystère.

## Ports → type d'appareil (les discriminants)
- `62078` (+ `49152`) → **iPhone/iPad** (lockdownd Apple)
- `7000` / `5000` → **AirPlay** : `GET http://<ip>:7000/info` (puis 5000, 49152) renvoie un plist binaire avec `name`, `model` (`MacBookAir10,1`, `AppleTV6,2`…), `deviceID`, `macAddress`, `osVersion`. Identification la plus précise disponible sans authentification.
- `8008` + `8009` (+ `8443`) → **Google Cast / Chromecast** : Smart TV, Android TV, enceintes. `SERVER: Chromecast/1.6.18`
- `16642` → rendu **DLNA MediaRenderer** (TV)
- `52869` / `1900` + `SERVER: UPnP/1.0, Portable SDK for UPnP devices` → **box/routeur** (UPnP IGD)
- `135/139/445` → pile Windows (SMB/RPC) ⇒ PC Windows
- `7680` → Delivery Optimization ⇒ **PC Windows** (souvent le seul port visible quand le pare-feu filtre le reste)
- `5900` → VNC (bannière `RFB 005.000`) ; `3389` → RDP
- `17500` → Dropbox en synchro LAN ⇒ poste de travail d'un utilisateur actif
- `631`/`515`/`9100` → imprimante ; `32400` → Plex ; `7547` → TR-069 (équipement opérateur)
- Un `8000`/`8080` qui répond `{"detail":"Not Found"}` = **FastAPI** : lire `/openapi.json` (titre + version) et `/docs` pour identifier l'application et son état (`/health` renvoie souvent id + compteurs).

## MAC
- Constructeur via `https://api.maclookup.app/v2/macs/<6 premiers hex>` (champ JSON `company`), ~1 appel/seconde.
- **Adresse aléatoire** (bit localement administré : 2ᵉ chiffre hexadécimal ∈ {2,6,A,E}) ⇒ Wi-Fi privé iOS/Android/macOS. Ne pas chercher de constructeur, écrire « adresse MAC aléatoire → appareil non identifiable ».
- Une même MAC sur deux IP = même machine (double bail DHCP) ou répéteur : le dire au lieu de compter deux appareils.

## UPnP/SSDP
- Le M-SEARCH **doit** être lié à l'interface LAN (`IP_MULTICAST_IF` + `bind((ip_locale, 0))`) — sinon 0 réponse. Relire le socket ~8 s.
- Chaque réponse porte `SERVER:` (indice de type) et `LOCATION:` (URL du XML descripteur).
- Dans le XML : `friendlyName` (souvent le nom donné par l'utilisateur, ex. « Téléviseur »), `modelName`, `manufacturer`. Un même appareil annonce plusieurs descripteurs (MediaRenderer, AVTransport, IGD) : dédoublonner par IP.

## Comptage et restitution
- Les mobiles se déconnectent et se reconnectent : un hôte présent dans un relevé ARP peut disparaître du suivant. Donner le compte comme un instantané et citer ceux vus puis partis.
- Ne pas inclure les adaptateurs virtuels de la machine auditée (VMware VMnet1/VMnet8, Hyper-V, VPN) : ils ne font pas partie « du réseau ».
- Vérifier le compte annoncé par énumération programmatique du fichier JSON, jamais de mémoire.
