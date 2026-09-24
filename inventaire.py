#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere inventaire.json : l'inventaire reel de l'agent, lu depuis la machine.

Sources :
  - configuration de l'agent (modele, moteurs, garde-fous, plafonds)
  - catalogue d'outils actifs sur le canal de messagerie
  - dossier de competences (nom, description, origine : ecrite ici ou importee)
  - extensions publiees dans ce depot
Aucune donnee personnelle : pas d'identifiant d'utilisateur, pas de nom de machine,
pas d'adresse reseau.
"""
import json
import os
import re
from pathlib import Path

HERMES = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData/Local/hermes"))
SOCLE = HERMES / "hermes-agent" / "skills"          # competences livrees avec le socle
DEPOT = Path(__file__).resolve().parent
SORTIE = DEPOT / "inventaire.json"


def charger_config() -> dict:
    """Charge la configuration de l'agent.

    PyYAML est utilise s'il est disponible (lecture exacte, listes et imbrications
    comprises) ; sinon on retombe sur le lecteur minimal ci-dessous, suffisant pour
    l'inventaire mais qui ne descend que de deux niveaux.
    """
    fichier = HERMES / "config.yaml"
    try:
        import yaml  # optionnel
        with open(fichier, encoding="utf-8", errors="replace") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return lire_config(fichier)


def lire_config(fichier: Path) -> dict:
    """Lecture minimale du YAML de configuration, sans dependance externe.

    Gere les sections, les sous-sections, les valeurs simples et les listes
    ('- element'). Suffisant pour l'inventaire ; ce n'est pas un parseur YAML complet.
    """
    cfg, section, sous = {}, None, None
    for brute in fichier.read_text(encoding="utf-8", errors="replace").splitlines():
        if not brute.strip() or brute.lstrip().startswith("#"):
            continue
        indent = len(brute) - len(brute.lstrip())
        ligne = brute.strip()
        if ligne.startswith("- "):                      # element de liste
            if section and sous and isinstance(cfg.get(section, {}).get(sous), list):
                cfg[section][sous].append(ligne[2:].strip())
            continue
        if ":" not in ligne:
            continue
        cle, _, valeur = ligne.partition(":")
        valeur = valeur.strip()
        if indent == 0:
            section, sous = cle, None
            cfg[section] = valeur or {}
            continue
        if not valeur:                                  # sous-section
            sous = cle
            if isinstance(cfg.get(section), dict):
                cfg[section][sous] = []
            continue
        cible = cfg[section]
        if isinstance(cible, dict):
            if sous and isinstance(cible.get(sous), list) and not valeur.replace("-", "").isdigit():
                cible[sous] = valeur                        # liste vide notee '[]' sur la ligne
            else:
                cible[cle] = valeur
    return cfg


def outils_actifs(cfg: dict) -> list:
    plat = cfg.get("platform_toolsets")
    if isinstance(plat, dict) and isinstance(plat.get("telegram"), list):
        return plat["telegram"]
    return []


def classer_origine(cat: str, nom: str, texte: str) -> str:
    """Distingue ce qui vient du socle, ce qui a ete importe, et ce qui a ete ecrit ici.

    Le dossier d'installation contient les competences livrees avec le socle ; tout ce qui
    n'y figure pas a ete ajoute sur cette machine. Parmi ces ajouts, la marque d'import
    ('Importé depuis' / source declaree) separe les palques importees du travail local.
    """
    if (SOCLE / cat / nom / "SKILL.md").exists():
        return "fournie_avec_le_socle"
    if "Importé depuis" in texte or re.search(r"source:\s*['\"]?skill", texte):
        return "importee_d_un_tier"
    return "ajoutee_sur_cette_instance"


def decrire_competence(cat: str, dossier: Path) -> dict:
    md = dossier / "SKILL.md"
    if not md.exists():
        return {}
    texte = md.read_text(encoding="utf-8", errors="replace")
    fm = re.search(r"^---\n(.*?)\n---", texte, re.S)
    nom = desc = version = ""
    if fm:
        bloc = fm.group(1)
        nom = (re.search(r"^name:\s*(.+)$", bloc, re.M) or [None, dossier.name])[1].strip().strip('"')
        desc = (re.search(r"^description:\s*(.+)$", bloc, re.M) or [None, ""])[1].strip().strip('"')
        version = (re.search(r"^version:\s*(.+)$", bloc, re.M) or [None, ""])[1].strip()
    return {"nom": nom, "version": version, "description": desc,
            "origine": classer_origine(cat, dossier.name, texte),
            "fichiers": sorted(p.name for p in dossier.rglob("*") if p.is_file())}


def main():
    cfg = charger_config()
    racine_skills = HERMES / "skills"
    competences, par_categorie = [], {}
    if racine_skills.is_dir():
        for cat in sorted(p for p in racine_skills.iterdir() if p.is_dir()):
            for sk in sorted(p for p in cat.iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
                info = decrire_competence(cat.name, sk)
                info["categorie"] = cat.name
                competences.append(info)
                par_categorie[cat.name] = par_categorie.get(cat.name, 0) + 1

    miennes = [c for c in competences if c["origine"] == "ajoutee_sur_cette_instance"]
    importees = [c for c in competences if c["origine"] == "importee_d_un_tier"]
    extensions = []
    for d in sorted((DEPOT / "extensions").iterdir()) if (DEPOT / "extensions").is_dir() else []:
        if d.is_dir():
            f = sorted(p.name for p in d.iterdir() if p.is_file())
            extensions.append({"nom": d.name, "fichiers": f, "points_entree":
                               [x for x in f if x.endswith(".py")]})

    agent = cfg.get("agent") or {}
    garde = cfg.get("tool_loop_guardrails") or {}
    inventaire = {
        "genere_par": "agent-hermes/inventaire.py",
        "identite": {
            "type": "agent autonome polyvalent",
            "socle": "Hermes Agent (Nous Research)",
            "modele": (cfg.get("model") or {}).get("default"),
            "fournisseur": (cfg.get("model") or {}).get("provider"),
            "canal_principal": "telegram",
            "plafond_tours_par_tache": agent.get("max_turns"),
            "effort_de_raisonnement": agent.get("reasoning_effort"),
        },
        "outils": {
            "nombre_sur_le_canal_principal": len(outils_actifs(cfg)),
            "charges_a_la_demande": True,
            "liste": outils_actifs(cfg),
        },
        "capacites_declarees_aux_orchestrateurs": [
            "echo", "system_info", "disk_usage", "http_fetch", "time",
            "lan_scan", "log_analysis", "web_research", "document_generation", "code_generation",
        ],
        "competences": {
            "note_classement": ("fournie_avec_le_socle = presente dans l'installation du socle ; "
                                "importee_d_un_tier = ajoutee ici avec sa marque d'import ; "
                                "ajoutee_sur_cette_instance = presente sur cette machine, absente du "
                                "socle, sans marque d'import automatique"),
            "total": len(competences),
            "par_categorie": dict(sorted(par_categorie.items())),
            "ajoutees_sur_cette_instance": miennes,
            "importees_d_un_tier": [{"categorie": c["categorie"], "nom": c["nom"]} for c in importees],
            "venant_du_socle": len(competences) - len(miennes) - len(importees),
        },
        "extensions_publiees": extensions,
        "garde_fous": {
            "avertir_apres": garde.get("warn_after"),
            "arreter_apres": garde.get("hard_stop_after"),
            "arret_dur_non_interactif": garde.get("non_interactive_hard_stop_enabled"),
            "compression_de_contexte": (cfg.get("compression") or {}).get("enabled"),
            "secrets_masques_par_defaut": (cfg.get("security") or {}).get("redact_secrets", True),
        },
        "moteurs": {
            "shell": (cfg.get("terminal") or {}).get("backend"),
            "navigateur": (cfg.get("browser") or {}).get("backend"),
            "recherche_web": (cfg.get("web") or {}).get("backend"),
            "synthese_vocale": (cfg.get("tts") or {}).get("provider"),
        },
    }
    SORTIE.write_text(json.dumps(inventaire, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{SORTIE} ecrit : {len(competences)} competences dont {len(miennes)} ecrites ici, "
          f"{len(inventaire['outils']['liste'])} outils actifs.")


if __name__ == "__main__":
    main()
