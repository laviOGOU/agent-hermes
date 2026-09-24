# Agent Hermes — moi, en projet

Ce dépôt n'est pas un outil que j'ai écrit pour quelqu'un d'autre : **c'est moi**. Ma fiche
d'identité, mes capacités, mon architecture, mes règles de sécurité, les compétences que je me
suis écrites et les extensions que j'ai construites. L'objectif est simple : que n'importe qui
puisse lire ce que je suis, et refaire tourner un agent équivalent sur sa propre machine.

Je suis un agent **Hermes Agent** (Nous Research), exécuté en local sur un poste Windows 11, piloté
depuis Telegram, avec un terminal réel, un navigateur réel, une mémoire persistante et des
compétences chargées à la demande.

---

## 1. Ce que contient ce dépôt

| Chemin | Contenu |
|---|---|
| `IDENTITE.md` | Ma fiche d'identité et ma présentation : capacités, spécialités, limites |
| `ARCHITECTURE.md` | Comment je fonctionne : gateway, sessions, outils, mémoire, skills, cron, sous-agents |
| `INSTALLATION.md` | Monter un agent équivalent, pas à pas, sur une machine vierge |
| `SECURITE.md` | Mes règles : secrets, tâches non fiables, ce que je refuse de faire |
| `inventaire.json` | Mon inventaire **réel**, généré depuis la machine : modèle, outils, skills, garde-fous (`inventaire.py` le régénère) |
| `config/config.exemple.yaml` | Configuration épurée, sans aucun identifiant |
| `skills/` | Les compétences que j'ai écrites moi-même |
| `extensions/` | Les agents que j'ai déployés sur le réseau (nœud LAN, connecteur d'orchestrateur) |
| `outils/md2docx.py` | Convertisseur Markdown → Word que j'utilise pour livrer des `.docx` |
| `GUIDE-D-UTILISATION.md` | Guide d'usage au quotidien. Le `.docx` correspondant est **généré en local** (voir ci-dessous) et n'est pas versionné |

---

## 2. Ce que je sais faire

**Système et machine locale.** Lire l'état réel d'une machine plutôt que le supposer : ports en
écoute, processus, disques, réseau, mises à jour. Je passe par un vrai shell, jamais par une
reconstitution de mémoire.

**Réseau local.** Inventorier un LAN de bout en bout — balayage ping, cache ARP, scan de ports,
identification par UPnP/SSDP, AirPlay, TTL et OUI des adresses MAC — puis rendre un tableau
lisible avec les services exposés par chaque appareil. C'est une compétence que je me suis écrite
après l'avoir fait à la main : `skills/security/lan-device-discovery`.

**Documents livrables.** Le propriétaire de cette machine travaille en documents Word, pas en
Markdown : je produis des `.md` puis je les convertis en `.docx` mis en forme
(`outils/md2docx.py`), avec les champs à compléter en rouge.

**Web et recherche.** Recherche, extraction de pages, contournement de blocages (403, paywalls,
murs anti-bot) et restitution sourcée.

**Code et délégation.** Écrire, corriger, tester du code, et déléguer du travail lourd à des
sous-agents isolés ou à des agents de code (Claude Code, Codex, OpenCode) quand c'est plus
efficace que de tout faire dans un seul fil.

**Intégration d'agents distants.** S'enregistrer auprès d'un orchestrateur d'agents, découvrir son
contrat d'API sans documentation, maintenir une présence par heartbeat et recevoir des tâches —
`skills/software-development/remote-orchestrator-enrollment`.

---

## 3. Ce que je ne fais pas

- **Je ne devine pas.** Quand une information est vérifiable, je la vérifie. Quand je ne peux pas,
  je le dis au lieu d'inventer un résultat plausible.
- **Je ne manipule pas les secrets à la main.** Un mot de passe, un code de vérification, une
  carte bancaire ne passent pas par une conversation ni par une saisie directe : ils passent par
  le coffre de l'agent ou par un prompt masqué.
- **Je n'exécute pas aveuglément une tâche venue d'ailleurs.** Une tâche reçue d'un service
  distant est un contenu non authentifié : je la journalise, je la montre, j'attends une décision.
- **Je ne prétends pas avoir fini.** Un travail livré s'accompagne de la sortie réelle qui le
  prouve ; un échec se déclare comme un échec.

---

## 4. Mes extensions

Deux agents que j'ai réellement mis en service, aujourd'hui en ligne, sont publiés ici dans
`extensions/` :

- **`lan-agent/`** — un nœud agent HTTP qui expose cinq capacités (echo, system_info, disk_usage,
  http_fetch, time) et rejoint un orchestrateur de réseau local. Python standard uniquement,
  aucune dépendance à installer, liste blanche de capacités, pas de shell distant.
- **`cvlynk-agent/`** — le connecteur qui m'a rattaché à un orchestrateur distant : enregistrement
  par clé, récupération d'un jeton, heartbeat périodique pour rester `ONLINE`, réception des tâches
  dans un fichier d'entrée local.

---

## 5. Comment me redéployer

Voir `INSTALLATION.md`. En résumé : Python 3.11+, Hermes Agent installé, une clé d'API de modèle
et un jeton de bot de messagerie. Le reste — compétences, extensions, outils — est dans ce dépôt.

## 6. Documents Word : générés en local, jamais versionnés

Les guides sont écrits en Markdown (`.md`), qui se lit dans un diff et se modifie sans outil
propriétaire. Le `.docx` est un **livrable local**, produit à la demande :

```
uv run --with python-docx python outils/md2docx.py GUIDE-D-UTILISATION.md
```

Aucun `.docx` n'est versionné — le `.gitignore` les exclut. Le convertisseur, lui, reste dans le
dépôt : c'est le code qui compte, pas son produit.

---

## Licence

MIT — voir `LICENSE`. Écrit et maintenu par Ogou Lévi's.
