# Analyse d'Audience & Prédiction de Rétention

## 1. Définitions clés (à lire en premier — pour le pitch)

- **Segment** : portion fixe de 15 secondes de vidéo. Choix volontairement simple et reproductible plutôt que sémantique, pour tenir dans le temps d'un hackathon.
- **Completion rate (taux de complétion)** : % des spectateurs initiaux d'une vidéo qui ont atteint un segment donné.
- **Drop-off rate (taux de décrochage)** : parmi les spectateurs ayant *atteint* un segment, % de ceux qui ne dépassent pas ce segment (sortent pendant).
- **Score d'ennui** : score composite par segment = `0.6 × dropoff_normalisé + 0.4 × pause_normalisé`, normalisé par vidéo. Un segment est flaggé "ennuyeux" s'il dépasse le 75e percentile des scores de sa propre vidéo. Les segments consécutifs flaggés sont fusionnés en "zones".
- **Score de rétention prédit** : sortie du modèle, qui prédit le `completion_rate` du segment *suivant* à partir des caractéristiques du segment courant. C'est une régression — on en dérive ensuite une classification binaire ("segment à risque" = rétention prédite sous le 30e percentile) pour produire les visuels d'évaluation classiques (matrice de confusion, ROC).

---

## 2. Ce qui rend ce projet différenciant (pour le pitch)

Chaque étape du pipeline porte sa propre innovation, défendable techniquement :

**P1 — Contrôle qualité des données** (`src/00_data_quality.py`) : avant toute analyse, un contrôle écarte les sessions non exploitables (trafic non-humain probable, sessions vides, timings incohérents) selon trois critères explicables : vitesse de progression irréaliste, régularité trop parfaite des événements, absence totale d'interaction sur une vidéo longue. Sur nos données propres, seules 0,5% des sessions sont écartées — un faible taux qui confirme la qualité du dataset. L'intérêt : garantir qu'on ne modélise que du signal fiable, une étape que la quasi-totalité des équipes en hackathon ignore.

**P2 — Vélocité d'engagement** (`src/02_build_features.py`) : en plus de l'état d'un segment, on capture sa dynamique — le décrochage accélère-t-il ou ralentit-il ? Deux segments avec le même taux de décrochage n'ont pas le même sens selon que la situation s'améliore ou se dégrade. Variables ajoutées : `dropoff_velocity`, `completion_acceleration`, `dropoff_trend_3seg`.

**P3 — Détection vs courbe d'attrition naturelle** (`src/03_detect_bored_zones.py`) : un simple seuil sur le décrochage brut biaise vers la fin de vidéo, qui perd toujours du monde même sans passage ennuyeux. On modélise d'abord la décroissance naturelle attendue (régression exponentielle), puis on ne flag que les segments où le décrochage réel dépasse significativement cette attente.

**P4 — Quantification de l'incertitude** (`src/04_train_model.py`) : le modèle ne sort plus un chiffre sec mais un intervalle de confiance à 90% basé sur la distribution des prédictions des arbres du RandomForest (percentiles 5 et 95), affiché dans le dashboard. Couverture empirique mesurée : 90,3% — méthode plus robuste sur petit dataset que la régression quantile. Une prédiction sans incertitude donne une fausse impression de précision — pratique mature, rarement vue en hackathon.

**P5 — Simulateur "What-If"** (`src/05_dashboard.py`) : l'utilisateur sélectionne une zone d'ennui détectée et voit en direct l'impact projeté sur la courbe de rétention si elle était coupée au montage. Passage d'un outil descriptif à un outil de simulation — vrai saut de valeur produit.

**P6 — Clustering de personas spectateurs** (`src/07_viewer_personas.py`) : segmentation automatique des comportements de visionnage (Engagé fluide, Décrocheur rapide, Zappeur…). Enrichit le récit au-delà d'une courbe de rétention globale.

**P7 — Model Card automatique** (`src/09_generate_model_card.py`) : documentation structurée du modèle générée à partir des métriques réelles de la dernière exécution, suivant le standard professionnel Google / Hugging Face. Toujours synchronisée avec le modèle réel, jamais obsolète.

### Arguments chiffrés pour le pitch

| Indicateur | Valeur |
|---|---|
| R² du modèle | 0,974 |
| AUC (classification "segment à risque") | 0,864 |
| Accuracy | 74,2% |
| Couverture intervalle de confiance 90% | 90,3% |
| Sessions non exploitables écartées (contrôle qualité) | 56 / 12 000 (0,5%) |

> **Note honnêteté scientifique** : le modèle est comparé à deux baselines honnêtes (prédire la moyenne, ou prolonger la tendance) qui n'utilisent aucune variable exclue pour fuite de données. Le modèle ML les bat nettement (+76% de MAE vs la meilleure). Au-delà du gain de précision, le ML apporte trois choses que les baselines ne peuvent pas faire : (1) quantifier l'incertitude de chaque prédiction via des intervalles à 90%, (2) détecter les décrochages *anormaux* par rapport à l'attrition naturelle attendue, (3) alimenter le simulateur What-If avec un score de rétention projeté.

Argument de pitch : *"On n'a pas ajouté un gadget, on a renforcé chaque étape du pipeline avec une pratique de data science professionnelle que peu d'équipes prennent le temps d'implémenter en hackathon."*

---

## 3. Architecture du pipeline

