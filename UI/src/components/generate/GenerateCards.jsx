// Created by Metrum AI for AMD

import { useState, useEffect, useRef } from "react";
import { C, gradient, radius } from "../../tokens";
import { Box, T, Badge } from "../primitives";
import useAssetUrl from "../../hooks/useAssetUrl";
import { fwColors, titleCase, fallbackGradients } from "../../lib/generate";
import { Shimmer, CheckDone, WaveViz, AssetImage } from "./GenerateShared";

export function RawImageCard({ item, onOpen }) {
  const [hovered, setHovered] = useState(false);
  const isDone = item.status === "done";
  const isGen = item.status === "generating";

  return (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => isDone && item.asset_url && onOpen?.({
        type: "image",
        asset_url: item.asset_url,
        title: titleCase(item.name),
        sub: "Raw model output",
      })}
      style={{
        height: 160, borderRadius: radius.lg,
        background: item.gradient || fallbackGradients[0],
        border: `1px solid ${hovered && isDone ? C.borderLight : C.border}`,
        position: "relative", overflow: "hidden",
        cursor: isDone && item.asset_url ? "pointer" : "default",
        transition: "border-color 0.2s ease, transform 0.2s ease",
        transform: hovered && isDone ? "translateY(-2px)" : "none",
      }}
    >
      {/* Real image overlay when available */}
      {item.asset_url && (
        <AssetImage s3Url={item.asset_url} style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover", borderRadius: radius.lg,
        }} />
      )}

      {isGen && <Shimmer />}

      {/* Generating center overlay */}
      {isGen && (
        <Box style={{
          position: "absolute", top: "36%", left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          zIndex: 2,
        }}>
          <Box style={{
            width: 10, height: 10, borderRadius: 5,
            background: C.accent,
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
          <T s={10} c={C.accent} w={600} style={{ animation: "pulse 1.5s ease-in-out infinite" }}>Generating...</T>
        </Box>
      )}

      {/* Status badge top right */}
      <Box style={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 5, alignItems: "center" }}>
        {isDone && <Badge bg={C.green} soft={C.greenSoft}>1024 x 1024</Badge>}
        {isDone && <CheckDone size={16} />}
      </Box>

      {/* Bottom info */}
      <Box style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "28px 14px 10px",
        background: "linear-gradient(transparent, rgba(0,0,0,0.9))",
      }}>
        <T s={12} c={C.white} w={600}>{titleCase(item.name)}</T>
        <T s={9} c={C.muted} style={{ marginTop: 2, lineHeight: 1.4 }}>{item.desc}</T>
      </Box>

      {/* Hover preview overlay */}
      {hovered && isDone && (
        <Box style={{
          position: "absolute", inset: 0,
          background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "fadeIn 0.15s ease",
          zIndex: 3,
        }}>
          <Box style={{
            padding: "8px 20px", borderRadius: radius.sm,
            background: C.glass, backdropFilter: "blur(8px)",
            border: `1px solid ${C.borderLight}`,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <T s={12} c={C.white} w={600}>{item.asset_url ? "Preview Full Size" : "Preview"}</T>
          </Box>
        </Box>
      )}
    </Box>
  );
}

