"""
Audience Analytics Dashboard — Watch Together Integration
Analyse en temps réel des sessions Watch Together.
Lancer : streamlit run src/05_dashboard.py
"""
import os as _os
import sys
import time
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

BASE_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _os.path.join(BASE_DIR, "src"))

st.set_page_config(
    page_title="Audience Analytics · Watch Together",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded",
)

WT_URL = _os.environ.get("WATCH_TOGETHER_URL", "http://localhost:4000")

# ============================================================
# DESIGN — Dark theme aligné sur Watch Together
# ============================================================
BG       = "#0a0412"
BG2      = "#12071e"
PANEL    = "rgba(255,255,255,0.05)"
PANEL2   = "rgba(255,255,255,0.08)"
BORDER   = "rgba(255,255,255,0.1)"
PINK     = "#d6228a"
PURPLE   = "#8a2ecf"
GREEN    = "#22c55e"
AMBER    = "#f59e0b"
RED      = "#ef4444"
BLUE     = "#3b82f6"
TEXT     = "#ffffff"
MUTED    = "rgba(255,255,255,0.5)"
FONT     = "'Segoe UI', system-ui, sans-serif"

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.03)",
    font=dict(family=FONT, color=TEXT, size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)", color=MUTED),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)", color=MUTED),
    legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor=BORDER, borderwidth=1, font=dict(color=TEXT)),
    margin=dict(t=40, l=10, r=10, b=10),
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {{ font-family: {FONT} !important; }}
#MainMenu, header, footer {{ visibility: hidden; }}

.stApp {{ background: linear-gradient(135deg, {BG} 0%, {BG2} 60%, #0d1f3c 100%) !important; color: {TEXT}; }}

section[data-testid="stSidebar"] {{
    background: rgba(10,4,18,0.95) !important;
    border-right: 1px solid {BORDER};
    backdrop-filter: blur(20px);
}}
section[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}

h1, h2, h3, h4 {{ color: {TEXT} !important; font-weight: 700 !important; }}
p, label {{ color: {TEXT} !important; }}

/* NAV BAR */
.wt-nav {{
    display:flex; align-items:center; justify-content:space-between;
    padding: 12px 24px;
    background: rgba(0,0,0,0.4);
    border-bottom: 1px solid {BORDER};
    backdrop-filter: blur(10px);
    margin-bottom: 1.5rem;
}}
.wt-logo {{
    width:36px; height:36px;
    background: linear-gradient(135deg, {PINK}, {PURPLE});
    border-radius: 10px;
    display:flex; align-items:center; justify-content:center;
    font-size:1rem; font-weight:900; color:white;
    box-shadow: 0 4px 15px rgba(214,34,138,0.4);
}}
.wt-brand {{ font-size:1.1rem; font-weight:800; letter-spacing:-0.3px; }}
.wt-tagline {{ font-size:0.75rem; color:{MUTED}; margin-top:2px; }}

/* LIVE BADGE */
.live-badge {{
    display:inline-flex; align-items:center; gap:6px;
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 99px;
    padding: 4px 12px;
    font-size: 0.7rem; font-weight:700; letter-spacing:2px;
    color: {RED}; text-transform:uppercase;
}}
.live-dot {{
    width:8px; height:8px; border-radius:50%;
    background:{RED};
    box-shadow: 0 0 8px {RED};
    animation: livepulse 1.4s ease-in-out infinite;
}}
@keyframes livepulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:0.4;transform:scale(0.8)}} }}

/* OFFLINE BADGE */
.offline-badge {{
    display:inline-flex; align-items:center; gap:6px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 99px;
    padding: 4px 12px;
    font-size: 0.7rem; font-weight:700; letter-spacing:2px;
    color: {MUTED}; text-transform:uppercase;
}}

/* KPI CARDS */
.kpi-grid {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:1rem; }}
.kpi-card {{
    flex:1; min-width:160px;
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 20px;
    position:relative; overflow:hidden;
    backdrop-filter: blur(10px);
    transition: transform 0.2s, border-color 0.2s;
}}
.kpi-card:hover {{ transform:translateY(-3px); border-color:rgba(214,34,138,0.4); }}
.kpi-card::before {{
    content:"";
    position:absolute; top:0; left:0; right:0; height:2px;
    background: linear-gradient(90deg, var(--c1), var(--c2));
}}
.kpi-label {{ font-size:0.65rem; color:{MUTED}; text-transform:uppercase; letter-spacing:1.5px; font-weight:600; }}
.kpi-value {{ font-size:2rem; font-weight:800; color:{TEXT}; line-height:1; margin-top:6px; }}
.kpi-icon {{ position:absolute; top:14px; right:16px; font-size:1.4rem; opacity:0.3; }}
.kpi-sub {{ font-size:0.7rem; color:{MUTED}; margin-top:4px; }}

