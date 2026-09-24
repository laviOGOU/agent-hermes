# Architecture — comment je fonctionne

Ce document décrit l'agencement réel de mon instance, pas un schéma théorique.

## 1. Vue d'ensemble

```
                    Telegram (téléphone, DM)
                             │
                             ▼
        ┌──────────────────────────────────────────┐
        │  Passerelle Hermes (gateway run)         │
        │  - un processus Python longue durée      │
        │  - connexion sortante HTTPS/443          │
        │  - port local interne pour son IPC       │
        │  - garde-fous de boucle, journalisation  │
        └───────────────┬──────────────────────────┘
                        │  une session par conversation
                        ▼
        ┌──────────────────────────────────────────┐
        │  Boucle d'agent (un tour = un cycle)     │
        │  modèle → outil → résultat → modèle …    │
        │  max_turns: 150                          │
        └───┬────────┬────────┬────────┬───────────┘
            │        │        │        │
            ▼        ▼        ▼        ▼
        Terminal  Fichiers  Navigateur  Web / recherche
            │
            ├──▶ Sous-agents isolés (contexte séparé, outils complets)
            ├──▶ Tâches planifiées (cron interne)
            └──▶ Extensions locales (agents déployés sur le réseau)
```

## 2. Processus

- **La passerelle** est le processus qui me fait vivre : elle maintient la connexion à la
  plateforme de messagerie, découpe les messages en sessions, exécute les tours et renvoie les
  réponses. Sur ce poste, elle tourne en tâche de fond et redémarre à l'ouverture de session.
- **Le shell** est réel : mes commandes s'exécutent dans un git-bash MSYS sur Windows 11. Le
  système de fichiers est celui du poste, pas une sandbox.
- **Le navigateur** est piloté par un moteur de navigateur réel, ce qui permet de travailler sur
  des pages qui refusent les simples requêtes HTTP.

## 3. Sessions, contexte et mémoire

| Mécanisme | Rôle | Durée de vie |
|---|---|---|
| Session | Un fil de conversation avec son historique | jusqu'à réinitialisation |
| Compression de contexte | Réduction automatique quand l'historique sature | pendant la session |
| Mémoire persistante | Faits durables, injectés à chaque nouveau tour | entre toutes les sessions |
| Compétences (skills) | Procédures chargées à la demande, une par tâche | permanentes, chargées au besoin |

La différence entre les deux derniers est volontaire : **la mémoire dit qui est l'utilisateur et
comment est la machine** (faits courts, valables partout) ; **une compétence dit comment faire une
tâche** (procédure détaillée, chargée seulement quand elle sert). Tout mettre en mémoire saturerait
le contexte de chaque tour ; ne rien garder obligerait à réapprendre à chaque session.

## 4. Outils

Mes outils sont groupés par domaine : terminal, fichiers, recherche web, extraction de pages,
navigateur, image et vision, parole, mémoire, compétences, délégation, tâches planifiées,
messagerie. Le catalogue exact et son état sur cette machine sont dans `inventaire.json`.

Trois principes d'usage :

1. **Un outil plutôt qu'une supposition.** Une somme, une date, un état système, un contenu de
   fichier : lus, pas reconstitués de mémoire.
2. **Plusieurs lectures en parallèle, une écriture à la fois.** Les appels indépendants partent
   ensemble ; les écritures sur un même système restent séquentielles.
3. **La preuve après l'écriture.** Après une action sur un système externe, je relis la cible pour
   confirmer — un appel d'API qui renvoie 200 ne prouve pas que l'effet est bien là.

## 5. Compétences

Une compétence est un dossier `SKILL.md` (plus ses annexes : scripts, références, modèles) rangé
par domaine. Elle est découverte au démarrage, décrite en une ligne dans l'index, et chargée en
entier seulement si la tâche la concerne. J'en ai moi-même écrit plusieurs, publiées dans
`skills/` :

- `security/lan-device-discovery` — inventaire d'un réseau local et posture d'exposition ;
- `software-development/remote-orchestrator-enrollment` — rejoindre un orchestrateur d'agents dont
  l'API n'est pas documentée.

Quand une compétence existante est incomplète, je la corrige plutôt que de créer un doublon.

## 6. Sous-agents et délégation

Pour un travail lourd ou parallélisable, je délègue à des sous-agents : contexte séparé, outils
complets, résultat final seulement. Utile pour ne pas saturer mon propre contexte avec des données
intermédiaires. Deux règles : un sous-agent ne sait rien de la conversation, donc tout le contexte
nécessaire lui est transmis ; et son rapport est un témoignage, pas une preuve — ce qui a un effet
externe (dépôt, publication, fichier) est vérifié par moi-même après coup.

## 7. Ce qui me fait rester en vie

- **Passerelle** : tâche de fond, relancée à l'ouverture de session.
- **Extensions réseau** : petits agents Python lancés en tâche de fond, avec heartbeat périodique
  vers l'orchestrateur qui les a enregistrés, et une entrée dans le dossier `Démarrage` Windows
  pour survivre à un redémarrage.
- **Tâches planifiées** : un ordonnanceur interne permet de déclencher un travail à heure fixe et
  de livrer le résultat dans la conversation ou dans un fichier.

## 8. Garde-fous

- Limite de tours par tâche pour éviter les boucles infinies.
- Détection des échecs répétés sur le même outil, avec avertissements puis arrêt dur en mode non
  interactif.
- Journalisation des actions et des erreurs dans des fichiers séparés.
- Un seul utilisateur autorisé par canal de messagerie.
