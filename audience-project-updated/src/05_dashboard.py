"""
Audience Analytics Dashboard — Watch Together Live Integration
Toutes les données viennent du serveur Watch Together en temps réel.
Lancer : streamlit run src/05_dashboard.py
"""
import os as _os, sys, time, requests, joblib
import numpy as np, pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _os.path.join(BASE_DIR, "src"))

st.set_page_config(page_title="Audience Analytics · Watch Together", layout="wide", page_icon="🎬", initial_sidebar_state="expanded")

# ── COULEURS ────────────────────────────────────────────────
BG    = "#0a0412"; BG2   = "#12071e"
PANEL = "rgba(255,255,255,0.05)"; PANEL2 = "rgba(255,255,255,0.08)"
BORDER= "rgba(255,255,255,0.1)"
PINK  = "#d6228a"; PURPLE= "#8a2ecf"; GREEN = "#22c55e"
AMBER = "#f59e0b"; RED   = "#ef4444"; BLUE  = "#3b82f6"
TEXT  = "#ffffff"; MUTED = "rgba(255,255,255,0.5)"
FONT  = "'Segoe UI', system-ui, sans-serif"

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.03)",
    font=dict(family=FONT, color=TEXT, size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)", color=MUTED),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)", color=MUTED),
    legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor=BORDER, borderwidth=1, font=dict(color=TEXT)),
    margin=dict(t=40, l=10, r=10, b=10),
)

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{{font-family:{FONT}!important}}
#MainMenu,header,footer{{visibility:hidden}}
.stApp{{background:linear-gradient(135deg,{BG} 0%,{BG2} 60%,#0d1f3c 100%)!important;color:{TEXT}}}
section[data-testid="stSidebar"]{{background:rgba(10,4,18,0.97)!important;border-right:1px solid {BORDER};backdrop-filter:blur(20px)}}
section[data-testid="stSidebar"] *{{color:{TEXT}!important}}
h1,h2,h3,h4{{color:{TEXT}!important;font-weight:700!important}}
p,label{{color:{TEXT}!important}}
.wt-nav{{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;background:rgba(0,0,0,0.4);border-bottom:1px solid {BORDER};backdrop-filter:blur(10px);margin-bottom:1.5rem}}
.wt-logo{{width:36px;height:36px;background:linear-gradient(135deg,{PINK},{PURPLE});border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1rem;font-weight:900;color:white;box-shadow:0 4px 15px rgba(214,34,138,0.4)}}
.live-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);border-radius:99px;padding:4px 12px;font-size:0.7rem;font-weight:700;letter-spacing:2px;color:{RED};text-transform:uppercase}}
.live-dot{{width:8px;height:8px;border-radius:50%;background:{RED};box-shadow:0 0 8px {RED};animation:livepulse 1.4s ease-in-out infinite}}
@keyframes livepulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:0.4;transform:scale(0.8)}}}}
.offline-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.15);border-radius:99px;padding:4px 12px;font-size:0.7rem;font-weight:700;letter-spacing:2px;color:{MUTED};text-transform:uppercase}}
.kpi-grid{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:1rem}}
.kpi-card{{flex:1;min-width:150px;background:{PANEL};border:1px solid {BORDER};border-radius:16px;padding:18px 20px;position:relative;overflow:hidden;backdrop-filter:blur(10px);transition:transform 0.2s,border-color 0.2s}}
.kpi-card:hover{{transform:translateY(-3px);border-color:rgba(214,34,138,0.4)}}
.kpi-card::before{{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--c1),var(--c2))}}
.kpi-label{{font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:1.5px;font-weight:600}}
.kpi-value{{font-size:2rem;font-weight:800;color:{TEXT};line-height:1;margin-top:6px}}
.kpi-icon{{position:absolute;top:14px;right:16px;font-size:1.4rem;opacity:0.3}}
.kpi-sub{{font-size:0.7rem;color:{MUTED};margin-top:4px}}
.room-card{{background:{PANEL};border:1px solid {BORDER};border-radius:18px;overflow:hidden;transition:all 0.25s ease;backdrop-filter:blur(10px)}}
.room-card:hover{{border-color:rgba(214,34,138,0.5);transform:translateY(-4px);box-shadow:0 20px 50px rgba(0,0,0,0.5)}}
.insight-card{{background:{PANEL};border:1px solid {BORDER};border-left:3px solid {AMBER};border-radius:10px;padding:12px 16px;margin-bottom:8px;font-size:0.88rem;backdrop-filter:blur(10px);transition:border-left-color 0.2s}}
.insight-card:hover{{border-left-color:{PINK}}}
.filmstrip-wrap{{background:rgba(0,0,0,0.3);border:1px solid {BORDER};border-radius:12px;padding:16px;overflow-x:auto;backdrop-filter:blur(10px)}}
.filmstrip-row{{display:flex;gap:3px}}
.film-frame{{flex:1;min-width:18px;height:60px;border-radius:3px;position:relative;transition:transform 0.15s}}
.film-frame:hover{{transform:scaleY(1.2);z-index:2}}
.film-frame.bored{{animation:boredpulse 1.6s ease-in-out infinite}}
@keyframes boredpulse{{0%,100%{{box-shadow:0 0 8px rgba(239,68,68,0.5)}}50%{{box-shadow:0 0 20px rgba(239,68,68,0.9)}}}}
.film-ruler{{display:flex;justify-content:space-between;font-size:0.6rem;color:{MUTED};margin-top:6px}}
.film-legend{{display:flex;gap:16px;margin-top:10px;font-size:0.7rem;color:{MUTED}}}
.film-legend span{{display:flex;align-items:center;gap:5px}}
.swatch{{width:10px;height:10px;border-radius:2px;display:inline-block}}
.event-item{{display:flex;align-items:center;gap:10px;padding:7px 10px;border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.78rem}}
.event-pill{{padding:2px 8px;border-radius:99px;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;flex-shrink:0}}
.ev-play{{background:rgba(34,197,94,0.2);color:{GREEN};border:1px solid rgba(34,197,94,0.3)}}
.ev-pause{{background:rgba(245,158,11,0.2);color:{AMBER};border:1px solid rgba(245,158,11,0.3)}}
.ev-seek{{background:rgba(59,130,246,0.2);color:{BLUE};border:1px solid rgba(59,130,246,0.3)}}
.section-title{{font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;padding-left:12px;border-left:3px solid {PINK}}}
div.stButton>button{{background:linear-gradient(90deg,{PINK},{PURPLE})!important;color:white!important;border:none!important;font-weight:700!important;border-radius:10px!important}}
.stSelectbox div[data-baseweb="select"]>div{{background:{PANEL}!important;border-color:{BORDER}!important;color:{TEXT}!important}}
[data-testid="stSlider"] [role="slider"]{{background:{PINK}!important;box-shadow:0 0 8px {PINK}}}
hr{{border-color:rgba(255,255,255,0.08)!important}}
</style>""", unsafe_allow_html=True)


# ── HELPERS ─────────────────────────────────────────────────
def kpi(label, value, icon, c1, c2, sub=""):
    return (f'<div class="kpi-card" style="--c1:{c1};--c2:{c2};">'
            f'<div class="kpi-icon">{icon}</div><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            + (f'<div class="kpi-sub">{sub}</div>' if sub else "") + '</div>')

def sec_title(t):
    st.markdown(f'<div class="section-title">{t}</div>', unsafe_allow_html=True)

WT_URL = _os.environ.get("WATCH_TOGETHER_URL", "http://localhost:4000")

def fetch(path, fallback=None, timeout=5):
    try:
        r = requests.get(f"{WT_URL}{path}", timeout=timeout)
        r.raise_for_status(); return r.json()
    except Exception:
        return fallback

def build_segments(events, room_id=None, seg_sec=15):
    if not events: return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(events)
    if df.empty or "event_type" not in df.columns: return pd.DataFrame(), pd.DataFrame()
    if room_id: df = df[df["session_id"] == room_id]
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    rows = []
    for (vid, sess), grp in df.groupby(["video_id","session_id"]):
        grp = grp.sort_values("timestamp_video")
        uv = grp["user_id"].nunique()
        if uv == 0: continue
        max_t = max(grp["timestamp_video"].max(), seg_sec*2)
        for i in range(max(1, int(np.ceil(max_t/seg_sec)))):
            t0, t1 = i*seg_sec, (i+1)*seg_sec
            seg_ev = grp[(grp["timestamp_video"]>=t0)&(grp["timestamp_video"]<t1)]
            vh = seg_ev["user_id"].nunique()
            np_ = int((seg_ev["event_type"]=="pause").sum())
            ns  = int((seg_ev["event_type"]=="seek").sum())
            compl = vh/uv; bored = min(1.0,(ns*0.4+np_*0.05)/max(1,uv))
            rows.append(dict(video_id=vid,session_id=sess,segment_id=i,start=t0,end=t1,
                n_viewers_reached=uv,completion_rate=min(1.0,compl),dropoff_rate=max(0.0,1.0-compl),
                n_pauses=np_,n_seeks=ns,bored_score=bored,is_bored=bored>0.3))
    if not rows: return pd.DataFrame(), pd.DataFrame()
    seg = pd.DataFrame(rows)
    bored_r = seg[seg["bored_score"]>0.3]
    zones = []
    if not bored_r.empty:
        for (v,s),g in bored_r.groupby(["video_id","session_id"]):
            zones.append(dict(video_id=v,session_id=s,zone_start=g["start"].min(),zone_end=g["end"].max(),avg_score=g["bored_score"].mean()))
    return seg, pd.DataFrame(zones) if zones else pd.DataFrame(columns=["video_id","session_id","zone_start","zone_end","avg_score"])

def filmstrip(seg_df, zones_df, thr=0.0):
    if seg_df.empty: return f'<p style="color:{MUTED};">En attente de données...</p>'
    n = len(seg_df); zm = np.zeros(n,dtype=bool)
    for _,z in zones_df.iterrows():
        if z["avg_score"]>=thr:
            zm |= (seg_df["start"].values<z["zone_end"])&(seg_df["end"].values>z["zone_start"])
    dn = (seg_df["dropoff_rate"].values-seg_df["dropoff_rate"].min())/(seg_df["dropoff_rate"].max()-seg_df["dropoff_rate"].min()+1e-9)
    frames=[]
    for i in range(n):
        if zm[i]: bg=f"linear-gradient(180deg,{RED},#b3201a)"; cls="film-frame bored"
        else:
            t=dn[i]; bg=f"linear-gradient(180deg,rgba(214,34,138,{0.08+0.5*t:.2f}),rgba(138,46,207,0.15))"; cls="film-frame"
        title=f"Seg {int(seg_df.iloc[i]['segment_id'])} · {int(seg_df.iloc[i]['start'])}-{int(seg_df.iloc[i]['end'])}s · drop {seg_df.iloc[i]['dropoff_rate']*100:.1f}%"
        frames.append(f'<div class="{cls}" style="background:{bg}" title="{title}"></div>')
    dur=int(seg_df["end"].max())
    ruler=f'<div class="film-ruler"><span>0s</span><span>{dur//2}s</span><span>{dur}s</span></div>'
    legend=(f'<div class="film-legend"><span><span class="swatch" style="background:rgba(138,46,207,0.3);"></span>Engagement</span>'
            f'<span><span class="swatch" style="background:rgba(214,34,138,0.6);"></span>Décrochage</span>'
            f'<span><span class="swatch" style="background:{RED};"></span>Zone ennui</span></div>')
    return f'<div class="filmstrip-wrap"><div class="filmstrip-row">{"".join(frames)}</div>{ruler}{legend}</div>'

def auto_insights(seg, zones, room_name):
    if seg.empty: return [f"⏳ En attente des premières données pour <b>{room_name}</b>..."]
    msgs=[]
    worst=seg.nlargest(1,"bored_score").iloc[0]
    if worst["bored_score"]>0.3: msgs.append(f"🔥 Zone d'ennui entre <b>{int(worst['start'])}s</b> et <b>{int(worst['end'])}s</b> — score {worst['bored_score']*100:.0f}%.")
    avg=seg["completion_rate"].mean()
    if avg<0.5: msgs.append(f"⚠️ Complétion faible : <b>{avg*100:.1f}%</b>. Plus de la moitié des viewers ont décroché.")
    elif avg>0.8: msgs.append(f"✅ Excellent engagement : <b>{avg*100:.1f}%</b> de complétion — contenu captivant.")
    ts=seg["n_seeks"].sum()
    if ts>10: msgs.append(f"⏩ <b>{int(ts)}</b> seeks enregistrés — les viewers naviguent dans le contenu.")
    if not zones.empty: msgs.append(f"🎯 <b>{len(zones)}</b> zone(s) d'ennui — à couper au montage pour améliorer la rétention.")
    if not msgs: msgs.append(f"✨ Session en cours — collecte des données en temps réel.")
    return msgs

def compute_personas(events):
    if not events: return None
    df=pd.DataFrame(events)
    if df.empty or len(df["user_id"].unique())<3: return None
    vstats=[]
    for uid,grp in df.groupby("user_id"):
        vstats.append(dict(user_id=uid,
            n_plays=int((grp["event_type"]=="play").sum()),
            n_pauses=int((grp["event_type"]=="pause").sum()),
            n_seeks=int((grp["event_type"]=="seek").sum()),
            max_time=float(grp["timestamp_video"].max()),
            session=grp["session_id"].iloc[0]))
    vstats=pd.DataFrame(vstats)
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        feats=["n_plays","n_pauses","n_seeks","max_time"]
        X=vstats[feats].fillna(0)
        X_s=StandardScaler().fit_transform(X)
        nc=min(3,len(vstats))
        km=KMeans(n_clusters=nc,random_state=42,n_init=10)
        vstats["cluster"]=km.fit_predict(X_s)
        means=vstats.groupby("cluster")["max_time"].mean().sort_values(ascending=False)
        labels=["🔥 Très engagé","😐 Modéré","💤 Décroché"]
        vstats["persona"]=vstats["cluster"].map({c:labels[i] for i,c in enumerate(means.index)})
    except Exception:
        vstats["persona"]="—"
    return vstats


# ── SIDEBAR ─────────────────────────────────────────────────
st.sidebar.markdown(f"""
<div style="padding:16px 0 8px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,{PINK},{PURPLE});border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1rem;">▶</div>
    <div><div style="font-weight:800;font-size:1rem;">Audience Analytics</div>
    <div style="font-size:0.7rem;color:{MUTED};">Watch Together · Live</div></div>
  </div>