/* ROOM CARDS */
.room-card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 18px;
    overflow:hidden;
    transition: all 0.25s ease;
    backdrop-filter: blur(10px);
    cursor: pointer;
}}
.room-card:hover {{ border-color:rgba(214,34,138,0.5); transform:translateY(-4px); box-shadow:0 20px 50px rgba(0,0,0,0.5); }}
.room-thumb {{ position:relative; height:140px; background:linear-gradient(135deg,rgba(138,46,207,0.3),rgba(214,34,138,0.2)); display:flex; align-items:center; justify-content:center; overflow:hidden; }}
.room-body {{ padding:14px; }}
.room-name {{ font-weight:700; font-size:0.95rem; margin-bottom:4px; }}
.room-meta {{ font-size:0.75rem; color:{MUTED}; }}
.room-video {{ font-size:0.78rem; color:{PINK}; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}

/* INSIGHT CARDS */
.insight-card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-left: 3px solid {AMBER};
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size:0.88rem;
    backdrop-filter: blur(10px);
    transition: border-left-color 0.2s;
}}
.insight-card:hover {{ border-left-color: {PINK}; }}

/* FILMSTRIP */
.filmstrip-wrap {{
    background: rgba(0,0,0,0.3);
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 16px;
    overflow-x: auto;
    backdrop-filter: blur(10px);
}}
.filmstrip-row {{ display:flex; gap:3px; }}
.film-frame {{
    flex:1; min-width:18px; height:60px;
    border-radius:3px;
    position:relative;
    transition: transform 0.15s;
}}
.film-frame:hover {{ transform:scaleY(1.2); z-index:2; }}
.film-frame.bored {{ animation: boredpulse 1.6s ease-in-out infinite; }}
@keyframes boredpulse {{ 0%,100%{{box-shadow:0 0 8px rgba(239,68,68,0.5)}} 50%{{box-shadow:0 0 20px rgba(239,68,68,0.9)}} }}
.film-ruler {{ display:flex; justify-content:space-between; font-size:0.6rem; color:{MUTED}; margin-top:6px; }}
.film-legend {{ display:flex; gap:16px; margin-top:10px; font-size:0.7rem; color:{MUTED}; }}
.film-legend span {{ display:flex; align-items:center; gap:5px; }}
.swatch {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}

/* EVENT FEED */
.event-item {{
    display:flex; align-items:center; gap:10px;
    padding: 7px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size:0.78rem;
}}
.event-pill {{
    padding: 2px 8px; border-radius:99px;
    font-size:0.65rem; font-weight:700;
    text-transform:uppercase; letter-spacing:1px;
    flex-shrink:0;
}}
.ev-play   {{ background:rgba(34,197,94,0.2); color:{GREEN}; border:1px solid rgba(34,197,94,0.3); }}
.ev-pause  {{ background:rgba(245,158,11,0.2); color:{AMBER}; border:1px solid rgba(245,158,11,0.3); }}
.ev-seek   {{ background:rgba(59,130,246,0.2); color:{BLUE};  border:1px solid rgba(59,130,246,0.3); }}

