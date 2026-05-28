// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { useState } from "react";
import { C } from "./tokens";
import { Box } from "./components/primitives";
import Nav from "./components/Nav";
import CampaignScreen from "./screens/CampaignScreen";
import GenerateScreen from "./screens/GenerateScreen";
import GpuSidebar from "./components/GpuSidebar";

export default function App() {
  const [screen, setScreen] = useState("campaign");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [generateUnlocked, setGenerateUnlocked] = useState(false);

  const handleApproveGenerate = () => {
    setGenerateUnlocked(true);
    setScreen("generate");
  };

  const handleNewCampaign = () => {
    setGenerateUnlocked(false);
    setScreen("campaign");
  };

  const handleStrategyStart = () => {
    setGenerateUnlocked(false);
  };

  return (
    <Box style={{
      background: C.bg,
      minHeight: "100vh",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      color: C.white,
      display: "flex",
      flexDirection: "column",
    }}>
      <Nav screen={screen} setScreen={setScreen} sidebarWidth={sidebarOpen ? 230 : 36} generateUnlocked={generateUnlocked} />
      <Box style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <Box style={{ flex: 1, overflowY: "auto", transition: "flex 0.3s ease", animation: "fadeIn 0.3s ease" }}>
          {screen === "campaign" && <CampaignScreen onNext={handleApproveGenerate} generateUnlocked={generateUnlocked} onStrategyStart={handleStrategyStart} />}
          {screen === "generate" && <GenerateScreen onNewCampaign={handleNewCampaign} />}
        </Box>
        <GpuSidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      </Box>
    </Box>
  );
}
