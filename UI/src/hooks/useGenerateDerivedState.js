// Created by Metrum AI for AMD

import { useMemo } from "react";
import { C } from "../tokens";
import { fallbackGradients, titleCase, compositionPreviewScore } from "../lib/generate";

export default function useGenerateDerivedState({
  campaign,
  pipelineStatus,
  imageTrackEnabled,
  audioTrackEnabled,
  videoTrackEnabled,
  isGenerating,
}) {
  const images = campaign?.generated_images || campaign?.images || [];
  const compositions = campaign?.compositions || [];
  const audioAds = campaign?.audio_ads || [];
  const videoAds = campaign?.video_ads || [];
  const copyVariants = campaign?.copy_variants || [];
  const scenePrompts = campaign?.scene_prompts || [];

  const displayCompositions = useMemo(() => {
    if (!compositions.length) return [];
    const groups = new Map();
    for (let i = 0; i < compositions.length; i++) {
      const comp = compositions[i];
      const k = `${comp.image_id || "img"}:${comp.copy_variant_id || comp.framework || i}`;
      const prev = groups.get(k);
      if (!prev || compositionPreviewScore(comp) > compositionPreviewScore(prev)) {
        groups.set(k, comp);
      }
    }
    return Array.from(groups.values());
  }, [compositions]);

  const rawImageItems = useMemo(() => {
    if (!imageTrackEnabled) return [];
    const defaultLabels = ["Primary Hero", "Lifestyle", "Mood / Abstract"];

    if (scenePrompts.length > 0) {
      const imgByScene = new Map();
      for (const img of images) {
        if (img.scene_prompt_id) imgByScene.set(img.scene_prompt_id, img);
      }
      return scenePrompts.map((sp, i) => {
        const img = imgByScene.get(sp.id);
        if (img && img.asset_url) {
          return {
            name: titleCase(sp.scene_type) || defaultLabels[i] || `Image ${i + 1}`,
            desc: sp.image_prompt ? `${sp.image_prompt.slice(0, 60)}...` : "",
            status: "done",
            asset_url: img.asset_url,
            gradient: fallbackGradients[i % 3],
          };
        }
        return {
          name: titleCase(sp.scene_type) || defaultLabels[i] || `Image ${i + 1}`,
          desc: sp.image_prompt ? `${sp.image_prompt.slice(0, 60)}...` : "Generating...",
          status: isGenerating ? "generating" : "queued",
          gradient: fallbackGradients[i % 3],
        };
      });
    }

    if (images.length > 0) {
      return images.map((img, i) => ({
        name: titleCase(img.scene_type) || defaultLabels[i] || `Image ${i + 1}`,
        desc: img.image_prompt ? `${img.image_prompt.slice(0, 60)}...` : "",
        status: img.asset_url ? "done" : "generating",
        asset_url: img.asset_url,
        gradient: fallbackGradients[i % 3],
      }));
    }

    return defaultLabels.map((name, i) => ({
      name,
      desc: "Generating...",
      status: isGenerating ? "generating" : "queued",
      gradient: fallbackGradients[i],
    }));
  }, [images, scenePrompts, imageTrackEnabled, isGenerating]);

  const rawAudioItems = useMemo(() => {
    if (!audioTrackEnabled) return [];
    if (audioAds.length === 0) {
      return [{ name: "Audio Ad", desc: "Waiting...", status: isGenerating ? "generating" : "queued" }];
    }
    return audioAds.map((ad, i) => ({
      name: titleCase(ad.tone) || `Audio ${i + 1}`,
      desc: ad.duration_sec ? `${ad.duration_sec.toFixed(1)}s` : "Generating...",
      status: ad.is_generated && ad.asset_url ? "done" : "generating",
      asset_url: ad.asset_url || null,
    }));
  }, [audioAds, audioTrackEnabled, isGenerating]);

  const stageInFlight = (st) =>
    pipelineStatus.some((r) => r.stage === st && (r.status === "running" || r.status === "retrying"));
  const videoGenRunning = stageInFlight("video_gen");
  const videoMuxRunning = stageInFlight("video_mux");

  const rawVideoItems = useMemo(() => {
    if (!videoTrackEnabled) return [];
    const scriptSlice = (s) => {
      if (!s) return "";
      const t = String(s);
      return t.length > 72 ? `${t.slice(0, 72)}...` : t;
    };

    const sourceAd = videoAds.find((v) => Boolean(v.video_url));
    if (sourceAd) {
      const hasFinal = Boolean(sourceAd.final_url);
      return [{
        name: "Video Clip",
        desc: scriptSlice(sourceAd.script || ""),
        status: "done",
        preview_url: sourceAd.video_url,
        asset_url: sourceAd.video_url,
        sub: hasFinal ? "LTX output (final ready)" : "LTX raw output",
        final_ready: hasFinal,
      }];
    }

    return [{
      name: "Video Clip",
      desc: "Waiting for pipeline...",
      status: isGenerating && videoGenRunning ? "generating" : "queued",
      final_ready: false,
    }];
  }, [videoTrackEnabled, videoAds, isGenerating, videoGenRunning]);

  const videoDeliverableItems = useMemo(() => {
    if (!videoTrackEnabled) return [];
    const copyLabelFor = (i) => {
      const cv = copyVariants[i];
      if (!cv) return `Copy ${i + 1}`;
      const fw = cv.framework || `Copy ${i + 1}`;
      const hl = (cv.headline || "").trim();
      return hl ? `${fw}: ${hl}` : fw;
    };
    const row = (v, title, i) => ({
      title,
      final_url: v?.final_url || null,
      done: Boolean(v?.final_url),
      hasRaw: Boolean(v?.video_url),
      copy_label: copyLabelFor(i),
    });

    const hasAnyFinal = videoAds.some((v) => v.final_url);
    if (hasAnyFinal || videoAds.length > 1) {
      return videoAds
        .filter((v) => v.final_url || v.is_generated !== false)
        .map((v, i) => row(v, `Clip ${i + 1}`, i));
    }

    const cvCount = Math.max(copyVariants.length, 3);
    return Array.from({ length: cvCount }, (_, i) => ({
      title: `Clip ${i + 1}`,
      final_url: null,
      done: false,
      hasRaw: videoAds.length > 0 && Boolean(videoAds[0]?.video_url),
      copy_label: copyLabelFor(i),
    }));
  }, [videoTrackEnabled, videoAds, copyVariants]);

  const creativeItems = useMemo(() => {
    const compLookup = new Map();
    for (const comp of displayCompositions) {
      const k = `${comp.image_id || ""}:${comp.copy_variant_id || ""}`;
      compLookup.set(k, comp);
    }

    const imgs = images.length > 0 ? images : [null, null, null];
    const cvs = copyVariants.length > 0 ? copyVariants : [
      { framework: "AIDA", headline: "", cta: "" },
      { framework: "PAS", headline: "", cta: "" },
      { framework: "BAB", headline: "", cta: "" },
    ];
    const sceneLabels = ["Hero", "Lifestyle", "Mood"];
    const items = [];

    for (let ii = 0; ii < imgs.length; ii++) {
      for (const cv of cvs) {
        const imgId = imgs[ii]?.id || "";
        const cvId = cv.id || "";
        const match = compLookup.get(`${imgId}:${cvId}`);

        if (match) {
          items.push({
            copy: match.headline || cv.headline || "",
            cta: match.cta || cv.cta || "",
            fw: match.framework || cv.framework || "AIDA",
            dim: match.ad_size || "1080x1350",
            done: Boolean(match.asset_url),
            asset_url: match.asset_url || null,
            img: titleCase(match.scene_type) || titleCase(imgs[ii]?.scene_type) || sceneLabels[ii] || `Type ${ii + 1}`,
          });
        } else {
          items.push({
            copy: cv.headline || "",
            cta: cv.cta || "",
            fw: cv.framework || "AIDA",
            dim: "1080x1350",
            done: false,
            active: isGenerating,
            img: titleCase(imgs[ii]?.scene_type) || sceneLabels[ii] || `Type ${ii + 1}`,
          });
        }
      }
    }
    return items;
  }, [displayCompositions, images, copyVariants, isGenerating]);

  const creativeGroups = useMemo(() => {
    const map = new Map();
    for (const item of creativeItems) {
      const key = item.img || "Other";
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(item);
    }
    return Array.from(map.entries());
  }, [creativeItems]);

  const pipelineBadges = useMemo(() => {
    const stageMap = {};
    for (const run of pipelineStatus) {
      stageMap[run.stage] = run;
    }
    const badges = [{ n: "Qwen 3", role: "Strategy", stage: "strategy" }];
    if (imageTrackEnabled) {
      badges.push({ n: "FLUX.1-schnell", role: "Images", stage: "image_gen" });
      badges.push({ n: "Compositor", role: "Overlay", stage: "composition" });
    }
    if (audioTrackEnabled) {
      badges.push({ n: "Kokoro TTS", role: "Audio", stage: "audio_gen" });
    }
    if (videoTrackEnabled) {
      badges.push({ n: "AnimateDiff", role: "Clips", stage: "video_gen" });
      badges.push({ n: "FFmpeg mux", role: "Video + brand", stage: "video_mux" });
    }
    return badges.map((p) => {
      const run = stageMap[p.stage];
      const status = run?.status || "pending";
      const inProgress = status === "running" || status === "retrying";
      return {
        ...p,
        s: status === "completed" ? "✓" : inProgress ? "..." : status === "failed" ? "✗" : "-",
        c: status === "completed" ? C.green : inProgress ? C.yellow : status === "failed" ? C.red : C.dim,
      };
    });
  }, [audioTrackEnabled, imageTrackEnabled, videoTrackEnabled, pipelineStatus]);

  const doneCount = creativeItems.filter((c) => c.done).length;
  const videoSlotCount = videoTrackEnabled ? Math.max(1, scenePrompts.length || videoAds.length || 1) : 0;
  const totalAssets = images.length + compositions.length + audioAds.filter((a) => a.is_generated).length + videoAds.filter((v) => v.final_url).length;
  const totalExpected = (imageTrackEnabled ? 12 : 0) + (audioTrackEnabled ? 2 : 0) + videoSlotCount;
  const prog = Math.min(totalAssets, totalExpected);

  return {
    images, compositions, audioAds, videoAds, copyVariants, scenePrompts,
    displayCompositions, rawImageItems, rawAudioItems, rawVideoItems,
    videoDeliverableItems, creativeItems, creativeGroups, pipelineBadges,
    doneCount, totalAssets, totalExpected, prog, videoMuxRunning,
  };
}
