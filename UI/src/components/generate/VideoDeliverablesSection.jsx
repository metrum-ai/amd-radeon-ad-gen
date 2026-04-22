// Created by Metrum AI for AMD

import { C, gradient } from "../../tokens";
import { Box, T } from "../primitives";
import SectionHeader from "./SectionHeader";
import "../../css/generate/VideoDeliverablesSection.css";

export default function VideoDeliverablesSection({
  show, imageTrackEnabled, videoDeliverableItems, done, isGenerating, videoMuxRunning, onOpen, VideoDeliverableCard,
}) {
  if (!show) return null;
  return (
    <Box className="video-deliverables-section">
      <SectionHeader
        step={imageTrackEnabled ? undefined : "2"}
        title="Video Deliverables"
        sub="Final MP4 with voiceover and brand overlay"
        right={
          <Box className="video-deliverables-section__progress">
            <Box className="video-deliverables-section__progressBar" style={{ background: C.border, borderRadius: 2 }}>
              <Box style={{
                height: "100%",
                width: `${videoDeliverableItems.length ? (videoDeliverableItems.filter((x) => x.done).length / videoDeliverableItems.length) * 100 : 0}%`,
                background: done ? C.green : gradient.amdH, borderRadius: 2, transition: "width 0.5s ease",
              }} />
            </Box>
            <T s={13} c={done ? C.green : C.accent} w={700}>{videoDeliverableItems.filter((x) => x.done).length}/{videoDeliverableItems.length}</T>
          </Box>
        }
      />
      <Box className="video-deliverables-section__grid">
        {videoDeliverableItems.map((vd, i) => (
          <VideoDeliverableCard key={`vd-${i}`} item={vd} isGenerating={isGenerating} muxRunning={videoMuxRunning} onOpen={onOpen} />
        ))}
      </Box>
    </Box>
  );
}
