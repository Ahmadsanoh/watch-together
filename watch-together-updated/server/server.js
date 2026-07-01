import express from "express";
import multer from "multer";
import { WebSocketServer } from "ws";
import { createServer } from "http";
import { randomUUID } from "crypto";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UPLOADS_DIR = path.join(__dirname, "uploads");
if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR);

const PORT = process.env.PORT || 4000;
const rooms = new Map();
const lobbyClients = new Map();

// ============================================================
// VIDEO LIBRARY — 15 vidéos (identiques à client/src/videos.js)
// ============================================================
const VIDEO_LIBRARY = [
  { id:"v01", title:"Big Buck Bunny", genre:"Animation · Comédie", year:2008, duration:"10 min", type:"hls", url:"https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8", thumbnail:"https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/220px-Big_buck_bunny_poster_big.jpg" },
  { id:"v02", title:"Sintel", genre:"Animation · Fantastique", year:2010, duration:"14 min", type:"youtube", videoId:"eRsGyueVLvQ", thumbnail:"https://img.youtube.com/vi/eRsGyueVLvQ/mqdefault.jpg" },
  { id:"v03", title:"Tears of Steel", genre:"Sci-Fi · Action", year:2012, duration:"12 min", type:"youtube", videoId:"R6MlUcmOul8", thumbnail:"https://img.youtube.com/vi/R6MlUcmOul8/mqdefault.jpg" },
  { id:"v04", title:"Elephants Dream", genre:"Animation · Mystère", year:2006, duration:"11 min", type:"youtube", videoId:"_EVETFmP1L4", thumbnail:"https://img.youtube.com/vi/_EVETFmP1L4/mqdefault.jpg" },
  { id:"v05", title:"Cosmos Laundromat", genre:"Animation · Drame", year:2015, duration:"13 min", type:"youtube", videoId:"Y-rmzh0PI3c", thumbnail:"https://img.youtube.com/vi/Y-rmzh0PI3c/mqdefault.jpg" },
  { id:"v06", title:"Agent 327", genre:"Animation · Espionnage", year:2017, duration:"4 min", type:"youtube", videoId:"mN0zPOpADL4", thumbnail:"https://img.youtube.com/vi/mN0zPOpADL4/mqdefault.jpg" },
  { id:"v07", title:"Sprite Fright", genre:"Animation · Horreur", year:2021, duration:"8 min", type:"youtube", videoId:"_cMxraX_5RE", thumbnail:"https://img.youtube.com/vi/_cMxraX_5RE/mqdefault.jpg" },
  { id:"v08", title:"Charge", genre:"Animation · Super-héros", year:2022, duration:"4 min", type:"youtube", videoId:"UXqq0ZvbOnk", thumbnail:"https://img.youtube.com/vi/UXqq0ZvbOnk/mqdefault.jpg" },
  { id:"v09", title:"Coffee Run", genre:"Animation · Action", year:2020, duration:"3 min", type:"youtube", videoId:"YE7VzlLtp-4", thumbnail:"https://img.youtube.com/vi/YE7VzlLtp-4/mqdefault.jpg" },
  { id:"v10", title:"Wing It", genre:"Animation · Comédie", year:2020, duration:"3 min", type:"youtube", videoId:"d2FEfgJxFXM", thumbnail:"https://img.youtube.com/vi/d2FEfgJxFXM/mqdefault.jpg" },
  { id:"v11", title:"Hero", genre:"Animation · Émouvant", year:2018, duration:"1 min", type:"youtube", videoId:"pKmSdY56VtY", thumbnail:"https://img.youtube.com/vi/pKmSdY56VtY/mqdefault.jpg" },
  { id:"v12", title:"Caminandes: Llama Drama", genre:"Animation · Comédie", year:2013, duration:"2 min", type:"youtube", videoId:"SkVqJ1SGeL0", thumbnail:"https://img.youtube.com/vi/SkVqJ1SGeL0/mqdefault.jpg" },
  { id:"v13", title:"Cosmos Laundromat : Pilot", genre:"Animation · SF", year:2015, duration:"12 min", type:"youtube", videoId:"cBTMnLYzQnA", thumbnail:"https://img.youtube.com/vi/cBTMnLYzQnA/mqdefault.jpg" },
  { id:"v14", title:"Glass Half", genre:"Court-métrage · Drame", year:2020, duration:"6 min", type:"youtube", videoId:"Wf1kHLFKBmk", thumbnail:"https://img.youtube.com/vi/Wf1kHLFKBmk/mqdefault.jpg" },
  { id:"v15", title:"Blender Demo Reel", genre:"Démonstration · Art", year:2023, duration:"5 min", type:"youtube", videoId:"dQw4w9WgXcQ", thumbnail:"https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg" },
];

