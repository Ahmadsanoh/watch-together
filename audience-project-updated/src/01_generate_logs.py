"""
P1 (VERSION UNIFIEE) — Genere la dataset SALE de Rachida (30 videos),
la NETTOIE, puis l'ADAPTE au format attendu par le reste du pipeline.

Ce script remplace l'ancien generateur (qui produisait des donnees deja
propres). Il met en valeur le vrai travail de donnees :
  1) generation de logs realistes AVEC defauts (casse, doublons, NaN, dates
     melangees, valeurs corrompues) ;
  2) nettoyage complet documente ;
  3) adaptation au schema du pipeline (event_type, colonnes, ids).
"""
import os as _os
BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)
N_VIDEOS = 30
N_SESSIONS = 12000
COMPLETION_THRESHOLD = 0.80
DATA = _os.path.join(BASE_DIR, "data")
_os.makedirs(DATA, exist_ok=True)

# 1) CATALOGUE + zones d'ennui cachees
videos, ground_truth = [], []
for vid in range(1, N_VIDEOS + 1):
    duration = int(rng.integers(180, 900))
    bz = float(rng.uniform(0.25, 0.80))
    bs = float(rng.uniform(0.4, 1.0))
    videos.append({"video_id": f"v{vid}", "duration_sec": duration, "title": f"Video {vid}"})
    center = bz * duration
    ground_truth.append({"video_id": f"v{vid}", "start": int(max(0, center-20)),
                         "end": int(min(duration, center+20)), "_zf": bz, "_st": bs})
videos_df = pd.DataFrame(videos)
gt_df = pd.DataFrame(ground_truth)

# 2) EVENEMENTS realistes
rows = []
base_time = datetime(2025,1,1,8,0,0)
devices = ["mobile","desktop","tablet","tv"]
for session_id in range(1, N_SESSIONS+1):
    gi = int(rng.integers(0, N_VIDEOS))
    vrow, grow = videos_df.iloc[gi], gt_df.iloc[gi]
    video_id = vrow["video_id"]; duration = int(vrow["duration_sec"])
    boredom_pos = grow["_zf"]*duration; strength = grow["_st"]
    user_id = int(rng.integers(1,4000))
    device = rng.choice(devices, p=[0.5,0.3,0.15,0.05])
    session_start = base_time + timedelta(minutes=int(rng.integers(0,60*24*45)))
    r = rng.random()
    if r < 0.22: wf = rng.uniform(0.01,0.15)
    elif r < 0.22+0.35*strength: wf = np.clip(rng.normal(grow["_zf"],0.05),0.05,0.95)
    elif r < 0.85: wf = rng.uniform(0.80,1.0)
    else: wf = rng.uniform(0.15,0.80)
    watched = float(np.clip(wf,0,1)*duration)
    sid = f"s{session_id:06d}"
    rows.append([user_id,video_id,sid,"play",0.0,session_start,device])
    for _ in range(int(rng.poisson(1.5+2.0*strength))):
        if rng.random()<0.6: pos=float(np.clip(rng.normal(boredom_pos,duration*0.05),0,watched))
        else: pos=float(rng.uniform(0,watched)) if watched>0 else 0.0
        if pos<=watched: rows.append([user_id,video_id,sid,"pause",round(pos,1),session_start+timedelta(seconds=pos),device])
    for _ in range(int(rng.poisson(1.0+1.5*strength))):
        pos=float(rng.uniform(0,watched)) if watched>0 else 0.0
        rows.append([user_id,video_id,sid,"seek",round(pos,1),session_start+timedelta(seconds=pos),device])
    for _ in range(int(rng.poisson(0.6))):
        pos=float(rng.uniform(0,watched)) if watched>0 else 0.0
        rows.append([user_id,video_id,sid,"replay",round(pos,1),session_start+timedelta(seconds=pos),device])
    et = "complete" if watched>=COMPLETION_THRESHOLD*duration else "abandon"
    rows.append([user_id,video_id,sid,et,round(watched,1),session_start+timedelta(seconds=watched),device])

events = pd.DataFrame(rows, columns=["user_id","video_id","session_id","event_type","position_sec","timestamp","device"])
events = events.sort_values(["session_id","timestamp"]).reset_index(drop=True)

# 3) SALISSAGE
events["timestamp"]=events["timestamp"].astype(str)
n=len(events)
def mc(x):
    r=rng.random()
    if r<0.15: return x.upper()
    if r<0.30: return x.capitalize()
    if r<0.36 and x=="complete": return "completed"
    if r<0.40 and x=="abandon": return "abandoned"
    return x
events["event_type"]=events["event_type"].map(mc)
for col,frac in [("device",0.08),("position_sec",0.04),("user_id",0.01)]:
    idx=rng.choice(n,size=int(n*frac),replace=False); events.loc[idx,col]=np.nan
dup=rng.choice(n,size=int(n*0.03),replace=False); events=pd.concat([events,events.loc[dup]],ignore_index=True); n=len(events)
bad=rng.choice(n,size=int(n*0.01),replace=False); events.loc[bad,"position_sec"]=events.loc[bad,"position_sec"].astype(float)*rng.uniform(1.5,3.0)
neg=rng.choice(n,size=int(n*0.005),replace=False); events.loc[neg,"position_sec"]=-events.loc[neg,"position_sec"].astype(float).abs()
def sp(x):
    if isinstance(x,str) and rng.random()<0.05: return f"  {x} "
    return x
