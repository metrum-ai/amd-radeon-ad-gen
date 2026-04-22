// Created by Metrum AI for AMD

import { C, gradient } from "../../tokens";
import { Box, T } from "../primitives";
import SectionHeader from "./SectionHeader";
import "../../css/generate/CreativeDirectivesSection.css";

export default function CreativeDirectivesSection({
  show, done, creativeItems, doneCount, creativeGroups, isGenerating, onOpen, CreativeCard,
}) {
  if (!show) return null;
  return (
    <Box className="creative-directives-section">
      <SectionHeader
        step="2"
        title="Creative Directives"
        sub="Final ad creatives with brand overlay, copy, and CTA applied"
        right={
          <Box className="creative-directives-section__progress">
            <Box className="creative-directives-section__progressBar" style={{ background: C.border, borderRadius: 2 }}>
              <Box style={{
                height: "100%", width: `${creativeItems.length ? (doneCount / creativeItems.length) * 100 : 0}%`,
                background: done ? C.green : gradient.amdH, borderRadius: 2, transition: "width 0.5s ease",
              }} />
            </Box>
            <T s={13} c={done ? C.green : C.accent} w={700}>{doneCount}/{creativeItems.length}</T>
          </Box>
        }
      />
      {creativeGroups.map(([imgType, group]) => {
        const groupDone = group.every((c) => c.done);
        const groupActive = group.some((c) => c.active);
        return (
          <Box key={imgType} className="creative-directives-section__group">
            <Box className="creative-directives-section__groupHeader">
              <Box style={{
                width: 7, height: 7, borderRadius: 4,
                background: groupDone ? C.green : (groupActive ? C.accent : C.dim),
                animation: groupActive && !groupDone ? "pulse 1.5s ease-in-out infinite" : "none",
                flexShrink: 0,
              }} />
              <T s={10} c={C.text} w={600} className="creative-directives-section__groupLabel">{imgType} variant</T>
              <Box style={{ flex: 1, height: 1, background: C.border }} />
              <T s={10} c={groupDone ? C.green : C.dim} w={600}>{group.filter((c) => c.done).length}/{group.length}</T>
            </Box>
            <Box className="creative-directives-section__grid">
              {group.map((ad, i) => (
                <CreativeCard key={`${imgType}-${i}`} ad={ad} isGenerating={isGenerating} onOpen={onOpen} />
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