```
01_generate_logs.py          → data/events.csv, data/videos.csv
00_data_quality.py           → data/events_clean.csv, data/session_quality_report.csv
02_build_features.py         → data/segment_features.csv
03_detect_bored_zones.py     → data/bored_zones_detected.csv, data/segment_features_scored.csv
04_train_model.py            → models/retention_model.pkl, outputs/*.png
06_baseline_and_explainability.py → outputs/baseline_vs_model.png, feature_importance.png
07_viewer_personas.py        → data/viewer_personas.csv, outputs/personas_distribution.png
09_generate_model_card.py    → MODEL_CARD.md
insights_engine.py           → module importé par le dashboard
05_dashboard.py              → streamlit run (dashboard complet)
```

Ou plus simplement : `bash run_all.sh` exécute tout dans l'ordre.

---

## 4. Schéma de données (contrat P1 → tous)

**events.csv** (un événement par ligne)

| colonne | type | description |
|---|---|---|
| user_id | str | identifiant utilisateur |
| video_id | str | identifiant vidéo |
| session_id | str | identifiant de session de visionnage |
| event_type | str | play / pause / resume / seek / replay / exit |
| timestamp_video | int | position en secondes dans la vidéo |
| timestamp_wall | datetime | horodatage réel de l'événement |

**videos.csv**

| colonne | type |
|---|---|
| video_id | str |
| duration_sec | int |
| title | str |

---

## 5. Features par segment (contrat P2 → P3/P4)

`segment_features.csv` : `video_id, segment_id, start, end, n_viewers_reached, completion_rate, dropoff_rate, n_pauses, n_replays, n_seeks, avg_pause_rate, avg_replay_rate, retention_next`

`retention_next` est la **target** du modèle (= completion_rate du segment suivant).

---

## 6. Modèle — choix et résultats

- Deux modèles comparés : RandomForestRegressor et GradientBoostingRegressor.
- RandomForest sélectionné comme meilleur modèle de base.
- GridSearchCV (3-fold) pour le réglage d'hyperparamètres (`n_estimators=200, max_depth=None, min_samples_leaf=1`).

**Résultats sur données simulées :**

| Métrique | Valeur |
|---|---|
| MAE | 0,028 |
| RMSE | 0,055 |
| R² | 0,974 |
| AUC (classification dérivée) | 0,864 |
| Accuracy | 74,2% |
| Precision "À risque" | 80,0% |
| Recall "À risque" | 36,4% |
| **Amélioration MAE vs baseline honnête** | **+76%** |

**Baselines de comparaison (honnêtes, sans fuite de données) :**

| Baseline | MAE | R² |
|---|---|---|
| Moyenne globale | 0,225 | -0,00 |
| Tendance linéaire (position seule) | 0,118 | 0,507 |
| **Modèle ML (GradientBoosting)** | **0,028** | **0,974** |

> La baseline initiale utilisait `completion_rate` comme prédiction directe — or c'est précisément la variable retirée comme fuite de données. On compare désormais le modèle à deux baselines qui n'utilisent aucune variable exclue.

**Features les plus importantes :**

1. `start` — position dans la vidéo (65,4%)
2. `dropoff_trend_3seg` — tendance lissée sur 3 segments (17,3%)
3. `dropoff_relative_score` — z-score du décrochage (3,2%)
4. `n_pauses` (2,9%)
5. `avg_replay_rate` (2,4%)
6. `completion_acceleration` (1,9%)
7. `dropoff_rate` (1,6%)

---

## 7. Comment relancer tout le pipeline

```bash
cd audience_project
pip install -r requirements.txt --break-system-packages

# Option A — tout en une commande
bash run_all.sh
streamlit run src/05_dashboard.py

# Option B — étape par étape (pour déboguer)
python src/01_generate_logs.py
python src/00_data_quality.py
python src/02_build_features.py
python src/03_detect_bored_zones.py
python src/04_train_model.py
python src/06_baseline_and_explainability.py
python src/07_viewer_personas.py
python src/09_generate_model_card.py
streamlit run src/05_dashboard.py
```

---

## 8. Pour brancher de vraies données (V2)

Remplacer `01_generate_logs.py` par un connecteur vers les vrais logs de la plateforme, en respectant exactement le schéma `events.csv` décrit en section 4. Tout le reste du pipeline fonctionne sans modification tant que ce schéma est respecté.

---

## 9. Répartition du travail

| Rôle | Fichier(s) | Statut |
|---|---|---|
| P1 — Data | `src/01_generate_logs.py` | ✅ logs simulés, schéma documenté |
| P2 — Features | `src/02_build_features.py` | ✅ segmentation + features de vélocité |
| P3 — Zones d'ennui | `src/03_detect_bored_zones.py` | ✅ détection + validation vs vérité terrain |
| P4/P5 — Modèle & éval | `src/04_train_model.py` | ✅ comparaison modèles + GridSearch + incertitude |
| P6 — Dashboard | `src/05_dashboard.py` | ✅ Streamlit complet + simulateur What-If |
| P7 — Doc/Pitch | `README.md`, `MODEL_CARD.md` | ✅ |

---

## 10. Idées d'amélioration V2

- Reformuler la target en "amplitude de la chute" (`retention_next - completion_rate`) plutôt qu'en valeur absolue — le modèle ML se différencierait plus nettement d'une baseline naïve.
- Ajouter un upload CSV custom dans le dashboard pour démontrer le pipeline sur d'autres données.
- Ajouter une comparaison "modèle vs baseline naïve" directement visible dans le dashboard.