// ============================================================
// EVENT LOG
// ============================================================
const eventLog = [];
const MAX_EVENTS = 20000;

function logEvent(userId, videoId, sessionId, eventType, timestampVideo) {
  eventLog.push({
    user_id: userId,
    video_id: String(videoId),
    session_id: sessionId,
    event_type: eventType,
    timestamp_video: Math.round(timestampVideo || 0),
    timestamp_wall: new Date().toISOString(),
  });
  if (eventLog.length > MAX_EVENTS) eventLog.shift();
}

function getOrCreateRoom(roomId, roomName) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, {
      id: roomId, name: roomName || roomId,
      adminId: null, presenterId: null,
      clients: new Map(), participants: new Map(),
      content: { mode:"hls", url:null, videoId:null, title:null, thumbnail:null, videoLibId:null },
      createdAt: Date.now(),
      currentVideoTime: 0,
      isPlaying: false,
      viewerJoinTimes: new Map(),
    });
  }
  return rooms.get(roomId);
}

function broadcast(room, payload, excludeId = null) {
  const data = JSON.stringify(payload);
  for (const [id, ws] of room.clients.entries()) {
    if (id !== excludeId && ws.readyState === ws.OPEN) ws.send(data);
  }
}

function sendTo(ws, payload) {
  if (ws && ws.readyState === ws.OPEN) ws.send(JSON.stringify(payload));
}

function participantList(room) {
  return Array.from(room.participants.entries()).map(([id, info]) => ({
    clientId: id, name: info.name,
    isPresenter: room.presenterId === id,
    isAdmin: room.adminId === id,
  }));
}

function broadcastPresence(room) {
  broadcast(room, {
    type: "presence",
    viewerCount: room.clients.size,
    presenterId: room.presenterId,
    adminId: room.adminId,
    participants: participantList(room),
  });
}

function roomSummary(room) {
  const videoMeta = VIDEO_LIBRARY.find(v => v.id === room.content.videoLibId) || null;
  return {
    id: room.id, name: room.name,
    viewerCount: room.clients.size,
    contentMode: room.content.mode,
    contentTitle: room.content.title || (videoMeta?.title),
    contentThumbnail: room.content.thumbnail || (videoMeta?.thumbnail),
    contentVideoLibId: room.content.videoLibId,
    videoMeta: videoMeta,
    hasPresenter: !!room.presenterId,
    currentVideoTime: room.currentVideoTime || 0,
    isPlaying: room.isPlaying || false,
    createdAt: room.createdAt,
  };
}

function getWaitingList() {
  return Array.from(lobbyClients.entries()).map(([id, info]) => ({
    clientId: id, name: info.name, connectedAt: info.connectedAt,
  }));
}

function broadcastAll() {
  const roomList = Array.from(rooms.values()).map(roomSummary);
  const waitingList = getWaitingList();
  const data = JSON.stringify({ type: "global_state", rooms: roomList, waiting: waitingList });
  for (const ws of wss.clients) {
    if (ws.readyState === ws.OPEN) ws.send(data);
  }
}

