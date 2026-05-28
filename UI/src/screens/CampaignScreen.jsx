// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { useState } from "react";
import { C } from "../tokens";
import { Box } from "../components/primitives";
import BriefScreen from "./BriefScreen";
import StrategyScreen from "./StrategyScreen";
import CampaignStrategyPlaceholder from "../components/campaign/CampaignStrategyPlaceholder";
import "../css/campaign/CampaignScreen.css";
import { useGetCampaignQuery } from "../store/api/campaignApi";
import { useAppSelector } from "../store/hooks";
import { selectCampaignId } from "../store/sessionSlice";

const CampaignScreen = ({ onNext, generateUnlocked, onStrategyStart }) => {
  const campaignId = useAppSelector(selectCampaignId);
  const { data: campaign } = useGetCampaignQuery(campaignId, {
    skip: !campaignId,
    pollingInterval: 3000,
  });
  const phase = campaign?.status || "brief";
  const hasStrategyData = !!(campaign?.strategy?.length || campaign?.strategies?.length);
  const isRunning = phase === "strategy_running" || phase === "pending";
  const [manualReady, setManualReady] = useState(false);
  const strategyReady = manualReady || hasStrategyData || isRunning;

  return (
    <Box className="campaign-screen" style={{ background: C.border }}>
      <Box className="campaign-screen__pane" style={{ flex: strategyReady ? "0 0 33%" : "0 0 50%", padding: strategyReady ? "28px 24px" : "36px 36px", background: C.bg }}>
        <BriefScreen onNext={() => { setManualReady(true); onStrategyStart?.(); }} />
      </Box>

      <Box className="campaign-screen__strategyPane" style={{ flex: strategyReady ? "1 1 67%" : "0 0 50%", background: strategyReady ? C.bg : C.surface }}>
        {strategyReady ? (
          <Box className="campaign-screen__strategyInner" style={{ padding: "28px 32px" }}>
            <StrategyScreen onNext={onNext} generateUnlocked={generateUnlocked} />
          </Box>
        ) : (
          <CampaignStrategyPlaceholder />
        )}
      </Box>
    </Box>
  );
};

export default CampaignScreen;
