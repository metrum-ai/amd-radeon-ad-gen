// Created by Metrum AI for AMD

import { C } from "../../tokens";
import { Box, T, Badge } from "../primitives";
import SectionHeader from "./SectionHeader";
import "../../css/generate/RawOutputsSection.css";

export default function RawOutputsSection({
  rawImageItems, rawAudioItems, rawVideoItems, done, onOpen,
  RawImageCard, RawAudioCard, RawVideoCard,
}) {
  return (
    <Box className="raw-outputs-section">
      <SectionHeader
        step="1"
        title="Raw AI Outputs"
        sub="Unprocessed model outputs before brand compositing"
      />
      <Box className="raw-outputs-section__columns">
        {[
          rawImageItems.length > 0 && (
            <Box key="img" className="raw-outputs-section__column" style={{ flex: 3 }}>
              <Box className="raw-outputs-section__labelRow">
                <T s={10} c={C.muted} w={600} className="raw-outputs-section__label">Images</T>
                <Box style={{ flex: 1, height: 1, background: C.border }} />
                <Badge bg={C.dim}>FLUX.1-schnell</Badge>
              </Box>
              <Box className="raw-outputs-section__grid" style={{ gridTemplateColumns: `repeat(${rawImageItems.length}, 1fr)` }}>
                {rawImageItems.map((img, i) => (
                  <RawImageCard key={i} item={done ? { ...img, status: "done" } : img} onOpen={onOpen} />
                ))}
              </Box>
            </Box>
          ),
          rawAudioItems.length > 0 && (
            <Box key="aud" className="raw-outputs-section__column" style={{ flex: 2 }}>
              <Box className="raw-outputs-section__labelRow">
                <T s={10} c={C.muted} w={600} className="raw-outputs-section__label">Audio</T>
                <Box style={{ flex: 1, height: 1, background: C.border }} />
                <Badge bg={C.dim}>Kokoro TTS</Badge>
              </Box>
              <Box className="raw-outputs-section__grid" style={{ gridTemplateColumns: `repeat(${rawAudioItems.length}, 1fr)` }}>
                {rawAudioItems.map((a, i) => (
                  <RawAudioCard key={i} item={done ? { ...a, status: "done" } : a} onOpen={onOpen} />
                ))}
              </Box>
            </Box>
          ),
          rawVideoItems.length > 0 && (
            <Box key="vid" className="raw-outputs-section__column" style={{ flex: 2 }}>
              <Box className="raw-outputs-section__labelRow">
                <T s={10} c={C.muted} w={600} className="raw-outputs-section__label">Video</T>
                <Box style={{ flex: 1, height: 1, background: C.border }} />
                <Badge bg={C.dim}>AnimateDiff</Badge>
              </Box>
              <Box className="raw-outputs-section__grid" style={{ gridTemplateColumns: `repeat(${rawVideoItems.length}, 1fr)` }}>
                {rawVideoItems.map((v, i) => (
                  <RawVideoCard key={i} item={done ? { ...v, status: "done" } : v} onOpen={onOpen} />
                ))}
              </Box>
            </Box>
          ),
        ].filter(Boolean).flatMap((node, idx) => idx === 0 ? [node] : [
          <Box key={`sep-${idx}`} className="raw-outputs-section__separator" style={{ background: C.border }} />,
          node,
        ])}
      </Box>
    </Box>
  );
}