// ============================================================
// EXPRESS
// ============================================================
const app = express();
app.use(express.json());
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});
app.use("/uploads", express.static(UPLOADS_DIR));

// Rooms
app.get("/api/rooms", (req, res) => res.json(Array.from(rooms.values()).map(roomSummary)));
app.get("/api/waiting", (req, res) => res.json(getWaitingList()));

// Video Library
app.get("/api/videos", (req, res) => res.json(VIDEO_LIBRARY));

// Create room
app.post("/api/rooms", (req, res) => {
  const { name, video } = req.body;
  const id = randomUUID().slice(0, 8);
  const room = getOrCreateRoom(id, name || `Room ${rooms.size + 1}`);
  if (video) {
    room.content = { mode: video.mode || "hls", url: video.url || null, videoId: video.videoId || null, title: video.title || null, thumbnail: video.thumbnail || null, videoLibId: video.videoLibId || null };
  }
  broadcastAll();
  res.json(roomSummary(room));
});

// Delete room
app.delete("/api/rooms/:roomId", (req, res) => {
  const { roomId } = req.params;
  if (rooms.has(roomId)) {
    broadcast(rooms.get(roomId), { type: "room_closed" });
    rooms.delete(roomId);
    broadcastAll();
  }
  res.json({ ok: true });
});

// Live Events
app.get("/api/live-events", (req, res) => {
  const limit = parseInt(req.query.limit) || 5000;
  const roomId = req.query.room_id;
  const filtered = roomId ? eventLog.filter(e => e.session_id === roomId) : eventLog;
  res.json(filtered.slice(-limit));
});

app.get("/api/live-events/csv", (req, res) => {
  res.setHeader("Content-Type", "text/csv");
  res.setHeader("Content-Disposition", "attachment; filename=live_events.csv");
  const header = "user_id,video_id,session_id,event_type,timestamp_video,timestamp_wall";
  const rows = eventLog.map(e =>
    `${e.user_id},${e.video_id},${e.session_id},${e.event_type},${e.timestamp_video},${e.timestamp_wall}`
  );
  res.send([header, ...rows].join("\n"));
});

// Live Stats
app.get("/api/live-stats", (req, res) => {
  const roomStats = Array.from(rooms.values()).map(room => {
    const roomEvents = eventLog.filter(e => e.session_id === room.id);
    const recent = roomEvents.filter(e => new Date(e.timestamp_wall) > new Date(Date.now() - 5 * 60 * 1000));
    const videoMeta = VIDEO_LIBRARY.find(v => v.id === room.content.videoLibId) || null;
    return {
      room_id: room.id,
      room_name: room.name,
      video_id: room.content.videoLibId || room.content.title || `room_${room.id}`,
      video_title: room.content.title || (videoMeta?.title) || room.name,
      video_thumbnail: room.content.thumbnail || (videoMeta?.thumbnail) || null,
      video_genre: videoMeta?.genre || null,
      video_duration: videoMeta?.duration || null,
      viewer_count: room.clients.size,
      current_video_time: room.currentVideoTime || 0,
      is_playing: room.isPlaying || false,
      content_mode: room.content.mode,
      total_events: roomEvents.length,
      events_last_5min: recent.length,
      pauses_last_5min: recent.filter(e => e.event_type === "pause").length,
      seeks_last_5min: recent.filter(e => e.event_type === "seek").length,
    };
  });

  const recentAll = eventLog.filter(e => new Date(e.timestamp_wall) > new Date(Date.now() - 60000));
  res.json({
    rooms: roomStats,
    video_library: VIDEO_LIBRARY,
    total_events: eventLog.length,
    total_active_viewers: Array.from(rooms.values()).reduce((s, r) => s + r.clients.size, 0),
    events_last_minute: recentAll.length,
    pause_rate_last_min: recentAll.filter(e => e.event_type === "pause").length,
    seek_rate_last_min: recentAll.filter(e => e.event_type === "seek").length,
    unique_videos_live: new Set(roomStats.map(r => r.video_id)).size,
    server_uptime_sec: Math.floor(process.uptime()),
    generated_at: new Date().toISOString(),
  });
});

