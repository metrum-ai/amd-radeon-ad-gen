// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { C, radius } from "../../tokens";
import { Box, T, Badge, Btn } from "../primitives";
import SectionHeader from "./SectionHeader";
import "../../css/generate/CampaignPackageSection.css";

export default function CampaignPackageSection({
  done, totalAssets, campaign, isGenerating, generationQueued, handleExport, exporting, onNewCampaign, onOpenPreview, CampaignThumbnail,
}) {
  return (
    <Box>
      <SectionHeader
        step="3"
        title="Campaign Package"
        sub={done ? "Click to preview and download" : "Available once generation completes"}
        right={done ? <Badge bg={C.green}>Ready</Badge> : null}
      />

      <CampaignThumbnail
        done={done}
        isGenerating={isGenerating}
        generationQueued={generationQueued}
        campaignName={campaign?.name || "Campaign"}
        assetCount={totalAssets}
        onOpen={onOpenPreview}
      />

      {done && (
        <Box className="campaign-package-section__footer" style={{ borderTop: `1px solid ${C.border}` }}>
          <T s={11} c={C.dim}>Includes raw directives, final assets, and metadata.</T>
          <Box className="campaign-package-section__actions">
            <Btn sm primary onClick={handleExport} disabled={exporting}>
              {exporting ? "Exporting..." : "Download Package (.zip)"}
            </Btn>
            <Btn sm onClick={onNewCampaign}>+ New Campaign</Btn>
          </Box>
        </Box>
      )}
    </Box>
  );
}