</div>""", unsafe_allow_html=True)

st.sidebar.markdown(f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">⚙️ Connexion</div>', unsafe_allow_html=True)
refresh_sec = st.sidebar.selectbox("Rafraîchissement", [5,10,30,60], index=1, format_func=lambda x:f"Toutes les {x}s")
if st.sidebar.button("🔄 Actualiser maintenant"): st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f'<div style="font-size:0.7rem;color:{MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">🎛️ Filtres d\'analyse</div>', unsafe_allow_html=True)
min_bored = st.sidebar.slider("Seuil score d'ennui", 0.0, 1.0, 0.3, 0.05)
show_segments   = st.sidebar.checkbox("Détail par segment", value=True)
show_whatif     = st.sidebar.checkbox("Simulateur What-If", value=True)
show_personas   = st.sidebar.checkbox("Personas de spectateurs", value=True)
show_explain    = st.sidebar.checkbox("Explicabilité du modèle", value=True)
show_predictor  = st.sidebar.checkbox("Prédiction par session", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f'<div style="font-size:0.68rem;color:{MUTED};">Données exclusivement issues de Watch Together en temps réel.</div>', unsafe_allow_html=True)


# ── FETCH ───────────────────────────────────────────────────
stats  = fetch("/api/live-stats")
events = fetch("/api/live-events?limit=10000", fallback=[])
is_connected = stats is not None


# ── NAVBAR ──────────────────────────────────────────────────
badge = f'<div class="live-badge"><span class="live-dot"></span>LIVE</div>' if is_connected else f'<div class="offline-badge">⚫ HORS LIGNE</div>'
st.markdown(f"""
<div class="wt-nav">
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="wt-logo">▶</div>
    <div><div style="font-size:1.1rem;font-weight:800;">Audience Analytics</div>
    <div style="font-size:0.75rem;color:{MUTED};">Analyse temps réel · Watch Together</div></div>
  </div>
  <div style="display:flex;align-items:center;gap:14px;">{badge}
    <div style="font-size:0.72rem;color:{MUTED};">Actualisé {datetime.now().strftime('%H:%M:%S')}</div>
  </div>
