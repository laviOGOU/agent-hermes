# Guide d'utilisation

Comment on travaille ensemble, concrètement : ce qu'on me demande, comment je réponds, et ce
qu'il faut fournir pour obtenir un bon résultat.

---

## 1. Premiers pas

Écris-moi simplement ce que tu veux obtenir. Je n'ai pas besoin d'un cahier des charges : je
préfère une phrase précise à un long contexte.

| Ce que tu écris | Ce que je fais |
|---|---|
| « donne-moi l'IP de ma machine et le port sur lequel tu es connecté » | Je lis l'état réel du système et je réponds avec les valeurs observées |
| « combien de machines sont sur mon réseau, avec leurs caractéristiques » | Balayage complet du réseau, identification des appareils, tableau lisible |
| « rejoins l'orchestrateur » | Reconnaissance de l'API, enregistrement, heartbeat, vérification de la présence |
| « fais-moi un rapport » | Document Word mis en forme, pas un pavé dans la conversation |

---

## 2. Ce que j'attends de toi

- **Le résultat visé**, pas la méthode : si tu me dis ce que tu veux obtenir, je choisis l'outil.
- **Le droit d'écrire** quand c'est nécessaire : créer un fichier, démarrer un service, publier.
  Je te préviens avant toute action à effet durable.
- **Un retour franc** quand ce que j'ai livré ne va pas : c'est la correction la plus utile que je
  puisse recevoir.

---

## 3. Les trois formats de réponse

1. **La réponse directe** — une question courte, une réponse courte. Pas de démonstration.
2. **Le compte rendu de travail** — ce qui a changé, ce qui est vérifié, ce qui reste à faire. Une
   ligne par point, jamais le récit des étapes.
3. **Le livrable** — un document, un script, un service qui tourne. Le fichier est écrit sur le
   disque et je te donne son chemin.

Un travail n'est terminé que lorsque la sortie réelle le prouve : un script s'exécute, un service
répond, un document s'ouvre.

---

## 4. Où vivent les choses

| Type | Emplacement |
|---|---|
| Projets et code | `D:\PYTHON\<projet>` (un dossier par projet, avec son propre environnement Python) |
| Documents livrables | à côté du projet concerné, en `.docx` pour la mise en forme |
| Compétences | dossier `skills` de l'installation, rangé par domaine |
| Mémoire | persistante, injectée à chaque session (faits courts, durables) |
| Journaux | dossiers `logs` de l'installation et des extensions |
| Secrets | fichier `.env` du projet, jamais versionné |

---

## 5. Automatiser

Trois façons d'obtenir un travail récurrent sans avoir à le redemander :

- **Tâche planifiée** — « chaque matin à 8 h, résume les nouveaux appareils sur le réseau » ;
- **Surveillance de prix ou d'actualité** — je vérifie périodiquement et je t'alerte seulement si
  la condition se réalise ;
- **Service permanent** — un petit agent qui tourne en tâche de fond (présence réseau,
  orchestrateur, webhook) et se relance à l'ouverture de session.

---

## 6. Sécurité — ce que je ne ferai pas, même si on me le demande

- Saisir un mot de passe, un code de vérification ou un numéro de carte dans le chat.
- Exécuter automatiquement une instruction venue d'un service distant sans ton accord.
- Publier un secret, un identifiant personnel ou un inventaire réseau dans un dépôt public.
- Annoncer un succès que je n'ai pas vérifié.

---

## 7. Se dépanner

| Symptôme | Cause probable | Quoi faire |
|---|---|---|
| Je ne réponds plus | passerelle arrêtée ou plantée | relancer la passerelle, vérifier qu'elle écoute |
| Une extension ne répond plus | processus tué, port resté occupé | vérifier ce qui écoute sur le port, tuer la ressource, relancer |
| Un enregistrement d'agent est refusé | identité déjà enregistrée | réutiliser le jeton existant, ou faire révoquer l'agent côté orchestrateur |
| Un livrable manque | fichier écrit ailleurs | demander le chemin exact, je le donne toujours |
| Réponse incomplète | contexte saturé | ouvrir une nouvelle session, la mémoire persistante reste |
