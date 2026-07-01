import { useEffect, useState } from "react";
import Dashboard from "./Dashboard.jsx";
import Room from "./Room.jsx";
import WaitingRoom from "./WaitingRoom.jsx";

const ADMIN_CODE = "Admin-show-room";
const GUEST_CODE = "guest room";
const SESSION_KEY = "wt_session_v3";

export const saveSession = (d) => localStorage.setItem(SESSION_KEY, JSON.stringify(d));
export const loadSession = () => { try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; } };
export const clearSession = () => localStorage.removeItem(SESSION_KEY);

export default function App() {
  // "login" | "waiting" | "dashboard" | "room"
  const [view, setView] = useState("login");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [isApproved, setIsApproved] = useState(false);
  const [activeRoom, setActiveRoom] = useState(null);
  const [deniedMsg, setDeniedMsg] = useState("");

  useEffect(() => {
    const s = loadSession();
    if (!s?.isValid) return;
    setName(s.name);
    setIsAdmin(s.isAdmin || false);
    setIsApproved(s.isApproved || false);
    if (s.isAdmin || s.isApproved) {
      if (s.activeRoom) { setActiveRoom(s.activeRoom); setView("room"); }
      else setView("dashboard");
    } else {
      // Invité non encore approuvé → retour à l'écran d'attente
      setView("waiting");
    }
  }, []);

  useEffect(() => {
    if (view === "login") return;
    const s = loadSession();
    if (s?.isValid) saveSession({ ...s, isApproved, activeRoom: view === "room" ? activeRoom : null });
  }, [view, activeRoom, isApproved]);

  const handleLogin = () => {
    const trimCode = code.trim();
    const trimName = name.trim();
    if (!trimName) { setCodeError("Entrez votre nom."); return; }
    if (trimCode === ADMIN_CODE) {
      saveSession({ name: trimName, isAdmin: true, isValid: true, isApproved: true, activeRoom: null });
      setIsAdmin(true); setIsApproved(true); setCodeError(""); setView("dashboard");
    } else if (trimCode === GUEST_CODE) {
      saveSession({ name: trimName, isAdmin: false, isValid: true, isApproved: false, activeRoom: null });
      setIsAdmin(false); setIsApproved(false); setCodeError(""); setView("waiting");
    } else {
      setCodeError("Code incorrect. Vérifiez votre code d'accès.");
    }
  };

  const handleApproved = () => {
    setIsApproved(true);
    const s = loadSession();
    if (s) saveSession({ ...s, isApproved: true });
    setView("dashboard");
  };

  const handleDenied = (reason) => {
    setDeniedMsg(reason || "Accès refusé par l'administrateur.");
    clearSession();
    setView("denied");
  };

  const handleJoinRoom = (room, asPresenter) => {
    const r = { ...room, asPresenter };
    setActiveRoom(r);
    setView("room");
  };

  const handleBackToDashboard = () => { setActiveRoom(null); setView("dashboard"); };

  const handleLogout = () => {
    clearSession();
    setName(""); setCode(""); setIsAdmin(false); setIsApproved(false);
    setActiveRoom(null); setCodeError(""); setDeniedMsg(""); setView("login");
  };

  const breadcrumb = view === "login" || view === "waiting" || view === "denied"
    ? []
    : view === "dashboard"
    ? [{ label: "Tableau de bord" }]
    : [{ label: "Tableau de bord", onClick: handleBackToDashboard }, { label: activeRoom?.name || "Salon" }];

  // Pages sans breadcrumb global
  if (view === "login") return <LoginPage name={name} setName={setName} code={code} setCode={setCode} codeError={codeError} setCodeError={setCodeError} onLogin={handleLogin} />;
  if (view === "denied") return <DeniedPage message={deniedMsg} onLogout={handleLogout} />;

  // Pages avec breadcrumb
  return (
    <div style={wrap.outer}>
      <div style={wrap.nav}>
        <div style={wrap.navLeft}>
          <div style={wrap.logo}>▶</div>
          <div style={wrap.crumbList}>
            <span style={wrap.crumbHome}>Watch Together</span>
            {breadcrumb.map((c, i) => (
              <span key={i} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                <span style={wrap.sep}>›</span>
                {c.onClick
                  ? <button style={wrap.crumbLink} onClick={c.onClick}>{c.label}</button>
                  : <span style={wrap.crumbCurrent}>{c.label}</span>
                }
              </span>
            ))}
          </div>
        </div>
        <div style={wrap.navRight}>
          <span style={wrap.userChip}>{isAdmin ? "👑" : "👀"} {name}</span>
          <button style={wrap.logoutBtn} onClick={handleLogout}>Déconnexion</button>
        </div>
      </div>

      <div style={wrap.content}>
        {view === "waiting" && <WaitingRoom name={name} onApproved={handleApproved} onDenied={handleDenied} onLogout={handleLogout} />}
        {view === "dashboard" && <Dashboard name={name} isAdmin={isAdmin} onJoinRoom={handleJoinRoom} onLogout={handleLogout} />}
        {view === "room" && activeRoom && (
          <Room roomId={activeRoom.id} roomName={activeRoom.name} name={name} asPresenter={activeRoom.asPresenter} isGlobalAdmin={isAdmin} onBackToDashboard={handleBackToDashboard} pendingVideo={activeRoom.pendingVideo || null} />
        )}
      </div>
    </div>
  );
}

