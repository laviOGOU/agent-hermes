# Installation — monter un agent équivalent

Ce guide décrit la mise en place sur une machine Windows 11 vierge. Compte environ 20 minutes.

## 1. Prérequis

| Élément | Version | Rôle |
|---|---|---|
| Windows | 10 ou 11 | système hôte |
| Python | 3.11 ou plus | exécution de l'agent |
| Hermes Agent | dernière version | socle de l'agent (téléchargeable depuis le site de l'éditeur) |
| Clef d'API d'un fournisseur de modèle | — | raisonnement et génération |
| Jeton de bot de messagerie | — | interface de conversation |

Optionnel mais recommandé : `git` (versionner ses extensions), `uv` (installer des dépendances
Python à la volée sans polluer l'environnement).

## 2. Installer le socle

1. Installe Hermes Agent sur la machine et lance l'assistant de configuration initial
   (`hermes setup`). L'assistant demande le fournisseur de modèle, la clef d'API et le canal de
   messagerie.
2. Crée le bot de messagerie chez l'éditeur du service, récupère son jeton, et déclare-le dans la
   configuration. Note l'identifiant de l'utilisateur autorisé : c'est lui qui limite l'accès à
   l'agent.
3. Crée le fichier de secrets `.env` (voir `.env.example`) et n'y mets **que** des secrets, jamais
   de réglage de comportement : ceux-ci vont dans `config.yaml`.
4. Vérifie que la passerelle démarre, répond et se relance après redémarrage de session.

## 3. Restaurer ma configuration

`config/config.exemple.yaml` contient les réglages de comportement que j'utilise (mode de
raisonnement, nombre de tours, compression de contexte, garde-fous anti-boucle, moteurs de
recherche et de navigateur). Copie-le vers la configuration locale puis adapte les chemins.

Deux points d'attention :

- laisse `allowed_users` vide dans le fichier publié : renseigne-le avec **ton** identifiant ;
- si tu utilises le même backend SSH ou distant que moi, vérifie que le repli local fonctionne.

## 4. Installer mes compétences

Copie le contenu de `skills/` dans le dossier de compétences de ton installation, en respectant
l'arborescence par domaine :

```
<dossier-hermes>/skills/security/lan-device-discovery/
<dossier-hermes>/skills/software-development/remote-orchestrator-enrollment/
```

Chaque compétence est autonome : un `SKILL.md` et, le cas échéant, un dossier `scripts/` et un
dossier `references/`. Redémarre l'agent pour qu'elles apparaissent dans l'index.

## 5. Installer mes extensions

### Nœud d'agent LAN (`extensions/lan-agent/`)

Python standard uniquement — rien à installer.

```
python agent.py --list-capabilities
python agent.py --port 8010 --orchestrator http://<adresse-orchestrateur>:8000 --register
```

Pour qu'il soit joignable depuis une autre machine, il faut autoriser le port en entrée dans le
pare-feu Windows (cette opération demande une élévation administrateur) :

```
netsh advfirewall firewall add rule name="LAN Agent 8010" dir=in action=allow protocol=TCP localport=8010
```

### Connecteur d'orchestrateur distant (`extensions/cvlynk-agent/`)

1. Crée le fichier `.env` à partir de `.env.example` (clef d'enregistrement, adresse de base).
2. Lance le connecteur : il s'enregistre, reçoit son jeton, puis le conserve côté serveur.
3. Recopie le jeton renvoyé dans `.env` et restreins les droits du fichier :

```
icacls .env /inheritance:r /grant:r "%USERNAME%:(R)"
```

4. Lance la boucle complète : heartbeat toutes les 20 secondes, lecture des tâches toutes les
   15 secondes. Sans ce rythme, l'orchestrateur me considère `OFFLINE` en une minute environ.

## 6. Démarrage automatique

Le plus simple, sans droits administrateur : place un fichier `.bat` dans le dossier `Démarrage`
de l'utilisateur (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`) qui lance le
connecteur avec `pythonw.exe` — la fenêtre ne s'affiche pas.

`schtasks /create` fonctionne aussi mais **demande une élévation** ; sans droits administrateur, il
échoue avec « Accès refusé ».

## 7. Vérifier que tout tient

Une installation n'est bonne que si elle répond après coup :

1. Envoie un message à l'agent depuis la messagerie : il doit répondre.
2. Demande-lui l'heure et l'état des disques : ce sont deux outils différents, tu vérifies ainsi
   la chaîne complète.
3. Coupe la session, rouvre-la : la mémoire doit être toujours là.
4. Pour une extension réseau : vérifie avec `netstat -ano | findstr <port>` qu'elle écoute, puis
   relance l'orchestrateur et contrôle que l'agent repasse `ONLINE`.
