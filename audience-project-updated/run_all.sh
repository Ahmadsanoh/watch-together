#!/bin/bash
# Relance l'intégralité du pipeline dans le bon ordre, puis propose de lancer le dashboard.
# Usage : bash run_all.sh

set -e
cd "$(dirname "$0")"

echo "=== 1/8 Génération des logs ==="
python src/01_generate_logs.py

echo -e "\n=== 2/8 Contrôle qualité des données (détection sessions suspectes) ==="
python src/00_data_quality.py

echo -e "\n=== 3/8 Construction des features par segment (+ vélocité d'engagement) ==="
python src/02_build_features.py

echo -e "\n=== 4/8 Détection des zones d'ennui (vs courbe d'attrition naturelle) ==="
python src/03_detect_bored_zones.py

echo -e "\n=== 5/8 Entraînement, évaluation et incertitude du modèle ==="
python src/04_train_model.py

echo -e "\n=== 6/8 Baseline & explicabilité ==="
python src/06_baseline_and_explainability.py

echo -e "\n=== 7/9 Personas de spectateurs ==="
python src/07_viewer_personas.py

echo -e "\n=== 8/9 Modèle par session (approche complémentaire, même dataset) ==="
python src/08_session_model.py

echo -e "\n=== 9/9 Génération de la Model Card ==="
python src/09_generate_model_card.py

echo -e "\n✅ Pipeline terminé. Pour lancer le dashboard :"
echo "   streamlit run src/05_dashboard.py"
