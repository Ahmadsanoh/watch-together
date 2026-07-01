"""
P2 - Découpage des vidéos en segments fixes + calcul des features par segment.

Segment fixe de SEGMENT_LEN secondes (paramétrable).

Sortie : data/segment_features.csv avec, par (video_id, segment_id) :
  - start, end
  - n_viewers_reached   : nb d'utilisateurs ayant atteint ce segment
  - completion_rate     : % des viewers initiaux ayant atteint ce segment
  - dropoff_rate        : % des viewers présents au début du segment qui sortent dedans
  - n_pauses            : nb de pauses commencées dans ce segment
  - n_replays           : nb de replays dont le point d'arrivée est dans ce segment
  - n_seeks             : nb de seeks dans ce segment
  - avg_pause_rate      : n_pauses / n_viewers_reached
  - retention_next      : taux de complétion du segment suivant (= TARGET pour le modèle)
"""


import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import pandas as pd
import numpy as np

SEGMENT_LEN = 15  # secondes


def build_segments(duration, seg_len=SEGMENT_LEN):
    segs = []
    s = 0
    seg_id = 0
    while s < duration:
        e = min(duration, s + seg_len)
        segs.append({"segment_id": seg_id, "start": s, "end": e})
        s = e
        seg_id += 1
    return pd.DataFrame(segs)


def main():
    # On utilise events_clean.csv (sessions non exploitables déjà écartées
    # par 00_data_quality.py) plutôt que events.csv brut — sinon le contrôle
    # qualité est effectué pour rien et les sessions aberrantes faussent les taux.
    events = pd.read_csv(_os.path.join(BASE_DIR, "data/events_clean.csv"))
    videos = pd.read_csv(_os.path.join(BASE_DIR, "data/videos.csv"))

    all_segment_rows = []

    for _, video in videos.iterrows():
        vid = video["video_id"]
        duration = video["duration_sec"]
        ev = events[events["video_id"] == vid].copy()
        n_total_viewers = ev["user_id"].nunique()

        segments = build_segments(duration)

        # Compatibilité : données de la fille utilisent "position_sec",
        # l'original utilisait "timestamp_video" — on unifie ici.
        pos_col = "position_sec" if "position_sec" in ev.columns else "timestamp_video"
        max_pos_per_user = ev.groupby("user_id")[pos_col].max()

        for _, seg in segments.iterrows():
            start, end = seg["start"], seg["end"]
            seg_id = seg["segment_id"]

            n_reached = (max_pos_per_user >= start).sum()
            n_reached_next_start = (max_pos_per_user >= end).sum()

            completion_rate = n_reached / n_total_viewers if n_total_viewers else 0
            dropoff_rate = (
                (n_reached - n_reached_next_start) / n_reached if n_reached else 0
            )

            seg_events = ev[(ev[pos_col] >= start) & (ev[pos_col] < end)]
            n_pauses = (seg_events["event_type"] == "pause").sum()
            n_replays = (seg_events["event_type"] == "replay").sum() if "replay" in ev["event_type"].values else 0
            n_seeks = (seg_events["event_type"] == "seek").sum()

            all_segment_rows.append({
                "video_id": vid,
                "segment_id": seg_id,
                "start": start,
                "end": end,
                "n_viewers_reached": n_reached,
                "completion_rate": round(completion_rate, 4),
                "dropoff_rate": round(dropoff_rate, 4),
                "n_pauses": int(n_pauses),
                "n_replays": int(n_replays),
                "n_seeks": int(n_seeks),
                "avg_pause_rate": round(n_pauses / n_reached, 4) if n_reached else 0,
                "avg_replay_rate": round(n_replays / n_reached, 4) if n_reached else 0,
            })

    df = pd.DataFrame(all_segment_rows)

    # target : retention_next = completion_rate du segment suivant (même vidéo)
    df["retention_next"] = (
        df.groupby("video_id")["completion_rate"].shift(-1)
    )
    # pour le dernier segment de chaque vidéo, pas de "suivant" -> on copie sa propre completion_rate
    df["retention_next"] = df["retention_next"].fillna(df["completion_rate"])

    # --- Innovation P2 : vélocité d'engagement ---
    # Au lieu de regarder seulement l'état d'un segment (combien décrochent),
    # on capture aussi la DYNAMIQUE : le décrochage accélère-t-il ou ralentit-il ?
    # Deux segments avec le même dropoff_rate n'ont pas le même sens si l'un vient
    # d'une situation qui s'améliore et l'autre d'une qui se dégrade. C'est un
    # signal prédictif souvent absent des analyses de rétention basiques.
    df["dropoff_velocity"] = df.groupby("video_id")["dropoff_rate"].diff().fillna(0)
    df["completion_acceleration"] = (
        df.groupby("video_id")["completion_rate"].diff().diff().fillna(0)
    )
    # tendance lissée sur 2 segments précédents, pour absorber le bruit segment-à-segment
    df["dropoff_trend_3seg"] = (
        df.groupby("video_id")["dropoff_rate"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )

    # --- Amélioration proposée : score relatif par vidéo ---
    # Un dropoff_rate de 15% n'a pas le même sens sur une vidéo qui retient
    # bien son audience que sur une vidéo qui décroche partout. On compare
    # donc chaque segment à la moyenne ET à l'écart-type de SA PROPRE vidéo
    # (z-score), pour détecter les zones anormalement mauvaises *relativement*
    # au reste de la même vidéo, en complément du seuillage absolu déjà fait
    # par P3 (qui compare toutes les vidéos confondues).
    df["dropoff_relative_score"] = df.groupby("video_id")["dropoff_rate"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
    )
    # un segment est "anormalement mauvais" si son z-score dépasse +1 écart-type
    # au-dessus de la moyenne de sa propre vidéo
    df["is_relative_outlier"] = df["dropoff_relative_score"] > 1.0

    df.to_csv(_os.path.join(BASE_DIR, "data/segment_features.csv"), index=False)
    print(f"Segments générés : {len(df)}")
    print(df.head(15))


if __name__ == "__main__":
    main()
