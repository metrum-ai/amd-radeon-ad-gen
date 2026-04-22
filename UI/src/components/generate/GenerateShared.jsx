// Created by Metrum AI for AMD

import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { C, gradient, shadow, radius } from "../../tokens";
import { Box, T } from "../primitives";
import useAssetUrl from "../../hooks/useAssetUrl";

export function Shimmer() {
  return (
    <Box style={{
      position: "absolute", inset: 0,
      background: `linear-gradient(90deg, transparent 0%, ${C.accent}08 50%, transparent 100%)`,
      backgroundSize: "200% 100%",
      animation: "shimmer 2s infinite linear",
    }} />
  );
}
export function CheckDone({ size = 20 }) {
  return (
    <Box style={{
      width: size, height: size, borderRadius: size / 2,
      background: C.green, display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <T s={size * 0.5} c="#fff" w={700}>{"\u2713"}</T>
    </Box>
  );
}
export function WaveViz({ done, count = 40, progress = 0 }) {
  const bars = useMemo(() => Array.from({ length: count }, () => Math.random() * 18 + 3), [count]);
  const activeIdx = Math.floor((progress / 100) * count);
  return (
    <Box style={{ display: "flex", gap: 1.5, alignItems: "end", height: 28, flex: 1 }}>
      {bars.map((h, i) => {
        const played = progress > 0 && i <= activeIdx;
        return (
          <Box key={i} style={{
            flex: 1, borderRadius: 1, height: h,
            background: done ? C.teal : C.border,
            opacity: done ? (played ? 1 : 0.3) : 0.2,
            transition: played ? "opacity 0.05s linear" : "opacity 0.3s ease",
          }} />
        );
      })}
    </Box>
  );
}

/* ---- Metrics stat cards with horizontal carousel ---- */

function MetricsStatCard({ children }) {
  return (
    <Box style={{
      display: "flex",
      alignItems: "stretch",
      gap: 10,
      width: "100%",
      minWidth: 0,
      padding: "7px 10px",
      background: C.elevated,
      borderRadius: radius.sm,
      border: `1px solid ${C.border}`,
      flexShrink: 0,
    }}>
      {children}
    </Box>
  );
}

function MetricTag({ label, accentColor }) {
  return (
    <Box style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "0 7px",
      borderRadius: 999,
      border: `1px solid ${accentColor}33`,
      background: `${accentColor}12`,
      flexShrink: 0,
      minWidth: 0,
    }}>
      <T s={6} c={accentColor} w={700} style={{
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        lineHeight: 1.8,
      }}>{label}</T>
    </Box>
  );
}

function MetricCell({ title, value, unit, accent, wrapValue = false, flex = "1 1 0" }) {
  return (
    <Box style={{ textAlign: "center", minWidth: 0, flex }}>
      <T s={6} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em", lineHeight: 1.2 }}>{title}</T>
      <Box style={{ display: "flex", alignItems: wrapValue ? "flex-start" : "baseline", gap: 2, justifyContent: "center", minWidth: 0, marginTop: 2, flexDirection: wrapValue ? "column" : "row" }}>
        <T s={11} w={700} c={accent || C.text} style={{
          maxWidth: "100%",
          overflow: wrapValue ? "visible" : "hidden",
          textOverflow: wrapValue ? "clip" : "ellipsis",
          whiteSpace: wrapValue ? "normal" : "nowrap",
          lineHeight: wrapValue ? 1.15 : 1,
          wordBreak: wrapValue ? "break-word" : "normal",
          fontSize: wrapValue ? 10 : undefined,
        }}>{value ?? "--"}</T>
        {unit && <T s={5} c={C.dim}>{unit}</T>}
      </Box>
    </Box>
  );
}

function MetricSep() {
  return <Box style={{ width: 1, alignSelf: "stretch", background: C.border, flexShrink: 0 }} />;
}