events["event_type"]=events["event_type"].map(sp)
def mts(ts):
    if not isinstance(ts,str): return ts
    r=rng.random()
    try: dt=pd.to_datetime(ts)
    except Exception: return ts
    if r<0.10: return dt.strftime("%d/%m/%Y %H:%M:%S")
    if r<0.18: return str(int(dt.timestamp()))
    if r<0.22: return ""
    return ts
events["timestamp"]=events["timestamp"].map(mts)
def mv(v):
    if rng.random()<0.03: return f"video_{v}"
    return v
events["video_id"]=events["video_id"].map(mv)
corrupt=pd.DataFrame({"user_id":["ERROR","null","#N/A"],"video_id":["?","","v-1"],
    "session_id":["s000000","","NA"],"event_type":["???","","unknown"],
    "position_sec":["abc","","NaN"],"timestamp":["not_a_date","","0000-00-00"],"device":["","???","robot"]})
events=pd.concat([events,corrupt],ignore_index=True)
events=events.sample(frac=1.0,random_state=RANDOM_SEED).reset_index(drop=True)
events.to_csv(_os.path.join(DATA,"events_raw.csv"),index=False)
n_raw=len(events)

# 4) NETTOYAGE
raw=pd.read_csv(_os.path.join(DATA,"events_raw.csv"),dtype=str)
report={}
raw["event_type"]=raw["event_type"].astype(str).str.strip().str.lower().replace({"completed":"complete","abandoned":"abandon"})
ve={"play","pause","seek","replay","complete","abandon"}
b=len(raw); raw=raw[raw["event_type"].isin(ve)]; report["event_type invalides"]=b-len(raw)
raw["video_id"]=raw["video_id"].astype(str).str.replace("video_","",regex=False).str.strip()
b=len(raw); raw=raw[raw["video_id"].str.match(r"^v\d+$")]; report["video_id invalides"]=b-len(raw)
raw["user_id"]=pd.to_numeric(raw["user_id"],errors="coerce")
raw["session_id"]=raw["session_id"].astype(str).str.strip()
b=len(raw); raw=raw.dropna(subset=["user_id"]); raw=raw[raw["session_id"].str.match(r"^s\d+$")]; report["user/session invalides"]=b-len(raw)
raw["position_sec"]=pd.to_numeric(raw["position_sec"],errors="coerce")
raw=raw.merge(videos_df[["video_id","duration_sec"]],on="video_id",how="left")
neg=(raw["position_sec"]<0).sum(); raw.loc[raw["position_sec"]<0,"position_sec"]=np.nan
over=(raw["position_sec"]>raw["duration_sec"]*1.05).sum(); raw.loc[raw["position_sec"]>raw["duration_sec"]*1.05,"position_sec"]=np.nan
raw.loc[(raw["position_sec"].isna())&(raw["event_type"]=="play"),"position_sec"]=0.0
report["positions negatives"]=int(neg); report["positions > duree"]=int(over)
def pts(x):
    if x is None or str(x).strip()=="" or str(x).lower()=="nan": return pd.NaT
    s=str(x).strip()
    if s.isdigit():
        try: return pd.to_datetime(int(s),unit="s")
        except Exception: return pd.NaT
    try: return pd.to_datetime(s,format="%d/%m/%Y %H:%M:%S")
    except Exception: pass
    try: return pd.to_datetime(s)
    except Exception: return pd.NaT
raw["timestamp"]=raw["timestamp"].map(pts)
b=len(raw); raw=raw.dropna(subset=["timestamp"]); report["timestamps invalides"]=b-len(raw)
raw["device"]=raw["device"].astype(str).str.strip().str.lower()
raw.loc[~raw["device"].isin({"mobile","desktop","tablet","tv"}),"device"]="unknown"
b=len(raw); raw=raw.drop_duplicates(); report["doublons"]=b-len(raw)
clean=raw.sort_values(["session_id","timestamp"]).reset_index(drop=True)
n_clean=len(clean)

# 5) ADAPTATION au format pipeline
adapted=clean.copy()
adapted["event_type"]=adapted["event_type"].replace({"complete":"exit","abandon":"exit"})
adapted=adapted.rename(columns={"position_sec":"timestamp_video","timestamp":"timestamp_wall"})
adapted["user_id"]="u"+adapted["user_id"].astype(int).astype(str)+"_"+adapted["video_id"]
adapted=adapted[["user_id","video_id","session_id","event_type","timestamp_video","timestamp_wall"]]
adapted.to_csv(_os.path.join(DATA,"events.csv"),index=False)
videos_df.to_csv(_os.path.join(DATA,"videos.csv"),index=False)
gt_df[["video_id","start","end"]].to_csv(_os.path.join(DATA,"ground_truth_bored_zones.csv"),index=False)
pd.DataFrame([{"etape":k,"lignes":v} for k,v in report.items()]).to_csv(_os.path.join(DATA,"cleaning_report.csv"),index=False)

print("="*60)
print("P1 — DATASET SALE -> NETTOYEE -> ADAPTEE (30 videos)")
print("="*60)
print(f"Lignes brutes (sales)  : {n_raw:,}")
print(f"Lignes apres nettoyage : {n_clean:,}  (retirees: {n_raw-n_clean:,})")
print("\nRapport de nettoyage :")
for k,v in report.items(): print(f"   - {k:<28}: {v:,}")
print(f"\nVideos: {videos_df.shape[0]} | Sessions: {clean['session_id'].nunique():,} | Evenements: {len(adapted):,}")
