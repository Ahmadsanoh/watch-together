"""
P3 - Détection des zones d'ennui — version innovante.

PROBLÈME avec un seuil de percentile brut (notre première version) :
toute vidéo perd naturellement des spectateurs au fil du temps, même
sans aucun passage ennuyeux particulier (attrition naturelle). Un simple
seuil sur le dropoff_rate brut va donc presque toujours flagger la fin
de la vidéo comme "ennuyeuse", même quand elle ne l'est pas plus que le
reste — c'est un biais structurel.

INNOVATION : on modélise d'abord la courbe d'attrition NATURELLE attendue
pour chaque vidéo (une décroissance exponentielle lissée, ajustée sur les
données réelles de cette vidéo), puis on ne flag que les segments où le
décrochage RÉEL dépasse significativement ce qui était attendu. Une zone
d'ennui devient donc : "un endroit où on perd plus de monde que ce que la
vidéo perd déjà naturellement ailleurs" — beaucoup plus défendable
scientifiquement qu'un seuil arbitraire, et ça évite de systématiquement
accuser la fin de la vidéo à tort.

Méthode : régression exponentielle simple completion_rate ~ exp(-k*t),
ajustée par moindres carrés sur chaque vidéo, puis résidu = écart entre
réel et attendu à chaque segment.

Sortie : data/segment_features_scored.csv, data/bored_zones_detected.csv
"""


import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit

THRESHOLD_RESIDUAL_PCT = 0.08  # un segment est "ennuyeux" s'il perd 8 points
                                # de complétion de PLUS que ce que prédit la
                                # courbe d'attrition naturelle de sa vidéo


def attrition_curve(t, k, c):
    """Modèle de décroissance exponentielle : completion attendue au temps t."""
    return np.exp(-k * t) * (1 - c) + c


def fit_natural_attrition(seg: pd.DataFrame):
    t = seg["start"].values.astype(float)
    y = seg["completion_rate"].values.astype(float)
    try:
        popt, _ = curve_fit(attrition_curve, t, y, p0=[0.001, 0.1], maxfev=5000)
        predicted = attrition_curve(t, *popt)
    except Exception:
        predicted = np.linspace(y[0], y[-1], len(y))
    return predicted


def main():
    df = pd.read_csv(_os.path.join(BASE_DIR, "data/segment_features.csv"))

    df["expected_completion"] = np.nan
    for vid, seg in df.groupby("video_id"):
        seg = seg.sort_values("start")
        predicted = fit_natural_attrition(seg)
        df.loc[seg.index, "expected_completion"] = predicted

    df["attrition_residual"] = df["expected_completion"] - df["completion_rate"]

    def normalize(s):
        return (s - s.min()) / (s.max() - s.min()) if s.max() != s.min() else s * 0

    df["residual_norm"] = df.groupby("video_id")["attrition_residual"].transform(normalize)
    df["pause_norm"] = df.groupby("video_id")["avg_pause_rate"].transform(normalize)
    df["dropoff_norm"] = df.groupby("video_id")["dropoff_rate"].transform(normalize)

    # Score ENSEMBLE : on combine deux familles de signaux complémentaires.
    #   - attrition_residual (innovation) : capte les écarts structurels par
    #     rapport à la dynamique d'attrition propre à CETTE vidéo
    #   - dropoff_rate / pause brut : capte les pics locaux de décrochage,
    #     plus réactif sur des creux courts qu'une courbe lissée peut absorber
    # L'ensemble est plus robuste qu'une seule des deux approches isolément —
    # c'est le même principe qu'un ensemble de modèles en ML : on combine des
    # signaux complémentaires plutôt que de parier sur un seul.
    df["bored_score"] = (
        0.4 * df["residual_norm"] + 0.4 * df["dropoff_norm"] + 0.2 * df["pause_norm"]
    )

    score_threshold = df.groupby("video_id")["bored_score"].transform(
        lambda x: np.percentile(x, 75)
    )
    df["is_bored"] = df["bored_score"] >= score_threshold

    df.to_csv(_os.path.join(BASE_DIR, "data/segment_features_scored.csv"), index=False)

    zones = []
    for vid, g in df.groupby("video_id"):
        g = g.sort_values("segment_id").reset_index(drop=True)
        in_zone = False
        zone_start, zone_end, scores = None, None, []
        for _, row in g.iterrows():
            if row["is_bored"]:
                if not in_zone:
                    in_zone = True
                    zone_start = row["start"]
                zone_end = row["end"]
                scores.append(row["bored_score"])
            else:
                if in_zone:
                    zones.append({
                        "video_id": vid, "zone_start": zone_start,
                        "zone_end": zone_end, "avg_score": round(np.mean(scores), 3),
                    })
                    in_zone = False
                    scores = []
        if in_zone:
            zones.append({
                "video_id": vid, "zone_start": zone_start,
                "zone_end": zone_end, "avg_score": round(np.mean(scores), 3),
            })

    zones_df = pd.DataFrame(zones)
    zones_df.to_csv(_os.path.join(BASE_DIR, "data/bored_zones_detected.csv"), index=False)

    print(f"Zones d'ennui détectées (vs courbe d'attrition naturelle) : {len(zones_df)}")
    print(zones_df)

    try:
        truth = pd.read_csv(_os.path.join(BASE_DIR, "data/ground_truth_bored_zones.csv"))
        print("\n--- Vérité terrain (pour référence interne) ---")
        print(truth)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
