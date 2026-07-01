"""
07 - Innovation #2 : personas de spectateurs (clustering non supervisé).

Au lieu de ne traiter que la rétention au niveau "segment de vidéo", on
caractérise chaque UTILISATEUR par son comportement de visionnage (KMeans),
ce qui permet de raconter une histoire du type :
  "30% de vos viewers sont des 'binge-watchers engagés', 15% sont des
   'zappeurs', etc." -> ça enrichit le dashboard au-delà de la seule
   prédiction de rétention et c'est un bon visuel de pitch.

Features par utilisateur (agrégées sur toutes ses sessions) :
  - max_completion : plus loin point atteint / durée vidéo (moyenne)
  - n_pauses_total, n_replays_total, n_seeks_total
  - exited_early : a quitté avant 50% de la vidéo (0/1, moyenne = taux)

Sortie : data/viewer_personas.csv (user_id, cluster, persona_label, features...)
         outputs/personas_distribution.png
"""


import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = _os.path.join(BASE_DIR, "data")
OUT = _os.path.join(BASE_DIR, "outputs")
N_CLUSTERS = 4


def main():
    events = pd.read_csv(f"{DATA_DIR}/events.csv")
    videos = pd.read_csv(f"{DATA_DIR}/videos.csv")
    # Si duration_sec existe déjà dans events (données de la fille), pas besoin de merge
    if "duration_sec" not in events.columns:
        events = events.merge(videos[["video_id", "duration_sec"]], on="video_id")

    pos_col = "position_sec" if "position_sec" in events.columns else "timestamp_video"
    grp = events.groupby("user_id")
    max_pos = grp[pos_col].max()
    duration = grp["duration_sec"].first()
    n_pauses = events[events.event_type == "pause"].groupby("user_id").size()
    n_replays = events[events.event_type == "replay"].groupby("user_id").size()
    n_seeks = events[events.event_type == "seek"].groupby("user_id").size()

    feats = pd.DataFrame({
        "completion_ratio": (max_pos / duration).clip(0, 1),
        "n_pauses": n_pauses,
        "n_replays": n_replays,
        "n_seeks": n_seeks,
    }).fillna(0)

    X = StandardScaler().fit_transform(feats)
    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    feats["cluster"] = km.fit_predict(X)

    # labellisation automatique des clusters selon leurs caractéristiques moyennes
    profile = feats.groupby("cluster").mean()
    labels = {}
    for c, row in profile.iterrows():
        if row["completion_ratio"] > 0.8 and row["n_pauses"] < profile["n_pauses"].median():
            labels[c] = "Engagé fluide"
        elif row["completion_ratio"] > 0.8:
            labels[c] = "Engagé attentif (pause souvent)"
        elif row["completion_ratio"] < 0.4:
            labels[c] = "Décrocheur rapide"
        else:
            labels[c] = "Zappeur (replay/seek fréquents)" if row["n_replays"] + row["n_seeks"] > profile[["n_replays","n_seeks"]].sum(axis=1).median() else "Engagement moyen"

    feats["persona_label"] = feats["cluster"].map(labels)
    feats = feats.reset_index().rename(columns={"index": "user_id"})

    feats.to_csv(f"{DATA_DIR}/viewer_personas.csv", index=False)

    dist = feats["persona_label"].value_counts(normalize=True) * 100
    plt.figure(figsize=(7, 5))
    dist.sort_values().plot(kind="barh", color="#8172B2")
    plt.xlabel("% des spectateurs")
    plt.title("Répartition des personas de spectateurs")
    plt.tight_layout()
    plt.savefig(f"{OUT}/personas_distribution.png", dpi=120)
    plt.close()

    print("Personas détectées :")
    print(dist.round(1))
    print(f"\nGénérés : data/viewer_personas.csv, outputs/personas_distribution.png")


if __name__ == "__main__":
    main()
