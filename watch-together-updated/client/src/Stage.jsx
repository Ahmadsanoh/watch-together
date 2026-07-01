import { useEffect, useRef } from "react";
import Hls from "hls.js";

const DEFAULT_STREAM_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8";

let youtubeApiPromise = null;
function loadYoutubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (youtubeApiPromise) return youtubeApiPromise;
  youtubeApiPromise = new Promise((resolve) => {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.body.appendChild(tag);
    window.onYouTubeIframeAPIReady = () => resolve(window.YT);
  });
  return youtubeApiPromise;
}

/**
 * Affiche le contenu actif de la room.
 * Expose via `registerHandlers` les fonctions play/pause/seek/getCurrentTime
 * pour que Room.jsx puisse piloter ou écouter le lecteur actif, quel que soit son type.
 */
export default function Stage({ content, isPresenter, onLocalAction, registerHandlers, remoteScreenStream }) {
  const videoRef = useRef(null); // utilisé pour hls / file
  const youtubePlayerRef = useRef(null);
  const youtubeContainerId = useRef(`yt-player-${Math.random().toString(36).slice(2)}`);
  const screenVideoRef = useRef(null); // affichage du flux d'écran partagé (invités) ou aperçu local (présentateur)

  // --- HLS / fichier uploadé : initialisation du lecteur natif ---
  useEffect(() => {
    if (content.mode !== "hls" && content.mode !== "file") return;
    const video = videoRef.current;
    if (!video) return;

    const url = content.url || DEFAULT_STREAM_URL;
    if (!url) return;

    if (content.mode === "hls" && Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(url);
      hls.attachMedia(video);
      return () => hls.destroy();
    } else {
      video.src = url;
    }
  }, [content.mode, content.url]);

  // --- YouTube : initialisation du lecteur via l'API IFrame ---
  useEffect(() => {
    if (content.mode !== "youtube" || !content.videoId) return;
    let cancelled = false;

    loadYoutubeApi().then((YT) => {
      if (cancelled) return;
      youtubePlayerRef.current = new YT.Player(youtubeContainerId.current, {
        videoId: content.videoId,
        playerVars: { controls: isPresenter ? 1 : 0, modestbranding: 1 },
        events: {
          onStateChange: (e) => {
            if (!isPresenter) return;
            if (e.data === YT.PlayerState.PLAYING) {
              onLocalAction("play", youtubePlayerRef.current.getCurrentTime());
            } else if (e.data === YT.PlayerState.PAUSED) {
              onLocalAction("pause", youtubePlayerRef.current.getCurrentTime());
            }
          },
        },
      });
    });

    return () => {
      cancelled = true;
      youtubePlayerRef.current?.destroy?.();
    };
  }, [content.mode, content.videoId, isPresenter]);

  // --- Flux d'écran partagé distant (côté invités) ---
  useEffect(() => {
    if (content.mode !== "screen") return;
    const video = screenVideoRef.current;
    if (!video || !remoteScreenStream) return;
    video.srcObject = remoteScreenStream;
  }, [content.mode, remoteScreenStream]);

  // --- Expose les handlers play/pause/seek/getTime au composant parent ---
  useEffect(() => {
    registerHandlers({
      applyRemote: (type, time) => {
        if (content.mode === "hls" || content.mode === "file") {
          const video = videoRef.current;
          if (!video) return;
          video.currentTime = time;
          if (type === "play") video.play();
          if (type === "pause") video.pause();
        } else if (content.mode === "youtube" && youtubePlayerRef.current) {
          youtubePlayerRef.current.seekTo(time, true);
          if (type === "play") youtubePlayerRef.current.playVideo();
          if (type === "pause") youtubePlayerRef.current.pauseVideo();
        }
      },
      getCurrentTime: () => {
        if (content.mode === "hls" || content.mode === "file") {
          return videoRef.current?.currentTime || 0;
        }
        if (content.mode === "youtube" && youtubePlayerRef.current) {
          return youtubePlayerRef.current.getCurrentTime();
        }
        return 0;
      },
      isPaused: () => {
        if (content.mode === "hls" || content.mode === "file") {
          return videoRef.current?.paused ?? true;
        }
        return false;
      },
    });
  }, [content.mode, registerHandlers]);

  // --- Rendu selon le type de contenu actif ---
  if (content.mode === "image") {
    return (
      <div style={styles.imageWrapper}>
        <img src={content.url} alt="Contenu partagé" style={styles.image} />
      </div>
    );
  }

  if (content.mode === "pdf") {
    return (
      <div style={styles.pdfWrapper}>
        <iframe src={content.url} title="Document PDF" style={styles.pdfFrame} />
      </div>
    );
  }

  if (content.mode === "office") {
    return (
      <div style={styles.officeWrapper}>
        <p style={styles.officeText}>
          📊 Le présentateur partage un fichier PowerPoint
          {content.originalName ? ` (${content.originalName})` : ""}.
        </p>
        <p style={styles.officeHint}>
          Les fichiers PowerPoint ne peuvent pas s'afficher directement dans le navigateur.
          Téléchargez-le pour le consulter, ou demandez au présentateur de l'exporter en PDF
          avant de le partager pour un affichage direct.
        </p>
        <a href={content.url} download={content.originalName || true} style={styles.officeDownload}>
          ⬇️ Télécharger le fichier
        </a>
      </div>
    );
  }

  if (content.mode === "youtube") {
    return <div id={youtubeContainerId.current} style={styles.youtube} />;
  }

  if (content.mode === "screen") {
    return (
      <video
        ref={screenVideoRef}
        autoPlay
        playsInline
        controls={false}
        style={styles.video}
      />
    );
  }

  // hls / file : lecteur vidéo natif, contrôles visibles uniquement pour le présentateur
  return (
    <video
      ref={videoRef}
      controls={isPresenter}
      controlsList={!isPresenter ? "noplaybackrate nofullscreen" : undefined}
      style={styles.video}
      onPlay={() => onLocalAction("play", videoRef.current?.currentTime || 0)}
      onPause={() => onLocalAction("pause", videoRef.current?.currentTime || 0)}
      onSeeked={() => onLocalAction("seek", videoRef.current?.currentTime || 0)}
    />
  );
}