export function MetricsCarousel({ metrics }) {
  const cards = [];
  const [activeIndex, setActiveIndex] = useState(0);

  if (metrics?.image_gen) {
    const m = metrics.image_gen;
    cards.push(
      <MetricsStatCard key="img">
        <MetricTag label="Image" accentColor={C.accent} />
        <MetricCell title="Rate" value={m.images_per_min} unit="img/min" accent={C.accent} flex="0.9 1 0" />
        <MetricSep />
        <MetricCell title="Generated" value={m.total_images} flex="0.8 1 0" />
        <MetricSep />
        <MetricCell title="Model" value={m.model || "--"} wrapValue flex="1.6 1 0" />
      </MetricsStatCard>
    );
  }

  if (metrics?.video_gen) {
    const m = metrics.video_gen;
    cards.push(
      <MetricsStatCard key="vid">
        <MetricTag label="Video" accentColor={C.teal} />
        <MetricCell title="Rate" value={m.clips_per_min} unit="clip/min" accent={C.teal} flex="0.9 1 0" />
        <MetricSep />
        <MetricCell title="Clips" value={m.total_clips} flex="0.8 1 0" />
        <MetricSep />
        <MetricCell title="Model" value={m.model || "--"} wrapValue flex="1.6 1 0" />
      </MetricsStatCard>
    );
  }

  useEffect(() => {
    setActiveIndex((prev) => Math.min(prev, Math.max(cards.length - 1, 0)));
  }, [cards.length]);

  if (cards.length === 0) return null;

  if (cards.length === 1) {
    return (
      <Box style={{ width: 360, maxWidth: "100%", minWidth: 0, flexShrink: 1 }}>
        {cards[0]}
      </Box>
    );
  }

  const goPrev = () => setActiveIndex((prev) => (prev - 1 + cards.length) % cards.length);
  const goNext = () => setActiveIndex((prev) => (prev + 1) % cards.length);

  return (
    <Box style={{
      display: "flex",
      alignItems: "center",
      gap: 6,
      minWidth: 0,
      flexShrink: 1,
      width: 420,
      maxWidth: "100%",
    }}>
      <Box
        onClick={goPrev}
        style={{
          width: 20,
          height: 20,
          borderRadius: 10,
          background: C.elevated,
          border: `1px solid ${C.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          flexShrink: 0,
        }}
      >
        <T s={10} c={C.text} w={700}>{"\u2039"}</T>
      </Box>

      <Box style={{
        minWidth: 0,
        flex: 1,
        overflow: "hidden",
        borderRadius: radius.sm,
      }}>
        <Box style={{
          display: "flex",
          width: `${cards.length * 100}%`,
          transform: `translateX(-${activeIndex * (100 / cards.length)}%)`,
          transition: "transform 0.28s ease",
        }}>
          {cards.map((card, i) => (
            <Box
              key={i}
              style={{
                width: `${100 / cards.length}%`,
                display: "flex",
                justifyContent: "center",
              }}
            >
              {card}
            </Box>
          ))}
        </Box>
      </Box>

      <Box
        onClick={goNext}
        style={{
          width: 20,
          height: 20,
          borderRadius: 10,
          background: C.elevated,
          border: `1px solid ${C.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          flexShrink: 0,
        }}
      >
        <T s={10} c={C.text} w={700}>{"\u203A"}</T>
      </Box>

      <Box style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 26,
        flexShrink: 0,
      }}>
        <T s={8} c={C.dim} w={700} style={{ letterSpacing: "0.04em" }}>
          {activeIndex + 1}/{cards.length}
        </T>
      </Box>
    </Box>
  );
}
export function AssetImage({ s3Url, alt, style }) {
  const [url, setUrl] = useState(null);
  const { getUrl } = useAssetUrl();
  useEffect(() => {
    if (s3Url) getUrl(s3Url).then(setUrl);
  }, [s3Url, getUrl]);
  if (!url) return null;
  return <img src={url} alt={alt || ""} style={style} />;
}

