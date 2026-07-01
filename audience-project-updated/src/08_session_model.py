"""
P4-bis — MODELE PAR SESSION (approche Rachida), sur la MEME dataset unifiee.
Reconstruit les features par session depuis data/events.csv (source commune),
entraine/compare 4 modeles, sauvegarde dans data/sessions/ pour le dashboard.

Cible : is_completed (1 = a regarde >= 80%, 0 = a abandonne).
On EXCLUT les variables qui trichent (watch_ratio, last_position, span) pour
un modele honnete, coherent avec le reste du projet.
"""
import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import numpy as np, pandas as pd, time, joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

DATA = _os.path.join(BASE_DIR, "data")
SESS = _os.path.join(DATA, "sessions")
_os.makedirs(SESS, exist_ok=True)
COMPLETION = 0.80

ev = pd.read_csv(_os.path.join(DATA, "events.csv"))
vids = pd.read_csv(_os.path.join(DATA, "videos.csv"))
ev = ev.merge(vids[["video_id","duration_sec"]], on="video_id", how="left")

# reconstruire par session
g = ev.groupby("session_id")
feat = pd.DataFrame(index=sorted(ev["session_id"].unique()))
feat.index.name = "session_id"
feat["video_id"] = g["video_id"].first()
feat["duration_sec"] = g["duration_sec"].first()
feat["last_position"] = g["timestamp_video"].max()
feat["watch_ratio"] = (feat["last_position"]/feat["duration_sec"]).clip(0,1)
ev_ct = ev.pivot_table(index="session_id", columns="event_type", values="timestamp_video", aggfunc="count", fill_value=0)
for c in ["pause","seek","play","replay"]:
    feat[f"n_{c}s" if c!="play" else "n_plays"] = ev_ct.get(c, 0)
feat["n_events"] = g.size()
wm = (feat["last_position"]/60).replace(0, np.nan)
feat["pauses_per_min"] = (feat["n_pauses"]/wm).fillna(0)
feat["seeks_per_min"] = (feat["n_seeks"]/wm).fillna(0)
# cible : exit avec >=80% = complete
feat["is_completed"] = (feat["watch_ratio"] >= COMPLETION).astype(int)
feat = feat.reset_index().replace([np.inf,-np.inf], np.nan).fillna(0)
feat.to_csv(_os.path.join(SESS, "sessions_features.csv"), index=False)

# modele honnete : exclure les variables qui trichent
DROP = ["session_id","video_id","is_completed","watch_ratio","last_position"]
feats = [c for c in feat.columns if c not in DROP]
X = feat[feats].copy(); y = feat["is_completed"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
sc = StandardScaler(); Xtr_s = sc.fit_transform(Xtr); Xte_s = sc.transform(Xte)

models = {
    "Regression logistique": (LogisticRegression(max_iter=1000, random_state=42), True),
    "Random Forest": (RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1), False),
    "Gradient Boosting": (GradientBoostingClassifier(random_state=42), False),
    "SVM (RBF)": (SVC(probability=True, random_state=42), True),
}
res = []
for name,(m,ns) in models.items():
    a,b = (Xtr_s,Xte_s) if ns else (Xtr,Xte)
    t=time.time(); m.fit(a,ytr); tt=time.time()-t
    p=m.predict(b); pr=m.predict_proba(b)[:,1]
    Xcv = sc.fit_transform(X) if ns else X
    cv = cross_val_score(m, Xcv, y, cv=5, scoring="f1", n_jobs=-1)
    res.append({"Modèle":name,"Accuracy":accuracy_score(yte,p),"Précision":precision_score(yte,p),
        "Rappel":recall_score(yte,p),"F1":f1_score(yte,p),"ROC-AUC":roc_auc_score(yte,pr),
        "CV-F1 (moy)":cv.mean(),"CV-F1 (std)":cv.std(),"Temps (s)":tt})
comp = pd.DataFrame(res).set_index("Modèle")
comp.round(4).to_csv(_os.path.join(SESS, "comparaison_4_modeles.csv"))
best_name = comp["CV-F1 (moy)"].idxmax()
bm, ns = models[best_name]
bm.fit(sc.fit_transform(Xtr) if ns else Xtr, ytr)
joblib.dump({"model":bm,"scaler":sc if ns else None,"needs_scaling":ns,
             "features":list(X.columns),"model_name":best_name},
            _os.path.join(SESS, "model_final.joblib"))
print("MODELE SESSION (dataset unifiee) — comparaison :")
print(comp.round(3).to_string())
print(f"\nMeilleur : {best_name} | F1={comp.loc[best_name,'F1']:.3f} | sessions={len(feat):,} | videos={feat['video_id'].nunique()}")
