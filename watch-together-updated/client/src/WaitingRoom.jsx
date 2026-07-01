import { useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:4000";

export default function WaitingRoom({ name, onApproved, onDenied, onLogout }) {
  const wsRef = useRef(null);
  const [status, setStatus] = useState("connecting"); // connecting | waiting | denied
  const [position, setPosition] = useState(null);
  const [dots, setDots] = useState(".");
  const reconnectTimer = useRef(null);

  // Animation des points de suspension
  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? "." : d + "."), 600);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let manualClose = false;

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "join_lobby", name }));
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "lobby_joined") {
          setStatus("waiting");
          setPosition(msg.position);
        }
        if (msg.type === "global_state") {
          // Mettre à jour la position dans la file
          const pos = msg.waiting?.findIndex(u => u.name === name);
          if (pos !== -1 && pos !== undefined) setPosition(pos + 1);
        }
        if (msg.type === "access_granted") {
          setStatus("approved");
          ws.close();
          setTimeout(() => onApproved(), 600);
        }
        if (msg.type === "access_denied") {
          setStatus("denied");
          onDenied(msg.reason);
        }
      };

      ws.onclose = () => {
        if (!manualClose && status !== "approved" && status !== "denied") {
          reconnectTimer.current = setTimeout(connect, 2000);
        }
      };
    };

    connect();
    return () => {
      manualClose = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [name]);

  return (
    <div style={s.container}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.6; transform:scale(0.95); } }
        @keyframes fadeInUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
        @keyframes orbit { to { transform: rotate(360deg); } }
      `}</style>

      <div style={s.card}>
        {/* Animation centrale */}
        <div style={s.animWrap}>
          <div style={s.orbitRing} />
          <div style={s.orbitRing2} />
          <div style={s.centerIcon}>⏳</div>
        </div>

        <h2 style={s.title}>En attente d'approbation</h2>
        <p style={s.sub}>
          Bonjour <strong style={{ color: "#d6228a" }}>{name}</strong> ! Votre demande d'accès a été envoyée.
          L'administrateur va vous approuver{dots}
        </p>

        {position && (
          <div style={s.positionBadge}>
            <span style={{ fontSize:"1.1rem" }}>🧍</span>
            <span>Vous êtes <strong>n°{position}</strong> dans la file d'attente</span>
          </div>
        )}

        <div style={s.infoBox}>
          <div style={s.infoRow}><span>✓</span><span>Connecté au serveur</span></div>
          <div style={s.infoRow}><span style={{ color:"#f59e0b" }}>◷</span><span>En attente de l'approbation admin</span></div>
          <div style={{ ...s.infoRow, color:"rgba(255,255,255,0.3)" }}><span>○</span><span>Accès aux salons</span></div>
        </div>

        <button style={s.logoutBtn} onClick={onLogout}>← Annuler et se déconnecter</button>
      </div>
    </div>
  );
}

const s = {
  container: { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" },
  card: { background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)", padding: "3rem 2.5rem", borderRadius: "24px", width: "440px", maxWidth: "100%", color: "white", textAlign: "center", boxShadow: "0 20px 60px rgba(0,0,0,0.5)", animation: "fadeInUp 0.5s ease" },
  animWrap: { position: "relative", width: "100px", height: "100px", margin: "0 auto 2rem" },
  orbitRing: { position: "absolute", inset: 0, borderRadius: "50%", border: "2px solid transparent", borderTopColor: "#d6228a", animation: "orbit 1.5s linear infinite" },
  orbitRing2: { position: "absolute", inset: "8px", borderRadius: "50%", border: "2px solid transparent", borderTopColor: "rgba(138,46,207,0.5)", animation: "orbit 2s linear infinite reverse" },
  centerIcon: { position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2.5rem", animation: "pulse 2s ease infinite" },
  title: { margin: "0 0 0.7rem", fontSize: "1.5rem", fontWeight: "800" },
  sub: { color: "rgba(255,255,255,0.6)", fontSize: "0.9rem", lineHeight: 1.6, marginBottom: "1.5rem" },
  positionBadge: { display: "inline-flex", alignItems: "center", gap: "0.5rem", background: "rgba(214,34,138,0.15)", border: "1px solid rgba(214,34,138,0.3)", borderRadius: "99px", padding: "0.5rem 1.2rem", fontSize: "0.9rem", marginBottom: "1.5rem" },
  infoBox: { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px", padding: "1rem 1.2rem", marginBottom: "1.5rem", display: "flex", flexDirection: "column", gap: "0.5rem", textAlign: "left" },
  infoRow: { display: "flex", alignItems: "center", gap: "0.6rem", fontSize: "0.82rem", color: "#22c55e" },
  logoutBtn: { background: "transparent", color: "rgba(255,255,255,0.4)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px", padding: "0.5rem 1rem", fontSize: "0.8rem", cursor: "pointer" },
};
