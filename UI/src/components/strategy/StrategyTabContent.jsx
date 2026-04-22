// Created by Metrum AI for AMD

import { C, radius, shadow, gradient } from "../../tokens";
import { Box, T, Badge, Card } from "../primitives";
import StrategySkeleton from "./StrategySkeleton";
import { frameworkColors, isTrackRecommended } from "../../lib/strategy";
import "../../css/strategy/StrategyTabContent.css";

function trackLockLabel(row, hwCaps) {
  if (row.hwKey === "image" && hwCaps?.services?.image?.up === false) {
    return "Image service offline";
  }
  if (row.hwKey === "video" && hwCaps?.services?.video?.up === false) {
    return "Video service offline";
  }
  return "Track unavailable";
}

export default function StrategyTabContent({
  tab, strategyReady, copyReady, scenesReady, audioReady, strategy, messagingAngles, audiences, copyVariants, scenes, audioAds, tracks, setTracks, hwAllowed, hwCaps,
}) {
  const tr = strategy?.track_recommendations || {};
  const showTrackRec =
    strategy?.market_data_used !== false;
  const recImg =
    showTrackRec && isTrackRecommended(tr.image_text);
  const recAudio =
    showTrackRec && isTrackRecommended(tr.audio_podcast);
  const recVideo =
    showTrackRec && isTrackRecommended(tr.video);

  return (
    <Box className="strategy-tab-content" key={tab}>
      {tab === "direction" && (
        <Card>
          {!strategyReady ? (
            <>
              <StrategySkeleton h={12} w="30%" style={{ marginBottom: 12 }} />
              <StrategySkeleton h={60} style={{ marginBottom: 20 }} />
              <StrategySkeleton h={12} w="30%" style={{ marginBottom: 12 }} />
              <StrategySkeleton h={60} />
            </>
          ) : (
            <>
              <Box style={{ marginBottom: 20 }}>
                <T s={11} c={C.muted} w={700} style={{ marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Positioning</T>
                <T s={14} c={C.text} style={{ lineHeight: 1.8 }}>{strategy?.campaign_direction || "Strategy data will appear here after generation."}</T>
              </Box>
              {messagingAngles.length > 0 && (
                <Box style={{ paddingTop: 20, borderTop: `1px solid ${C.borderLight}` }}>
                  <T s={11} c={C.muted} w={700} style={{ marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Messaging Angles</T>
                  {messagingAngles.map((angle, i) => (
                    <T key={i} s={13} c={C.text} style={{ lineHeight: 1.7, marginBottom: 4 }}>
                      {typeof angle === "string" ? `- ${angle}` : `- ${angle.angle || angle.name || JSON.stringify(angle)}`}
                    </T>
                  ))}
                </Box>
              )}
            </>
          )}
        </Card>
      )}

      {tab === "audience" && (
        <Box className="strategy-tab-content__stack">
          {!strategyReady ? [1, 2, 3].map((i) => <Card key={i}><StrategySkeleton h={80} /></Card>) : (
            (audiences.length > 0 ? audiences : [{ name: "No audience data", demographics: "-", platforms: "-", rationale: "Run strategy generation first" }]).map((seg, i) => (
              <Card key={i}>
                <T s={15} w={600} style={{ marginBottom: 14 }}>{seg.name || seg.segment_name || `Segment ${i + 1}`}</T>
                {[
                  ["Demographics", seg.demographics || seg.demo || "-"],
                  ["Platforms", Array.isArray(seg.platforms) ? seg.platforms.join(", ") : (seg.platforms || "-")],
                  ["Rationale", seg.rationale || seg.why || seg.description || "-"],
                ].map(([k, v]) => (
                  <Box key={k} style={{ marginBottom: 10 }}>
                    <T s={10} c={C.dim} w={700} className="strategy-tab-content__label" style={{ marginBottom: 3 }}>{k}</T>
                    <T s={13} c={C.text} style={{ lineHeight: 1.6 }}>{v}</T>
                  </Box>
                ))}
              </Card>
            ))
          )}
        </Box>
      )}

      {tab === "copy" && (
        <Box className="strategy-tab-content__stack">
          {!copyReady ? [1, 2, 3].map((i) => <Card key={i}><StrategySkeleton h={120} /></Card>) : (
            (copyVariants.length > 0 ? copyVariants : []).map((v, i) => {
              const color = frameworkColors[v.framework] || C.blue;
              return (
                <Card key={v.id || i} style={{ borderLeft: `3px solid ${color}` }}>
                  <Badge bg={color}>{v.framework}</Badge>
                  <T s={17} w={600} className="strategy-tab-content__copyTitle">{v.headline}</T>
                  <T s={13} c={C.text} style={{ lineHeight: 1.7, marginBottom: 14 }}>{v.body}</T>
                  <Box className="strategy-tab-content__cta" style={{ borderLeft: `3px solid ${color}`, padding: "8px 14px", background: `${color}06`, borderRadius: `0 ${radius.sm}px ${radius.sm}px 0` }}>
                    <T s={10} c={C.dim} w={600} style={{ textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>CTA</T>
                    <T s={14} w={600} c={color}>{v.cta}</T>
                  </Box>
                  {v.hashtags && v.hashtags.length > 0 && <T s={11} c={C.dim}>{v.hashtags.join(" ")}</T>}
                </Card>
              );
            })
          )}
        </Box>
      )}

      {tab === "scenes" && (
        <Box className="strategy-tab-content__stack">
          {!scenesReady ? [1, 2, 3].map((i) => <Card key={i}><StrategySkeleton h={80} /></Card>) : (
            (scenes.length > 0 ? scenes : []).map((s, i) => (
              <Card key={s.id || i} className="strategy-tab-content__sceneCard">
                <Box className="strategy-tab-content__scenePreview" style={{ background: `linear-gradient(135deg, ${C.elevated}, ${C.accent}08)`, borderRadius: radius.sm }}>
                  <T s={10} c={C.dim}>Preview</T>
                </Box>
                <Box>
                  <T s={12} c={C.accent} w={600} style={{ marginBottom: 4 }}>{(s.scene_type || "scene").charAt(0).toUpperCase() + (s.scene_type || "scene").slice(1)}</T>
                  <T s={13} c={C.text} style={{ lineHeight: 1.7 }}>{s.image_prompt}</T>
                  {s.video_script && <T s={11} c={C.dim} style={{ marginTop: 6, fontStyle: "italic" }}>Video: {s.video_script}</T>}
                </Box>
              </Card>
            ))
          )}
        </Box>
      )}

      {tab === "audio" && (
        <Box className="strategy-tab-content__stack">
          {!audioReady ? [1, 2].map((i) => <Card key={i}><StrategySkeleton h={80} /></Card>) : (
            (audioAds.length > 0 ? audioAds : []).map((a, i) => {
              const color = i % 2 === 0 ? C.teal : C.accent;
              return (
                <Card key={a.id || i} style={{ borderLeft: `3px solid ${color}` }}>
                  <Box className="strategy-tab-content__audioHeader">
                    <Badge bg={color}>{a.tone}</Badge>
                    <T s={11} c={C.dim}>Voice: {a.voice || "af_heart"}</T>
                  </Box>
                  <T s={13} c={C.text} style={{ lineHeight: 1.8, fontStyle: "italic" }}>"{a.script}"</T>
                </Card>
              );
            })
          )}
        </Box>
      )}

      {tab === "tracks" && (
        <Box className="strategy-tab-content__stack">
          {[
            { name: "Track 1: Image + Text Ads", desc: "3 hero images -> 9 ad creatives (3x3 crops) + 3 copy variants", assets: 15, gpu: "GPU 1 (FLUX)", k: "img", on: tracks.img, hwKey: "image", rec: recImg },
            { name: "Track 2: Audio Ads", desc: "2 clips (host-read + produced spot)", assets: 2, gpu: "CPU only", k: "audio", on: tracks.audio, hwKey: null, rec: recAudio },
            { name: "Track 3: Video Campaign", desc: "4s clip (AnimateDiff Lightning) + brand mux", assets: 1, gpu: "GPU 1 (AnimateDiff)", k: "video", on: tracks.video, hwKey: "video", rec: recVideo },
          ].map((row) => {
            const locked = row.hwKey && !hwAllowed[row.hwKey];
            return (
              <Card key={row.k} onClick={() => { if (locked) return; setTracks((p) => ({ ...p, [row.k]: !p[row.k] })); }} className="strategy-tab-content__trackCard" style={{ cursor: locked ? "not-allowed" : "pointer", boxShadow: row.on && !locked ? shadow.lg : shadow.md, borderLeft: locked ? `3px solid ${C.red || "#e53e3e"}` : row.on ? `3px solid ${C.accent}` : "3px solid transparent", opacity: locked ? 0.5 : 1 }}>
                <Box>
                  <Box className="strategy-tab-content__trackMeta" style={{ flexWrap: "wrap" }}>
                    <T s={14} w={600}>{row.name}</T>
                    {row.rec && <Badge bg={C.green}>Recommended</Badge>}
                    {locked && <Badge bg={C.red || "#e53e3e"}>{trackLockLabel(row, hwCaps)}</Badge>}
                  </Box>
                  <T s={13} c={C.text}>{row.desc}</T>
                  <T s={11} c={C.dim} style={{ marginTop: 4 }}>{row.assets} assets / {row.gpu}</T>
                </Box>
                <Box style={{ width: 24, height: 24, borderRadius: 8, flexShrink: 0, background: locked ? C.border : row.on ? C.accent : "transparent", border: `2px solid ${locked ? C.border : row.on ? C.accent : C.border}`, display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.15s ease", boxShadow: !locked && row.on ? shadow.glow(C.accent) : "none" }}>
                  {locked && <T s={12} c={C.dim}>{"✗"}</T>}
                  {!locked && row.on && <T s={12} c="#fff">{"✓"}</T>}
                </Box>
              </Card>
            );
          })}
        </Box>
      )}
    </Box>
  );
}
