import { useEffect, useRef, useState } from "react";
import { VIDEO_LIBRARY } from "./videos.js";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:4000";
const HTTP_URL = WS_URL.replace(/^ws/, "http");

export default function Dashboard({ name, isAdmin, onJoinRoom, onLogout }) {
  const [rooms, setRooms] = useState([]);
  const [waitingUsers, setWaitingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // null | "create" | "assign"
  const [newRoomName, setNewRoomName] = useState("");
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [assignTarget, setAssignTarget] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    fetch(`${HTTP_URL}/api/rooms`).then(r=>r.json()).then(d=>{setRooms(d);setLoading(false);}).catch(()=>setLoading(false));
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.type === "global_state") {
        setRooms(m.rooms || []);
        setWaitingUsers(m.waiting || []);
        setLoading(false);
      }
      // Compatibilité ancien format
      if (m.type === "room_list") setRooms(m.rooms || []);
      if (m.type === "waiting_list") setWaitingUsers(m.users || []);
    };
    return () => ws.close();
  }, []);

  const approveUser = (targetId) => {
    wsRef.current?.send(JSON.stringify({ type: "approve_user", targetId }));
  };
  const approveAll = () => {
    wsRef.current?.send(JSON.stringify({ type: "approve_all" }));
  };
  const rejectUser = (targetId) => {
    wsRef.current?.send(JSON.stringify({ type: "reject_user", targetId }));
  };

  async function createRoom() {
    const n = newRoomName.trim();
    if (!n) return;
    const video = selectedVideo ? {
      mode: selectedVideo.type === "youtube" ? "youtube" : "hls",
      url: selectedVideo.url || null,
      videoId: selectedVideo.videoId || null,
      title: selectedVideo.title,
      thumbnail: selectedVideo.thumbnail,
      videoLibId: selectedVideo.id,
    } : null;
    const res = await fetch(`${HTTP_URL}/api/rooms`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ name: n, video }),
    });
    const room = await res.json();
    setModal(null); setNewRoomName(""); setSelectedVideo(null);
    onJoinRoom({ id: room.id, name: room.name }, true);
  }

  async function assignVideoToRoom(room) {
    if (!selectedVideo) return;
    // On rejoint la room en admin et on y enverra le content_change
    setModal(null);
    onJoinRoom({ id: room.id, name: room.name, pendingVideo: selectedVideo }, true);
  }

  async function deleteRoom(roomId, e) {
    e.stopPropagation();
    if (!confirm("Fermer cette room et déconnecter ses membres ?")) return;
    await fetch(`${HTTP_URL}/api/rooms/${roomId}`, { method:"DELETE" });
  }

  const sorted = [...rooms].sort((a,b) => b.viewerCount - a.viewerCount);

  return (
    <div style={s.container}>
      <style>{`
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        .room-card:hover{transform:translateY(-5px) scale(1.02)!important;box-shadow:0 24px 60px rgba(0,0,0,0.7)!important}
        .room-card:hover .hover-overlay{opacity:1!important}
        .vid-card:hover{border-color:rgba(214,34,138,0.8)!important;transform:scale(1.03)}
        .vid-card.selected{border-color:#d6228a!important;box-shadow:0 0 0 2px rgba(214,34,138,0.4)}
        .btn:hover{filter:brightness(1.15);transform:translateY(-1px)}
        ::-webkit-scrollbar{width:5px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.12);border-radius:3px}
        input::placeholder{color:rgba(255,255,255,0.3)} input:focus{border-color:rgba(214,34,138,0.6)!important;outline:none}
      `}</style>

      {/* Barre d'actions */}
      <div style={s.header}>
        <div style={{ display:"flex", alignItems:"center", gap:"0.5rem" }}>
          <div style={s.userBadge}>{isAdmin?"👑 Administrateur":"👀 Invité"}</div>
          <span style={{ color:"rgba(255,255,255,0.35)", fontSize:"0.8rem" }}>· {rooms.length} salon{rooms.length>1?"s":""} actif{rooms.length>1?"s":""}</span>
        </div>
        <div style={s.hr}>
          {isAdmin && <button className="btn" style={{ ...s.primaryBtn, transition:"all 0.2s" }} onClick={()=>{ setModal("create"); setSelectedVideo(null); setNewRoomName(""); }}>+ Nouveau salon</button>}
          {isAdmin && <button className="btn" style={{ ...s.secondaryBtn, transition:"all 0.2s" }} onClick={()=>{ setAssignTarget(null); setSelectedVideo(null); setModal("assign"); }}>🎬 Assigner une vidéo</button>}
        </div>
      </div>

      {/* ===== PANNEAU LISTE D'ATTENTE (admin seulement) ===== */}
      {isAdmin && waitingUsers.length > 0 && (
        <div style={wl.banner}>
          <div style={wl.bannerLeft}>
            <div style={wl.pulse} />
            <span style={wl.bannerTitle}>
              🧍 {waitingUsers.length} invité{waitingUsers.length > 1 ? "s" : ""} en attente d'approbation
            </span>
          </div>
          <button style={wl.approveAllBtn} onClick={approveAll}>
            ✓ Approuver tout ({waitingUsers.length})
          </button>
        </div>
      )}

      {isAdmin && waitingUsers.length > 0 && (
        <div style={wl.listWrap}>
          <div style={wl.listGrid}>
            {waitingUsers.map((u, i) => (
              <div key={u.clientId} style={{ ...wl.userCard, animationDelay: `${i * 0.05}s` }}>
                <div style={wl.avatar}>{u.name.charAt(0).toUpperCase()}</div>
                <div style={wl.userInfo}>
                  <div style={wl.userName}>{u.name}</div>
                  <div style={wl.userTime}>
                    En attente depuis {Math.floor((Date.now() - u.connectedAt) / 1000)}s
                  </div>
                </div>
                <div style={wl.actions}>
                  <button style={wl.approveBtn} onClick={() => approveUser(u.clientId)} title="Approuver">
                    ✓ Approuver
                  </button>
                  <button style={wl.rejectBtn} onClick={() => rejectUser(u.clientId)} title="Refuser">
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal créer room */}
      {modal==="create" && (
        <div style={s.overlay} onClick={()=>setModal(null)}>
          <div style={s.modal} onClick={e=>e.stopPropagation()}>
            <div style={s.modalHeader}>
              <h2 style={s.modalTitle}>Créer un nouveau salon</h2>
              <button style={s.closeBtn} onClick={()=>setModal(null)}>✕</button>
            </div>

            <label style={s.fieldLabel}>Nom du salon</label>
            <input style={s.modalInput} value={newRoomName} onChange={e=>setNewRoomName(e.target.value)}
              placeholder="Ex : Équipe Design, Room VIP, Séance 1..." autoFocus
              onKeyDown={e=>{ if(e.key==="Enter"&&newRoomName.trim()) createRoom(); if(e.key==="Escape") setModal(null); }} />

            <div style={{ marginBottom:"0.8rem" }}>
              <label style={s.fieldLabel}>Choisir une vidéo à diffuser (optionnel)</label>
              <div style={s.vidGrid}>
                {VIDEO_LIBRARY.map(v => (
                  <div key={v.id} className={`vid-card${selectedVideo?.id===v.id?" selected":""}`}
                    style={{ ...s.vidCard, transition:"all 0.15s" }}
                    onClick={()=>setSelectedVideo(selectedVideo?.id===v.id?null:v)}>
                    <div style={s.vidThumb}>
                      {v.thumbnail
                        ? <img src={v.thumbnail} alt={v.title} style={s.vidThumbImg} onError={e=>{e.target.style.display="none";}} />
                        : <div style={{ ...s.vidThumbFallback, background: v.color||"#333" }} />
                      }
                      {selectedVideo?.id===v.id && <div style={s.selectedMark}>✓</div>}
                    </div>
                    <div style={s.vidInfo}>
                      <div style={s.vidTitle}>{v.title}</div>
                      <div style={s.vidMeta}>{v.genre} · {v.duration}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {selectedVideo && (
              <div style={s.selectedPreview}>
                <span style={{ fontSize:"0.8rem", color:"rgba(255,255,255,0.5)" }}>Vidéo sélectionnée :</span>
                <strong style={{ color:"#d6228a" }}> {selectedVideo.title}</strong>
              </div>
            )}

            <div style={{ display:"flex", gap:"0.8rem", marginTop:"1.2rem" }}>
              <button className="btn" style={{ ...s.primaryBtn, flex:1, padding:"0.8rem", transition:"all 0.2s", opacity:!newRoomName.trim()?0.5:1 }}
                disabled={!newRoomName.trim()} onClick={createRoom}>
                Créer et entrer dans le salon →
              </button>
              <button style={{ ...s.logoutBtn, padding:"0.8rem 1.2rem" }} onClick={()=>setModal(null)}>Annuler</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal assigner vidéo à une room existante */}
      {modal==="assign" && (
        <div style={s.overlay} onClick={()=>setModal(null)}>
          <div style={{ ...s.modal, maxWidth:"780px" }} onClick={e=>e.stopPropagation()}>
            <div style={s.modalHeader}>
              <h2 style={s.modalTitle}>🎬 Assigner une vidéo à un salon</h2>
              <button style={s.closeBtn} onClick={()=>setModal(null)}>✕</button>
            </div>

            {rooms.length===0 && <p style={{ color:"rgba(255,255,255,0.5)", textAlign:"center", padding:"2rem" }}>Aucun salon actif. Créez-en un d'abord.</p>}

            {rooms.length>0 && (
              <>
                <label style={s.fieldLabel}>1 · Choisir le salon cible</label>
                <div style={{ display:"flex", gap:"0.5rem", marginBottom:"1.2rem", flexWrap:"wrap" }}>
                  {rooms.map(r => (
                    <div key={r.id} onClick={()=>setAssignTarget(r)}
                      style={{ ...s.roomChip, borderColor: assignTarget?.id===r.id?"#d6228a":"rgba(255,255,255,0.15)", background: assignTarget?.id===r.id?"rgba(214,34,138,0.15)":"rgba(255,255,255,0.05)", cursor:"pointer", transition:"all 0.15s" }}>
                      {r.name} <span style={{ color:"rgba(255,255,255,0.4)", fontSize:"0.7rem" }}>· {r.viewerCount} en ligne</span>
                    </div>
                  ))}
                </div>

                <label style={s.fieldLabel}>2 · Choisir la vidéo</label>
                <div style={s.vidGrid}>
                  {VIDEO_LIBRARY.map(v => (
                    <div key={v.id} className={`vid-card${selectedVideo?.id===v.id?" selected":""}`}
                      style={{ ...s.vidCard, transition:"all 0.15s" }}
                      onClick={()=>setSelectedVideo(selectedVideo?.id===v.id?null:v)}>
                      <div style={s.vidThumb}>
                        {v.thumbnail
                          ? <img src={v.thumbnail} alt={v.title} style={s.vidThumbImg} onError={e=>{e.target.style.display="none";}} />
                          : <div style={{ ...s.vidThumbFallback, background:v.color||"#333" }} />
                        }
                        {selectedVideo?.id===v.id && <div style={s.selectedMark}>✓</div>}
                      </div>
                      <div style={s.vidInfo}>
                        <div style={s.vidTitle}>{v.title}</div>
                        <div style={s.vidMeta}>{v.genre} · {v.duration}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display:"flex", gap:"0.8rem", marginTop:"1.2rem" }}>
                  <button className="btn"
                    style={{ ...s.primaryBtn, flex:1, padding:"0.8rem", transition:"all 0.2s", opacity:(!assignTarget||!selectedVideo)?0.5:1 }}
                    disabled={!assignTarget||!selectedVideo}
                    onClick={()=>assignVideoToRoom(assignTarget)}>
                    Entrer dans le salon et diffuser →
                  </button>
                  <button style={{ ...s.logoutBtn, padding:"0.8rem 1.2rem" }} onClick={()=>setModal(null)}>Annuler</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Body */}
      <div style={s.body}>
        {isAdmin && (
          <div style={s.section}>
            <div style={s.sectionTitle}>🎬 Bibliothèque vidéo ({VIDEO_LIBRARY.length} titres)</div>
            <div style={s.libGrid}>
              {VIDEO_LIBRARY.map((v,i) => (
                <div key={v.id} style={{ ...s.libCard, animationDelay:`${i*0.03}s` }}>
                  <div style={s.libThumb}>
                    {v.thumbnail
                      ? <img src={v.thumbnail} alt={v.title} style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none";}} />
                      : <div style={{ ...s.libThumbFallback, background:v.color||"#333" }}>{v.title[0]}</div>
                    }
                    <div style={s.libTypeBadge}>{v.type==="youtube"?"▶ YouTube":"📡 HLS"}</div>
                  </div>
                  <div style={s.libInfo}>
                    <div style={s.libTitle}>{v.title}</div>
                    <div style={s.libMeta}>{v.year} · {v.duration}</div>
                    <div style={s.libGenre}>{v.genre}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {loading ? (
          <div style={s.emptyState}><div style={{ fontSize:"2rem", animation:"pulse 1.5s infinite" }}>⏳</div><p>Chargement...</p></div>
        ) : (
          <div style={s.section}>
            <div style={s.sectionTitle}>
              {isAdmin ? `📺 Salons actifs (${rooms.length})` : `🎬 Salons disponibles — choisissez votre programme`}
              {isAdmin && <span style={{ marginLeft:"0.8rem", fontSize:"0.8rem", color:"rgba(255,255,255,0.4)" }}>Cliquez pour entrer et monitorer</span>}
            </div>

            {rooms.length===0 ? (
              <div style={s.emptyState}>
                <div style={{ fontSize:"4rem", marginBottom:"1rem" }}>🎬</div>
                <h2 style={{ margin:"0 0 0.5rem", fontSize:"1.3rem" }}>Aucun salon actif</h2>
                <p style={{ color:"rgba(255,255,255,0.4)", marginBottom:"1.5rem" }}>
                  {isAdmin ? "Créez votre premier salon pour commencer." : "Aucun salon disponible pour le moment. Revenez plus tard."}
                </p>
                {isAdmin && <button className="btn" style={{ ...s.primaryBtn, transition:"all 0.2s" }} onClick={()=>{ setModal("create"); setSelectedVideo(null); setNewRoomName(""); }}>+ Créer le premier salon</button>}
              </div>
            ) : (
              <div style={s.roomGrid}>
                {sorted.map((room, i) => (
                  <RoomCard key={room.id} room={room} isAdmin={isAdmin} index={i}
                    onJoin={()=>onJoinRoom(room, isAdmin)}
                    onDelete={(e)=>deleteRoom(room.id,e)}
                    onAssign={()=>{ setAssignTarget(room); setSelectedVideo(null); setModal("assign"); }}
                  />
                ))}
                {isAdmin && (
                  <div style={s.addCard} onClick={()=>{ setModal("create"); setSelectedVideo(null); setNewRoomName(""); }}>
                    <div style={{ fontSize:"2.5rem", marginBottom:"0.6rem" }}>+</div>
                    <div style={{ fontWeight:"700" }}>Nouveau salon</div>
                    <div style={{ fontSize:"0.8rem", color:"rgba(255,255,255,0.35)", marginTop:"0.3rem" }}>Créer et diffuser</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function RoomCard({ room, isAdmin, index, onJoin, onDelete, onAssign }) {
  const thumb = room.contentThumbnail;
  const title = room.contentTitle;

  return (
    <div className="room-card" style={{ ...s.roomCard, animationDelay:`${index*0.05}s` }} onClick={onJoin}>
      {/* Thumbnail */}
      <div style={s.roomThumb}>
        {thumb
          ? <img src={thumb} alt={title||""} style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none";}} />
          : <div style={s.roomThumbFallback}>
              <span style={{ fontSize:"2.5rem" }}>
                {room.contentMode==="youtube"?"▶️":room.contentMode==="screen"?"🖥️":room.contentMode==="file"?"🎬":room.contentMode==="image"?"🖼️":"📡"}
              </span>
            </div>
        }

        {/* Badges */}
        {room.hasPresenter && (
          <div style={s.liveDot}>
            <span style={{ width:"7px", height:"7px", borderRadius:"50%", background:"#ef4444", animation:"pulse 1s infinite", display:"inline-block" }}/>
            LIVE
          </div>
        )}

        {/* Viewers */}
        <div style={s.viewerBadge}>
          <span style={{ width:"6px", height:"6px", borderRadius:"50%", background:room.viewerCount>0?"#22c55e":"rgba(255,255,255,0.3)", display:"inline-block" }}/>
          {room.viewerCount} en ligne
        </div>

        {/* Overlay au hover */}
        <div className="hover-overlay" style={s.hoverOverlay}>
          <div style={s.joinPill}>{isAdmin?"Entrer & monitorer →":"Rejoindre →"}</div>
        </div>

        {/* Admin actions */}
        {isAdmin && (
          <div style={{ position:"absolute", top:"0.5rem", right:"0.5rem", display:"flex", gap:"0.3rem", zIndex:3 }} onClick={e=>e.stopPropagation()}>
            <button style={s.miniBtn} onClick={onAssign} title="Changer la vidéo">🎬</button>
            <button style={{ ...s.miniBtn, color:"#ef4444" }} onClick={onDelete} title="Fermer la room">✕</button>
          </div>
        )}
      </div>

      {/* Infos */}
      <div style={s.roomBody}>
        <div style={s.roomName}>{room.name}</div>
        {title && <div style={s.roomVideoTitle}>▶ {title}</div>}
        <div style={s.roomMeta}>
          <span style={{ color: room.hasPresenter?"#22c55e":"rgba(255,255,255,0.35)" }}>
            {room.hasPresenter?"🎤 Présentateur actif":"⏸ En attente"}
          </span>
          <span style={{ fontFamily:"monospace", fontSize:"0.65rem", color:"rgba(255,255,255,0.2)" }}>#{room.id}</span>
        </div>
      </div>
    </div>
  );
}

const s = {
  container: { flex: 1, color: "white", fontFamily: "'Segoe UI',system-ui,sans-serif", display: "flex", flexDirection: "column" },
  header: { display:"flex", justifyContent:"space-between", alignItems:"center", padding:"1rem 2rem", background:"rgba(0,0,0,0.4)", borderBottom:"1px solid rgba(255,255,255,0.06)", backdropFilter:"blur(10px)", flexWrap:"wrap", gap:"0.8rem" },
  hl: { display:"flex", alignItems:"center", gap:"1rem" },
  logo: { width:"42px", height:"42px", background:"linear-gradient(135deg,#d6228a,#8a2ecf)", borderRadius:"12px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"1.2rem", boxShadow:"0 4px 15px rgba(214,34,138,0.4)", flexShrink:0 },
  appName: { fontWeight:"800", fontSize:"1.1rem" },
  welcome: { fontSize:"0.8rem", color:"rgba(255,255,255,0.5)" },
  hr: { display:"flex", alignItems:"center", gap:"0.8rem", flexWrap:"wrap" },
  userBadge: { background:"rgba(255,255,255,0.08)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"999px", padding:"0.3rem 0.9rem", fontSize:"0.8rem", fontWeight:"600" },
  primaryBtn: { background:"linear-gradient(135deg,#d6228a,#8a2ecf)", color:"white", border:"none", borderRadius:"10px", padding:"0.5rem 1.1rem", fontWeight:"700", fontSize:"0.88rem", cursor:"pointer", boxShadow:"0 4px 15px rgba(214,34,138,0.3)" },
  secondaryBtn: { background:"rgba(255,255,255,0.08)", color:"white", border:"1px solid rgba(255,255,255,0.15)", borderRadius:"10px", padding:"0.5rem 1rem", fontWeight:"600", fontSize:"0.88rem", cursor:"pointer" },
  logoutBtn: { background:"rgba(255,255,255,0.06)", color:"rgba(255,255,255,0.7)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"10px", padding:"0.5rem 1rem", fontSize:"0.85rem", cursor:"pointer" },

  overlay: { position:"fixed", inset:0, background:"rgba(0,0,0,0.8)", backdropFilter:"blur(8px)", display:"flex", alignItems:"flex-start", justifyContent:"center", zIndex:1000, overflowY:"auto", padding:"2rem" },
  modal: { background:"rgba(15,8,30,0.97)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"22px", padding:"2rem", width:"100%", maxWidth:"720px", boxShadow:"0 30px 80px rgba(0,0,0,0.8)", color:"white", marginTop:"2rem" },
  modalHeader: { display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"1.5rem" },
  modalTitle: { margin:0, fontSize:"1.4rem", fontWeight:"800" },
  closeBtn: { background:"rgba(255,255,255,0.08)", border:"none", color:"white", borderRadius:"8px", width:"32px", height:"32px", cursor:"pointer", fontSize:"0.9rem" },
  fieldLabel: { display:"block", fontSize:"0.75rem", fontWeight:"700", color:"rgba(255,255,255,0.5)", textTransform:"uppercase", letterSpacing:"0.8px", marginBottom:"0.6rem" },
  modalInput: { width:"100%", padding:"0.85rem 1rem", borderRadius:"12px", border:"1px solid rgba(255,255,255,0.12)", background:"rgba(255,255,255,0.07)", color:"white", fontSize:"0.95rem", boxSizing:"border-box", marginBottom:"1.3rem" },

  vidGrid: { display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(140px,1fr))", gap:"0.7rem", maxHeight:"320px", overflowY:"auto", paddingRight:"4px" },
  vidCard: { border:"2px solid rgba(255,255,255,0.08)", borderRadius:"12px", overflow:"hidden", cursor:"pointer", transition:"all 0.15s", background:"rgba(255,255,255,0.03)" },
  vidThumb: { position:"relative", height:"80px", background:"rgba(0,0,0,0.5)", overflow:"hidden" },
  vidThumbImg: { width:"100%", height:"100%", objectFit:"cover" },
  vidThumbFallback: { width:"100%", height:"100%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"1.5rem", color:"white" },
  selectedMark: { position:"absolute", inset:0, background:"rgba(214,34,138,0.6)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"1.5rem", fontWeight:"900", color:"white" },
  vidInfo: { padding:"0.4rem 0.5rem" },
  vidTitle: { fontSize:"0.75rem", fontWeight:"700", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  vidMeta: { fontSize:"0.65rem", color:"rgba(255,255,255,0.4)", marginTop:"0.1rem", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },

  selectedPreview: { background:"rgba(214,34,138,0.08)", border:"1px solid rgba(214,34,138,0.2)", borderRadius:"10px", padding:"0.6rem 0.9rem", fontSize:"0.85rem" },
  roomChip: { padding:"0.4rem 0.9rem", borderRadius:"99px", border:"1.5px solid", fontSize:"0.85rem", fontWeight:"600" },

  body: { flex:1, padding:"1.5rem 2rem", maxWidth:"1500px", width:"100%", margin:"0 auto", boxSizing:"border-box" },
  section: { marginBottom:"2.5rem" },
  sectionTitle: { fontSize:"1rem", fontWeight:"700", color:"rgba(255,255,255,0.65)", marginBottom:"1.2rem", display:"flex", alignItems:"center", gap:"0.6rem" },

  libGrid: { display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(120px,1fr))", gap:"0.8rem" },
  libCard: { background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:"12px", overflow:"hidden", animation:"fadeIn 0.4s ease forwards", opacity:0 },
  libThumb: { position:"relative", height:"70px", background:"rgba(0,0,0,0.5)" },
  libThumbFallback: { width:"100%", height:"100%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"1.4rem", color:"white", fontWeight:"800" },
  libTypeBadge: { position:"absolute", bottom:"0.3rem", left:"0.3rem", background:"rgba(0,0,0,0.7)", borderRadius:"4px", padding:"1px 5px", fontSize:"0.6rem", color:"rgba(255,255,255,0.7)" },
  libInfo: { padding:"0.4rem 0.5rem" },
  libTitle: { fontSize:"0.72rem", fontWeight:"700", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  libMeta: { fontSize:"0.6rem", color:"rgba(255,255,255,0.35)" },
  libGenre: { fontSize:"0.6rem", color:"rgba(255,255,255,0.25)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },

  roomGrid: { display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:"1.2rem" },
  roomCard: { background:"rgba(255,255,255,0.05)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:"18px", overflow:"hidden", cursor:"pointer", transition:"all 0.25s cubic-bezier(0.34,1.56,0.64,1)", animation:"fadeIn 0.4s ease forwards", opacity:0 },
  roomThumb: { position:"relative", height:"150px", background:"linear-gradient(135deg,rgba(138,46,207,0.3),rgba(214,34,138,0.2))", overflow:"hidden" },
  roomThumbFallback: { width:"100%", height:"100%", display:"flex", alignItems:"center", justifyContent:"center" },
  liveDot: { position:"absolute", top:"0.6rem", left:"0.6rem", display:"flex", alignItems:"center", gap:"0.35rem", background:"rgba(0,0,0,0.7)", borderRadius:"6px", padding:"0.2rem 0.5rem", fontSize:"0.68rem", fontWeight:"700", color:"#ef4444", backdropFilter:"blur(4px)" },
  viewerBadge: { position:"absolute", bottom:"0.6rem", left:"0.6rem", display:"flex", alignItems:"center", gap:"0.35rem", background:"rgba(0,0,0,0.65)", borderRadius:"6px", padding:"0.2rem 0.5rem", fontSize:"0.7rem", color:"white", backdropFilter:"blur(4px)" },
  hoverOverlay: { position:"absolute", inset:0, background:"rgba(0,0,0,0.55)", display:"flex", alignItems:"center", justifyContent:"center", opacity:0, transition:"opacity 0.2s", backdropFilter:"blur(2px)" },
  joinPill: { background:"linear-gradient(135deg,#d6228a,#8a2ecf)", color:"white", borderRadius:"99px", padding:"0.6rem 1.4rem", fontWeight:"700", fontSize:"0.9rem", boxShadow:"0 4px 20px rgba(214,34,138,0.5)" },
  miniBtn: { background:"rgba(0,0,0,0.6)", color:"white", border:"none", borderRadius:"6px", width:"26px", height:"26px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", fontSize:"0.75rem", backdropFilter:"blur(4px)" },
  roomBody: { padding:"0.9rem 1rem" },
  roomName: { fontWeight:"700", fontSize:"1rem", marginBottom:"0.3rem" },
  roomVideoTitle: { fontSize:"0.8rem", color:"#c896ec", marginBottom:"0.4rem", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  roomMeta: { display:"flex", justifyContent:"space-between", alignItems:"center", fontSize:"0.75rem" },

  addCard: { background:"rgba(255,255,255,0.03)", border:"2px dashed rgba(255,255,255,0.1)", borderRadius:"18px", minHeight:"220px", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", cursor:"pointer", color:"rgba(255,255,255,0.35)", transition:"all 0.2s" },
  emptyState: { display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"40vh", color:"rgba(255,255,255,0.5)", textAlign:"center", gap:"0.5rem" },
};

const wl = {
  banner: { display: "flex", justifyContent: "space-between", alignItems: "center", background: "linear-gradient(90deg,rgba(214,34,138,0.15),rgba(245,158,11,0.1))", borderBottom: "1px solid rgba(214,34,138,0.2)", padding: "0.7rem 2rem", flexWrap: "wrap", gap: "0.5rem" },
  bannerLeft: { display: "flex", alignItems: "center", gap: "0.7rem" },
  pulse: { width: "10px", height: "10px", borderRadius: "50%", background: "#f59e0b", animation: "pulse 1s infinite" },
  bannerTitle: { fontWeight: "700", fontSize: "0.9rem", color: "white" },
  approveAllBtn: { background: "linear-gradient(135deg,#22c55e,#16a34a)", color: "white", border: "none", borderRadius: "8px", padding: "0.4rem 1rem", fontWeight: "700", fontSize: "0.85rem", cursor: "pointer" },
  listWrap: { background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0.8rem 2rem" },
  listGrid: { display: "flex", flexWrap: "wrap", gap: "0.6rem" },
  userCard: { display: "flex", alignItems: "center", gap: "0.7rem", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "12px", padding: "0.6rem 0.9rem", animation: "fadeIn 0.3s ease" },
  avatar: { width: "34px", height: "34px", borderRadius: "50%", background: "linear-gradient(135deg,#d6228a,#8a2ecf)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "800", fontSize: "0.95rem", flexShrink: 0 },
  userInfo: { minWidth: "80px" },
  userName: { fontWeight: "700", fontSize: "0.85rem", color: "white" },
  userTime: { fontSize: "0.68rem", color: "rgba(255,255,255,0.4)", marginTop: "0.1rem" },
  actions: { display: "flex", gap: "0.4rem", marginLeft: "auto" },
  approveBtn: { background: "rgba(34,197,94,0.2)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)", borderRadius: "7px", padding: "0.3rem 0.7rem", fontSize: "0.75rem", fontWeight: "700", cursor: "pointer" },
  rejectBtn: { background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.25)", borderRadius: "7px", padding: "0.3rem 0.6rem", fontSize: "0.75rem", fontWeight: "700", cursor: "pointer" },
};
