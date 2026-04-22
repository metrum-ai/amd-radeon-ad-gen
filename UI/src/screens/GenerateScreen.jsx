// Created by Metrum AI for AMD

import { useState, useEffect, useCallback, useRef } from "react";
import { C, gradient, radius } from "../tokens";
import { Box, T, Badge } from "../components/primitives";
import useGenerateDerivedState from "../hooks/useGenerateDerivedState";
import RawOutputsSection from "../components/generate/RawOutputsSection";
import CreativeDirectivesSection from "../components/generate/CreativeDirectivesSection";
import VideoDeliverablesSection from "../components/generate/VideoDeliverablesSection";
import CampaignPackageSection from "../components/generate/CampaignPackageSection";
import { RawImageCard, RawAudioCard, RawVideoCard, VideoDeliverableCard, CreativeCard, CampaignThumbnail } from "../components/generate/GenerateCards";
import { QuickViewModal, CampaignPreviewModal } from "../components/generate/GenerateModals";
import { MetricsCarousel } from "../components/generate/GenerateShared";
import "../css/generate/GenerateScreen.css";
import { useGetCampaignQuery } from "../store/api/campaignApi";
import { useGetPipelineStatusQuery } from "../store/api/pipelineApi";
import { useLazyGetExportsQuery, useTriggerExportMutation } from "../store/api/exportApi";
import { useAppSelector } from "../store/hooks";
import { selectCampaignId } from "../store/sessionSlice";
import { normalizePipelineStatus } from "../lib/rtk";

/* ---- hooks ---- */