function LoginPage({ name, setName, code, setCode, codeError, setCodeError, onLogin }) {
  return (
    <div style={lp.container}>
      <style>{`input::placeholder{color:rgba(255,255,255,0.3)} input:focus{border-color:rgba(214,34,138,0.6)!important;outline:none} .login-btn:hover{filter:brightness(1.15);transform:translateY(-1px)}`}</style>
      <div style={lp.topBar}>
        <span style={lp.brand}>▶ Watch Together</span>
        <span style={lp.pageLbl}>📍 Connexion</span>
      </div>
      <div style={lp.body}>
        <div style={lp.card}>
          <div style={lp.logo}>▶</div>
          <h1 style={lp.title}>Watch Together</h1>
          <p style={lp.sub}>Plateforme de visionnage synchronisé en temps réel</p>

          <label style={lp.lbl}>Votre nom</label>
          <input style={lp.input} value={name} onChange={e => setName(e.target.value)} placeholder="Ex : Ahmad" autoFocus onKeyDown={e => e.key === "Enter" && onLogin()} />

          <label style={lp.lbl}>Code d'accès</label>
          <input style={{ ...lp.input, borderColor: codeError ? "#ef4444" : "rgba(255,255,255,0.12)", marginBottom: codeError ? "0.4rem" : "1.4rem" }}
            type="password" value={code} onChange={e => { setCode(e.target.value); setCodeError(""); }}
            placeholder="Entrez votre code" onKeyDown={e => e.key === "Enter" && onLogin()} />
          {codeError && <p style={{ color:"#ef4444", fontSize:"0.8rem", margin:"0 0 1rem" }}>{codeError}</p>}

          <div style={lp.hint}>
            <div style={lp.hintR}><span>👑</span><span>Code Admin : fourni par votre responsable</span></div>
            <div style={lp.hintR}><span>👀</span><span>Code Invité : partagé par votre organisateur</span></div>
          </div>

          <button className="login-btn" style={{ ...lp.btn, opacity: !name.trim()||!code.trim()?0.5:1, transition:"all 0.2s" }} disabled={!name.trim()||!code.trim()} onClick={onLogin}>
            Accéder →
          </button>
        </div>
      </div>
    </div>
  );
}