/* ---- RawAudioCard ---- */
export function RawAudioCard({ item, onOpen }) {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const { getUrl } = useAssetUrl();
  const isDone = item.status === "done";
  const isGen = item.status === "generating";

  // Resolve the real audio URL if available
  useEffect(() => {
    if (item.asset_url) {
      getUrl(item.asset_url).then(setAudioUrl);
    }
  }, [item.asset_url, getUrl]);

  // Real audio playback progress
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTimeUpdate = () => {
      if (audio.duration) {
        setProgress((audio.currentTime / audio.duration) * 100);
      }
    };
    const onEnded = () => {
      setPlaying(false);
      setProgress(0);
    };
    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
    };
  }, [audioUrl]);

  // Fake playback when no real audio
  useEffect(() => {
    if (!playing || audioUrl) return;
    const id = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) { setPlaying(false); return 0; }
        return prev + 1;
      });
    }, 150);
    return () => clearInterval(id);
  }, [playing, audioUrl]);

  const togglePlay = (e) => {
    e.stopPropagation();
    if (!isDone) return;
    const audio = audioRef.current;
    if (audioUrl && audio) {
      if (playing) {
        audio.pause();
        setPlaying(false);
      } else {
        audio.play().catch(() => {});
        setPlaying(true);
      }
    } else {
      if (playing) {
        setPlaying(false);
      } else {
        if (progress >= 100) setProgress(0);
        setPlaying(true);
      }
    }
  };

  const duration = audioRef.current?.duration || 15;
  const elapsedSec = Math.floor((progress / 100) * duration);
  const durationInt = Math.floor(duration);
  const timeStr = isDone
    ? `0:${String(elapsedSec).padStart(2, "0")} / 0:${String(durationInt).padStart(2, "0")}`
    : "--:--";

  const handleDownload = (e) => {
    e.stopPropagation();
    if (audioUrl) {
      const filename = `${(item.name || "audio").replace(/\s+/g, "_").toLowerCase()}.wav`;
      fetch(audioUrl)
        .then(r => r.blob())
        .then(blob => {
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = blobUrl;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
        })
        .catch(() => window.open(audioUrl, "_blank"));
    } else if (item.asset_url) {
      onOpen?.({ type: "audio", asset_url: item.asset_url, title: titleCase(item.name), sub: "Audio output" });
    }
  };

  return (
    <Box style={{
      height: 160, borderRadius: radius.lg,
      background: C.elevated,
      border: `1px solid ${isDone ? (playing ? C.teal + "50" : C.teal + "30") : C.border}`,
      padding: 14, position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      transition: "border-color 0.2s ease",
    }}>
      {isGen && <Shimmer />}
      {audioUrl && <audio ref={audioRef} src={audioUrl} preload="metadata" />}

      {/* Header */}
      <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
        <Box>
          <T s={12} c={C.white} w={600}>{titleCase(item.name)}</T>
          <T s={9} c={C.muted} style={{ marginTop: 2 }}>{item.desc}</T>
        </Box>
        {isDone && <CheckDone size={18} />}
        {isGen && (
          <Box style={{
            width: 8, height: 8, borderRadius: 4, background: C.accent,
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
        )}
      </Box>

      {/* Player area */}
      <Box style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 6 }}>
        {/* Waveform + play button row */}
        <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Box
            onClick={togglePlay}
            style={{
              width: 32, height: 32, borderRadius: 16, flexShrink: 0,
              background: isDone ? (playing ? C.teal : gradient.amd) : C.hover,
              border: `1px solid ${isDone ? "transparent" : C.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: isDone ? "pointer" : "not-allowed",
              transition: "all 0.15s ease, transform 0.1s ease",
              opacity: isDone ? 1 : 0.35,
              transform: isDone ? "scale(1)" : "scale(0.9)",
              boxShadow: playing ? `0 0 16px ${C.teal}40` : "none",
            }}
            onMouseEnter={e => { if (isDone) e.currentTarget.style.transform = "scale(1.08)"; }}
            onMouseLeave={e => { if (isDone) e.currentTarget.style.transform = "scale(1)"; }}
          >
            {playing ? (
              <Box style={{ display: "flex", gap: 2 }}>
                <Box style={{ width: 2.5, height: 11, background: "#fff", borderRadius: 1 }} />
                <Box style={{ width: 2.5, height: 11, background: "#fff", borderRadius: 1 }} />
              </Box>
            ) : (
              <Box style={{
                width: 0, height: 0,
                borderTop: "6px solid transparent",
                borderBottom: "6px solid transparent",
                borderLeft: "10px solid #fff",
                marginLeft: 2,
              }} />
            )}
          </Box>
          <Box style={{ flex: 1 }}>
            <WaveViz done={isDone} progress={playing || progress > 0 ? progress : 0} />
          </Box>
        </Box>

        {/* Progress bar + time */}
        <Box style={{ display: "flex", alignItems: "center", gap: 8, paddingLeft: 42 }}>
          <Box style={{ flex: 1, height: 3, background: C.border, borderRadius: 2, overflow: "hidden" }}>
            <Box style={{
              height: "100%", width: `${progress}%`,
              background: playing ? C.teal : (progress > 0 ? C.teal : "transparent"),
              borderRadius: 2,
              transition: playing ? "width 0.15s linear" : "width 0.3s ease",
            }} />
          </Box>
          <T s={10} c={playing ? C.teal : C.dim} w={500} style={{ flexShrink: 0, fontFamily: "'Inter', monospace", minWidth: 60, textAlign: "right" }}>
            {timeStr}
          </T>
        </Box>
      </Box>

      {/* Footer */}
      <Box style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
        {isDone ? (
          <Box style={{ display: "flex", gap: 6 }}>
            <Box
              onClick={handleDownload}
              style={{
                padding: "3px 10px", borderRadius: 12, cursor: "pointer",
                background: `${C.teal}12`, transition: "all 0.15s ease",
              }}
              onMouseEnter={e => e.currentTarget.style.background = `${C.teal}25`}
              onMouseLeave={e => e.currentTarget.style.background = `${C.teal}12`}
            >
              <T s={10} c={C.teal} w={700} style={{ letterSpacing: "0.06em" }}>WAV</T>
            </Box>
          </Box>
        ) : (
          <T s={10} c={C.accent} w={600} style={{ animation: "pulse 2s ease-in-out infinite" }}>Rendering...</T>
        )}
        {isDone && (
          <Box
            onClick={handleDownload}
            style={{
              padding: "5px 14px", borderRadius: radius.sm,
              background: C.hover, border: `1px solid ${C.border}`,
              cursor: "pointer", transition: "all 0.15s ease",
              display: "flex", alignItems: "center", gap: 6,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = C.teal; e.currentTarget.style.background = `${C.teal}10`; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.hover; }}
          >
            <T s={10} c={C.text} w={600}>Download</T>
          </Box>
        )}
      </Box>
    </Box>
  );
}

/* ---- RawVideoCard (LTX raw clip in Raw Outputs section) ---- */
export function RawVideoCard({ item, onOpen }) {
  const [hovered, setHovered] = useState(false);
  const [resolvedSrc, setResolvedSrc] = useState(null);
  const videoRef = useRef(null);
  const { getUrl } = useAssetUrl();
  const isDone = item.status === "done";
  const isGen = item.status === "generating";
  const openUrl = item.preview_url || item.asset_url;

  useEffect(() => {
    if (openUrl && isDone) getUrl(openUrl).then(setResolvedSrc);
    else setResolvedSrc(null);
  }, [openUrl, isDone, getUrl]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !resolvedSrc) return;
    if (hovered && isDone) el.play().catch(() => {});
    else {
      el.pause();
      try { el.currentTime = 0; } catch (_) { /* ignore */ }
    }
  }, [hovered, resolvedSrc, isDone]);

  return (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => isDone && openUrl && onOpen?.({
        type: "video",
        asset_url: openUrl,
        title: item.name || "Video clip",
        sub: item.sub || "Model output",
      })}
      style={{
        height: 160, borderRadius: radius.lg,
        background: "linear-gradient(145deg, #0f1218 0%, #1a1528 45%, #0c1018 100%)",
        border: `1px solid ${hovered && isDone ? C.borderLight : C.border}`,
        position: "relative", overflow: "hidden",
        cursor: isDone && openUrl ? "pointer" : "default",
        transition: "border-color 0.2s ease, transform 0.2s ease",
        transform: hovered && isDone ? "translateY(-2px)" : "none",
      }}
    >
      {resolvedSrc && isDone && (
        <video
          ref={videoRef}
          src={resolvedSrc}
          muted
          playsInline
          loop
          style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            objectFit: "cover", borderRadius: radius.lg,
          }}
        />
      )}

      {isGen && <Shimmer />}

      {isGen && (
        <Box style={{
          position: "absolute", top: "36%", left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          zIndex: 2,
        }}>
          <Box style={{
            width: 10, height: 10, borderRadius: 5,
            background: C.accent,
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
          <T s={10} c={C.accent} w={600} style={{ animation: "pulse 1.5s ease-in-out infinite" }}>Generating video...</T>
        </Box>
      )}

      <Box style={{ position: "absolute", top: 10, right: 10, display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end", maxWidth: "70%" }}>
        {item.final_ready && <Badge bg={C.green} soft={C.greenSoft}>Final</Badge>}
        {isDone && !item.final_ready && <Badge bg={C.teal}>Raw</Badge>}
        {isDone && <CheckDone size={16} />}
      </Box>

      <Box style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "28px 14px 10px",
        background: "linear-gradient(transparent, rgba(0,0,0,0.9))",
      }}>
        <T s={12} c={C.white} w={600}>{item.name}</T>
        <T s={9} c={C.muted} style={{ marginTop: 2, lineHeight: 1.4 }}>{item.desc}</T>
      </Box>

      {hovered && isDone && (
        <Box style={{
          position: "absolute", inset: 0,
          background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "fadeIn 0.15s ease",
          zIndex: 3,
        }}>
          <Box style={{
            padding: "8px 20px", borderRadius: radius.sm,
            background: C.glass, backdropFilter: "blur(8px)",
          }}>
            <T s={11} c="#fff" w={600}>Quick View</T>
          </Box>
        </Box>
      )}
    </Box>
  );
}

/* ---- VideoDeliverableCard (final MP4 with brand overlay) ---- */
export function VideoDeliverableCard({ item, isGenerating, muxRunning, onOpen }) {
  const [hovered, setHovered] = useState(false);
  const isDone = item.done;
  const isActive = !isDone && (isGenerating || muxRunning);
  const thumbRef = useRef(null);

  useEffect(() => {
    const el = thumbRef.current;
    if (!el || !isDone) return;
    if (hovered) el.play().catch(() => {});
    else { el.pause(); el.currentTime = 0; }
  }, [hovered, isDone]);

  const [resolvedSrc, setResolvedSrc] = useState(null);
  const { getUrl } = useAssetUrl();
  useEffect(() => {
    if (item.final_url) getUrl(item.final_url).then(setResolvedSrc);
    else setResolvedSrc(null);
  }, [item.final_url, getUrl]);

  return (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => isDone && item.final_url && onOpen?.({
        type: "video",
        asset_url: item.final_url,
        title: item.title || "Branded video",
        sub: "Final deliverable",
      })}
      style={{
        borderRadius: radius.lg,
        border: `1px solid ${hovered && isDone ? C.borderLight : C.border}`,
        background: C.elevated,
        overflow: "hidden",
        position: "relative",
        transition: "border-color 0.2s ease, transform 0.2s ease",
        transform: hovered && isDone ? "translateY(-2px)" : "none",
        cursor: isDone ? "pointer" : "default",
      }}
    >
      <Box style={{
        height: 220,
        background: C.card,
        position: "relative", overflow: "hidden",
      }}>
        {resolvedSrc && isDone && (
          <video
            ref={thumbRef}
            src={resolvedSrc}
            muted
            playsInline
            loop
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}

        {isActive && <Shimmer />}

        {isDone && hovered && (
          <Box style={{
            position: "absolute", inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "flex", alignItems: "center", justifyContent: "center",
            animation: "fadeIn 0.15s ease",
          }}>
            <Box style={{
              padding: "10px 24px", borderRadius: radius.sm,
              background: gradient.amd, cursor: "pointer",
            }}>
              <T s={12} c="#fff" w={600}>Quick View</T>
            </Box>
          </Box>
        )}

        {isActive && (
          <Box style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 8,
          }}>
            <Box style={{
              width: 10, height: 10, borderRadius: 5, background: C.accent,
              animation: "pulse 1.5s ease-in-out infinite",
            }} />
            <T s={12} c={C.accent} w={600}>
              {item.hasRaw ? "Brand overlay..." : "Waiting for clip..."}
            </T>
          </Box>
        )}

        {!isDone && !isActive && (
          <Box style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 4,
          }}>
            <T s={12} c={C.dim}>Queued</T>
          </Box>
        )}
      </Box>

      <Box style={{
        padding: "12px 16px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        borderTop: `1px solid ${C.border}`,
      }}>
        <Box style={{ minWidth: 0 }}>
          <T s={11} c={C.text} w={600}>{item.title}</T>
          <T
            s={10}
            c={C.muted}
            style={{
              marginTop: 4,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 240,
            }}
          >
            {item.copy_label || "Copy variant"}
          </T>
        </Box>
        {isDone && <CheckDone size={18} />}
      </Box>
    </Box>
  );
}

/* ---- CreativeCard ---- */
export function CreativeCard({ ad, isGenerating, onOpen }) {
  const [hovered, setHovered] = useState(false);
  const fwc = fwColors[ad.fw] || C.blue;
  const isDone = ad.done;
  const isActive = !isDone && isGenerating;

  return (
    <Box
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => isDone && ad.asset_url && onOpen?.({
        type: "image",
        asset_url: ad.asset_url,
        title: ad.copy || "Creative Asset",
        sub: `${ad.fw || ""} ${ad.dim || ""}`.trim(),
      })}
      style={{
        borderRadius: radius.lg,
        border: `1px solid ${hovered && isDone ? C.borderLight : C.border}`,
        background: C.elevated,
        overflow: "hidden",
        position: "relative",
        transition: "border-color 0.2s ease, transform 0.2s ease",
        transform: hovered && isDone ? "translateY(-2px)" : "none",
        cursor: isDone ? "pointer" : "default",
      }}
    >
      <Box style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: fwc,
      }} />

      <Box style={{
        height: 220,
        background: C.card,
        position: "relative", overflow: "hidden",
      }}>
        {/* Real composition image when available */}
        {ad.asset_url && <AssetImage s3Url={ad.asset_url} style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover",
        }} />}

        {isActive && <Shimmer />}

        {isDone && (
          <>
            {/* Copy positioned at bottom like a real ad */}
            <Box style={{
              position: "absolute", bottom: 0, left: 0, right: 0,
              padding: "32px 18px 16px",
              background: "linear-gradient(transparent 0%, rgba(0,0,0,0.6) 40%, rgba(0,0,0,0.85) 100%)",
            }}>
              <T s={16} c={C.white} w={700} style={{ lineHeight: 1.25, marginBottom: 6 }}>{ad.copy}</T>
              {ad.cta && <T s={11} c={fwc} w={600}>{ad.cta} {"\u2192"}</T>}
            </Box>

            {hovered && (
              <Box style={{
                position: "absolute", inset: 0,
                background: "rgba(0,0,0,0.55)",
                display: "flex", alignItems: "center", justifyContent: "center",
                animation: "fadeIn 0.15s ease",
              }}>
                <Box style={{
                  padding: "10px 24px", borderRadius: radius.sm,
                  background: gradient.amd, cursor: "pointer",
                }}>
                  <T s={12} c="#fff" w={600}>{ad.asset_url ? "Quick View" : "View"}</T>
                </Box>
              </Box>
            )}
          </>
        )}

        {isActive && (
          <Box style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 10,
          }}>
            <Box style={{
              width: 10, height: 10, borderRadius: 5, background: C.accent,
              animation: "pulse 1.5s ease-in-out infinite",
            }} />
            <T s={12} c={C.accent} w={600}>Compositing...</T>
            <T s={10} c={C.dim}>Applying brand overlay + copy</T>
          </Box>
        )}

        {!isDone && !isActive && (
          <Box style={{
            position: "absolute", inset: 0,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 4,
          }}>
            <T s={12} c={C.dim}>Queued</T>
            <T s={10} c={C.dim} style={{ opacity: 0.5 }}>Waiting for raw image</T>
          </Box>
        )}
      </Box>

      <Box style={{
        padding: "12px 16px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        borderTop: `1px solid ${C.border}`,
      }}>
        <Box style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Badge bg={fwc}>{ad.fw}</Badge>
          <T s={10} c={C.dim}>{ad.dim}</T>
        </Box>
        {isDone && <CheckDone size={18} />}
      </Box>
    </Box>
  );
}

/* ---- CampaignThumbnail ---- */
export function CampaignThumbnail({ done, isGenerating, generationQueued, campaignName, assetCount, onOpen }) {
  const [hovered, setHovered] = useState(false);
  return (
    <Box
      onClick={onOpen}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        height: 220, borderRadius: radius.lg,
        background: "linear-gradient(145deg, #1a1020 0%, #2d1525 35%, #1a1018 100%)",
        border: `1px solid ${hovered && done ? C.borderLight : C.border}`,
        position: "relative", overflow: "hidden",
        cursor: done ? "pointer" : "default",
        transition: "border-color 0.2s ease, transform 0.2s ease",
        transform: hovered && done ? "translateY(-2px)" : "none",
      }}
    >
      {!done && <Shimmer />}

      <Box style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.7) 100%)",
      }} />

      <Box style={{
        position: "absolute", inset: 0, display: "flex",
        flexDirection: "column", justifyContent: "flex-end",
        padding: "28px 32px",
      }}>
        <Box style={{ display: "flex", alignItems: "end", justifyContent: "space-between" }}>
          <Box>
            <img src="/assets/amd_logo.png" alt="AMD" style={{
              height: 32, objectFit: "contain", marginBottom: 12,
              filter: "brightness(0) invert(1)",
            }} />
            <T s={24} w={700} c="#fff" style={{ lineHeight: 1.2 }}>{campaignName || "Campaign"}</T>
            <T s={12} c="rgba(255,255,255,0.6)" style={{ marginTop: 6 }}>
              {done
                ? `${assetCount} assets generated`
                : isGenerating
                ? "Generating campaign assets..."
                : generationQueued
                ? "Generation job queued..."
                : "No generation job queued"}
            </T>
          </Box>
          {done && <Badge bg={C.green}>Ready</Badge>}
          {!done && (
            <Box style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
              <Box style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Box style={{
                  width: 6, height: 6, borderRadius: 3, background: C.accent,
                  animation: "pulse 1.5s ease-in-out infinite",
                }} />
                <T s={11} c={C.accent} w={600}>In Progress</T>
              </Box>
              <Box style={{
                padding: "8px 20px", borderRadius: radius.sm,
                background: C.hover, border: `1px solid ${C.border}`,
                opacity: 0.4, cursor: "not-allowed",
              }}>
                <T s={11} c={C.dim} w={600}>Download Campaign</T>
              </Box>
            </Box>
          )}
        </Box>
      </Box>

      {hovered && done && (
        <Box style={{
          position: "absolute", inset: 0,
          background: "rgba(0,0,0,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "fadeIn 0.15s ease",
        }}>
          <Box style={{
            padding: "12px 32px", borderRadius: radius.md,
            background: gradient.amd,
          }}>
            <T s={14} c="#fff" w={600}>Open Campaign Preview</T>
          </Box>
        </Box>
      )}
    </Box>
  );
}

/* ---- CampaignPreviewModal ---- */
