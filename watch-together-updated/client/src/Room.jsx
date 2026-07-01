import { useCallback, useEffect, useRef, useState } from "react";
import Stage from "./Stage.jsx";
import { VIDEO_LIBRARY } from "./videos.js";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:4000";
const HTTP_URL = WS_URL.replace(/^ws/, "http");
const REACTION_EMOJIS = ["👍", "❤️", "😂", "👏", "🎉", "😮"];
const ICE_SERVERS = [{ urls: "stun:stun.l.google.com:19302" }];

function extractYoutubeId(url) {
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/);
  return m ? m[1] : null;
}

function detectFileMode(file) {
  const n = file.name.toLowerCase();
  if (file.type.startsWith("image/")) return "image";
  if (file.type === "application/pdf" || n.endsWith(".pdf")) return "pdf";
  if (n.endsWith(".ppt") || n.endsWith(".pptx") || file.type.includes("powerpoint") || file.type.includes("presentation")) return "office";
  return "file";
}

function connectionColor(s) { return s === "connected" ? "#22c55e" : s === "disconnected" ? "#ef4444" : "#f59e0b"; }

export default function Room({ roomId, roomName, name, asPresenter, isGlobalAdmin, onBackToDashboard, pendingVideo }) {
  const wsRef = useRef(null);
  const chatEndRef = useRef(null);
  const stageHandlersRef = useRef(null);
  const videoWrapperRef = useRef(null);
  const participantsRef = useRef([]);
  const pendingVideoSent = useRef(false);
  const contentRef = useRef({ mode: "hls", url: null, videoId: null });

  const [myClientId, setMyClientId] = useState(null);
  const [isPresenter, setIsPresenter] = useState(asPresenter);
  const [isAdmin, setIsAdmin] = useState(asPresenter);
  const [adminId, setAdminId] = useState(null);
  const [viewerCount, setViewerCount] = useState(1);
  const [status, setStatus] = useState("Connexion...");
  const [connectionState, setConnectionState] = useState("connecting");
  const [participants, setParticipants] = useState([]);
  const [content, setContent] = useState({ mode: "hls", url: null, videoId: null });
  const [currentRoomName, setCurrentRoomName] = useState(roomName || roomId);

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatOpen, setChatOpen] = useState(true);
  const [floatingReactions, setFloatingReactions] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [youtubeInput, setYoutubeInput] = useState("");
  const [imageUrlInput, setImageUrlInput] = useState("");
  const [screenSharing, setScreenSharing] = useState(false);
  const [remoteScreenStream, setRemoteScreenStream] = useState(null);
  const [showLibrary, setShowLibrary] = useState(false);

  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef(null);
  const manualClose = useRef(false);
  const localStreamRef = useRef(null);
  const peerConnectionsRef = useRef(new Map());
  const peerConnectionRef = useRef(null);

  useEffect(() => { contentRef.current = content; }, [content]);
  useEffect(() => { participantsRef.current = participants; }, [participants]);

  useEffect(() => {
    manualClose.current = false;
    const connect = () => {
      setConnectionState(reconnectAttempt.current === 0 ? "connecting" : "reconnecting");
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        setConnectionState("connected");
        ws.send(JSON.stringify({ type: "join", roomId, name, asPresenter, roomName: roomName || roomId }));
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "joined":
            ws._clientId = msg.clientId;
            setMyClientId(msg.clientId);
            setIsPresenter(msg.isPresenter);
            setIsAdmin(msg.isAdmin);
            setAdminId(msg.adminId);
            setViewerCount(msg.viewerCount);
            setParticipants(msg.participants || []);
            setContent(msg.content || { mode: "hls", url: null, videoId: null });
            setCurrentRoomName(msg.roomName || roomName || roomId);
            setStatus(msg.isPresenter ? (msg.isAdmin ? "👑 Administrateur" : "🎤 Présentateur") : "Synchronisé");
            if (!msg.isPresenter) ws.send(JSON.stringify({ type: "request_sync" }));
            // Si on a une vidéo pré-assignée depuis le dashboard, on la diffuse maintenant
            if (msg.isPresenter && pendingVideo && !pendingVideoSent.current) {
              pendingVideoSent.current = true;
              const cv = {
                type: "content_change",
                mode: pendingVideo.type === "youtube" ? "youtube" : "hls",
                url: pendingVideo.url || null,
                videoId: pendingVideo.videoId || null,
                title: pendingVideo.title,
                thumbnail: pendingVideo.thumbnail,
                videoLibId: pendingVideo.id,
              };
              ws.send(JSON.stringify(cv));
              setContent({ mode: cv.mode, url: cv.url, videoId: cv.videoId, title: cv.title, thumbnail: cv.thumbnail, videoLibId: cv.videoLibId });
            }
            break;

          case "presence": {
            const prevIds = new Set(participantsRef.current.map(p => p.clientId));
            setViewerCount(msg.viewerCount);
            setParticipants(msg.participants || []);
            setAdminId(msg.adminId);
            const nowPresenter = msg.presenterId === wsRef.current?._clientId;
            const nowAdmin = msg.adminId === wsRef.current?._clientId;
            setIsPresenter(nowPresenter);
            setIsAdmin(nowAdmin);
            if (!msg.presenterId) setStatus("Aucun présentateur");
            else if (nowPresenter && nowAdmin) setStatus("👑 Administrateur");
            else if (nowPresenter) setStatus("🎤 Présentateur");
            else setStatus("Synchronisé");
            if (nowPresenter && contentRef.current.mode === "screen" && localStreamRef.current) {
              (msg.participants || []).forEach(p => { if (p.clientId !== wsRef.current?._clientId && !prevIds.has(p.clientId)) createOfferForPeer(p.clientId); });
            }
            break;
          }

          case "play": case "pause": case "seek":
            stageHandlersRef.current?.applyRemote(msg.type, msg.time); break;

          case "sync_request":
            if (stageHandlersRef.current) ws.send(JSON.stringify({ type: "sync_state", to: msg.from, time: stageHandlersRef.current.getCurrentTime(), playing: !stageHandlersRef.current.isPaused() }));
            break;

          case "sync_state":
            stageHandlersRef.current?.applyRemote(msg.playing ? "play" : "pause", msg.time); break;

          case "content_change":
            setContent(msg.content);
            if (msg.content.mode !== "screen") { closeAllPeerConnections(); setRemoteScreenStream(null); setScreenSharing(false); }
            break;

          case "chat":
            setChatMessages(prev => [...prev, msg]); break;

          case "reaction": {
            const id = `${msg.from}-${Date.now()}-${Math.random()}`;
            const left = 5 + Math.random() * 60;
            setFloatingReactions(prev => [...prev, { id, emoji: msg.emoji, name: msg.name, left }]);
            setTimeout(() => setFloatingReactions(prev => prev.filter(r => r.id !== id)), 3000);
            break;
          }

          case "rtc_signal": handleRtcSignal(msg); break;
          case "room_closed": onBackToDashboard(); break;
          case "room_list": break; // ignoré dans Room
          default: break;
        }
      };

      ws.onclose = () => {
        if (manualClose.current) return;
        setConnectionState("disconnected");
        setStatus("Reconnexion...");
        const delay = Math.min(1000 * 2 ** reconnectAttempt.current, 30000);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      manualClose.current = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      closeAllPeerConnections();
      localStreamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, [roomId, name, asPresenter]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  const registerStageHandlers = useCallback(h => { stageHandlersRef.current = h; }, []);
  const handleLocalAction = (type, time) => { if (!isPresenter) return; wsRef.current?.send(JSON.stringify({ type, time })); };

  function createPeerConnection(targetClientId) {
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    localStreamRef.current?.getTracks().forEach(track => pc.addTrack(track, localStreamRef.current));
    pc.onicecandidate = e => { if (e.candidate) wsRef.current?.send(JSON.stringify({ type: "rtc_signal", to: targetClientId, kind: "ice", candidate: e.candidate })); };
    peerConnectionsRef.current.set(targetClientId, pc);
    return pc;
  }

  async function createOfferForPeer(targetClientId) {
    const pc = createPeerConnection(targetClientId);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    wsRef.current?.send(JSON.stringify({ type: "rtc_signal", to: targetClientId, kind: "offer", sdp: offer }));
  }

  function closeAllPeerConnections() {
    peerConnectionsRef.current.forEach(pc => pc.close());
    peerConnectionsRef.current.clear();
    peerConnectionRef.current?.close();
    peerConnectionRef.current = null;
  }

  async function handleRtcSignal(msg) {
    const { kind, from } = msg;
    if (isPresenter) {
      const pc = peerConnectionsRef.current.get(from);
      if (!pc) return;
      if (kind === "answer") await pc.setRemoteDescription(msg.sdp);
      else if (kind === "ice" && msg.candidate) await pc.addIceCandidate(msg.candidate).catch(() => {});
      return;
    }
    if (kind === "offer") {
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      pc.ontrack = e => setRemoteScreenStream(e.streams[0]);
      pc.onicecandidate = e => { if (e.candidate) wsRef.current?.send(JSON.stringify({ type: "rtc_signal", to: from, kind: "ice", candidate: e.candidate })); };
      await pc.setRemoteDescription(msg.sdp);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      wsRef.current?.send(JSON.stringify({ type: "rtc_signal", to: from, kind: "answer", sdp: answer }));
      peerConnectionRef.current = pc;
    } else if (kind === "ice" && msg.candidate && peerConnectionRef.current) {
      await peerConnectionRef.current.addIceCandidate(msg.candidate).catch(() => {});
    }
  }

  async function startScreenShare() {
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
      let micStream = null;
      try { micStream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch {}
      const combined = new MediaStream([...screenStream.getVideoTracks(), ...screenStream.getAudioTracks(), ...(micStream ? micStream.getAudioTracks() : [])]);
      localStreamRef.current = combined;
      setScreenSharing(true);
      screenStream.getVideoTracks()[0].onended = () => stopScreenShare();
      wsRef.current?.send(JSON.stringify({ type: "content_change", mode: "screen" }));
      setContent({ mode: "screen", url: null, videoId: null });
      participantsRef.current.forEach(p => { if (p.clientId !== wsRef.current?._clientId) createOfferForPeer(p.clientId); });
    } catch (err) { console.error("Partage d'écran refusé", err); }
  }

  function stopScreenShare() {
    localStreamRef.current?.getTracks().forEach(t => t.stop());
    localStreamRef.current = null;
    closeAllPeerConnections();
    setScreenSharing(false);
    wsRef.current?.send(JSON.stringify({ type: "content_change", mode: "hls" }));
    setContent({ mode: "hls", url: null, videoId: null });
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${HTTP_URL}/api/upload`, { method: "POST", body: formData });
      const data = await res.json();
      const fullUrl = `${HTTP_URL}${data.url}`;
      const mode = detectFileMode(file);
      wsRef.current?.send(JSON.stringify({ type: "content_change", mode, url: fullUrl, originalName: file.name }));
      setContent({ mode, url: fullUrl, videoId: null, originalName: file.name });
    } catch (err) { console.error(err); }
    finally { setUploading(false); e.target.value = ""; }
  }

  function pickFromLibrary(v) {
    const payload = {
      type: "content_change",
      mode: v.type === "youtube" ? "youtube" : "hls",
      url: v.url || null,
      videoId: v.videoId || null,
      title: v.title,
      thumbnail: v.thumbnail,
      videoLibId: v.id,
    };
    wsRef.current?.send(JSON.stringify(payload));
    setContent({ mode: payload.mode, url: payload.url, videoId: payload.videoId, title: payload.title, thumbnail: payload.thumbnail, videoLibId: payload.videoLibId });
    setShowLibrary(false);
  }

  function submitYoutube(e) {
    e?.preventDefault();
    const videoId = extractYoutubeId(youtubeInput.trim());
    if (!videoId) return;
    wsRef.current?.send(JSON.stringify({ type: "content_change", mode: "youtube", videoId }));
    setContent({ mode: "youtube", url: null, videoId });
    setYoutubeInput("");
  }

  function submitImageUrl(e) {
    e?.preventDefault();
    const url = imageUrlInput.trim();
    if (!url) return;
    wsRef.current?.send(JSON.stringify({ type: "content_change", mode: "image", url }));
    setContent({ mode: "image", url, videoId: null });
    setImageUrlInput("");
  }

  function backToHls() { wsRef.current?.send(JSON.stringify({ type: "content_change", mode: "hls" })); setContent({ mode: "hls", url: null, videoId: null }); if (screenSharing) stopScreenShare(); }
  function youtubeSkip(sec) { const t = (stageHandlersRef.current?.getCurrentTime() || 0) + sec; stageHandlersRef.current?.applyRemote("seek", t); handleLocalAction("seek", t); }

  const grantPresenter = (id) => wsRef.current?.send(JSON.stringify({ type: "grant_presenter", to: id }));
  const reclaimPresenter = () => wsRef.current?.send(JSON.stringify({ type: "reclaim_presenter" }));
  const claimPresenter = () => wsRef.current?.send(JSON.stringify({ type: "claim_presenter" }));

  const sendChat = (e) => { e.preventDefault(); const text = chatInput.trim(); if (!text) return; wsRef.current?.send(JSON.stringify({ type: "chat", text })); setChatInput(""); };
  const sendReaction = (emoji) => wsRef.current?.send(JSON.stringify({ type: "reaction", emoji }));

  const handleBack = () => { if (screenSharing) stopScreenShare(); onBackToDashboard(); };
  const handleFullscreen = () => { const el = videoWrapperRef.current; if (!el) return; document.fullscreenElement ? document.exitFullscreen?.() : el.requestFullscreen?.(); };

  const noPresenter = !participants.some(p => p.isPresenter);

  return (
    <div style={s.container}>
      <style>{`
        @keyframes floatUp{0%{opacity:1;transform:translateY(0) scale(1)}100%{opacity:0;transform:translateY(-120px) scale(1.3)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
        .pnl-btn:hover{filter:brightness(1.2);transform:translateY(-1px)}
        .reaction-btn:hover{transform:scale(1.3)}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.15);border-radius:2px}
        input::placeholder{color:rgba(255,255,255,0.3)} input:focus{outline:none;border-color:rgba(214,34,138,0.6)!important}
      `}</style>

      {/* Barre room légère — le breadcrumb global est dans App.jsx */}
      <div style={s.header}>
        <div style={s.headerLeft}>
          <div style={{ ...s.connDot, background: connectionColor(connectionState) }} title={connectionState} />
          <span style={{ fontSize:"0.82rem", color:"rgba(255,255,255,0.5)" }}>
            {viewerCount} participant{viewerCount>1?"s":""} · ID : {roomId}
          </span>
        </div>
        <div style={s.headerRight}>
          <div style={{ ...s.badge, background: isAdmin ? "linear-gradient(135deg,#f59e0b,#d97706)" : isPresenter ? "linear-gradient(135deg,#d6228a,#8a2ecf)" : "rgba(255,255,255,0.1)" }}>
            {isAdmin ? "👑 Admin" : isPresenter ? "🎤 Présentateur" : "👀 Invité"}
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={s.main}>
        <div style={s.videoCol}>
          <div ref={videoWrapperRef} style={s.videoWrapper}>
            <Stage content={content} isPresenter={isPresenter} onLocalAction={handleLocalAction} registerHandlers={registerStageHandlers} remoteScreenStream={remoteScreenStream} />
            <div style={s.reactionsOverlay}>
              {floatingReactions.map(r => (
                <div key={r.id} style={{ ...s.floatingReaction, left: `${r.left}%`, animation: "floatUp 3s ease-out forwards" }}>
                  <span style={{ fontSize: "2.2rem" }}>{r.emoji}</span>
                  <span style={s.floatingName}>{r.name}</span>
                </div>
              ))}
            </div>
            <button style={s.fsBtn} onClick={handleFullscreen}>⛶</button>
          </div>

          <div style={s.statusBar}>
            <span style={{ color: noPresenter ? "#f59e0b" : "#bba7d8", fontSize: "0.85rem" }}>
              {noPresenter ? "⏸ En attente d'un présentateur" : status}
            </span>
            {/* Seul l'admin peut reprendre le contrôle — les invités n'ont aucun bouton ici */}
            {isAdmin && !isPresenter && <button style={s.reclaimBtn} onClick={reclaimPresenter}>👑 Reprendre le contrôle</button>}
          </div>

          <div style={s.reactionBar}>
            <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>Réagir :</span>
            {REACTION_EMOJIS.map(emoji => (
              <button key={emoji} className="reaction-btn" style={s.reactionBtn} onClick={() => sendReaction(emoji)}>{emoji}</button>
            ))}
          </div>

          {isPresenter && (
            <div style={s.presenterPanel}>
              <div style={s.panelTitle}>{isAdmin ? "👑 Panneau Admin" : "🎤 Panneau Présentateur"}</div>
              <div style={s.panelRow}>
                <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={backToHls}>📡 Flux HLS</button>
                <button className="pnl-btn" style={{ ...s.panelBtn, background:"linear-gradient(135deg,#f59e0b,#d97706)", transition: "all 0.15s" }} onClick={()=>setShowLibrary(v=>!v)}>
                  🎬 Bibliothèque
                </button>
                <label className="pnl-btn" style={{ ...s.fileLabel, transition: "all 0.15s" }}>
                  {uploading ? "⏳ Envoi..." : "📁 Uploader"}
                  <input type="file" accept="video/*,image/*,.pdf,.ppt,.pptx" onChange={handleFileUpload} style={{ display: "none" }} />
                </label>
                {!screenSharing
                  ? <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={startScreenShare}>🖥️ Partager l'écran</button>
                  : <button className="pnl-btn" style={{ ...s.panelBtn, background: "#ef4444", transition: "all 0.15s" }} onClick={stopScreenShare}>⏹ Arrêter</button>
                }
              </div>

              {/* Bibliothèque vidéo inline */}
              {showLibrary && (
                <div style={libS.container}>
                  <div style={libS.header}>
                    <span style={libS.title}>🎬 Bibliothèque — choisir une vidéo</span>
                    <button style={libS.closeBtn} onClick={()=>setShowLibrary(false)}>✕</button>
                  </div>
                  <div style={libS.grid}>
                    {VIDEO_LIBRARY.map(v => (
                      <div key={v.id} style={libS.card} onClick={()=>pickFromLibrary(v)}>
                        <div style={libS.thumb}>
                          {v.thumbnail
                            ? <img src={v.thumbnail} alt={v.title} style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none";}} />
                            : <div style={{ ...libS.thumbFallback, background:v.color||"#333" }} />
                          }
                          <div style={libS.badge}>{v.type==="youtube"?"▶":"📡"}</div>
                        </div>
                        <div style={libS.info}>
                          <div style={libS.name}>{v.title}</div>
                          <div style={libS.meta}>{v.duration} · {v.year}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div style={s.panelRow}>
                <input style={s.panelInput} value={youtubeInput} onChange={e => setYoutubeInput(e.target.value)} placeholder="Lien YouTube..." onKeyDown={e => e.key === "Enter" && submitYoutube()} />
                <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={submitYoutube}>▶ YouTube</button>
              </div>
              {content.mode === "youtube" && (
                <div style={s.panelRow}>
                  <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={() => youtubeSkip(-10)}>⏪ -10s</button>
                  <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={() => youtubeSkip(10)}>+10s ⏩</button>
                </div>
              )}
              <div style={s.panelRow}>
                <input style={s.panelInput} value={imageUrlInput} onChange={e => setImageUrlInput(e.target.value)} placeholder="URL d'une image..." onKeyDown={e => e.key === "Enter" && submitImageUrl()} />
                <button className="pnl-btn" style={{ ...s.panelBtn, transition: "all 0.15s" }} onClick={submitImageUrl}>🖼️ Image</button>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div style={s.sidebar}>
          <div style={s.sideCard}>
            <div style={s.sideCardTitle}>👥 Participants ({participants.length})</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxHeight: "200px", overflowY: "auto" }}>
              {participants.map(p => (
                <div key={p.clientId} style={s.participantItem}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <div style={{ ...s.avatar, background: p.isAdmin ? "linear-gradient(135deg,#f59e0b,#d97706)" : p.isPresenter ? "linear-gradient(135deg,#d6228a,#8a2ecf)" : "rgba(255,255,255,0.1)" }}>
                      {p.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontSize: "0.85rem", fontWeight: "600" }}>{p.name} {p.clientId === myClientId ? "(moi)" : ""}</div>
                      <div style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)" }}>{p.isAdmin ? "👑 Admin" : p.isPresenter ? "🎤 Présentateur" : "👀 Invité"}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.3rem" }}>
                    {isAdmin && p.clientId !== myClientId && !p.isPresenter && (
                      <button style={s.grantBtn} onClick={() => grantPresenter(p.clientId)}>Donner</button>
                    )}
                    {isAdmin && p.clientId !== myClientId && p.isPresenter && !p.isAdmin && (
                      <button style={{ ...s.grantBtn, background: "rgba(239,68,68,0.2)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444" }} onClick={reclaimPresenter}>Révoquer</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...s.sideCard, flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div style={{ ...s.sideCardTitle, cursor: "pointer" }} onClick={() => setChatOpen(o => !o)}>
              💬 Chat {chatOpen ? "▾" : "▸"}
            </div>
            {chatOpen && (
              <>
                <div style={{ flex: 1, overflowY: "auto", maxHeight: "300px", display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "0.7rem" }}>
                  {chatMessages.length === 0 && <div style={{ textAlign: "center", color: "rgba(255,255,255,0.2)", fontSize: "0.8rem", padding: "1rem" }}>Aucun message</div>}
                  {chatMessages.map((m, i) => (
                    <div key={i} style={{ display: "flex", flexDirection: "column", gap: "0.1rem" }}>
                      <span style={{ fontSize: "0.72rem", color: "#c896ec", fontWeight: "700" }}>{m.from}</span>
                      <span style={{ fontSize: "0.85rem", lineHeight: 1.4, wordBreak: "break-word" }}>{m.text}</span>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                <form onSubmit={sendChat} style={{ display: "flex", gap: "0.4rem" }}>
                  <input style={s.chatInput} value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Écrire un message..." />
                  <button type="submit" style={s.chatSend}>→</button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const s = {
  container: { flex: 1, color: "white", fontFamily: "'Segoe UI',system-ui,sans-serif", display: "flex", flexDirection: "column" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.8rem 1.5rem", background: "rgba(0,0,0,0.4)", borderBottom: "1px solid rgba(255,255,255,0.06)", backdropFilter: "blur(10px)", flexWrap: "wrap", gap: "0.5rem" },
  headerLeft: { display: "flex", alignItems: "center", gap: "0.8rem" },
  backBtn: { background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "0.4rem 0.9rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: "600", flexShrink: 0 },
  divider: { width: "1px", height: "24px", background: "rgba(255,255,255,0.1)" },
  logoSmall: { width: "34px", height: "34px", background: "linear-gradient(135deg,#d6228a,#8a2ecf)", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem", flexShrink: 0 },
  roomName: { fontWeight: "700", fontSize: "1rem" },
  roomSub: { fontSize: "0.72rem", color: "rgba(255,255,255,0.4)" },
  headerRight: { display: "flex", alignItems: "center", gap: "0.6rem" },
  connDot: { width: "8px", height: "8px", borderRadius: "50%", flexShrink: 0 },
  badge: { padding: "0.3rem 0.8rem", borderRadius: "999px", fontSize: "0.8rem", fontWeight: "600" },
  main: { display: "flex", flex: 1, gap: "1rem", padding: "1rem 1.5rem", maxWidth: "1400px", width: "100%", margin: "0 auto", boxSizing: "border-box", flexWrap: "wrap" },
  videoCol: { flex: "1 1 600px", minWidth: "320px", display: "flex", flexDirection: "column", gap: "0.8rem" },
  videoWrapper: { position: "relative", borderRadius: "16px", overflow: "hidden", background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.08)" },
  reactionsOverlay: { position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" },
  floatingReaction: { position: "absolute", bottom: "15%", display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" },
  floatingName: { fontSize: "0.7rem", color: "white", background: "rgba(0,0,0,0.6)", padding: "2px 8px", borderRadius: "99px", whiteSpace: "nowrap" },
  fsBtn: { position: "absolute", bottom: "0.7rem", right: "0.7rem", background: "rgba(0,0,0,0.5)", color: "white", border: "none", borderRadius: "8px", padding: "0.3rem 0.6rem", fontSize: "1rem", cursor: "pointer", zIndex: 10 },
  statusBar: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.6rem 1rem", background: "rgba(255,255,255,0.04)", borderRadius: "12px", border: "1px solid rgba(255,255,255,0.06)" },
  claimBtn: { background: "rgba(245,158,11,0.2)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)", borderRadius: "8px", padding: "0.3rem 0.8rem", cursor: "pointer", fontSize: "0.8rem", fontWeight: "600" },
  reclaimBtn: { background: "linear-gradient(135deg,#f59e0b,#d97706)", color: "white", border: "none", borderRadius: "8px", padding: "0.3rem 0.8rem", cursor: "pointer", fontSize: "0.8rem", fontWeight: "600" },
  reactionBar: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" },
  reactionBtn: { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px", padding: "0.4rem 0.7rem", fontSize: "1.3rem", cursor: "pointer", transition: "transform 0.15s" },
  presenterPanel: { background: "rgba(255,255,255,0.04)", borderRadius: "16px", padding: "1rem 1.2rem", border: "1px solid rgba(255,255,255,0.08)", display: "flex", flexDirection: "column", gap: "0.7rem" },
  panelTitle: { fontWeight: "700", fontSize: "0.9rem", color: "rgba(255,255,255,0.7)" },
  panelRow: { display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" },
  panelBtn: { background: "linear-gradient(135deg,rgba(214,34,138,0.8),rgba(138,46,207,0.8))", color: "white", border: "none", borderRadius: "8px", padding: "0.5rem 0.9rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: "600" },
  fileLabel: { background: "rgba(255,255,255,0.1)", color: "white", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "0.5rem 0.9rem", cursor: "pointer", fontSize: "0.82rem", fontWeight: "600" },
  panelInput: { flex: 1, minWidth: "160px", padding: "0.5rem 0.8rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.06)", color: "white", fontSize: "0.85rem" },
  sidebar: { flex: "0 0 300px", display: "flex", flexDirection: "column", gap: "0.8rem", maxHeight: "calc(100vh - 120px)" },
  sideCard: { background: "rgba(255,255,255,0.04)", borderRadius: "16px", padding: "1rem", border: "1px solid rgba(255,255,255,0.08)" },
  sideCardTitle: { fontWeight: "700", fontSize: "0.82rem", color: "rgba(255,255,255,0.6)", marginBottom: "0.8rem", textTransform: "uppercase", letterSpacing: "0.5px" },
  participantItem: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" },
  avatar: { width: "30px", height: "30px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "700", fontSize: "0.8rem", flexShrink: 0 },
  grantBtn: { background: "rgba(138,46,207,0.2)", color: "#c896ec", border: "1px solid rgba(138,46,207,0.3)", borderRadius: "6px", padding: "0.2rem 0.5rem", fontSize: "0.7rem", cursor: "pointer" },
  chatInput: { flex: 1, padding: "0.5rem 0.8rem", borderRadius: "10px", border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.06)", color: "white", fontSize: "0.85rem" },
  chatSend: { background: "linear-gradient(135deg,#d6228a,#8a2ecf)", color: "white", border: "none", borderRadius: "10px", padding: "0.5rem 0.9rem", cursor: "pointer", fontSize: "1rem", fontWeight: "700" },
};

const libS = {
  container: { background: "rgba(0,0,0,0.4)", borderRadius: "12px", padding: "0.8rem", border: "1px solid rgba(245,158,11,0.2)" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.7rem" },
  title: { fontSize: "0.85rem", fontWeight: "700", color: "#f59e0b" },
  closeBtn: { background: "rgba(255,255,255,0.08)", border: "none", color: "white", borderRadius: "6px", width: "24px", height: "24px", cursor: "pointer", fontSize: "0.75rem" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))", gap: "0.5rem", maxHeight: "260px", overflowY: "auto" },
  card: { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", overflow: "hidden", cursor: "pointer", transition: "all 0.15s" },
  thumb: { position: "relative", height: "60px", background: "rgba(0,0,0,0.5)" },
  thumbFallback: { width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1.2rem" },
  badge: { position: "absolute", bottom: "0.2rem", left: "0.2rem", background: "rgba(0,0,0,0.7)", borderRadius: "3px", padding: "1px 4px", fontSize: "0.55rem", color: "rgba(255,255,255,0.7)" },
  info: { padding: "0.3rem 0.4rem" },
  name: { fontSize: "0.68rem", fontWeight: "700", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  meta: { fontSize: "0.58rem", color: "rgba(255,255,255,0.35)", marginTop: "0.1rem" },
};
