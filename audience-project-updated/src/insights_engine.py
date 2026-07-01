"""
Innovation #3 : générateur d'insights automatique en langage naturel.

Transforme les chiffres bruts (zones d'ennui, drop-off, personas) en
recommandations actionnables lisibles par un humain non-technique
(ex: un créateur de contenu, un chef de produit éditorial).

C'est un système à base de règles (pas un LLM) : rapide, déterministe,
explicable, sans dépendance API — mais conçu comme un moteur de templates
intelligents qui priorise les insights par impact. Peut être branché plus
tard sur un vrai LLM pour enrichir le phrasé.
"""

import pandas as pd


def generate_insights(seg_v: pd.DataFrame, zones_v: pd.DataFrame, video_title: str) -> list[str]:
    """Génère une liste de phrases d'insight, triées par priorité décroissante."""
    insights = []

    if len(seg_v) == 0:
        return ["Pas assez de données pour générer des insights sur cette vidéo."]

    final_completion = seg_v.iloc[-1]["completion_rate"]
    initial_viewers = seg_v.iloc[0]["n_viewers_reached"]

    # 1. Zone d'ennui la plus critique
    if len(zones_v) > 0:
        worst = zones_v.loc[zones_v["avg_score"].idxmax()]
        duration = worst["zone_end"] - worst["zone_start"]
        insights.append(
            f"🔴 **Zone critique détectée** entre {int(worst['zone_start'])}s et "
            f"{int(worst['zone_end'])}s (durée {int(duration)}s, score d'ennui "
            f"{worst['avg_score']:.2f}). C'est le passage qui fait perdre le plus "
            f"de spectateurs — à raccourcir ou redynamiser en priorité."
        )
        if len(zones_v) > 1:
            insights.append(
                f"⚠️ {len(zones_v)} zones d'ennui identifiées au total sur cette vidéo. "
                f"Une vidéo bien rythmée en a généralement 0 à 1."
            )
    else:
        insights.append(
            "✅ Aucune zone d'ennui significative détectée — le rythme global de la "
            "vidéo semble bien maîtrisé."
        )

    # 2. Vitesse de décrochage initiale (30 premières secondes)
    early = seg_v[seg_v["start"] < 30]
    if len(early) > 0:
        early_dropoff = early["dropoff_rate"].mean()
        if early_dropoff > 0.05:
            insights.append(
                f"⏱️ **Accroche à retravailler** : {early_dropoff*100:.1f}% de décrochage "
                f"moyen dans les 30 premières secondes. C'est généralement le passage le "
                f"plus déterminant pour la rétention globale."
            )

    # 3. Complétion finale
    if final_completion < 0.3:
        insights.append(
            f"📉 Seulement {final_completion*100:.1f}% des spectateurs terminent la vidéo. "
            f"Envisager de raccourcir la vidéo ou de restructurer la fin."
        )
    elif final_completion > 0.7:
        insights.append(
            f"📈 Excellente rétention : {final_completion*100:.1f}% des spectateurs vont "
            f"jusqu'au bout. Ce format peut servir de référence pour les prochaines vidéos."
        )

    # 4. Pauses fréquentes = signal ambigu (intérêt vs confusion)
    high_pause_segs = seg_v[seg_v["avg_pause_rate"] > seg_v["avg_pause_rate"].quantile(0.85)]
    if len(high_pause_segs) > 0:
        seg = high_pause_segs.iloc[0]
        insights.append(
            f"⏸️ Pic de pauses détecté autour de {int(seg['start'])}s — peut indiquer un "
            f"passage dense (les spectateurs ont besoin de temps pour assimiler) ou un "
            f"point de confusion. À vérifier qualitativement."
        )

    return insights


def generate_global_insights(overview: pd.DataFrame, personas: pd.DataFrame = None) -> list[str]:
    """Insights cross-vidéos pour la vue d'ensemble."""
    insights = []

    best = overview.loc[overview["completion_finale"].idxmax()]
    worst = overview.loc[overview["completion_finale"].idxmin()]

    insights.append(
        f"🏆 **{best['title']}** a la meilleure rétention finale "
        f"({best['completion_finale']*100:.1f}%) — analyser ce qui fonctionne bien dans "
        f"son rythme pour le répliquer."
    )
    insights.append(
        f"🔻 **{worst['title']}** a la rétention la plus faible "
        f"({worst['completion_finale']*100:.1f}%) — candidate prioritaire pour un montage "
        f"correctif basé sur ses zones d'ennui."
    )

    if personas is not None and len(personas) > 0:
        dist = personas["persona_label"].value_counts(normalize=True) * 100
        top_persona = dist.idxmax()
        insights.append(
            f"👥 Le persona dominant de votre audience est **'{top_persona}'** "
            f"({dist.max():.0f}% des spectateurs) — adapter le ton éditorial à ce profil "
            f"peut améliorer l'engagement global."
        )

    return insights