/* ---- Modal audio player with waveform visualization ---- */
export function ModalAudioPlayer({ url }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => {
      if (audio.duration) setProgress((audio.currentTime / audio.duration) * 100);
    };
    const onEnd = () => { setPlaying(false); setProgress(0); };
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnd);
    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnd);
    };
  }, [url]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) { audio.pause(); setPlaying(false); }
    else { audio.play().catch(() => {}); setPlaying(true); }
  };

  const seek = (e) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.currentTime = pct * audio.duration;
    setProgress(pct * 100);
  };

  const duration = audioRef.current?.duration || 0;
  const elapsed = Math.floor((progress / 100) * duration);
  const durationInt = Math.floor(duration);
  const fmtTime = (s) => `0:${String(s).padStart(2, "0")}`;
  const timeStr = duration ? `${fmtTime(elapsed)} / ${fmtTime(durationInt)}` : "0:00 / 0:00";

  return (
    <Box style={{ width: "100%", maxWidth: 520, padding: "24px 0" }}>
      <audio ref={audioRef} src={url} preload="metadata" />
      <Box style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
        <Box
          onClick={togglePlay}
          style={{
            width: 48, height: 48, borderRadius: 24, flexShrink: 0,
            background: playing ? C.teal : gradient.amd,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", transition: "all 0.15s ease",
            boxShadow: playing ? `0 0 24px ${C.teal}40` : shadow.sm,
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.06)"; }}
          onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; }}
        >
          {playing ? (
            <Box style={{ display: "flex", gap: 3 }}>
              <Box style={{ width: 3, height: 16, background: "#fff", borderRadius: 1 }} />
              <Box style={{ width: 3, height: 16, background: "#fff", borderRadius: 1 }} />
            </Box>
          ) : (
            <Box style={{
              width: 0, height: 0,
              borderTop: "9px solid transparent",
              borderBottom: "9px solid transparent",
              borderLeft: "14px solid #fff",
              marginLeft: 3,
            }} />
          )}
        </Box>
        <Box style={{ flex: 1 }}>
          <WaveViz done={true} progress={progress} count={60} />
        </Box>
      </Box>
      <Box style={{ display: "flex", alignItems: "center", gap: 10, paddingLeft: 62 }}>
        <Box
          onClick={seek}
          style={{ flex: 1, height: 4, background: C.border, borderRadius: 2, overflow: "hidden", cursor: "pointer" }}
        >
          <Box style={{
            height: "100%", width: `${progress}%`,
            background: C.teal, borderRadius: 2,
            transition: playing ? "width 0.15s linear" : "width 0.3s ease",
          }} />
        </Box>
        <T s={11} c={playing ? C.teal : C.dim} w={500} style={{ flexShrink: 0, fontFamily: "'Inter', monospace" }}>
          {timeStr}
        </T>
      </Box>
    </Box>
  );
}

