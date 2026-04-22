// Created by Metrum AI for AMD

import { useState, useEffect } from "react";
import { C, gradient, shadow, radius } from "../../tokens";
import { Box, T, Badge, Btn } from "../primitives";
import useAssetUrl from "../../hooks/useAssetUrl";
import { titleCase, fallbackGradients } from "../../lib/generate";
import { AssetImage, ModalAudioPlayer, ModalVideoPlayer } from "./GenerateShared";

export function QuickViewModal({ item, onClose }) {
  const [url, setUrl] = useState(null);
  const { getUrl } = useAssetUrl();
  const isVideo = item?.type === "video";

  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  useEffect(() => {
    let mounted = true;
    setUrl(null);
    if (!item?.asset_url) return;
    getUrl(item.asset_url).then((resolved) => {
      if (mounted) setUrl(resolved);
    });
    return () => { mounted = false; };
  }, [item, getUrl]);

  return (
    <Box
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1200,
        background: "rgba(0,0,0,0.85)",
        display: "flex", alignItems: "center", justifyContent: "center",
        animation: "fadeIn 0.18s ease",
      }}
    >
      <Box
        onClick={(e) => e.stopPropagation()}
        style={{
          width: isVideo ? "fit-content" : "min(1180px, 96vw)",
          maxWidth: "96vw",
          maxHeight: "92vh",
          background: C.surface, border: `1px solid ${C.borderLight}`,
          borderRadius: radius.lg, overflow: "hidden", boxShadow: shadow.xl,
        }}
      >
        <Box style={{
          padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <Box>
            <T s={13} w={600}>{item?.title || "Quick View"}</T>
            {item?.sub ? <T s={10} c={C.dim}>{item.sub}</T> : null}
          </Box>
          <Box
            onClick={onClose}
            style={{
              width: 26, height: 26, borderRadius: radius.sm, cursor: "pointer",
              background: C.elevated, border: `1px solid ${C.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <T s={12} c={C.muted}>{"\u2715"}</T>
          </Box>
        </Box>
        <Box style={{
          padding: 14, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 10,
          minHeight: 340, maxHeight: "calc(92vh - 62px)", overflow: "auto",
        }}>
          {!url && !isVideo && <T s={12} c={C.dim}>Loading asset...</T>}
          {url && item?.type === "audio" && (
            <ModalAudioPlayer url={url} />
          )}
          {item?.type === "video" && (
            <ModalVideoPlayer url={url} />
          )}
          {url && item?.type !== "audio" && item?.type !== "video" && (
            <Box style={{
              maxWidth: "min(68vw, 860px)", maxHeight: "80vh",
              borderRadius: radius.md,
              overflow: "hidden", background: C.card,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <img src={url} alt={item?.title || ""} style={{ maxWidth: "100%", maxHeight: "80vh", objectFit: "contain", display: "block" }} />
            </Box>
          )}
          {url && (
            <Box style={{ display: "flex", gap: 10, marginTop: 4 }}>
              {item?.type !== "audio" && <Box
                onClick={() => window.open(url, "_blank")}
                style={{
                  padding: "6px 12px", borderRadius: radius.sm,
                  border: `1px solid ${C.border}`, background: C.elevated, cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderLight; e.currentTarget.style.background = C.hover; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.elevated; }}
              >
                <T s={11} c={C.text} w={600}>Open Full Resolution</T>
              </Box>}
              <Box
                onClick={() => {
                  const ext = item?.type === "audio" ? "wav" : item?.type === "video" ? "mp4" : "png";
                  const filename = `${(item?.title || "asset").replace(/\s+/g, "_").toLowerCase()}.${ext}`;
                  fetch(url)
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
                    .catch(() => window.open(url, "_blank"));
                }}
                style={{
                  padding: "6px 16px", borderRadius: radius.sm,
                  background: gradient.amd, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 6,
                  transition: "opacity 0.15s ease",
                }}
                onMouseEnter={e => { e.currentTarget.style.opacity = "0.85"; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = "1"; }}
              >
                <T s={13} c="#fff" w={600}>{"\u2193"}</T>
                <T s={11} c="#fff" w={600}>Download</T>
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}

/* ---- CampaignPreviewModal ---- */
export function CampaignPreviewModal({ onClose, campaign, compositions, images, audioAds, videoAds, onExport, exporting, onQuickView, imageTrackEnabled, audioTrackEnabled, videoTrackEnabled }) {
  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const videoList = videoAds || [];
  const videoFinalCount = videoList.filter(v => v.final_url).length;
  const totalAssets =
    (compositions?.length || 0) +
    (images?.length || 0) +
    (audioAds || []).filter(a => a.is_generated && a.asset_url).length +
    videoFinalCount;
  const hasImages = imageTrackEnabled && (images?.length > 0 || compositions?.length > 0);
  const hasAudio = audioTrackEnabled && (audioAds || []).some(a => a.is_generated && a.asset_url);
  const hasVideo = videoTrackEnabled && videoList.some(v => v.video_url || v.final_url);

  return (
    <Box style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      animation: "fadeIn 0.2s ease",
    }} onClick={onClose}>
      <Box
        onClick={e => e.stopPropagation()}
        style={{
          width: "90%", maxWidth: 900, maxHeight: "85vh",
          background: C.surface, border: `1px solid ${C.border}`,
          borderRadius: radius.lg, overflow: "hidden",
          display: "flex", flexDirection: "column",
          position: "relative",
        }}
      >
        <Box style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 2,
          background: gradient.amdH,
        }} />

        {/* Modal header */}
        <Box style={{
          padding: "18px 24px", borderBottom: `1px solid ${C.border}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
          flexShrink: 0,
        }}>
          <Box style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <img src="/assets/amd_logo.png" alt="AMD" style={{
              height: 22, objectFit: "contain",
              filter: "brightness(0) invert(1)",
            }} />
            <Box style={{ width: 1, height: 20, background: C.border }} />
            <T s={15} w={700}>{campaign?.name || "Campaign"}</T>
            <Badge bg={C.green}>{totalAssets} Assets</Badge>
          </Box>
          <Box style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Btn primary style={{ padding: "8px 22px" }} onClick={onExport} disabled={exporting}>
              {exporting ? "Exporting..." : "Download All (.zip)"}
            </Btn>
            <Box
              onClick={onClose}
              style={{
                width: 30, height: 30, borderRadius: radius.sm,
                background: C.elevated, border: `1px solid ${C.border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer",
              }}
            >
              <T s={14} c={C.muted}>{"\u2715"}</T>
            </Box>
          </Box>
        </Box>

        {/* Scrollable content */}
        <Box style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>

          {/* Ad Creatives grid */}
          {compositions && compositions.length > 0 && (
            <>
              <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>Ad Creatives</T>
              <Box style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
                {compositions.map((comp, i) => (
                  <Box
                    key={comp.id || i}
                    onClick={() => comp.asset_url && onQuickView?.({
                      type: "image",
                      asset_url: comp.asset_url,
                      title: comp.headline || `Creative ${i + 1}`,
                      sub: comp.ad_size || "Creative",
                    })}
                    style={{
                      borderRadius: radius.md, overflow: "hidden",
                      border: `1px solid ${C.border}`, background: C.elevated,
                      position: "relative",
                      cursor: comp.asset_url ? "pointer" : "default",
                    }}
                  >
                    <Box style={{ height: 140, background: C.card, position: "relative", overflow: "hidden" }}>
                      <AssetImage s3Url={comp.asset_url} style={{
                        position: "absolute", inset: 0, width: "100%", height: "100%",
                        objectFit: "cover",
                      }} />
                    </Box>
                    <Box style={{
                      padding: "8px 12px", borderTop: `1px solid ${C.border}`,
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                    }}>
                      <T s={9} c={C.dim}>{comp.ad_size || "1080x1350"}</T>
                      <T s={10} c={C.muted}>Quick View</T>
                    </Box>
                  </Box>
                ))}
              </Box>
            </>
          )}

          {/* Raw images + Audio + Video (conditionally shown based on enabled tracks) */}
          {(hasImages || hasAudio || hasVideo) && (
            <Box style={{
              display: "grid",
              gridTemplateColumns: (() => {
                const cols = [];
                if (hasImages) cols.push("3fr");
                if (hasAudio) cols.push("2fr");
                if (hasVideo) cols.push("2fr");
                return cols.join(" ") || "1fr";
              })(),
              gap: 20, marginBottom: 24,
            }}>
              {hasImages && (
                <Box>
                  <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>Hero Images</T>
                  <Box style={{ display: "flex", gap: 10 }}>
                    {(images || []).map((img, i) => (
                      <Box
                        key={img.id || i}
                        onClick={() => img.asset_url && onQuickView?.({
                          type: "image",
                          asset_url: img.asset_url,
                          title: titleCase(img.scene_type) || `Image ${i + 1}`,
                          sub: "Raw generated image",
                        })}
                        style={{
                          flex: 1, height: 120, borderRadius: radius.md,
                          background: fallbackGradients[i % 3],
                          border: `1px solid ${C.border}`,
                          position: "relative", overflow: "hidden",
                          cursor: "pointer", transition: "border-color 0.15s ease, transform 0.15s ease",
                        }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderLight; e.currentTarget.style.transform = "translateY(-2px)"; }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.transform = "none"; }}
                      >
                        <AssetImage s3Url={img.asset_url} style={{
                          position: "absolute", inset: 0, width: "100%", height: "100%",
                          objectFit: "cover", borderRadius: radius.md,
                        }} />
                        <Box style={{
                          position: "absolute", bottom: 0, left: 0, right: 0,
                          padding: "20px 10px 8px",
                          background: "linear-gradient(transparent, rgba(0,0,0,0.85))",
                          display: "flex", justifyContent: "space-between", alignItems: "flex-end",
                        }}>
                          <T s={10} c={C.white} w={600}>{titleCase(img.scene_type) || `Image ${i + 1}`}</T>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
              {hasAudio && (
                <Box>
                  <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>Audio Ads</T>
                  <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {(audioAds || []).filter(a => a.is_generated && a.asset_url).map((a, i) => (
                      <Box
                        key={a.id || i}
                        onClick={() => onQuickView?.({
                          type: "audio",
                          asset_url: a.asset_url,
                          title: titleCase(a.tone) || `Audio ${i + 1}`,
                          sub: "Generated audio clip",
                        })}
                        style={{
                          padding: "10px 14px", borderRadius: radius.md,
                          background: C.elevated, border: `1px solid ${C.border}`,
                          display: "flex", justifyContent: "space-between", alignItems: "center",
                          cursor: "pointer",
                          transition: "border-color 0.15s ease",
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = C.borderLight}
                        onMouseLeave={e => e.currentTarget.style.borderColor = C.border}
                      >
                        <Box>
                          <T s={11} w={600}>{titleCase(a.tone)}</T>
                          <T s={9} c={C.dim}>{a.duration_sec ? `${a.duration_sec.toFixed(1)}s` : ""}</T>
                        </Box>
                        <Badge bg={C.teal}>Play</Badge>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
              {hasVideo && (
                <Box>
                  <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>Video</T>
                  <Box style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {videoList.filter(v => v.final_url || v.video_url).map((v, i) => {
                      const url = v.final_url || v.video_url;
                      const label = v.final_url ? "Final" : "Raw clip";
                      return (
                        <Box
                          key={v.id || i}
                          onClick={() => url && onQuickView?.({
                            type: "video",
                            asset_url: url,
                            title: `Scene ${i + 1}`,
                            sub: label,
                          })}
                          style={{
                            padding: "10px 14px", borderRadius: radius.md,
                            background: C.elevated, border: `1px solid ${C.border}`,
                            display: "flex", justifyContent: "space-between", alignItems: "center",
                            cursor: url ? "pointer" : "default",
                            transition: "border-color 0.15s ease",
                          }}
                          onMouseEnter={e => { if (url) e.currentTarget.style.borderColor = C.borderLight; }}
                          onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; }}
                        >
                          <Box>
                            <T s={11} w={600}>Clip {i + 1}</T>
                            <T s={9} c={C.dim}>{v.duration_sec != null ? `${Number(v.duration_sec).toFixed(1)}s` : label}</T>
                          </Box>
                          <Badge bg={v.final_url ? C.green : C.teal}>{label}</Badge>
                        </Box>
                      );
                    })}
                  </Box>
                </Box>
              )}
            </Box>
          )}

          {/* Documents */}
          <T s={12} c={C.text} w={700} style={{ textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12 }}>Documents</T>
          <Box style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            {[
              { name: "Strategy Brief", desc: "Direction + audiences", type: "JSON", data: campaign?.strategy },
              { name: "Copy Variants", desc: "AIDA / PAS / BAB", type: "JSON", data: campaign?.copy_variants },
              { name: "Audio Scripts", desc: "All tones", type: "JSON", data: (audioAds || []).filter(a => a.script) },
            ].map((doc, i) => {
              const hasData = doc.data && doc.data.length > 0;
              const downloadDoc = () => {
                if (!hasData) return;
                const blob = new Blob([JSON.stringify(doc.data, null, 2)], { type: "application/json" });
                const blobUrl = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = blobUrl;
                a.download = `${doc.name.replace(/\s+/g, "_").toLowerCase()}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
              };
              return (
                <Box key={i} style={{
                  padding: "12px 14px", borderRadius: radius.md,
                  background: C.elevated, border: `1px solid ${C.border}`,
                  display: "flex", alignItems: "center", gap: 10,
                }}>
                  <Box style={{
                    width: 28, height: 28, borderRadius: radius.sm,
                    background: C.hover, border: `1px solid ${C.border}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0,
                  }}>
                    <T s={8} c={C.muted} w={700}>{doc.type}</T>
                  </Box>
                  <Box style={{ flex: 1, minWidth: 0 }}>
                    <T s={11} w={600}>{doc.name}</T>
                    <T s={9} c={C.dim}>{doc.desc}</T>
                  </Box>
                  <Box
                    onClick={downloadDoc}
                    style={{
                      padding: "5px 12px", borderRadius: radius.sm,
                      background: C.hover, border: `1px solid ${C.border}`,
                      cursor: hasData ? "pointer" : "not-allowed",
                      opacity: hasData ? 1 : 0.4,
                      transition: "all 0.15s ease",
                      flexShrink: 0,
                      display: "flex", alignItems: "center", gap: 5,
                    }}
                    onMouseEnter={e => { if (hasData) { e.currentTarget.style.borderColor = C.teal; e.currentTarget.style.background = `${C.teal}10`; } }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.hover; }}
                  >
                    <T s={11} c={hasData ? C.teal : C.dim} w={600}>{"\u2193"}</T>
                    <T s={9} c={hasData ? C.teal : C.dim} w={600}>Download</T>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
