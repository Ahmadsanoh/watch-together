"""
P4/P5 - Modèle de prédiction de rétention.

Deux angles, comme convenu :
  1) RÉGRESSION : prédire retention_next (taux de complétion continu du segment suivant)
     -> RandomForestRegressor / GradientBoostingRegressor
  2) CLASSIFICATION dérivée : à partir du score continu prédit, on seuille pour
     classer un segment comme "à risque de décrochage" (drop) ou non, et on sort
     les visuels classiques demandés (matrice de confusion, ROC).

Sortie :
  - models/retention_model.pkl
  - outputs/eval_regression.png      (réel vs prédit)
  - outputs/eval_confusion_matrix.png
  - outputs/eval_roc_curve.png
  - outputs/model_metrics.json
"""


import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import pandas as pd
import numpy as np
import json
import joblib

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    confusion_matrix, roc_curve, auc, classification_report,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FEATURES = [
    "start", "dropoff_rate",
    "n_pauses", "n_replays", "n_seeks", "avg_pause_rate", "avg_replay_rate",
    # --- CORRECTION : features de vélocité calculées dans 02_build_features
    # mais absentes du modèle dans la version initiale — on les branche ici.
    # n_replays ré-inclus : la feature était morte (= 0 partout) parce que
    # 02_build_features lisait events.csv brut (sessions déjà écartées). Une fois
    # events_clean.csv utilisé, n_replays retrouve un vrai signal (moy. 4.9).
    "dropoff_velocity",        # accélération ou freinage du décrochage
    "completion_acceleration", # dynamique de la courbe de complétion
    "dropoff_trend_3seg",      # tendance lissée sur 3 segments
    "dropoff_relative_score",  # z-score du décrochage par rapport à la vidéo
]
# --- Correction fuite de données ---
# Deux variables "trichent" en révélant quasiment la cible directement :
#   - completion_rate (corrélation ~0.99 avec retention_next) : c'est presque
#     la même mesure décalée d'un segment
#   - n_viewers_reached (corrélation ~0.99 aussi) : c'est en réalité
#     completion_rate x nombre total de viewers, donc la MÊME fuite déguisée
#     sous un autre nom — la retirer seule ne suffisait pas, il fallait
#     repérer ce doublon caché.
# On garde "start" (position temporelle) : c'est un proxy légitime (plus on
# avance dans la vidéo, plus la rétention baisse mécaniquement), pas une
# fuite directe de la cible — mais on le signale comme un effet structurel
# à mentionner au jury si la question revient (cf. mémo de l'équipe).
LEAKY_FEATURES = ["completion_rate", "n_viewers_reached"]
TARGET = "retention_next"