/* ---- Custom video player ---- */
export function ModalVideoPlayer({ url }) {
  const ref = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [videoReady, setVideoReady] = useState(false);
  const [videoAspect, setVideoAspect] = useState(1);
  const hideTimer = useRef(null);

  const fmt = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const scheduleHide = useCallback(() => {
    clearTimeout(hideTimer.current);
    setShowControls(true);
    if (playing) {
      hideTimer.current = setTimeout(() => setShowControls(false), 2500);
    }
  }, [playing]);

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    const onTime = () => {
      setCurrentTime(v.currentTime);
      setProgress(v.duration ? v.currentTime / v.duration : 0);
    };
    const onMeta = () => {
      setDuration(v.duration || 0);
      if (v.videoWidth && v.videoHeight) {
        setVideoAspect(v.videoWidth / v.videoHeight);
      }
    };
    const onLoaded = () => setVideoReady(true);
    const onPlay = () => setPlaying(true);
    const onPause = () => { setPlaying(false); setShowControls(true); };
    const onEnd = () => { setPlaying(false); setShowControls(true); setProgress(0); };
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("loadedmetadata", onMeta);
    v.addEventListener("loadeddata", onLoaded);
    v.addEventListener("play", onPlay);
    v.addEventListener("pause", onPause);
    v.addEventListener("ended", onEnd);
    return () => {
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("loadedmetadata", onMeta);
      v.removeEventListener("loadeddata", onLoaded);
      v.removeEventListener("play", onPlay);
      v.removeEventListener("pause", onPause);
      v.removeEventListener("ended", onEnd);
    };
  }, []);

  useEffect(() => { scheduleHide(); }, [playing, scheduleHide]);
  useEffect(() => {
    setPlaying(false);
    setProgress(0);
    setDuration(0);
    setCurrentTime(0);
    setShowControls(true);
    setVideoReady(false);
    setVideoAspect(1);
  }, [url]);

  const toggle = () => {
    const v = ref.current;
    if (!v) return;
    v.paused ? v.play() : v.pause();
  };

  const seek = (e) => {
    const v = ref.current;
    if (!v || !v.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    v.currentTime = pct * v.duration;
  };

  const changeVol = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setVolume(pct);
    setMuted(pct === 0);
    if (ref.current) { ref.current.volume = pct; ref.current.muted = pct === 0; }
  };

  const toggleMute = () => {
    const v = ref.current;
    if (!v) return;
    const next = !muted;
    setMuted(next);
    v.muted = next;
  };

  const toggleFS = () => {
    const v = ref.current;
    if (!v) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else v.requestFullscreen?.();
  };

  const iconBtn = { cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", opacity: 0.85, transition: "opacity 0.15s" };
  const playerWidth = videoAspect >= 1
    ? "min(86vw, 860px)"
    : "min(72vh, 86vw, 640px)";

  return (
    <Box
      onMouseMove={scheduleHide}
      onMouseEnter={() => setShowControls(true)}
      style={{
        position: "relative",
        width: playerWidth,
        aspectRatio: `${videoAspect}`,
        borderRadius: radius.lg, overflow: "hidden",
        background: "#000", userSelect: "none",
      }}
    >
      {!videoReady && (
        <Box style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(145deg, #0f1218 0%, #181d2a 45%, #0c1018 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          zIndex: 2,
        }}>
          <Shimmer />
          <Box style={{
            position: "relative",
            zIndex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}>
            <Box style={{
              width: 28,
              height: 28,
              borderRadius: 999,
              border: `2px solid ${C.border}`,
              borderTopColor: C.accent,
              animation: "spin 0.9s linear infinite",
            }} />
            <T s={12} c={C.text} w={600}>
              {url ? "Loading preview..." : "Fetching preview..."}
            </T>
          </Box>
        </Box>
      )}
      <video
        ref={ref}
        src={url}
        loop
        playsInline
        onClick={toggle}
        style={{
          width: "100%",
          height: "100%",
          display: "block",
          maxHeight: "72vh",
          cursor: "pointer",
          objectFit: "contain",
          opacity: videoReady ? 1 : 0,
          transition: "opacity 0.2s ease",
        }}
      />

      {/* Big center play button (shown when paused) */}
      {videoReady && !playing && (
        <Box
          onClick={toggle}
          style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(0,0,0,0.35)", cursor: "pointer",
            transition: "opacity 0.2s",
          }}
        >
          <Box style={{
            width: 64, height: 64, borderRadius: "50%",
            background: "rgba(237,28,36,0.9)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 24px rgba(237,28,36,0.3)",
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="white"><polygon points="6,3 20,12 6,21" /></svg>
          </Box>
        </Box>
      )}

      {/* Bottom control bar */}
      <Box style={{
        position: "absolute", left: 0, right: 0, bottom: 0,
        background: "linear-gradient(transparent, rgba(0,0,0,0.85))",
        padding: "24px 14px 10px",
        opacity: videoReady && showControls ? 1 : 0,
        transition: "opacity 0.3s ease",
        pointerEvents: videoReady && showControls ? "auto" : "none",
      }}>
        {/* Progress bar */}
        <Box
          onClick={seek}
          style={{
            height: 4, borderRadius: 2, background: "rgba(255,255,255,0.15)",
            cursor: "pointer", marginBottom: 8, position: "relative",
          }}
        >
          <Box style={{
            height: "100%", borderRadius: 2, width: `${progress * 100}%`,
            background: C.accent, transition: "width 0.1s linear",
          }} />
          <Box style={{
            position: "absolute", top: -4, left: `calc(${progress * 100}% - 6px)`,
            width: 12, height: 12, borderRadius: "50%",
            background: C.accent, border: "2px solid #fff",
            boxShadow: "0 0 6px rgba(237,28,36,0.4)",
            opacity: showControls ? 1 : 0, transition: "opacity 0.15s",
          }} />
        </Box>

        <Box style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Play/Pause */}
          <Box onClick={toggle} style={iconBtn}>
            {playing
              ? <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><rect x="5" y="3" width="5" height="18" rx="1"/><rect x="14" y="3" width="5" height="18" rx="1"/></svg>
              : <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><polygon points="6,3 20,12 6,21"/></svg>
            }
          </Box>

          {/* Time */}
          <T s={10} c="rgba(255,255,255,0.7)" style={{ fontVariantNumeric: "tabular-nums", minWidth: 70 }}>
            {fmt(currentTime)} / {fmt(duration)}
          </T>

          <Box style={{ flex: 1 }} />

          {/* Volume */}
          <Box onClick={toggleMute} style={iconBtn}>
            {muted || volume === 0
              ? <svg width="15" height="15" viewBox="0 0 24 24" fill="white"><path d="M11 5L6 9H2v6h4l5 4V5zM23 9l-6 6M17 9l6 6" stroke="white" strokeWidth="2" fill="none"/></svg>
              : <svg width="15" height="15" viewBox="0 0 24 24" fill="white"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14" stroke="white" strokeWidth="1.5" fill="none"/></svg>
            }
          </Box>
          <Box
            onClick={changeVol}
            style={{ width: 56, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.15)", cursor: "pointer", position: "relative" }}
          >
            <Box style={{ height: "100%", borderRadius: 2, width: `${(muted ? 0 : volume) * 100}%`, background: "rgba(255,255,255,0.6)" }} />
          </Box>

          {/* Fullscreen */}
          <Box onClick={toggleFS} style={iconBtn}>
            <svg width="15" height="15" viewBox="0 0 24 24" stroke="white" strokeWidth="2" fill="none">
              <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
              <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
            </svg>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}


/* ---- QuickView modal for images, audio, video ---- */
