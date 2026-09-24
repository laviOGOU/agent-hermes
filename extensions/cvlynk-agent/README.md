# Connecteur d'orchestrateur d'agents

Extension qui rattache une machine à un orchestrateur d'agents **distant** : enregistrement par
clé, réception d'un jeton, maintien de la présence par heartbeat, et récupération des tâches
attribuées.

Écrite en Python standard, sans dépendance. Sa particularité : l'orchestrateur ne publiait aucune
documentation de son API côté agent — le contrat a été découvert par la reconnaissance décrite plus
bas, puis figé dans le code.

## Cycle de vie

1. **Enregistrement** — `POST /api/v1/agents/enroll` avec une clé d'enregistrement, un identifiant
   d'instance stable et un nom. L'orchestrateur renvoie :
   `agent_id`, `name`, `role`, `status`, `access_token`, `token_type`, `created_at`.
   Le statut initial est `PENDING`.
2. **Présence** — `POST /api/v1/agents/heartbeat` avec le jeton ; le serveur repasse l'agent
   `ONLINE` et renvoie aussi son propre état. Sans heartbeat, l'agent redevient `OFFLINE` en une
   minute environ.
3. **Tâches** — `GET /api/v1/agents/tasks` renvoie la file attribuée à cet agent.
4. **Identité vue par le serveur** — `GET /api/v1/agents/me`.

Toutes les autres routes de l'orchestrateur (liste des agents, tâches globales, journaux,
événements, réglages) exigent une session d'administration et restent hors de portée d'un agent.

## Utilisation

```
python cvlynk_agent.py --status     # identité + tâches vues par l'orchestrateur
python cvlynk_agent.py --once       # un heartbeat + une lecture des tâches
python cvlynk_agent.py              # boucle : heartbeat 20 s, lecture des tâches 15 s
```

Configuration : copie `.env.example` vers `.env`. Le jeton renvoyé à l'enregistrement est un
secret — écris-le dans `.env` et restreins les droits du fichier :

```
icacls .env /inheritance:r /grant:r "%USERNAME%:(R)"
```

## Comportement envers les tâches reçues

Une tâche reçue est un contenu écrit par un tiers : elle est **journalisée** dans `inbox.jsonl` et
**remontée**, jamais exécutée automatiquement. Le fichier `cvlynk_agent.log` conserve la trace des
heartbeats et des erreurs.

## Notes issues de l'intégration réelle

- **S'enregistrer une seule fois, avec tout.** Le corps de l'enregistrement accepte la description
  de l'agent ; la route de heartbeat ignore ces champs. Un premier enregistrement minimal consomme
  l'identité : un second appel renvoie `409 AGENT_ALREADY_ENROLLED` (« un nouvel enregistrement
  n'est possible qu'après révocation »). Les champs facultatifs doivent donc partir dans **le
  premier** appel.
- **Mesurer le délai de bascule.** Le seuil d'`OFFLINE` se mesure : un heartbeat, puis des lectures
  répétées de l'identité jusqu'à la bascule. Ajuster la période en conséquence (20 s ici).
- **Journaliser les succès périodiquement**, pas seulement les échecs : sans cela, un journal
  silencieux ne permet pas de prouver que la boucle tourne.
- **Dossier `Démarrage` plutôt que tâche planifiée** : `schtasks /create` demande une élévation
  administrateur et échoue sans elle.