// Clear events
app.delete("/api/live-events", (req, res) => {
  eventLog.length = 0;
  res.json({ ok: true });
});

// Upload
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOADS_DIR),
  filename: (req, file, cb) => { const ext = path.extname(file.originalname) || ""; cb(null, `${randomUUID()}${ext}`); },
});
const upload = multer({ storage, limits: { fileSize: 500 * 1024 * 1024 } });
app.post("/api/upload", upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).json({ error: "Aucun fichier" });
  res.json({ url: `/uploads/${req.file.filename}`, originalName: req.file.originalname });
});

// ============================================================
// WEBSOCKET
// ============================================================
const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });

wss.on("connection", (ws) => {
  const clientId = randomUUID();
  let currentRoomId = null;
  let inLobby = false;

  ws.isAlive = true;
  ws.on("pong", () => { ws.isAlive = true; });

  sendTo(ws, {
    type: "global_state",
    rooms: Array.from(rooms.values()).map(roomSummary),
    waiting: getWaitingList(),
  });

  ws.on("message", (raw) => {
    let msg; try { msg = JSON.parse(raw.toString()); } catch { return; }
    const { type } = msg;

    if (type === "join_lobby") {
      inLobby = true;
      lobbyClients.set(clientId, { name: msg.name || "Invité", ws, connectedAt: Date.now() });
      sendTo(ws, { type: "lobby_joined", clientId, position: lobbyClients.size });
      broadcastAll();
      return;
    }
    if (type === "approve_user") {
      const target = lobbyClients.get(msg.targetId);
      if (target) { sendTo(target.ws, { type: "access_granted" }); lobbyClients.delete(msg.targetId); broadcastAll(); }
      return;
    }
    if (type === "approve_all") {
      for (const [, info] of lobbyClients.entries()) sendTo(info.ws, { type: "access_granted" });
      lobbyClients.clear(); broadcastAll(); return;
    }
    if (type === "reject_user") {
      const target = lobbyClients.get(msg.targetId);
      if (target) { sendTo(target.ws, { type: "access_denied", reason: msg.reason || "Accès refusé." }); lobbyClients.delete(msg.targetId); broadcastAll(); }
      return;
    }

    if (type === "join") {
      const { roomId, name, asPresenter, roomName } = msg;
      currentRoomId = roomId;
      const room = getOrCreateRoom(roomId, roomName);
      const adminStillOnline = room.adminId && room.clients.has(room.adminId);
      room.clients.set(clientId, ws);
      room.participants.set(clientId, { name: name || "Invité" });
      if (asPresenter && (!room.adminId || !adminStillOnline)) {
        room.adminId = clientId;
        room.presenterId = clientId;
      }
      const videoId = room.content.videoLibId || room.content.title || `room_${roomId}`;
      const userId = `${(name||"viewer").replace(/[^a-zA-Z0-9]/g,"_")}_${clientId.slice(0,4)}`;
      logEvent(userId, videoId, roomId, "play", room.currentVideoTime || 0);
      room.viewerJoinTimes.set(clientId, { joinedAt: Date.now(), videoPositionAtJoin: room.currentVideoTime || 0, userId, videoId });
      sendTo(ws, {
        type: "joined", clientId, roomId,
        isPresenter: room.presenterId === clientId,
        isAdmin: room.adminId === clientId,
        viewerCount: room.clients.size,
        participants: participantList(room),
        content: room.content,
        adminId: room.adminId, presenterId: room.presenterId,
        roomName: room.name,
      });
      broadcastPresence(room);
      broadcastAll();
      return;
    }

    if (!currentRoomId || !rooms.has(currentRoomId)) return;
    const room = rooms.get(currentRoomId);
    const isPresenter = room.presenterId === clientId;
    const isAdmin = room.adminId === clientId;

    if (["play","pause","seek"].includes(type) && isPresenter) {
      broadcast(room, { type, time: msg.time, ts: Date.now() }, clientId);
      room.currentVideoTime = msg.time || 0;
      room.isPlaying = (type === "play");
      const videoId = room.content.videoLibId || room.content.title || `room_${currentRoomId}`;
      for (const [vid] of room.viewerJoinTimes.entries()) {
        const vName = room.participants.get(vid)?.name || "viewer";
        logEvent(`${vName.replace(/[^a-zA-Z0-9]/g,"_")}_${vid.slice(0,4)}`, videoId, currentRoomId, type, msg.time || 0);
      }
      const presName = room.participants.get(clientId)?.name || "presenter";
      logEvent(`${presName.replace(/[^a-zA-Z0-9]/g,"_")}_${clientId.slice(0,4)}`, videoId, currentRoomId, type, msg.time || 0);
      return;
    }
    if (type === "content_change" && isPresenter) {
      room.content = { mode:msg.mode, url:msg.url||null, videoId:msg.videoId||null, originalName:msg.originalName||null, title:msg.title||null, thumbnail:msg.thumbnail||null, videoLibId:msg.videoLibId||null };
      broadcast(room, { type:"content_change", content:room.content }, clientId);
      broadcastAll(); return;
    }
    if (type === "grant_presenter" && isAdmin) { if (room.participants.has(msg.to)) { room.presenterId = msg.to; broadcastPresence(room); } return; }
    if (type === "reclaim_presenter" && isAdmin) { room.presenterId = clientId; broadcastPresence(room); return; }
    if (type === "request_sync") { broadcast(room, { type:"sync_request", from:clientId }, clientId); return; }
    if (type === "sync_state" && isPresenter) { sendTo(room.clients.get(msg.to), { type:"sync_state", time:msg.time, playing:msg.playing }); return; }
    if (type === "chat") {
      const sender = room.participants.get(clientId)?.name || "Anonyme";
      const text = (msg.text||"").slice(0,500); if (!text.trim()) return;
      broadcast(room, { type:"chat", from:sender, fromId:clientId, text, ts:Date.now() }); return;
    }
    if (type === "reaction") {
      const allowed = ["👍","❤️","😂","👏","🎉","😮"]; if (!allowed.includes(msg.emoji)) return;
      broadcast(room, { type:"reaction", emoji:msg.emoji, from:clientId, name:room.participants.get(clientId)?.name||"Anonyme" }); return;
    }
    if (type === "rtc_signal") { sendTo(room.clients.get(msg.to), { type:"rtc_signal", kind:msg.kind, sdp:msg.sdp, candidate:msg.candidate, from:clientId }); return; }
  });

  ws.on("close", () => {
    if (inLobby && lobbyClients.has(clientId)) { lobbyClients.delete(clientId); broadcastAll(); }
    if (!currentRoomId || !rooms.has(currentRoomId)) return;
    const room = rooms.get(currentRoomId);
    const viewerInfo = room.viewerJoinTimes.get(clientId);
    if (viewerInfo) {
      logEvent(viewerInfo.userId, viewerInfo.videoId, currentRoomId, "pause", room.currentVideoTime || 0);
      room.viewerJoinTimes.delete(clientId);
    }
    room.clients.delete(clientId);
    room.participants.delete(clientId);
    if (room.presenterId === clientId) room.presenterId = null;
    if (room.adminId === clientId) room.adminId = null;
    if (room.clients.size > 0) broadcastPresence(room);
    broadcastAll();
  });
});

setInterval(() => { wss.clients.forEach(ws => { if (!ws.isAlive) return ws.terminate(); ws.isAlive = false; ws.ping(); }); }, 30000);
httpServer.listen(PORT, () => console.log(`Watch Together server on http://localhost:${PORT}`));