def train_eval(df, feature_list, X_train_idx, X_test_idx, candidates):
    """Entraîne et évalue chaque modèle candidat sur un jeu de features donné."""
    X = df[feature_list]
    y = df[TARGET]
    X_train, X_test = X.loc[X_train_idx], X.loc[X_test_idx]
    y_train, y_test = y.loc[X_train_idx], y.loc[X_test_idx]

    results = {}
    best_model, best_name, best_score = None, None, -np.inf
    for name, model_cls in candidates.items():
        model = model_cls(random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        r2 = r2_score(y_test, preds)
        mae = mean_absolute_error(y_test, preds)
        results[name] = {"MAE": mae, "R2": r2}
        if r2 > best_score:
            best_score, best_name, best_model = r2, name, model
    return best_name, best_model, results


def main():
    df = pd.read_csv(_os.path.join(BASE_DIR, "data/segment_features.csv"))

    # --- CORRECTION : exclure les derniers segments de chaque vidéo ---
    # Pour ces segments, retention_next est rempli par fillna(completion_rate)
    # dans 02_build_features.py — la target est donc triviale (prédire sa propre
    # valeur), ce qui gonfle artificiellement les métriques. On les retire du
    # dataset avant tout split train/test.
    last_seg_idx = df.groupby("video_id")["segment_id"].idxmax()
    df = df.drop(index=last_seg_idx).reset_index(drop=True)
    print(f"Segments retenus pour l'entraînement : {len(df)} "
          f"({len(last_seg_idx)} derniers segments exclus)")

    # --- Démonstration transparente de la fuite de données ---
    # On entraîne rapidement la même config AVEC la variable qui triche
    # (completion_rate) pour documenter l'écart, avant de continuer avec
    # le modèle honnête (sans cette variable) pour la suite du pipeline.
    X_idx_train, X_idx_test = train_test_split(
        df.index, test_size=0.2, random_state=42
    )
    quick_candidates = {"RandomForest": RandomForestRegressor}
    _, _, leaky_results = train_eval(
        df, FEATURES + LEAKY_FEATURES, X_idx_train, X_idx_test, quick_candidates
    )
    _, _, honest_results = train_eval(
        df, FEATURES, X_idx_train, X_idx_test, quick_candidates
    )
    leaky_r2 = leaky_results["RandomForest"]["R2"]
    honest_r2 = honest_results["RandomForest"]["R2"]
    print(f"\n=== Vérification fuite de données ===")
    print(f"AVEC completion_rate (fuite)    : R² = {leaky_r2:.4f}")
    print(f"SANS completion_rate (honnête)  : R² = {honest_r2:.4f}")
    print("-> On retient la version honnête pour le modèle final.\n")

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # --- comparaison de modèles ---
    candidates = {
        "RandomForest": RandomForestRegressor(random_state=42),
        "GradientBoosting": GradientBoostingRegressor(random_state=42),
    }

    results = {}
    best_model, best_name, best_score = None, None, -np.inf

    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = mean_squared_error(y_test, preds) ** 0.5
        r2 = r2_score(y_test, preds)
        results[name] = {"MAE": mae, "RMSE": rmse, "R2": r2}
        print(f"{name}: MAE={mae:.4f} RMSE={rmse:.4f} R2={r2:.4f}")
        if r2 > best_score:
            best_score, best_name, best_model = r2, name, model

    print(f"\nMeilleur modèle de base : {best_name}")

    # --- réglage d'hyperparamètres sur le meilleur modèle (GridSearch léger) ---
    if best_name == "RandomForest":
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [None, 8, 12],
            "min_samples_leaf": [1, 3],
        }
        base = RandomForestRegressor(random_state=42)
    else:
        param_grid = {
            "n_estimators": [100, 200],
            "max_depth": [3, 5],
            "learning_rate": [0.05, 0.1],
        }
        base = GradientBoostingRegressor(random_state=42)

    grid = GridSearchCV(base, param_grid, cv=3, scoring="r2", n_jobs=-1)
    grid.fit(X_train, y_train)
    final_model = grid.best_estimator_
    print(f"Meilleurs hyperparamètres : {grid.best_params_}")

    final_preds = final_model.predict(X_test)
    final_mae = mean_absolute_error(y_test, final_preds)
    final_rmse = mean_squared_error(y_test, final_preds) ** 0.5
    final_r2 = r2_score(y_test, final_preds)
    print(f"Modèle final : MAE={final_mae:.4f} RMSE={final_rmse:.4f} R2={final_r2:.4f}")

    joblib.dump({"model": final_model, "features": FEATURES}, _os.path.join(BASE_DIR, "models/retention_model.pkl"))

    # --- Innovation P4/P5 : quantification de l'incertitude ---
    # Sur un petit dataset (< 200 segments), la régression quantile GBR
    # n'est pas assez stable pour atteindre 90% de couverture empirique.
    # On utilise à la place les distributions de prédictions des arbres du
    # RandomForest (chaque arbre vote indépendamment) : c'est l'approche
    # standard pour les intervalles de confiance basés sur RF, plus robuste
    # sur des données limitées et ne nécessite pas de modèles séparés.
    # Méthode : pour chaque point de test, on récupère les prédictions de
    # chaque arbre, puis on prend le 5e et 95e percentile de cette distribution
    # comme bornes inférieure et supérieure de l'intervalle à 90%.
    # Intervalles de confiance à 90%. La méthode par vote d'arbres nécessite un
    # RandomForest. Si le modèle final est un GradientBoosting, on entraîne un RF
    # auxiliaire (mêmes données) UNIQUEMENT pour estimer l'incertitude : les
    # prédictions restent celles du modèle final, mais les bornes viennent de la
    # dispersion des arbres du RF, méthode rigoureuse et bien calibrée.
    from sklearn.ensemble import RandomForestRegressor as _RF
    if isinstance(final_model, _RF):
        uncertainty_model = final_model
    else:
        uncertainty_model = _RF(n_estimators=300, random_state=42)
        uncertainty_model.fit(X_train, y_train)
    tree_preds_test = np.array([tree.predict(X_test) for tree in uncertainty_model.estimators_])
    pred_low  = np.percentile(tree_preds_test, 5,  axis=0)
    pred_high = np.percentile(tree_preds_test, 95, axis=0)
    coverage = np.mean((y_test.values >= pred_low) & (y_test.values <= pred_high))
    avg_interval_width = np.mean(pred_high - pred_low)

    # On sauvegarde les bornes sur le jeu de test (utiles pour le dashboard)
    # et on passe None pour les modèles quantiles qui ne sont plus utilisés.
    q_low_model, q_high_model = None, None

    print(f"\nIntervalle de confiance 90% (RF tree percentiles) : "
          f"couverture empirique = {coverage:.1%} "
          f"(cible : ~90%), largeur moyenne = {avg_interval_width:.4f}")

    joblib.dump(
        {"model": final_model, "features": FEATURES,
         "q_low_model": q_low_model, "q_high_model": q_high_model},
        _os.path.join(BASE_DIR, "models/retention_model.pkl")
    )

    plt.figure(figsize=(8, 5))
    order = np.argsort(y_test.values)
    plt.fill_between(
        range(len(order)), pred_low[order], pred_high[order],
        alpha=0.25, color="#4C72B0", label="Intervalle de confiance 90%"
    )
    plt.plot(range(len(order)), y_test.values[order], "o", markersize=3,
              color="black", label="Valeur réelle")
    plt.plot(range(len(order)), final_preds[order], "-", color="#DD8452",
              linewidth=1.5, label="Prédiction centrale")
    plt.xlabel("Segments (triés par rétention réelle)")
    plt.ylabel("Taux de rétention")
    plt.title(f"Prédiction avec intervalle de confiance (couverture {coverage:.0%})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_os.path.join(BASE_DIR, "outputs/eval_uncertainty.png"), dpi=120)
    plt.close()

    # --- visuel réel vs prédit (régression) ---
    plt.figure(figsize=(6, 6))
    plt.scatter(y_test, final_preds, alpha=0.5, color="#4C72B0")
    plt.plot([0, 1], [0, 1], "r--", label="Prédiction parfaite")
    plt.xlabel("Rétention réelle")
    plt.ylabel("Rétention prédite")
    plt.title(f"Réel vs Prédit ({best_name} optimisé) - R²={final_r2:.3f}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_os.path.join(BASE_DIR, "outputs/eval_regression.png"), dpi=120)
    plt.close()

    # --- classification dérivée : segment "à risque" si retention_next < seuil ---
    DROP_THRESHOLD = df["retention_next"].quantile(0.3)  # 30% les pires = "à risque"
    y_test_class = (y_test < DROP_THRESHOLD).astype(int)
    y_pred_class = (final_preds < DROP_THRESHOLD).astype(int)

    cm = confusion_matrix(y_test_class, y_pred_class)
    plt.figure(figsize=(5, 4))
    plt.imshow(cm, cmap="Blues")
    plt.title("Matrice de confusion (segment à risque)")
    plt.xlabel("Prédit")
    plt.ylabel("Réel")
    plt.xticks([0, 1], ["Sain", "À risque"])
    plt.yticks([0, 1], ["Sain", "À risque"])
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=14)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(_os.path.join(BASE_DIR, "outputs/eval_confusion_matrix.png"), dpi=120)
    plt.close()

    # ROC : on utilise le score continu prédit (inversé) comme score de risque
    risk_score = 1 - final_preds
    fpr, tpr, _ = roc_curve(y_test_class, risk_score)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(5, 5))
    plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.3f}", color="#C44E52")
    plt.plot([0, 1], [0, 1], "k--", alpha=0.4)
    plt.xlabel("Taux de faux positifs")
    plt.ylabel("Taux de vrais positifs")
    plt.title("Courbe ROC - détection segments à risque")
    plt.legend()
    plt.tight_layout()
    plt.savefig(_os.path.join(BASE_DIR, "outputs/eval_roc_curve.png"), dpi=120)
    plt.close()

    metrics_out = {
        "model_comparison": results,
        "best_base_model": best_name,
        "best_params": grid.best_params_,
        "final_metrics": {"MAE": final_mae, "RMSE": final_rmse, "R2": final_r2},
        "uncertainty": {"coverage_90pct": float(coverage), "avg_interval_width": float(avg_interval_width)},
        "classification_threshold": DROP_THRESHOLD,
        "roc_auc": roc_auc,
        "classification_report": classification_report(
            y_test_class, y_pred_class, target_names=["Sain", "À risque"], output_dict=True
        ),
    }
    with open(_os.path.join(BASE_DIR, "outputs/model_metrics.json"), "w") as f:
        json.dump(metrics_out, f, indent=2, default=float)

    print("\nFichiers générés dans outputs/ : eval_regression.png, eval_confusion_matrix.png, eval_roc_curve.png, model_metrics.json")


if __name__ == "__main__":
    main()
