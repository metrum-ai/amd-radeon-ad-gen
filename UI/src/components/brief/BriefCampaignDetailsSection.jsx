// Created by Metrum AI for AMD

import { C, gradient, shadow, radius } from "../../tokens";
import { Box, T, Label, Card } from "../primitives";
import { defaultTones, fieldStyle, textareaStyle } from "../../lib/brief";
import "../../css/brief/BriefCampaignDetailsSection.css";

export default function BriefCampaignDetailsSection({
  productDescription, setProductDescription, campaignObjective, setCampaignObjective,
  tones, setTones, customToneInput, setCustomToneInput, customTones, toggleTone, addCustomTone,
  refImage, setRefImage, uploadReferenceImage, setValidationError,
}) {
  const openRefPicker = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => uploadReferenceImage(e.target.files?.[0]);
    input.click();
  };

  return (
    <Card className="brief-details" style={{ padding: 22 }}>
      <Label accent={C.teal}>Campaign Details</Label>
      <Box className="brief-details__fieldBlock">
        <T s={12} c={C.text} w={600} style={{ marginBottom: 8 }}>Product Description <span style={{ color: C.red }}>*</span></T>
        <textarea value={productDescription} onChange={(e) => { setProductDescription(e.target.value); setValidationError(null); }} placeholder="AMD Radeon™ AI PRO R9700S -- 64 compute units, 32GB GDDR6, built for AI inference and content creation..." style={textareaStyle} />
      </Box>
      <Box className="brief-details__fieldBlock">
        <T s={12} c={C.text} w={600} style={{ marginBottom: 8 }}>Campaign Objective <span style={{ color: C.red }}>*</span></T>
        <textarea value={campaignObjective} onChange={(e) => { setCampaignObjective(e.target.value); setValidationError(null); }} placeholder="Drive awareness for AMD Radeon™ AI PRO R9700S among AI researchers, data scientists, and creative studios..." style={textareaStyle} />
      </Box>

      <T s={12} c={C.text} w={600} style={{ marginBottom: 10 }}>Style + Tone <span style={{ color: C.dim, fontSize: 11, fontWeight: 400 }}>-- select multiple</span></T>
      <Box className="brief-details__chips">
        {defaultTones.map((t) => {
          const active = tones.includes(t);
          return (
            <Box key={t} onClick={() => toggleTone(t)} className="brief-details__chip" style={{ padding: "7px 16px", borderRadius: 20, background: active ? gradient.amd : C.elevated, border: active ? "none" : `1px solid ${C.border}` }}>
              <T s={12} c={active ? "#fff" : C.text} w={active ? 600 : 400}>{t}</T>
            </Box>
          );
        })}
        {customTones.map((t) => (
          <Box key={t} className="brief-details__customChip" style={{ padding: "7px 10px 7px 16px", borderRadius: 20, background: gradient.amd }}>
            <T s={12} c="#fff" w={600}>{t}</T>
            <Box onClick={() => setTones((prev) => prev.filter((x) => x !== t))} style={{ width: 18, height: 18, borderRadius: 9, background: "rgba(255,255,255,0.25)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <T s={10} c="#fff">{"✕"}</T>
            </Box>
          </Box>
        ))}
      </Box>
      <Box className="brief-details__customToneRow">
        <input type="text" value={customToneInput} onChange={(e) => setCustomToneInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustomTone(); } }} placeholder="Add custom tone..." className="brief-details__customToneInput" style={{ ...fieldStyle, padding: "8px 14px" }} />
        <Box onClick={addCustomTone} className="brief-details__addTone" style={{ padding: "6px 14px", borderRadius: radius.sm, background: gradient.amd }}>
          <T s={12} c="#fff" w={600}>+ Add</T>
        </Box>
      </Box>

      <T s={12} c={C.text} w={600} style={{ marginBottom: 8 }}>Reference Image <span style={{ color: C.dim, fontSize: 11, fontWeight: 400 }}>-- optional</span></T>
      {refImage ? (
        <Box className="brief-details__refPreview" style={{ borderRadius: radius.md, boxShadow: shadow.sm }}>
          <img src={refImage} alt="Reference" style={{ width: "100%", maxHeight: 200, objectFit: "cover", display: "block" }} />
          <Box className="brief-details__refPreviewFooter" style={{ background: C.elevated }}>
            <T s={11} c={C.dim}>Reference image uploaded</T>
            <Box className="brief-details__refActions">
              <Box onClick={openRefPicker} style={{ cursor: "pointer", padding: "4px 12px", borderRadius: 6, background: C.blueSoft }}>
                <T s={11} c={C.blue} w={600}>Replace</T>
              </Box>
              <Box onClick={() => setRefImage(null)} style={{ cursor: "pointer", padding: "4px 12px", borderRadius: 6, background: C.redSoft }}>
                <T s={11} c={C.red} w={600}>Remove</T>
              </Box>
            </Box>
          </Box>
        </Box>
      ) : (
        <Box onClick={openRefPicker} className="brief-details__uploadBox" style={{ border: `2px dashed ${C.border}`, borderRadius: radius.md, padding: "32px 16px", background: C.elevated }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = C.accent; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = C.border; }}>
          <T s={20} c={C.dim} style={{ marginBottom: 6, opacity: 0.4 }}>+</T>
          <T s={12} c={C.dim}>Drop image or click to upload</T>
          <T s={10} c={C.dim} style={{ marginTop: 4, opacity: 0.5 }}>JPG, PNG, WebP</T>
        </Box>
      )}
    </Card>
  );
}
