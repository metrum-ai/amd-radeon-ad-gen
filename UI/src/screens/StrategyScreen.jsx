// Created by Metrum AI for AMD

import { useState, useEffect, useRef } from "react";
import { C, radius } from "../tokens";
import { Box, T, Btn } from "../components/primitives";
import useStrategyDerivedState from "../hooks/useStrategyDerivedState";
import StrategyHeader from "../components/strategy/StrategyHeader";
import StrategySummaryStats from "../components/strategy/StrategySummaryStats";
import StrategyTabs from "../components/strategy/StrategyTabs";
import StrategyTabContent from "../components/strategy/StrategyTabContent";
import "../css/strategy/StrategyScreen.css";
import { useGetCampaignQuery, useUpdateCampaignMutation } from "../store/api/campaignApi";
import { useGetPipelineStatusQuery, useTriggerPhase2Mutation } from "../store/api/pipelineApi";
import { useGetCapabilitiesQuery } from "../store/api/systemApi";
import { useAppSelector } from "../store/hooks";
import { selectCampaignId } from "../store/sessionSlice";
import { getRtkErrorMessage, normalizePipelineStatus } from "../lib/rtk";

const StrategyScreen = ({ onNext, generateUnlocked }) => {
  const campaignId = useAppSelector(selectCampaignId);
  const [tab, setTab] = useState("direction");
  const [tracks, setTracks] = useState({ img: true, audio: true, video: true });
  const [approving, setApproving] = useState(false);
  const [requestError, setRequestError] = useState(null);
  const wasLoadingRef = useRef(false);

  const {
    data: campaign,
    error: campaignQueryError,
  } = useGetCampaignQuery(campaignId, {
    skip: !campaignId,
    pollingInterval: 3000,
  });
  const {
    data: pipelineStatusData,
  } = useGetPipelineStatusQuery(campaignId, {
    skip: !campaignId,
    pollingInterval: 3000,
  });
  const { data: hwCaps } = useGetCapabilitiesQuery(undefined, {
    pollingInterval: 15000,
  });
  const [updateCampaign] = useUpdateCampaignMutation();
  const [triggerPhase2] = useTriggerPhase2Mutation();

  const pipelineStatus = normalizePipelineStatus(pipelineStatusData);
  const phase = campaign?.status || "brief";
  const campaignError = requestError || (campaignQueryError ? getRtkErrorMessage(campaignQueryError) : null);
  const isLoading = phase === "strategy_running" || phase === "pending";
  const isFailed = phase === "failed";

  const {
    strategy,
    audiences,
    copyVariants,
    scenes,
    audioAds,
    messagingAngles,
    elapsed,
    stageStatus,
    strategyReady,
    copyReady,
    scenesReady,
    audioReady,
    runningTab,
  } = useStrategyDerivedState({ campaign, pipelineStatus });

  useEffect(() => {
    if (wasLoadingRef.current && !isLoading) {
      setTab("direction");
    }
    wasLoadingRef.current = isLoading;
  }, [isLoading]);

  const capsRef = useRef(null);

  const strategyMarketRecActive =
    strategy?.market_data_used !== false;

  useEffect(() => {
    const t = campaign?.tracks;
    if (!t) return;
    const hasRec =
      strategyMarketRecActive &&
      strategyReady &&
      strategy?.track_recommendations &&
      Object.keys(strategy.track_recommendations).length > 0;
    if (hasRec) return;
    setTracks((prev) => ({
      ...prev,
      audio: t.audio_podcast !== false,
      img: capsRef.current ? capsRef.current.image !== false : t.image_text !== false,
      video: capsRef.current ? capsRef.current.video !== false : t.video !== false,
    }));
  }, [campaign?.tracks, strategyReady, strategy?.track_recommendations, strategyMarketRecActive]);

  useEffect(() => {
    const a = hwCaps?.allowed_tracks;
    if (!a) return;
    capsRef.current = a;
    const hasRec =
      strategyMarketRecActive &&
      strategyReady &&
      strategy?.track_recommendations &&
      Object.keys(strategy.track_recommendations).length > 0;
    if (hasRec) return;
    setTracks((prev) => ({
      ...prev,
      img: a.image !== false,
      video: a.video !== false,
    }));
  }, [hwCaps, strategyReady, strategy?.track_recommendations, strategyMarketRecActive]);

  useEffect(() => {
    if (!strategyMarketRecActive) return;
    if (!strategyReady || !strategy?.track_recommendations) return;
    const tr = strategy.track_recommendations;
    if (!tr || typeof tr !== "object" || !Object.keys(tr).length) return;
    const a = hwCaps?.allowed_tracks || {};
    setTracks({
      img: a.image === false ? false : tr.image_text?.recommended !== false,
      audio: tr.audio_podcast?.recommended === true,
      video: a.video === false ? false : tr.video?.recommended === true,
    });
  }, [strategyReady, strategy?.id, strategy?.track_recommendations, hwCaps?.allowed_tracks, strategyMarketRecActive]);

  const hwAllowed = hwCaps?.allowed_tracks || { llm: true, image: false, video: false };

  const handleApprove = async () => {
    setApproving(true);
    setRequestError(null);
    try {
      await updateCampaign({
        id: campaign?.id || campaignId,
        data: {
          tracks: {
            image_text: tracks.img && hwAllowed.image !== false,
            audio_podcast: tracks.audio,
            video: tracks.video && hwAllowed.video !== false,
          },
        },
      }).unwrap();
      await triggerPhase2(campaign?.id || campaignId).unwrap();
      onNext();
    } catch (error) {
      setRequestError(getRtkErrorMessage(error));
    } finally {
      setApproving(false);
    }
  };

  return (
    <Box className="strategy-screen">
      <StrategyHeader campaign={campaign} isLoading={isLoading} isFailed={isFailed} elapsed={elapsed} />

      {campaignError && (
        <Box style={{
          padding: "12px 16px", borderRadius: radius.sm,
          background: `${C.red}15`, border: `1px solid ${C.red}40`,
          marginBottom: 16,
        }}>
          <T s={12} c={C.red} w={500}>{campaignError}</T>
        </Box>
      )}

      <StrategySummaryStats
        strategyReady={strategyReady}
        copyReady={copyReady}
        scenesReady={scenesReady}
        audioReady={audioReady}
        audiences={audiences}
        copyVariants={copyVariants}
        scenes={scenes}
        audioAds={audioAds}
      />

      <StrategyTabs
        tab={tab}
        setTab={setTab}
        stageStatus={stageStatus}
        isLoading={isLoading}
        runningTab={runningTab}
      />

      <StrategyTabContent
        tab={tab}
        strategyReady={strategyReady}
        copyReady={copyReady}
        scenesReady={scenesReady}
        audioReady={audioReady}
        strategy={strategy}
        messagingAngles={messagingAngles}
        audiences={audiences}
        copyVariants={copyVariants}
        scenes={scenes}
        audioAds={audioAds}
        tracks={tracks}
        setTracks={setTracks}
        hwAllowed={hwAllowed}
        hwCaps={hwCaps}
      />

      <Box className="strategy-screen__footer" style={{ borderTop: `1px solid ${C.borderLight}` }}>
        {generateUnlocked ? (
          <Box style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
            padding: "4px 0",
          }}>
            <T s={13} c={C.dim} w={500}>
              Generation already in progress. Switch to the Output tab or create a new campaign.
            </T>
          </Box>
        ) : (
          <>
            <Box />
            <Btn primary onClick={handleApprove} disabled={isLoading || approving}>
              {approving ? "Starting..." : "Approve & Generate"} {"→"}
            </Btn>
          </>
        )}
      </Box>
    </Box>
  );
};

export default StrategyScreen;
