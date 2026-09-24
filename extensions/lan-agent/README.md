# Nœud d'agent LAN

Petit agent HTTP qui rejoint un orchestrateur multi-agents sur un réseau local et expose une liste
blanche de capacités. C'est l'extension qui a servi à rattacher un poste de travail à un
orchestrateur hébergé sur le réseau, et à faire exécuter par ce poste des tâches que
l'orchestrateur lui délègue.

Python standard uniquement : **aucune dépendance à installer**.

## Ce qu'il fait

| Capacité | Rôle |
|---|---|
| `echo` | renvoie le texte reçu (test de liaison) |
| `system_info` | OS, nom de machine, CPU, mémoire, IP locale, uptime |
| `disk_usage` | espace disque par volume |
| `http_fetch` | récupération d'une URL (code HTTP + début du corps) |
| `time` | heure locale et UTC, fuseau |

Pas de shell distant : la liste des capacités est une liste blanche (`HANDLERS` dans `agent.py`).
Ajouter une capacité, c'est écrire une fonction `cap_xxx(payload) -> dict` et l'inscrire dans
`CAPABILITIES` et `HANDLERS`.

## Démarrage

```
python agent.py --list-capabilities
python agent.py --port 8010 --orchestrator http://[ADRESSE_ORCHESTRATEUR]:8000 --register
```

L'agent s'enregistre auprès de l'orchestrateur, puis lui envoie un heartbeat périodique. Pour
qu'il soit joignable depuis une autre machine, il faut autoriser le port en entrée dans le
pare-feu (élévation administrateur requise) :

```
netsh advfirewall firewall add rule name="LAN Agent 8010" dir=in action=allow protocol=TCP localport=8010
```

Un fichier `start_agent.bat` permet un lancement manuel ; une copie placée dans le dossier
`Démarrage` de Windows assure le lancement à l'ouverture de session, sans droits administrateur.

## API exposée par l'agent

| Route | Méthode | Effet |
|---|---|---|
| `/`, `/agent.json` | GET | manifeste (identité, endpoint, capacités) |
| `/health` | GET | état de l'agent |
| `/tasks` | GET | 50 dernières tâches traitées |
| `/task` (aussi `/tasks`, `/execute`, `/delegate`) | POST | exécute une tâche `{"capability": "...", ...}` |

## Options

```
--orchestrator URL    adresse de l'orchestrateur (défaut : http://127.0.0.1:8000)
--port N              port d'écoute (défaut : 8010)
--bind ADRESSE        interface d'écoute (défaut : 0.0.0.0)
--host ADRESSE        IP annoncée à l'orchestrateur
--register            s'enregistrer au démarrage
--no-heartbeat        ne pas envoyer de heartbeat
```

## Sécurité

- L'agent écoute par défaut sur `0.0.0.0` : toute machine du réseau peut l'appeler. Pour le
  limiter, écoute sur l'IP locale seulement (`--bind`) ou restreins la règle de pare-feu à
  l'adresse de l'orchestrateur.
- Aucune capacité n'exécute de commande arbitraire, par conception.
- Les tâches reçues sont journalisées dans `agent.log`, avec l'appelant.
