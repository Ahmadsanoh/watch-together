# Model Card — Modèle de Prédiction de Rétention Vidéo

*Généré automatiquement le 2026-07-01 à partir des métriques de la dernière exécution du pipeline.*

## 1. Vue d'ensemble

| | |
|---|---|
| **Tâche** | Régression — prédiction du taux de rétention du segment suivant d'une vidéo |
| **Algorithme** | Gradient Boosting Regressor (scikit-learn), optimisé par recherche d'hyperparamètres (GridSearchCV, 3-fold) |
| **Entrées** | 17 features par segment de 15 secondes (taux de complétion, décrochage, pauses, replays, vélocité d'engagement…) |
| **Sortie** | Taux de rétention prédit (0 à 1) + intervalle de confiance à 90% |

## 2. Données d'entraînement

- 30 vidéos, 1171 segments au total
- Logs de visionnage simulés (synthétiques), avec zones d'ennui injectées de façon contrôlée pour validation
- Schéma détaillé dans `README.md`, section 3

## 3. Qualité des données

Avant entraînement, un contrôle qualité écarte les sessions non exploitables
(trafic non-humain probable, sessions vides, timings incohérents) : 56 sessions
sur 12000 ont été écartées (0.47%), soit
99.53% de sessions fiables retenues. Le faible taux d'exclusion
confirme la bonne qualité des données. Détail des contrôles : {'anomalie_vitesse': 4, 'regularite_anormale': 2, 'sans_interaction_video_longue': 50}.


## 4. Performance

| Métrique | Valeur |
|---|---|
| MAE (erreur absolue moyenne) | 0.0278 |
| RMSE | 0.0415 |
| R² | 0.9740 |
| AUC (classification dérivée "segment à risque") | 0.987 |

**Comparaison à des baselines honnêtes** (prédire la moyenne, ou prolonger la
tendance) : le modèle réduit l'erreur (MAE) de **76.4%**
par rapport à la meilleure de ces baselines — c'est la preuve que le modèle
capture un signal réel et ne se contente pas de recopier une tendance triviale.

**Incertitude** : un intervalle de confiance à 90% est fourni pour chaque
prédiction (régression quantile). Couverture empirique mesurée sur le jeu
de test : 92.6% (cible : 90%).
Note de prudence : avec un jeu de test de petite taille, la calibration de
cet intervalle reste approximative et s'améliorerait avec davantage de
données réelles.

## 5. Variables les plus importantes

1. `dropoff_relative_score` (0.311)
2. `dropoff_trend_3seg` (0.275)
3. `start` (0.259)
4. `n_pauses` (0.065)
5. `n_seeks` (0.062)

## 6. Limites connues

- Les données d'entraînement sont **simulées**, pas issues d'une vraie plateforme. Les comportements modélisés (engagement, pauses, replays) sont plausibles mais pas calibrés sur des données réelles.
- Le R² élevé s'explique en partie par la nature cumulative de la cible (le taux de rétention d'un segment à l'autre varie peu mécaniquement) — la comparaison à la baseline (section 4) contextualise ce chiffre.
- Le jeu de données est de taille modeste (1171 segments) ce qui limite la robustesse statistique de la quantification d'incertitude.
- Le modèle n'a pas été testé sur des vidéos de genre ou de durée très différents de l'échantillon d'entraînement (généralisation non garantie hors distribution).

## 7. Usage prévu

Ce modèle est conçu comme un outil d'aide à la décision pour des équipes
éditoriales ou de production de contenu vidéo, afin d'identifier les
segments à risque de décrochage et prioriser les efforts de montage. Il
n'est pas conçu pour des décisions automatisées sans supervision humaine
(ex. suppression automatique de contenu).

## 8. Reproductibilité

```
bash run_all.sh
```
régénère l'intégralité des données, du modèle et de ce document à l'identique.