div.stButton > button {{
    background: linear-gradient(90deg, {PINK}, {PURPLE}) !important;
    color: white !important; border: none !important;
    font-weight: 700 !important; border-radius: 10px !important;
}}
.stSelectbox div[data-baseweb="select"] > div {{
    background: {PANEL} !important; border-color: {BORDER} !important; color: {TEXT} !important;
}}
[data-testid="stSlider"] [role="slider"] {{ background: {PINK} !important; box-shadow: 0 0 8px {PINK}; }}
hr {{ border-color: rgba(255,255,255,0.08) !important; }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def kpi(label, value, icon, c1, c2, sub=""):
    return (f'<div class="kpi-card" style="--c1:{c1};--c2:{c2};">'
            f'<div class="kpi-icon">{icon}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            + (f'<div class="kpi-sub">{sub}</div>' if sub else "")
            + f'</div>')


def fetch(endpoint, fallback=None, timeout=4):
    try:
        r = requests.get(f"{WT_URL}{endpoint}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def build_segments(events, room_id=None, seg_sec=15):
    """Reconstruit features par segment depuis les événements bruts."""
    if not events:
        return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(events)
    if df.empty or "event_type" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()
    if room_id:
        df = df[df["session_id"] == room_id]
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    rows = []
    for (vid, sess), grp in df.groupby(["video_id", "session_id"]):
        grp = grp.sort_values("timestamp_video")
        unique_viewers = grp["user_id"].nunique()
        if unique_viewers == 0:
            continue
        max_t = max(grp["timestamp_video"].max(), seg_sec * 2)
        n_segs = max(1, int(np.ceil(max_t / seg_sec)))
        for i in range(n_segs):
            t0, t1 = i * seg_sec, (i + 1) * seg_sec
            seg_ev = grp[(grp["timestamp_video"] >= t0) & (grp["timestamp_video"] < t1)]
            viewers_here = seg_ev["user_id"].nunique()
            n_pauses = int((seg_ev["event_type"] == "pause").sum())
            n_seeks  = int((seg_ev["event_type"] == "seek").sum())
            compl    = viewers_here / unique_viewers
            bored    = min(1.0, (n_seeks * 0.4 + n_pauses * 0.05) / max(1, unique_viewers))
            rows.append(dict(
                video_id=vid, session_id=sess, segment_id=i,
                start=t0, end=t1,
                n_viewers_reached=unique_viewers,
                completion_rate=min(1.0, compl),
                dropoff_rate=max(0.0, 1.0 - compl),
                n_pauses=n_pauses, n_seeks=n_seeks,
                bored_score=bored, is_bored=bored > 0.3,
            ))

    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    seg = pd.DataFrame(rows)
    bored_rows = seg[seg["bored_score"] > 0.3]
    zones = []
    if not bored_rows.empty:
        for (v, s), g in bored_rows.groupby(["video_id", "session_id"]):
            zones.append(dict(video_id=v, session_id=s, zone_start=g["start"].min(), zone_end=g["end"].max(), avg_score=g["bored_score"].mean()))
    return seg, pd.DataFrame(zones) if zones else pd.DataFrame(columns=["video_id","session_id","zone_start","zone_end","avg_score"])


def filmstrip(seg_df, zones_df, threshold=0.0):
    if seg_df.empty:
        return f'<p style="color:{MUTED};">En attente de données...</p>'
    n = len(seg_df)
    zone_mask = np.zeros(n, dtype=bool)
    for _, z in zones_df.iterrows():
        if z["avg_score"] >= threshold:
            zone_mask |= (seg_df["start"].values < z["zone_end"]) & (seg_df["end"].values > z["zone_start"])
    drop_norm = (seg_df["dropoff_rate"].values - seg_df["dropoff_rate"].min()) / (seg_df["dropoff_rate"].max() - seg_df["dropoff_rate"].min() + 1e-9)
    frames = []
    for i in range(n):
        if zone_mask[i]:
            bg = f"linear-gradient(180deg,{RED},#b3201a)"
            cls = "film-frame bored"
        else:
            t = drop_norm[i]
            bg = f"linear-gradient(180deg,rgba(214,34,138,{0.08+0.5*t:.2f}),rgba(138,46,207,0.15))"
            cls = "film-frame"
        title = f"Segment {int(seg_df.iloc[i]['segment_id'])} · {int(seg_df.iloc[i]['start'])}-{int(seg_df.iloc[i]['end'])}s · drop {seg_df.iloc[i]['dropoff_rate']*100:.1f}%"
        frames.append(f'<div class="{cls}" style="background:{bg}" title="{title}"></div>')
    dur = int(seg_df["end"].max())
    ruler = f'<div class="film-ruler"><span>0s</span><span>{dur//2}s</span><span>{dur}s</span></div>'
    legend = (f'<div class="film-legend">'
              f'<span><span class="swatch" style="background:rgba(138,46,207,0.3);"></span>Engagement</span>'
              f'<span><span class="swatch" style="background:rgba(214,34,138,0.6);"></span>Décrochage</span>'
              f'<span><span class="swatch" style="background:{RED};"></span>Zone d\'ennui</span>'
              f'</div>')
    return f'<div class="filmstrip-wrap"><div class="filmstrip-row">{"".join(frames)}</div>{ruler}{legend}</div>'


def auto_insights(seg, zones, room_name):
    msgs = []
    if seg.empty:
        return [f"⏳ En attente des premières données pour <b>{room_name}</b>..."]
    worst = seg.nlargest(1, "bored_score").iloc[0]
    if worst["bored_score"] > 0.3:
        msgs.append(f"🔥 Zone d'ennui détectée entre <b>{int(worst['start'])}s</b> et <b>{int(worst['end'])}s</b> — score {worst['bored_score']*100:.0f}%.")
    avg_compl = seg["completion_rate"].mean()
    if avg_compl < 0.5:
        msgs.append(f"⚠️ Taux de complétion moyen faible : <b>{avg_compl*100:.1f}%</b>. Plus de la moitié des viewers ont décroché.")
    elif avg_compl > 0.8:
        msgs.append(f"✅ Excellent engagement : <b>{avg_compl*100:.1f}%</b> de complétion moyenne — contenu très captivant.")
    total_seeks = seg["n_seeks"].sum()
    if total_seeks > 10:
        msgs.append(f"⏩ <b>{int(total_seeks)}</b> seeks enregistrés — signe que les viewers naviguent dans le contenu.")
    if not zones.empty:
        msgs.append(f"🎯 <b>{len(zones)}</b> zone(s) d'ennui identifiée(s) — à couper au montage pour améliorer la rétention.")
    if not msgs:
        msgs.append(f"✨ Session en cours pour <b>{room_name}</b> — collecte des données en temps réel.")
    return msgs


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown(f"""
<div style="padding:16px 0 8px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,{PINK},{PURPLE});border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1rem;">▶</div>
    <div>
      <div style="font-weight:800;font-size:1rem;">Audience Analytics</div>
      <div style="font-size:0.7rem;color:{MUTED};">Watch Together · Live</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

wt_url_input = st.sidebar.text_input("URL serveur Watch Together", value=WT_URL, help="Ex: http://localhost:4000 ou https://votre-serveur.onrender.com")
refresh_sec  = st.sidebar.selectbox("Rafraîchissement auto", [5, 10, 30, 60], index=1, format_func=lambda x: f"Toutes les {x}s")
min_bored    = st.sidebar.slider("Seuil détection ennui", 0.0, 1.0, 0.3, 0.05)

if st.sidebar.button("🔄 Actualiser maintenant"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f'<div style="font-size:0.7rem;color:{MUTED};">Les données proviennent exclusivement de votre serveur Watch Together en temps réel.</div>', unsafe_allow_html=True)


# ============================================================
# FETCH DATA
# ============================================================
stats  = fetch(f"{wt_url_input.rstrip('/')}/api/live-stats")
events = fetch(f"{wt_url_input.rstrip('/')}/api/live-events?limit=10000", fallback=[])
is_connected = stats is not None


# ============================================================
# NAV BAR
# ============================================================
badge_html = f'<div class="live-badge"><span class="live-dot"></span>LIVE</div>' if is_connected else f'<div class="offline-badge">⚫ HORS LIGNE</div>'
st.markdown(f"""
<div class="wt-nav">
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="wt-logo">▶</div>
    <div>
      <div class="wt-brand">Audience Analytics</div>
      <div class="wt-tagline">Analyse temps réel · Watch Together</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:14px;">
    {badge_html}
    <div style="font-size:0.72rem;color:{MUTED};">Actualisé {datetime.now().strftime('%H:%M:%S')}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# OFFLINE STATE
# ============================================================
if not is_connected:
    st.markdown(f"""
    <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);border-radius:16px;
    padding:40px;text-align:center;margin:2rem 0;">
      <div style="font-size:3rem;margin-bottom:1rem;">🔌</div>
      <div style="font-size:1.3rem;font-weight:700;margin-bottom:0.5rem;">Serveur Watch Together non joignable</div>
      <div style="color:{MUTED};font-size:0.9rem;margin-bottom:1.5rem;">
        Impossible de contacter <code>{wt_url_input}</code><br>
        Assurez-vous que le serveur Watch Together est démarré.
      </div>
      <div style="background:{PANEL};border:1px solid {BORDER};border-radius:10px;padding:16px;display:inline-block;text-align:left;">
        <div style="font-size:0.8rem;color:{MUTED};margin-bottom:8px;">Pour démarrer le serveur :</div>
        <code style="color:{GREEN};font-size:0.85rem;">cd watch-together/server<br>npm run dev</code>
      </div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(5)
    st.rerun()
    st.stop()


# ============================================================
# GLOBAL KPIs
# ============================================================
total_viewers  = stats.get("total_active_viewers", 0)
total_events   = stats.get("total_events", 0)
epm            = stats.get("events_last_minute", 0)
rooms_data     = stats.get("rooms", [])
n_rooms        = len(rooms_data)
pause_rate     = stats.get("pause_rate_last_min", 0)
seek_rate      = stats.get("seek_rate_last_min", 0)
uptime         = stats.get("server_uptime_sec", 0)
uptime_str     = f"{uptime//3600}h {(uptime%3600)//60}m" if uptime > 3600 else f"{uptime//60}m {uptime%60}s"

bored_score_global = 0.0
if seek_rate + pause_rate > 0 and epm > 0:
    bored_score_global = min(100, ((seek_rate * 0.4 + pause_rate * 0.1) / max(1, epm)) * 100)

kpi_html = (
    '<div class="kpi-grid">'
    + kpi("Viewers actifs", str(total_viewers),    "👁️", BLUE,   "#2a6fb0", f"{n_rooms} salon(s)")
    + kpi("Salons actifs",  str(n_rooms),           "📺", PURPLE, PINK,      "en cours")
    + kpi("Événements/min", str(epm),               "⚡", GREEN,  "#16a34a", f"{total_events:,} total")
    + kpi("Index d'ennui",  f"{bored_score_global:.0f}%", "🧠", AMBER,  RED,  f"{seek_rate} seeks/min")
    + kpi("Uptime serveur", uptime_str,             "🖥️", MUTED,  BORDER, "Watch Together")
    + '</div>'
)
st.markdown(kpi_html, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ROOMS GRID
# ============================================================
if not rooms_data:
    st.markdown(f"""
    <div style="text-align:center;padding:4rem;background:{PANEL};border:1px solid {BORDER};border-radius:18px;">
      <div style="font-size:3rem;margin-bottom:1rem;">🎬</div>
      <div style="font-size:1.2rem;font-weight:700;margin-bottom:0.5rem;">Aucun salon actif</div>
      <div style="color:{MUTED};">Créez un salon dans Watch Together pour voir les analytics apparaître ici.</div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(refresh_sec)
    st.rerun()
    st.stop()

st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:1rem;">📺 Salons en direct ({n_rooms})</div>', unsafe_allow_html=True)

room_cols = st.columns(min(n_rooms, 4))
for i, room in enumerate(rooms_data):
    with room_cols[i % min(n_rooms, 4)]:
        thumb = room.get("video_thumbnail") or ""
        title = room.get("video_title") or "Aucune vidéo"
        t_sec = int(room.get("current_video_time", 0))
        t_str = f"{t_sec//60:02d}:{t_sec%60:02d}"
        is_playing = room.get("is_playing", False)
        vc = room.get("viewer_count", 0)
        ev5 = room.get("events_last_5min", 0)
        bored5 = (room.get("seeks_last_5min", 0) * 0.4 + room.get("pauses_last_5min", 0) * 0.05) / max(1, ev5) if ev5 > 0 else 0
        bored_color = RED if bored5 > 0.3 else (AMBER if bored5 > 0.15 else GREEN)

        thumb_style = f"background-image:url('{thumb}');background-size:cover;background-position:center;" if thumb else f"background:linear-gradient(135deg,rgba(138,46,207,0.4),rgba(214,34,138,0.3));"

        st.markdown(f"""
        <div class="room-card">
          <div class="room-thumb" style="{thumb_style}">
            <div style="position:absolute;top:8px;left:8px;">
              <div class="live-badge" style="padding:3px 8px;font-size:0.6rem;">
                <span class="live-dot" style="width:6px;height:6px;"></span>
                {'▶ PLAY' if is_playing else '⏸ PAUSE'}
              </div>
            </div>
            <div style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.7);border-radius:6px;padding:3px 8px;font-size:0.7rem;font-family:monospace;">
              {t_str}
            </div>
            <div style="position:absolute;bottom:8px;left:8px;background:rgba(0,0,0,0.7);border-radius:6px;padding:3px 8px;font-size:0.7rem;">
              👥 {vc}
            </div>
          </div>
          <div class="room-body">
            <div class="room-name">{room.get('room_name','?')}</div>
            <div class="room-video">▶ {title}</div>
            <div class="room-meta" style="margin-top:6px;display:flex;gap:10px;">
              <span style="color:{bored_color};">● Ennui {bored5*100:.0f}%</span>
              <span>{ev5} événements/5min</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ROOM SELECTOR — ANALYSE DÉTAILLÉE
# ============================================================
room_names = {r["room_id"]: f"📺 {r['room_name']} — {r.get('video_title','?')}" for r in rooms_data}
selected_room_id = st.selectbox("Sélectionner un salon pour l'analyse détaillée", list(room_names.keys()), format_func=lambda x: room_names[x])
selected_room = next((r for r in rooms_data if r["room_id"] == selected_room_id), None)

if selected_room:
    st.markdown(f"""
    <div style="background:{PANEL};border:1px solid {BORDER};border-left:3px solid {PINK};border-radius:14px;padding:20px 24px;margin-bottom:1.5rem;">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div>
          <div style="font-size:0.65rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;">Analyse en cours</div>
          <div style="font-size:1.5rem;font-weight:800;margin-top:4px;">{selected_room.get('room_name')}</div>
          <div style="color:{PINK};font-size:0.85rem;margin-top:2px;">▶ {selected_room.get('video_title','—')} · {selected_room.get('video_genre','')}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.7rem;color:{MUTED};">Viewers connectés</div>
          <div style="font-size:2rem;font-weight:800;">{selected_room.get('viewer_count',0)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    room_events = [e for e in events if e.get("session_id") == selected_room_id]
    seg_df, zones_df = build_segments(room_events, selected_room_id)

    # Insights
    st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">🤖 Insights automatiques</div>', unsafe_allow_html=True)
    for ins in auto_insights(seg_df, zones_df, selected_room.get("room_name","?")):
        st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([3, 1])

    with col_left:
        # Filmstrip
        st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">🎞️ Timeline — pellicule de visionnage</div>', unsafe_allow_html=True)
        st.markdown(filmstrip(seg_df, zones_df, min_bored), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Courbe de rétention
        st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">📈 Courbe de rétention réelle</div>', unsafe_allow_html=True)
        if not seg_df.empty:
            fig = go.Figure()
            fig.update_layout(**PLOTLY_LAYOUT)
            fig.add_trace(go.Scatter(
                x=seg_df["start"], y=seg_df["completion_rate"],
                mode="lines+markers", name="Rétention réelle",
                line=dict(color=PINK, width=3),
                marker=dict(size=6, color=PINK),
                fill="tozeroy", fillcolor="rgba(214,34,138,0.08)",
            ))
            fig.add_trace(go.Scatter(
                x=seg_df["start"], y=seg_df["bored_score"],
                mode="lines", name="Score d'ennui",
                line=dict(color=AMBER, width=2, dash="dot"),
            ))
            for _, z in zones_df.iterrows():
                if z["avg_score"] >= min_bored:
                    fig.add_vrect(x0=z["zone_start"], x1=z["zone_end"], fillcolor=RED, opacity=0.12, line_width=0,
                                  annotation_text="⚠️", annotation_position="top left",
                                  annotation_font_color=RED, annotation_font_size=10)
            t_cur = selected_room.get("current_video_time", 0)
            if t_cur > 0:
                fig.add_vline(x=t_cur, line_color=GREEN, line_width=2, line_dash="dash",
                              annotation_text="▶ maintenant", annotation_font_color=GREEN, annotation_font_size=10)
            fig.update_layout(height=380, xaxis_title="Temps (s)", yaxis_title="Taux", yaxis_range=[0, 1.05],
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:40px;text-align:center;color:{MUTED};">⏳ En attente des données de lecture...</div>', unsafe_allow_html=True)

        # Zones d'ennui
        if not zones_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">🔥 Zones d\'ennui détectées</div>', unsafe_allow_html=True)
            fig_z = go.Figure()
            fig_z.update_layout(**PLOTLY_LAYOUT)
            for _, z in zones_df.iterrows():
                fig_z.add_trace(go.Bar(
                    x=[f"{int(z['zone_start'])}s→{int(z['zone_end'])}s"],
                    y=[z["avg_score"] * 100],
                    marker_color=f"rgba(239,68,68,{0.4 + z['avg_score']*0.6:.2f})",
                    text=[f"{z['avg_score']*100:.0f}%"],
                    textposition="outside", textfont=dict(color=TEXT),
                ))
            fig_z.update_layout(height=240, yaxis_title="Score d'ennui (%)", showlegend=False)
            st.plotly_chart(fig_z, use_container_width=True)

    with col_right:
        # Event feed
        st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">⚡ Flux d\'événements</div>', unsafe_allow_html=True)
        ev_icons = {"play": ("ev-play","▶"), "pause": ("ev-pause","⏸"), "seek": ("ev-seek","⏩")}
        feed_html = f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;max-height:480px;overflow-y:auto;">'
        last_ev = sorted(room_events, key=lambda e: e.get("timestamp_wall",""), reverse=True)[:30]
        if last_ev:
            for e in last_ev:
                ev_type = e.get("event_type","?")
                cls, icon = ev_icons.get(ev_type, ("ev-seek","?"))
                t_wall = e.get("timestamp_wall","")[:19].replace("T"," ")
                t_vid  = f"{int(e.get('timestamp_video',0))//60:02d}:{int(e.get('timestamp_video',0))%60:02d}"
                user   = e.get("user_id","?")[:12]
                feed_html += (f'<div class="event-item">'
                              f'<span class="event-pill {cls}">{icon} {ev_type}</span>'
                              f'<div><div style="color:{TEXT};font-size:0.75rem;">{user}</div>'
                              f'<div style="color:{MUTED};font-size:0.65rem;">{t_vid} · {t_wall[-8:]}</div></div>'
                              f'</div>')
        else:
            feed_html += f'<div style="padding:20px;text-align:center;color:{MUTED};font-size:0.8rem;">En attente...</div>'
        feed_html += "</div>"
        st.markdown(feed_html, unsafe_allow_html=True)

        # Stats segment
        if not seg_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">📊 Stats session</div>', unsafe_allow_html=True)
            stats_html = f'<div style="background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:14px;">'
            items = [
                ("Viewers max", str(int(seg_df["n_viewers_reached"].max()))),
                ("Complétion moy.", f"{seg_df['completion_rate'].mean()*100:.1f}%"),
                ("Score ennui max", f"{seg_df['bored_score'].max()*100:.0f}%"),
                ("Total pauses", str(int(seg_df["n_pauses"].sum()))),
                ("Total seeks", str(int(seg_df["n_seeks"].sum()))),
                ("Segments analysés", str(len(seg_df))),
            ]
            for label, val in items:
                stats_html += (f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                               f'border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.78rem;">'
                               f'<span style="color:{MUTED};">{label}</span>'
                               f'<span style="font-weight:700;">{val}</span></div>')
            stats_html += "</div>"
            st.markdown(stats_html, unsafe_allow_html=True)

    # ============================================================
    # DÉTAIL PAR SEGMENT
    # ============================================================
    if not seg_df.empty:
        st.markdown("---")
        st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">🔍 Détail par segment</div>', unsafe_allow_html=True)
        detail = seg_df[["segment_id","start","end","n_viewers_reached","completion_rate","dropoff_rate","n_pauses","n_seeks","bored_score","is_bored"]].copy()
        detail["completion_rate"] = (detail["completion_rate"]*100).round(1).astype(str) + "%"
        detail["dropoff_rate"]    = (detail["dropoff_rate"]*100).round(1).astype(str) + "%"
        detail["bored_score"]     = (detail["bored_score"]*100).round(1).astype(str) + "%"
        detail.columns = ["Segment","Début (s)","Fin (s)","Viewers","Complétion","Drop-off","Pauses","Seeks","Ennui","Zone ennui"]
        st.dataframe(detail, use_container_width=True, hide_index=True, height=280)

    # ============================================================
    # SIMULATEUR WHAT-IF
    # ============================================================
    if not seg_df.empty and not zones_df.empty:
        st.markdown("---")
        st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:0.4rem;">🎬 Simulateur "What-If" — impact d\'un montage</div>', unsafe_allow_html=True)
        st.caption("Sélectionnez une zone d'ennui à couper : on simule l'effet sur la rétention si ce passage était supprimé.")
        zone_options = [f"{int(z['zone_start'])}s – {int(z['zone_end'])}s  (score {z['avg_score']:.2f})" for _, z in zones_df.iterrows()]
        chosen = st.selectbox("Zone à simuler en suppression", zone_options, key="whatif_sel")
        chosen_idx = zone_options.index(chosen)
        chosen_zone = zones_df.iloc[chosen_idx]
        cut_start, cut_end = chosen_zone["zone_start"], chosen_zone["zone_end"]
        cut_dur = cut_end - cut_start
        sim = seg_df.sort_values("start").reset_index(drop=True)
        before = sim[sim["end"] <= cut_start]
        after  = sim[sim["start"] >= cut_end].copy()
        if len(before) > 0 and len(after) > 0:
            orig_drop = before.iloc[-1]["completion_rate"] - after.iloc[0]["completion_rate"]
            after["completion_rate_sim"] = (after["completion_rate"] + orig_drop).clip(upper=1.0)
            before["completion_rate_sim"] = before["completion_rate"]
            sim_full = pd.concat([before, after])
            gain = (sim_full["completion_rate_sim"].iloc[-1] - seg_df["completion_rate"].iloc[-1]) * 100
            fig_sim = go.Figure()
            fig_sim.update_layout(**PLOTLY_LAYOUT)
            fig_sim.add_trace(go.Scatter(x=seg_df["start"], y=seg_df["completion_rate"], mode="lines", name="Rétention actuelle", line=dict(color=MUTED, width=2)))
            fig_sim.add_trace(go.Scatter(x=sim_full["start"], y=sim_full["completion_rate_sim"], mode="lines", name="Rétention simulée (coupe)", line=dict(color=GREEN, width=3, dash="dash")))
            fig_sim.add_vrect(x0=cut_start, x1=cut_end, fillcolor=RED, opacity=0.15, line_width=0)
            fig_sim.update_layout(height=340, xaxis_title="Temps (s)", yaxis_title="Rétention", yaxis_range=[0,1.05], legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_sim, use_container_width=True)
            color_gain = GREEN if gain > 0 else RED
            st.markdown(f'<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.3);border-radius:10px;padding:14px 18px;font-size:0.9rem;">💡 En coupant ce passage de <b>{int(cut_dur)}s</b>, la rétention finale passerait de <b>{seg_df["completion_rate"].iloc[-1]*100:.1f}%</b> à <b>{sim_full["completion_rate_sim"].iloc[-1]*100:.1f}%</b> — gain estimé : <span style="color:{color_gain};font-weight:800;">+{gain:.1f} pts</span></div>', unsafe_allow_html=True)
        else:
            st.info("Pas assez de segments avant/après cette zone pour simuler.")

st.markdown("---")

# ============================================================
# VUE GLOBALE — Toutes les rooms
# ============================================================
st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin-bottom:1rem;">🌐 Vue globale — toutes les rooms</div>', unsafe_allow_html=True)

all_seg, _ = build_segments(events)
if not all_seg.empty:
    c1, c2 = st.columns(2)
    with c1:
        # Rétention par room
        fig_g = go.Figure()
        fig_g.update_layout(**PLOTLY_LAYOUT)
        colors = [PINK, PURPLE, GREEN, AMBER, BLUE, RED]
        for idx, (rid, grp) in enumerate(all_seg.groupby("session_id")):
            room_name = next((r["room_name"] for r in rooms_data if r["room_id"] == rid), rid)
            fig_g.add_trace(go.Scatter(
                x=grp["start"], y=grp["completion_rate"],
                mode="lines", name=room_name,
                line=dict(color=colors[idx % len(colors)], width=2),
            ))
        fig_g.update_layout(height=300, title_text="Rétention par salon",
                             title_font=dict(color=TEXT, size=13),
                             xaxis_title="Temps (s)", yaxis_title="Rétention", yaxis_range=[0,1.05])
        st.plotly_chart(fig_g, use_container_width=True)

    with c2:
        # Score ennui par room
        bored_by_room = all_seg.groupby("session_id")["bored_score"].mean().reset_index()
        bored_by_room["room_name"] = bored_by_room["session_id"].map(
            {r["room_id"]: r["room_name"] for r in rooms_data}
        ).fillna(bored_by_room["session_id"])
        fig_b = go.Figure()
        fig_b.update_layout(**PLOTLY_LAYOUT)
        fig_b.add_trace(go.Bar(
            x=bored_by_room["room_name"],
            y=bored_by_room["bored_score"] * 100,
            marker_color=[RED if v > 0.3 else (AMBER if v > 0.15 else GREEN)
                          for v in bored_by_room["bored_score"]],
            text=[f"{v*100:.0f}%" for v in bored_by_room["bored_score"]],
            textposition="outside", textfont=dict(color=TEXT),
        ))
        fig_b.update_layout(height=300, title_text="Score d'ennui moyen par salon",
                             title_font=dict(color=TEXT, size=13),
                             yaxis_title="Score (%)", showlegend=False)
        st.plotly_chart(fig_b, use_container_width=True)

    # Tableau global
    st.markdown(f'<div style="font-size:0.75rem;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:2px;margin:1rem 0 0.6rem;">📋 Tableau récapitulatif</div>', unsafe_allow_html=True)
    overview = all_seg.groupby("session_id").agg(
        completion_finale=("completion_rate","last"),
        bored_score_moy=("bored_score","mean"),
        total_pauses=("n_pauses","sum"),
        total_seeks=("n_seeks","sum"),
        n_segments=("segment_id","count"),
    ).reset_index()
    overview["salon"] = overview["session_id"].map({r["room_id"]: r["room_name"] for r in rooms_data}).fillna(overview["session_id"])
    overview["vidéo"] = overview["session_id"].map({r["room_id"]: r.get("video_title","—") for r in rooms_data}).fillna("—")
    overview["complétion (%)"] = (overview["completion_finale"] * 100).round(1)
    overview["ennui (%)"] = (overview["bored_score_moy"] * 100).round(1)
    st.dataframe(
        overview[["salon","vidéo","complétion (%)","ennui (%)","total_pauses","total_seeks","n_segments"]],
        use_container_width=True, hide_index=True,
    )
else:
    st.markdown(f'<div style="text-align:center;padding:3rem;background:{PANEL};border:1px solid {BORDER};border-radius:16px;color:{MUTED};">⏳ En attente des données de lecture — faites play/pause/seek dans Watch Together</div>', unsafe_allow_html=True)

st.markdown("---")

# Export
csv_link = f"{wt_url_input.rstrip('/')}/api/live-events/csv"
st.markdown(f"""
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
  <a href="{csv_link}" target="_blank" style="background:linear-gradient(90deg,{PINK},{PURPLE});color:white;font-weight:700;padding:10px 20px;border-radius:10px;text-decoration:none;font-size:0.85rem;">
    ⬇️ Télécharger les événements (CSV)
  </a>
  <div style="font-size:0.75rem;color:{MUTED};">{total_events:,} événements collectés · {len(rooms_data)} salon(s) actif(s)</div>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
time.sleep(0.5)
if refresh_sec <= 30:
    time.sleep(refresh_sec - 0.5)
    st.rerun()
