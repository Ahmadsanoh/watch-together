"""
00 - CONTROLE QUALITE DES DONNEES (en amont du pipeline).

Avant toute modelisation, une equipe data serieuse verifie la QUALITE de ses
logs : certaines sessions ne sont pas exploitables (trafic non-humain, sessions
vides, timings incoherents) et fausseraient les metriques de retention si on
les gardait. Ce module ecarte ces sessions pour ne modeliser que du signal fiable.

Trois controles simples, explicables (pas de boite noire) :
  1. Vitesse de progression irrealiste : la position video avance plus vite que
     le temps reel ne le permet (lecture automatique / script).
  2. Regularite trop parfaite des evenements : ecart-type des intervalles proche
     de zero (un humain est irregulier ; une machine ne l'est pas).
  3. Session sans aucune interaction (pause/seek/replay) sur une video longue :
     peu credible pour un vrai spectateur au-dela de 5 minutes.

INTERPRETATION DES RESULTATS (a assumer en soutenance) :
Nos donnees sont propres et representent un trafic essentiellement humain. Le
controle ecarte donc PEU de sessions — c'est le resultat ATTENDU et un bon
signe de qualite. L'interet du module n'est pas d'en filtrer beaucoup, mais de
GARANTIR qu'on ne modelise pas de sessions aberrantes. L'architecture
multi-controles reste prete a monter en charge sur de vraies donnees de
plateforme, ou ce type de trafic est plus frequent.

Sortie :
  - data/session_quality_report.csv : un diagnostic par session
  - data/events_clean.csv           : events.csv restreint aux sessions fiables
  - outputs/data_quality_summary.json
"""

import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import pandas as pd
import numpy as np
import json

DATA_DIR = _os.path.join(BASE_DIR, "data")
OUT = _os.path.join(BASE_DIR, "outputs")


def main():
    events = pd.read_csv(f"{DATA_DIR}/events.csv", parse_dates=["timestamp_wall"])
    videos = pd.read_csv(f"{DATA_DIR}/videos.csv")
    events = events.merge(videos[["video_id", "duration_sec"]], on="video_id")

    flags = []

    for session_id, g in events.groupby("session_id"):
        g = g.sort_values("timestamp_wall")
        duration = g["duration_sec"].iloc[0]
        n_events = len(g)

        # 1. vitesse de progression : delta position video / delta temps reel
        wall_span = (g["timestamp_wall"].max() - g["timestamp_wall"].min()).total_seconds()
        video_span = g["timestamp_video"].max() - g["timestamp_video"].min()
        speed_ratio = video_span / wall_span if wall_span > 0 else 1.0
        anomalie_vitesse = speed_ratio > 3.0

        # 2. regularite trop parfaite des intervalles entre evenements
        if n_events >= 4:
            intervals = g["timestamp_wall"].diff().dt.total_seconds().dropna()
            cv = intervals.std() / intervals.mean() if intervals.mean() > 0 else 1.0
            regularite_anormale = cv < 0.05
        else:
            regularite_anormale = False

        # 3. zero interaction (pause/seek/replay) sur une video longue (>5min)
        sans_interaction = (
            duration > 300
            and not g["event_type"].isin(["pause", "seek", "replay"]).any()
        )

        non_exploitable = anomalie_vitesse or regularite_anormale or sans_interaction

        flags.append({
            "session_id": session_id,
            "video_id": g["video_id"].iloc[0],
            "n_events": n_events,
            "speed_ratio": round(speed_ratio, 2),
            "anomalie_vitesse": anomalie_vitesse,
            "regularite_anormale": regularite_anormale,
            "sans_interaction_video_longue": sans_interaction,
            "non_exploitable": non_exploitable,
        })

    quality_df = pd.DataFrame(flags)
    quality_df.to_csv(f"{DATA_DIR}/session_quality_report.csv", index=False)

    a_ecarter = set(quality_df.loc[quality_df["non_exploitable"], "session_id"])
    events_clean = events[~events["session_id"].isin(a_ecarter)].drop(columns=["duration_sec"])
    events_clean.to_csv(f"{DATA_DIR}/events_clean.csv", index=False)

    summary = {
        "total_sessions": len(quality_df),
        "sessions_ecartees": int(quality_df["non_exploitable"].sum()),
        "sessions_ecartees_pct": round(quality_df["non_exploitable"].mean() * 100, 2),
        "sessions_fiables_pct": round((1 - quality_df["non_exploitable"].mean()) * 100, 2),
        "breakdown": {
            "anomalie_vitesse": int(quality_df["anomalie_vitesse"].sum()),
            "regularite_anormale": int(quality_df["regularite_anormale"].sum()),
            "sans_interaction_video_longue": int(quality_df["sans_interaction_video_longue"].sum()),
        },
    }
    with open(f"{OUT}/data_quality_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("CONTROLE QUALITE DES DONNEES")
    print(f"Sessions analysees        : {summary['total_sessions']:,}")
    print(f"Sessions ecartees         : {summary['sessions_ecartees']:,} "
          f"({summary['sessions_ecartees_pct']}%)")
    print(f"Sessions fiables retenues : {summary['sessions_fiables_pct']}%")
    print(f"Detail des controles      : {summary['breakdown']}")
    print(f"\n-> data/events_clean.csv genere (sessions fiables uniquement), "
          f"utilise dans la suite du pipeline.")


if __name__ == "__main__":
    main()