function useElapsed(startedAt, active) {
  const [elapsed, setElapsed] = useState("0:00");
  useEffect(() => {
    if (!active || !startedAt) return;
    const start = new Date(startedAt).getTime();
    const tick = () => {
      const diff = Math.floor((Date.now() - start) / 1000);
      const m = Math.floor(diff / 60);
      const s = diff % 60;
      setElapsed(`${m}:${s.toString().padStart(2, "0")}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, active]);
  return elapsed;
}

/* ---- small visual components ---- */

/* ==== MAIN GenerateScreen ==== */

const GenerateScreen = ({ onNewCampaign }) => {
  const campaignId = useAppSelector(selectCampaignId);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [quickView, setQuickView] = useState(null);
  const [exporting, setExporting] = useState(false);
  const { data: campaign } = useGetCampaignQuery(campaignId, {
    skip: !campaignId,
    pollingInterval: 3000,
  });
  const { data: pipelineStatusData } = useGetPipelineStatusQuery(campaignId, {
    skip: !campaignId,
    pollingInterval: 3000,
  });
  const [triggerExport] = useTriggerExportMutation();
  const [getExports] = useLazyGetExportsQuery();
  const pipelineStatus = normalizePipelineStatus(pipelineStatusData);
  const phase = campaign?.status || "brief";

  const done = phase === "completed";
  const isGenerating = phase === "generation_running";
  const isFailed = phase === "failed";
  const generationQueued = phase === "generation_pending" || isGenerating || done || isFailed;

  const tracks = campaign?.tracks || { image_text: true, audio_podcast: true, video: false };
  const imageTrackEnabled = tracks.image_text === true;
  const audioTrackEnabled = tracks.audio_podcast === true;
  const videoTrackEnabled = tracks.video === true;

  const {
    images,
    compositions,
    audioAds,
    videoAds,
    displayCompositions,
    rawImageItems,
    rawAudioItems,
    rawVideoItems,
    videoDeliverableItems,
    creativeItems,
    creativeGroups,
    pipelineBadges,
    doneCount,
    totalAssets,
    totalExpected,
    prog,
    videoMuxRunning,
  } = useGenerateDerivedState({
    campaign,
    pipelineStatus,
    imageTrackEnabled,
    audioTrackEnabled,
    videoTrackEnabled,
    isGenerating,
  });

  const showCreativeDirectives =
    imageTrackEnabled && (compositions.length > 0 || pipelineStatus.some((r) => r.stage === "composition"));

  // Elapsed timer (prefer any running stage, then image or video generation)
  const startedRun =
    pipelineStatus.find(r => r.status === "running" || r.status === "retrying")
    || pipelineStatus.find(r => r.stage === "image_gen")
    || pipelineStatus.find(r => r.stage === "video_gen")
    || pipelineStatus[0];
  const elapsed = useElapsed(startedRun?.started_at, isGenerating);

  // Export handling -- poll ref ensures cleanup on unmount
  const exportPollRef = useRef(null);

  useEffect(() => {
    return () => {
      if (exportPollRef.current) clearInterval(exportPollRef.current);
    };
  }, []);

  const handleExport = useCallback(async () => {
    if (!campaign?.id) return;
    setExporting(true);
    try {
      await triggerExport(campaign.id).unwrap();
      let tries = 0;
      exportPollRef.current = setInterval(async () => {
        tries++;
        try {
          const exports = await getExports(campaign.id, true).unwrap();
          if (exports.length > 0) {
            clearInterval(exportPollRef.current);
            exportPollRef.current = null;
            setExporting(false);
            window.open(exports[0].download_url, "_blank");
          }
        } catch { /* ignore */ }
        if (tries > 30) {
          clearInterval(exportPollRef.current);
          exportPollRef.current = null;
          setExporting(false);
        }
      }, 2000);
    } catch {
      setExporting(false);
    }
  }, [campaign?.id, getExports, triggerExport]);

  return (
    <Box className="generate-screen">

      {/* Header + Pipeline (single row) */}
      <Box className="generate-screen__header">
        {/* Title block */}
        <Box className="generate-screen__titleBlock">
          <T s={22} w={700}>
            {done ? "Campaign Ready" : isFailed ? "Generation Failed" : isGenerating ? "Generating Campaign Assets" : generationQueued ? "Generation Queued" : "Generation Not Started"}
          </T>
        </Box>

        {/* Pipeline chips (fills the middle) */}
        <Box className="generate-screen__pipeline" style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: radius.md }}>
          {pipelineBadges.map((p, i) => (
            <Box key={`${p.stage}-${p.n}`} className="generate-screen__pipelineItemWrap">
              <Box className="generate-screen__pipelineItem" style={{ background: C.elevated, border: `1px solid ${C.border}`, borderRadius: radius.sm }}>
                <Box style={{ width: 5, height: 5, borderRadius: 3, background: p.c, flexShrink: 0 }} />
                <Box>
                  <T s={10} w={500} className="generate-screen__pipelineLabel">{p.n}</T>
                  <T s={7} c={C.dim} w={400} className="generate-screen__pipelineRole">{p.role}</T>
                </Box>
                <T s={9} c={p.c} w={700}>{p.s}</T>
              </Box>
              {i < pipelineBadges.length - 1 && (
                <T s={9} c={C.dim} style={{ margin: "0 1px" }}>{"\u203A"}</T>
              )}
            </Box>
          ))}
          <MetricsCarousel metrics={campaign?.metrics} />
          <Box className="generate-screen__pipelineSpacer" />
          <Box className="generate-screen__progressWrap">
            <Box className="generate-screen__progressBar" style={{ background: C.border, borderRadius: 2 }}>
              <Box style={{
                height: "100%", width: `${totalExpected ? (prog / totalExpected) * 100 : 0}%`,
                background: done ? C.green : gradient.amdH,
                borderRadius: 2, transition: "width 0.8s ease",
              }} />
            </Box>
            <T s={12} w={700}>{prog}<span style={{ fontSize: 10, color: C.dim, fontWeight: 400 }}>/{totalExpected}</span></T>
          </Box>
        </Box>

        {/* Status + action */}
        <Box className="generate-screen__status">
          {done ? (
            <>
              <Badge bg={C.green}>All Complete</Badge>
              {campaign?.metrics?.image_gen?.total_generation_ms && (
                <T s={11} c={C.dim} w={500}>{(campaign.metrics.image_gen.total_generation_ms / 1000).toFixed(1)}s</T>
              )}
            </>
          ) : isFailed ? <Badge bg={C.red}>Failed</Badge> : isGenerating ? (
            <>
              <Box style={{
                width: 6, height: 6, borderRadius: 3, background: C.accent,
                animation: "pulse 1.5s ease-in-out infinite",
              }} />
              <T s={12} c={C.accent} w={600}>Generating</T>
              <T s={12} c={C.dim} style={{ fontFamily: "'Inter', monospace", minWidth: 36 }}>{elapsed}</T>
            </>
          ) : generationQueued ? (
            <Badge bg={C.yellow}>Queued</Badge>
          ) : (
            <Badge bg={C.dim}>Idle</Badge>
          )}
        </Box>
      </Box>

      <RawOutputsSection
        rawImageItems={rawImageItems}
        rawAudioItems={rawAudioItems}
        rawVideoItems={rawVideoItems}
        done={done}
        onOpen={setQuickView}
        RawImageCard={RawImageCard}
        RawAudioCard={RawAudioCard}
        RawVideoCard={RawVideoCard}
      />

      <CreativeDirectivesSection
        show={showCreativeDirectives}
        done={done}
        creativeItems={creativeItems}
        doneCount={doneCount}
        creativeGroups={creativeGroups}
        isGenerating={isGenerating}
        onOpen={setQuickView}
        CreativeCard={CreativeCard}
      />

      <VideoDeliverablesSection
        show={videoTrackEnabled && videoDeliverableItems.length > 0}
        imageTrackEnabled={imageTrackEnabled}
        videoDeliverableItems={videoDeliverableItems}
        done={done}
        isGenerating={isGenerating}
        videoMuxRunning={videoMuxRunning}
        onOpen={setQuickView}
        VideoDeliverableCard={VideoDeliverableCard}
      />

      <CampaignPackageSection
        done={done}
        totalAssets={totalAssets}
        campaign={campaign}
        isGenerating={isGenerating}
        generationQueued={generationQueued}
        handleExport={handleExport}
        exporting={exporting}
        onNewCampaign={onNewCampaign}
        onOpenPreview={() => done && setPreviewOpen(true)}
        CampaignThumbnail={CampaignThumbnail}
      />

      {/* Campaign preview modal */}
      {previewOpen && (
        <CampaignPreviewModal
          onClose={() => setPreviewOpen(false)}
          campaign={campaign}
          compositions={displayCompositions}
          images={images}
          audioAds={audioAds}
          videoAds={videoAds}
          onExport={handleExport}
          exporting={exporting}
          onQuickView={(item) => setQuickView(item)}
          imageTrackEnabled={imageTrackEnabled}
          audioTrackEnabled={audioTrackEnabled}
          videoTrackEnabled={videoTrackEnabled}
        />
      )}

      {/* Quick view modal */}
      {quickView && <QuickViewModal item={quickView} onClose={() => setQuickView(null)} />}
    </Box>
  );
};

export default GenerateScreen;