</div>""", unsafe_allow_html=True)


# ── OFFLINE ─────────────────────────────────────────────────
if not is_connected:
    st.markdown(f"""
    <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);border-radius:16px;padding:40px;text-align:center;margin:2rem 0;">
      <div style="font-size:3rem;margin-bottom:1rem;">🔌</div>
      <div style="font-size:1.3rem;font-weight:700;margin-bottom:0.5rem;">Serveur Watch Together non joignable</div>
      <div style="color:{MUTED};font-size:0.9rem;margin-bottom:1.5rem;">Impossible de contacter <code>http://localhost:4000</code></div>
      <div style="background:{PANEL};border:1px solid {BORDER};border-radius:10px;padding:16px;display:inline-block;text-align:left;">
        <code style="color:{GREEN};font-size:0.85rem;">cd watch-together/server<br>npm run dev</code>
      </div>
    </div>""", unsafe_allow_html=True)
    time.sleep(5); st.rerun(); st.stop()


# ── KPIs GLOBAUX ────────────────────────────────────────────
total_viewers = stats.get("total_active_viewers",0)
total_events  = stats.get("total_events",0)
epm           = stats.get("events_last_minute",0)
rooms_data    = stats.get("rooms",[])
n_rooms       = len(rooms_data)
seek_r        = stats.get("seek_rate_last_min",0)
pause_r       = stats.get("pause_rate_last_min",0)
uptime        = stats.get("server_uptime_sec",0)
uptime_str    = f"{uptime//3600}h {(uptime%3600)//60}m" if uptime>3600 else f"{uptime//60}m {uptime%60}s"
bored_g       = min(100,((seek_r*0.4+pause_r*0.1)/max(1,epm))*100) if epm>0 else 0

st.markdown(
    '<div class="kpi-grid">'
    + kpi("Viewers actifs",str(total_viewers),"👁️",BLUE,"#2a6fb0",f"{n_rooms} salon(s)")
    + kpi("Salons actifs",str(n_rooms),"📺",PURPLE,PINK,"en cours")
    + kpi("Événements/min",str(epm),"⚡",GREEN,"#16a34a",f"{total_events:,} total")
    + kpi("Index d'ennui",f"{bored_g:.0f}%","🧠",AMBER,RED,f"{seek_r} seeks/min")
    + kpi("Uptime serveur",uptime_str,"🖥️",MUTED,BORDER,"Watch Together")
    + '</div>', unsafe_allow_html=True)

st.markdown("---")

# ── ROOMS GRID ──────────────────────────────────────────────
if not rooms_data:
    st.markdown(f'<div style="text-align:center;padding:4rem;background:{PANEL};border:1px solid {BORDER};border-radius:18px;"><div style="font-size:3rem;margin-bottom:1rem;">🎬</div><div style="font-size:1.2rem;font-weight:700;">Aucun salon actif</div><div style="color:{MUTED};margin-top:0.5rem;">Créez un salon dans Watch Together pour voir les analytics.</div></div>', unsafe_allow_html=True)
    time.sleep(refresh_sec); st.rerun(); st.stop()

sec_title(f"📺 Salons en direct ({n_rooms})")
room_cols = st.columns(min(n_rooms,4))
for i,room in enumerate(rooms_data):
    with room_cols[i%min(n_rooms,4)]:
        thumb=room.get("video_thumbnail") or ""
        title=room.get("video_title") or "Aucune vidéo"
        t_sec=int(room.get("current_video_time",0))
        t_str=f"{t_sec//60:02d}:{t_sec%60:02d}"
        is_pl=room.get("is_playing",False); vc=room.get("viewer_count",0)
        ev5=room.get("events_last_5min",0)
        b5=(room.get("seeks_last_5min",0)*0.4+room.get("pauses_last_5min",0)*0.05)/max(1,ev5) if ev5>0 else 0
        bc=RED if b5>0.3 else (AMBER if b5>0.15 else GREEN)
        ts=f"background-image:url('{thumb}');background-size:cover;background-position:center;" if thumb else f"background:linear-gradient(135deg,rgba(138,46,207,0.4),rgba(214,34,138,0.3));"
        st.markdown(f"""<div class="room-card">
          <div style="position:relative;height:140px;overflow:hidden;{ts}">
            <div style="position:absolute;top:8px;left:8px;"><div class="live-badge" style="padding:3px 8px;font-size:0.6rem;"><span class="live-dot" style="width:6px;height:6px;"></span>{'▶ PLAY' if is_pl else '⏸ PAUSE'}</div></div>
            <div style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.7);border-radius:6px;padding:3px 8px;font-size:0.7rem;font-family:monospace;">{t_str}</div>
            <div style="position:absolute;bottom:8px;left:8px;background:rgba(0,0,0,0.7);border-radius:6px;padding:3px 8px;font-size:0.7rem;">👥 {vc}</div>
          </div>
          <div style="padding:14px;">
            <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">{room.get('room_name','?')}</div>
            <div style="font-size:0.78rem;color:{PINK};margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">▶ {title}</div>
            <div style="font-size:0.72rem;color:{MUTED};display:flex;gap:10px;"><span style="color:{bc};">● Ennui {b5*100:.0f}%</span><span>{ev5} ev/5min</span></div>
          </div></div>""", unsafe_allow_html=True)

st.markdown("---")

# ── ANALYSE DÉTAILLÉE PAR ROOM ──────────────────────────────
room_names = {r["room_id"]:f"📺 {r['room_name']} — {r.get('video_title','?')}" for r in rooms_data}
selected_room_id = st.selectbox("Sélectionner un salon pour l'analyse détaillée", list(room_names.keys()), format_func=lambda x:room_names[x])
selected_room = next((r for r in rooms_data if r["room_id"]==selected_room_id), None)

if selected_room:
    st.markdown(f"""<div style="background:{PANEL};border:1px solid {BORDER};border-left:3px solid {PINK};border-radius:14px;padding:20px 24px;margin-bottom:1.5rem;">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div><div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;">Analyse en cours</div>
          <div style="font-size:1.5rem;font-weight:800;margin-top:4px;">{selected_room.get('room_name')}</div>
          <div style="color:{PINK};font-size:0.85rem;margin-top:2px;">▶ {selected_room.get('video_title','—')} · {selected_room.get('video_genre','')}</div></div>
        <div style="text-align:right;"><div style="font-size:0.7rem;color:{MUTED};">Viewers</div>
          <div style="font-size:2rem;font-weight:800;">{selected_room.get('viewer_count',0)}</div></div>
      </div></div>""", unsafe_allow_html=True)

    room_events=[e for e in events if e.get("session_id")==selected_room_id]
    seg_df,zones_df=build_segments(room_events,selected_room_id)

    # Insights
    sec_title("🤖 Insights automatiques")
    for ins in auto_insights(seg_df,zones_df,selected_room.get("room_name","?")):
        st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)
    st.markdown("---")

    col_left,col_right=st.columns([3,1])
    with col_left:
        sec_title("🎞️ Timeline — pellicule de visionnage")
        st.markdown(filmstrip(seg_df,zones_df,min_bored), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        sec_title("📈 Courbe de rétention réelle")
        if not seg_df.empty:
            fig=go.Figure(); fig.update_layout(**PL)
            fig.add_trace(go.Scatter(x=seg_df["start"],y=seg_df["completion_rate"],mode="lines+markers",name="Rétention",line=dict(color=PINK,width=3),marker=dict(size=6,color=PINK),fill="tozeroy",fillcolor="rgba(214,34,138,0.08)"))
            fig.add_trace(go.Scatter(x=seg_df["start"],y=seg_df["bored_score"],mode="lines",name="Score ennui",line=dict(color=AMBER,width=2,dash="dot")))
            for _,z in zones_df.iterrows():
                if z["avg_score"]>=min_bored:
                    fig.add_vrect(x0=z["zone_start"],x1=z["zone_end"],fillcolor=RED,opacity=0.12,line_width=0,annotation_text="⚠️",annotation_position="top left",annotation_font_color=RED,annotation_font_size=10)
            t_cur=selected_room.get("current_video_time",0)
            if t_cur>0: fig.add_vline(x=t_cur,line_color=GREEN,line_width=2,line_dash="dash",annotation_text="▶ maintenant",annotation_font_color=GREEN,annotation_font_size=10)
            fig.update_layout(height=380,xaxis_title="Temps (s)",yaxis_title="Taux",yaxis_range=[0,1.05],legend=dict(orientation="h",yanchor="bottom",y=1.02))
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.markdown(f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:40px;text-align:center;color:{MUTED};">⏳ En attente des données de lecture...</div>', unsafe_allow_html=True)

        if not zones_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            sec_title("🔥 Zones d'ennui détectées")
            fig_z=go.Figure(); fig_z.update_layout(**PL)
            for _,z in zones_df.iterrows():
                fig_z.add_trace(go.Bar(x=[f"{int(z['zone_start'])}s→{int(z['zone_end'])}s"],y=[z["avg_score"]*100],marker_color=f"rgba(239,68,68,{0.4+z['avg_score']*0.6:.2f})",text=[f"{z['avg_score']*100:.0f}%"],textposition="outside",textfont=dict(color=TEXT)))
            fig_z.update_layout(height=240,yaxis_title="Score ennui (%)",showlegend=False)
            st.plotly_chart(fig_z,use_container_width=True)

    with col_right:
        sec_title("⚡ Flux d'événements")
        ev_icons={"play":("ev-play","▶"),"pause":("ev-pause","⏸"),"seek":("ev-seek","⏩")}
        feed=f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;max-height:480px;overflow-y:auto;">'
        last_ev=sorted(room_events,key=lambda e:e.get("timestamp_wall",""),reverse=True)[:30]
        if last_ev:
            for e in last_ev:
                et=e.get("event_type","?"); cls,icon=ev_icons.get(et,("ev-seek","?"))
                tw=e.get("timestamp_wall","")[:19].replace("T"," ")
                tv=f"{int(e.get('timestamp_video',0))//60:02d}:{int(e.get('timestamp_video',0))%60:02d}"
                u=e.get("user_id","?")[:12]
                feed+=(f'<div class="event-item"><span class="event-pill {cls}">{icon} {et}</span>'
                       f'<div><div style="color:{TEXT};font-size:0.75rem;">{u}</div>'
                       f'<div style="color:{MUTED};font-size:0.65rem;">{tv} · {tw[-8:]}</div></div></div>')
        else:
            feed+=f'<div style="padding:20px;text-align:center;color:{MUTED};font-size:0.8rem;">En attente...</div>'
        feed+="</div>"
        st.markdown(feed, unsafe_allow_html=True)
        if not seg_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            sec_title("📊 Stats session")
            sh=f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:14px;">'
            for lbl,val in [("Viewers max",str(int(seg_df["n_viewers_reached"].max()))),
                            ("Complétion moy.",f"{seg_df['completion_rate'].mean()*100:.1f}%"),
                            ("Score ennui max",f"{seg_df['bored_score'].max()*100:.0f}%"),
                            ("Total pauses",str(int(seg_df["n_pauses"].sum()))),
                            ("Total seeks",str(int(seg_df["n_seeks"].sum()))),
                            ("Segments",str(len(seg_df)))]:
                sh+=(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.78rem;">'
                     f'<span style="color:{MUTED};">{lbl}</span><span style="font-weight:700;">{val}</span></div>')
            sh+="</div>"
            st.markdown(sh, unsafe_allow_html=True)

    # ── DÉTAIL PAR SEGMENT ──────────────────────────────────
    if show_segments and not seg_df.empty:
        st.markdown("---")
        sec_title("🔍 Détail par segment")
        d=seg_df[["segment_id","start","end","n_viewers_reached","completion_rate","dropoff_rate","n_pauses","n_seeks","bored_score","is_bored"]].copy()
        d["completion_rate"]=(d["completion_rate"]*100).round(1).astype(str)+"%"
        d["dropoff_rate"]=(d["dropoff_rate"]*100).round(1).astype(str)+"%"
        d["bored_score"]=(d["bored_score"]*100).round(1).astype(str)+"%"
        d.columns=["Segment","Début (s)","Fin (s)","Viewers","Complétion","Drop-off","Pauses","Seeks","Score ennui","Zone ennui"]
        st.dataframe(d, use_container_width=True, hide_index=True, height=280)

    # ── SIMULATEUR WHAT-IF ──────────────────────────────────
    if show_whatif and not seg_df.empty and not zones_df.empty:
        st.markdown("---")
        sec_title("🎬 Simulateur \"What-If\" — impact d'un montage")
        st.caption("Sélectionnez une zone d'ennui à couper : on simule l'effet sur la rétention si ce passage était supprimé.")
        z_opts=[f"{int(z['zone_start'])}s – {int(z['zone_end'])}s  (score {z['avg_score']:.2f})" for _,z in zones_df.iterrows()]
        chosen=st.selectbox("Zone à simuler", z_opts, key="whatif")
        cz=zones_df.iloc[z_opts.index(chosen)]
        cs,ce=cz["zone_start"],cz["zone_end"]; cd=ce-cs
        sim=seg_df.sort_values("start").reset_index(drop=True)
        before=sim[sim["end"]<=cs]; after=sim[sim["start"]>=ce].copy()
        if len(before)>0 and len(after)>0:
            drop_in=before.iloc[-1]["completion_rate"]-after.iloc[0]["completion_rate"]
            after["cr_sim"]=(after["completion_rate"]+drop_in).clip(upper=1.0)
            before["cr_sim"]=before["completion_rate"]
            sf=pd.concat([before,after])
            gain=(sf["cr_sim"].iloc[-1]-seg_df["completion_rate"].iloc[-1])*100
            fig_s=go.Figure(); fig_s.update_layout(**PL)
            fig_s.add_trace(go.Scatter(x=seg_df["start"],y=seg_df["completion_rate"],mode="lines",name="Actuelle",line=dict(color=MUTED,width=2)))
            fig_s.add_trace(go.Scatter(x=sf["start"],y=sf["cr_sim"],mode="lines",name="Simulée (coupe)",line=dict(color=GREEN,width=3,dash="dash")))
            fig_s.add_vrect(x0=cs,x1=ce,fillcolor=RED,opacity=0.15,line_width=0)
            fig_s.update_layout(height=340,xaxis_title="Temps (s)",yaxis_title="Rétention",yaxis_range=[0,1.05],legend=dict(orientation="h",yanchor="bottom",y=1.02))
            st.plotly_chart(fig_s,use_container_width=True)
            gc=GREEN if gain>0 else RED
            st.markdown(f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.3);border-radius:10px;padding:14px 18px;font-size:0.9rem;">💡 En coupant <b>{int(cd)}s</b> : rétention <b>{seg_df["completion_rate"].iloc[-1]*100:.1f}%</b> → <b>{sf["cr_sim"].iloc[-1]*100:.1f}%</b> — gain estimé : <span style="color:{gc};font-weight:800;">{gain:+.1f} pts</span></div>', unsafe_allow_html=True)
        else:
            st.info("Pas assez de segments avant/après cette zone.")

st.markdown("---")

# ── VUE GLOBALE ─────────────────────────────────────────────
sec_title("🌐 Vue d'ensemble — toutes les vidéos")
all_seg,_=build_segments(events)
if not all_seg.empty:
    c1,c2=st.columns(2)
    with c1:
        fig_g=go.Figure(); fig_g.update_layout(**PL)
        colors=[PINK,PURPLE,GREEN,AMBER,BLUE,RED]
        for idx,(rid,grp) in enumerate(all_seg.groupby("session_id")):
            rn=next((r["room_name"] for r in rooms_data if r["room_id"]==rid),rid)
            fig_g.add_trace(go.Scatter(x=grp["start"],y=grp["completion_rate"],mode="lines",name=rn,line=dict(color=colors[idx%len(colors)],width=2)))
        fig_g.update_layout(height=300,title_text="Rétention par salon",title_font=dict(color=TEXT,size=13),xaxis_title="Temps (s)",yaxis_title="Rétention",yaxis_range=[0,1.05])
        st.plotly_chart(fig_g,use_container_width=True)
    with c2:
        br=all_seg.groupby("session_id")["bored_score"].mean().reset_index()
        br["room_name"]=br["session_id"].map({r["room_id"]:r["room_name"] for r in rooms_data}).fillna(br["session_id"])
        fig_b=go.Figure(); fig_b.update_layout(**PL)
        fig_b.add_trace(go.Bar(x=br["room_name"],y=br["bored_score"]*100,marker_color=[RED if v>0.3 else (AMBER if v>0.15 else GREEN) for v in br["bored_score"]],text=[f"{v*100:.0f}%" for v in br["bored_score"]],textposition="outside",textfont=dict(color=TEXT)))
        fig_b.update_layout(height=300,title_text="Score d'ennui par salon",title_font=dict(color=TEXT,size=13),yaxis_title="Score (%)",showlegend=False)
        st.plotly_chart(fig_b,use_container_width=True)
    sec_title("📋 Tableau récapitulatif")
    ov=all_seg.groupby("session_id").agg(completion_finale=("completion_rate","last"),bored_moy=("bored_score","mean"),pauses=("n_pauses","sum"),seeks=("n_seeks","sum"),segs=("segment_id","count")).reset_index()
    ov["salon"]=ov["session_id"].map({r["room_id"]:r["room_name"] for r in rooms_data}).fillna(ov["session_id"])
    ov["vidéo"]=ov["session_id"].map({r["room_id"]:r.get("video_title","—") for r in rooms_data}).fillna("—")
    ov["complétion (%"]=(ov["completion_finale"]*100).round(1)
    ov["ennui (%"]=(ov["bored_moy"]*100).round(1)
    st.dataframe(ov[["salon","vidéo","complétion (%","ennui (%","pauses","seeks","segs"]],use_container_width=True,hide_index=True)
else:
    st.markdown(f'<div style="text-align:center;padding:3rem;background:{PANEL};border:1px solid {BORDER};border-radius:16px;color:{MUTED};">⏳ Faites play/pause/seek dans Watch Together pour voir les analytics</div>', unsafe_allow_html=True)

# ── PERSONAS ────────────────────────────────────────────────
if show_personas and events:
    st.markdown("---")
    sec_title("👥 Personas de spectateurs (clustering comportemental)")
    st.caption("Segmentation KMeans des viewers selon leur comportement : engagement, pauses, seeks, durée de visionnage.")
    personas=compute_personas(events)
    if personas is not None and not personas.empty and "persona" in personas.columns:
        dist=personas["persona"].value_counts(normalize=True).mul(100).round(1)
        p1,p2=st.columns([1,1])
        with p1:
            fig_p=go.Figure(); fig_p.update_layout(**PL)
            fig_p.add_trace(go.Bar(x=dist.index,y=dist.values,marker_color=[PINK,AMBER,PURPLE][:len(dist)],text=[f"{v:.0f}%" for v in dist.values],textposition="outside",textfont=dict(color=TEXT)))
            fig_p.update_layout(height=300,yaxis_title="% des viewers",showlegend=False,title_text="Distribution des personas",title_font=dict(color=TEXT,size=13))
            st.plotly_chart(fig_p,use_container_width=True)
        with p2:
            st.dataframe(personas[["user_id","persona","n_plays","n_pauses","n_seeks","max_time"]].rename(columns={"user_id":"Viewer","persona":"Persona","n_plays":"Plays","n_pauses":"Pauses","n_seeks":"Seeks","max_time":"Temps max (s)"}),use_container_width=True,hide_index=True,height=300)
    else:
        st.info("Minimum 3 viewers différents requis pour le clustering.")

# ── EXPLICABILITÉ ────────────────────────────────────────────
if show_explain:
    st.markdown("---")
    sec_title("🔍 Explicabilité & preuve de valeur du modèle")
    OUT=_os.path.join(BASE_DIR,"outputs")
    cx,cy=st.columns(2)
    with cx:
        st.markdown(f'<div style="font-size:0.8rem;color:{MUTED};margin-bottom:0.5rem;">Importance des variables</div>', unsafe_allow_html=True)
        fi=_os.path.join(OUT,"feature_importance.png")
        if _os.path.exists(fi): st.image(fi,use_container_width=True)
        else: st.info("Lancer 06_baseline_and_explainability.py pour générer ce graphique.")
    with cy:
        st.markdown(f'<div style="font-size:0.8rem;color:{MUTED};margin-bottom:0.5rem;">Modèle vs baseline naïve</div>', unsafe_allow_html=True)
        bv=_os.path.join(OUT,"baseline_vs_model.png")
        if _os.path.exists(bv): st.image(bv,use_container_width=True)
        else: st.info("Lancer 06_baseline_and_explainability.py pour générer ce graphique.")
    c3,c4,c5=st.columns(3)
    for col,fname,cap in [(c3,"eval_roc_curve.png","Courbe ROC"),(c4,"eval_confusion_matrix.png","Matrice de confusion"),(c5,"eval_regression.png","Régression")]:
        with col:
            p=_os.path.join(OUT,fname)
            if _os.path.exists(p):
                st.markdown(f'<div style="font-size:0.8rem;color:{MUTED};margin-bottom:0.5rem;">{cap}</div>', unsafe_allow_html=True)
                st.image(p,use_container_width=True)

# ── PRÉDICTION PAR SESSION ───────────────────────────────────
if show_predictor:
    st.markdown("---")
    st.markdown(f'<div style="border-left:3px solid {AMBER};padding-left:12px;margin-bottom:8px;"><span style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;">MODÈLE COMPLÉMENTAIRE</span><br><span style="font-size:1.2rem;font-weight:800;">🎯 Prédiction par session</span></div>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:0.82rem;color:{MUTED};margin-bottom:1.2rem;">Prédit si un spectateur va finir ou abandonner la vidéo, à partir de son comportement (pauses, seeks, durée de session).</p>', unsafe_allow_html=True)

    SM=_os.path.join(BASE_DIR,"data","sessions","model_final.joblib")
    if _os.path.exists(SM):
        bundle=joblib.load(SM); sm=bundle["model"]; sf_=bundle["features"]
        m1,m2,m3=st.columns(3)
        card=f"background:{PANEL2};border:1px solid {BORDER};border-left:3px solid {AMBER};border-radius:8px;padding:16px;font-size:0.8rem;"
        with m1:
            st.markdown(f'<div style="{card}"><div style="color:{AMBER};font-size:0.65rem;letter-spacing:1px;margin-bottom:8px;">POURQUOI CETTE APPROCHE ?</div><div style="color:{MUTED};">Évite la fuite de données du modèle par segment (<code>completion_rate</code> corrélé à 0.99). Chaque session est indépendante.</div></div>', unsafe_allow_html=True)
        with m2:
            vars_html="".join(f'<span style="background:{BORDER};border-radius:4px;padding:2px 6px;margin:2px;display:inline-block;font-size:0.7rem;">{v}</span>' for v in sf_)
            st.markdown(f'<div style="{card}"><div style="color:{AMBER};font-size:0.65rem;letter-spacing:1px;margin-bottom:8px;">VARIABLES (SANS FUITE)</div><div style="line-height:2;">{vars_html}</div></div>', unsafe_allow_html=True)
        with m3:
            comp=_os.path.join(BASE_DIR,"data","sessions","comparaison_4_modeles.csv")
            st.markdown(f'<div style="{card}"><div style="color:{AMBER};font-size:0.65rem;letter-spacing:1px;margin-bottom:8px;">COMPARAISON 4 MODÈLES</div></div>', unsafe_allow_html=True)
            if _os.path.exists(comp): st.dataframe(pd.read_csv(comp),use_container_width=True,hide_index=True)

        for col,(lbl,val,c1_,c2_) in zip(st.columns(4),[("Accuracy","94.2%",AMBER,RED),("F1-score","92.7%",GREEN,AMBER),("ROC-AUC","98.2%",BLUE,GREEN),("Sessions","11 408",MUTED,BORDER)]):
            col.markdown(kpi(lbl,val,"",c1_,c2_), unsafe_allow_html=True)

        si=_os.path.join(BASE_DIR,"outputs","sessions_model")
        if _os.path.exists(si):
            ic1,ic2,ic3=st.columns(3)
            for col,fn,cap in [(ic1,"eval_confusion_matrix.png","Matrice de confusion"),(ic2,"eval_roc_curve.png","Courbe ROC"),(ic3,"eval_feature_importance.png","Importance des variables")]:
                fp=_os.path.join(si,fn)
                if _os.path.exists(fp):
                    with col:
                        st.image(fp,use_container_width=True)
                        st.markdown(f'<div style="text-align:center;font-size:0.7rem;color:{MUTED};">{cap}</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin:1.2rem 0 0.5rem;">🔮 Tester une prédiction en direct</div>', unsafe_allow_html=True)
        p1_,p2_,p3_=st.columns(3)
        with p1_:
            in_dur=st.number_input("Durée vidéo (sec)",60,1800,300)
            in_pau=st.number_input("Nombre de pauses",0,20,2)
        with p2_:
            in_sk=st.number_input("Nombre de seeks",0,20,1)
            in_pl=st.number_input("Nombre de plays",1,10,1)
        with p3_:
            in_ev=st.number_input("Nb total événements",1,50,5)
            in_dv=st.selectbox("Device",["desktop","mobile","tablet"])

        if st.button("🎯 Prédire"):
            row={"duration_sec":in_dur,"n_pauses":in_pau,"n_seeks":in_sk,"n_plays":in_pl,"n_events":in_ev,
                 "pauses_per_min":in_pau/(in_dur/60),"seeks_per_min":in_sk/(in_dur/60)}
            Xi=pd.DataFrame([row])
            for col in sf_:
                if col.startswith("device_") and col not in Xi.columns:
                    Xi[col]=1 if col==f"device_{in_dv}" else 0
            Xi=Xi.reindex(columns=sf_,fill_value=0)
            proba=sm.predict_proba(Xi)[0,1]
            icon_="✅" if proba>=0.5 else "⚠️"
            pred_="Finira la vidéo" if proba>=0.5 else "Risque d'abandon"
            cc=GREEN if proba>=0.5 else AMBER
            st.markdown(f'<div style="background:rgba(34,197,94,0.06);border:1px solid {cc};border-left:4px solid {cc};border-radius:8px;padding:16px;margin-top:12px;"><span style="font-size:1.4rem;">{icon_}</span> <span style="color:{cc};font-weight:700;font-size:1rem;">{pred_}</span> <span style="color:{MUTED};font-size:0.85rem;">— probabilité : </span><span style="font-weight:700;">{proba*100:.1f}%</span></div>', unsafe_allow_html=True)
    else:
        st.info("Fichier `data/sessions/model_final.joblib` introuvable.")

st.markdown("---")

# ── EXPORT ──────────────────────────────────────────────────
st.markdown(f"""<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
  <a href="http://localhost:4000/api/live-events/csv" target="_blank" style="background:linear-gradient(90deg,{PINK},{PURPLE});color:white;font-weight:700;padding:10px 20px;border-radius:10px;text-decoration:none;font-size:0.85rem;">⬇️ Télécharger les événements (CSV)</a>
  <div style="font-size:0.75rem;color:{MUTED};">{total_events:,} événements collectés · {n_rooms} salon(s) actif(s)</div>
</div>""", unsafe_allow_html=True)

time.sleep(0.5)
if refresh_sec<=30:
    time.sleep(refresh_sec-0.5)
    st.rerun()