function DeniedPage({ message, onLogout }) {
  return (
    <div style={{ minHeight:"100vh", background:"linear-gradient(135deg,#0a0412,#1a0b2e)", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Segoe UI',system-ui,sans-serif" }}>
      <div style={{ background:"rgba(255,255,255,0.05)", border:"1px solid rgba(239,68,68,0.3)", borderRadius:"24px", padding:"3rem", width:"400px", color:"white", textAlign:"center" }}>
        <div style={{ fontSize:"3rem", marginBottom:"1rem" }}>🚫</div>
        <h2 style={{ margin:"0 0 0.7rem", fontSize:"1.4rem" }}>Accès refusé</h2>
        <p style={{ color:"rgba(255,255,255,0.5)", marginBottom:"2rem", fontSize:"0.9rem" }}>{message}</p>
        <button onClick={onLogout} style={{ background:"linear-gradient(135deg,#d6228a,#8a2ecf)", color:"white", border:"none", borderRadius:"10px", padding:"0.8rem 2rem", fontWeight:"700", cursor:"pointer", fontSize:"0.95rem" }}>
          Retour à la connexion
        </button>
      </div>
    </div>
  );
}

const wrap = {
  outer: { minHeight:"100vh", background:"linear-gradient(135deg,#0a0412 0%,#1a0b2e 60%,#0d1f3c 100%)", fontFamily:"'Segoe UI',system-ui,sans-serif", display:"flex", flexDirection:"column", color:"white" },
  nav: { display:"flex", justifyContent:"space-between", alignItems:"center", padding:"0.7rem 1.5rem", background:"rgba(0,0,0,0.45)", borderBottom:"1px solid rgba(255,255,255,0.06)", backdropFilter:"blur(10px)", flexWrap:"wrap", gap:"0.5rem" },
  navLeft: { display:"flex", alignItems:"center", gap:"0.7rem" },
  logo: { width:"30px", height:"30px", background:"linear-gradient(135deg,#d6228a,#8a2ecf)", borderRadius:"8px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"0.85rem", flexShrink:0 },
  crumbList: { display:"flex", alignItems:"center", gap:"0.2rem" },
  crumbHome: { fontSize:"0.82rem", fontWeight:"700", color:"rgba(255,255,255,0.5)" },
  sep: { color:"rgba(255,255,255,0.2)", margin:"0 0.1rem" },
  crumbLink: { background:"none", border:"none", color:"rgba(255,255,255,0.45)", cursor:"pointer", fontSize:"0.82rem", padding:0, textDecoration:"underline dotted" },
  crumbCurrent: { color:"#d6228a", fontWeight:"700", fontSize:"0.82rem" },
  navRight: { display:"flex", alignItems:"center", gap:"0.7rem" },
  userChip: { background:"rgba(255,255,255,0.07)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"99px", padding:"0.25rem 0.8rem", fontSize:"0.8rem" },
  logoutBtn: { background:"rgba(255,255,255,0.06)", color:"rgba(255,255,255,0.65)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"8px", padding:"0.3rem 0.8rem", fontSize:"0.78rem", cursor:"pointer" },
  content: { flex:1, display:"flex", flexDirection:"column" },
};

const lp = {
  container: { minHeight:"100vh", background:"linear-gradient(135deg,#0a0412 0%,#1a0b2e 50%,#0d1f3c 100%)", fontFamily:"'Segoe UI',system-ui,sans-serif", color:"white", display:"flex", flexDirection:"column" },
  topBar: { display:"flex", justifyContent:"space-between", alignItems:"center", padding:"1rem 2rem", background:"rgba(0,0,0,0.3)", borderBottom:"1px solid rgba(255,255,255,0.06)" },
  brand: { fontWeight:"800", fontSize:"1rem" },
  pageLbl: { fontSize:"0.82rem", color:"#d6228a", fontWeight:"600" },
  body: { flex:1, display:"flex", alignItems:"center", justifyContent:"center", padding:"2rem" },
  card: { background:"rgba(255,255,255,0.05)", backdropFilter:"blur(20px)", border:"1px solid rgba(255,255,255,0.1)", padding:"2.5rem", borderRadius:"24px", width:"420px", maxWidth:"100%", color:"white", boxShadow:"0 20px 60px rgba(0,0,0,0.5)" },
  logo: { width:"52px", height:"52px", background:"linear-gradient(135deg,#d6228a,#8a2ecf)", borderRadius:"16px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"1.5rem", marginBottom:"1.2rem", boxShadow:"0 4px 20px rgba(214,34,138,0.4)" },
  title: { margin:"0 0 0.3rem", fontSize:"1.9rem", fontWeight:"800", letterSpacing:"-0.5px" },
  sub: { color:"rgba(255,255,255,0.45)", fontSize:"0.9rem", marginBottom:"2rem" },
  lbl: { display:"block", fontSize:"0.75rem", fontWeight:"700", marginBottom:"0.5rem", color:"rgba(255,255,255,0.6)", textTransform:"uppercase", letterSpacing:"0.8px" },
  input: { width:"100%", padding:"0.8rem 1rem", borderRadius:"12px", border:"1px solid rgba(255,255,255,0.12)", background:"rgba(255,255,255,0.07)", color:"white", fontSize:"0.95rem", boxSizing:"border-box", marginBottom:"1.1rem" },
  hint: { background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:"10px", padding:"0.8rem", marginBottom:"1.5rem", display:"flex", flexDirection:"column", gap:"0.4rem" },
  hintR: { display:"flex", alignItems:"center", gap:"0.5rem", fontSize:"0.78rem", color:"rgba(255,255,255,0.45)" },
  btn: { width:"100%", padding:"0.9rem", borderRadius:"12px", border:"none", background:"linear-gradient(135deg,#d6228a,#8a2ecf)", color:"white", fontWeight:"700", fontSize:"1rem", cursor:"pointer", boxShadow:"0 4px 20px rgba(214,34,138,0.35)" },
};