const styles = {
  video: {
    width: "100%",
    display: "block",
    borderRadius: "12px",
    background: "black",
    aspectRatio: "16 / 9",
  },
  youtube: {
    width: "100%",
    aspectRatio: "16 / 9",
    borderRadius: "12px",
    overflow: "hidden",
  },
  imageWrapper: {
    width: "100%",
    borderRadius: "12px",
    overflow: "hidden",
    background: "black",
    display: "flex",
    justifyContent: "center",
  },
  image: {
    maxWidth: "100%",
    maxHeight: "640px",
    objectFit: "contain",
  },
  pdfWrapper: {
    width: "100%",
    aspectRatio: "16 / 9",
    borderRadius: "12px",
    overflow: "hidden",
    background: "white",
  },
  pdfFrame: {
    width: "100%",
    height: "100%",
    border: "none",
  },
  officeWrapper: {
    width: "100%",
    aspectRatio: "16 / 9",
    borderRadius: "12px",
    background: "#1f1330",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    padding: "2rem",
    boxSizing: "border-box",
  },
  officeText: {
    fontSize: "1.1rem",
    color: "white",
    marginBottom: "0.5rem",
  },
  officeHint: {
    fontSize: "0.85rem",
    color: "#bba7d8",
    maxWidth: "480px",
    marginBottom: "1.2rem",
  },
  officeDownload: {
    background: "#8a2ecf",
    color: "white",
    textDecoration: "none",
    padding: "0.6rem 1.2rem",
    borderRadius: "8px",
    fontSize: "0.9rem",
  },
};
