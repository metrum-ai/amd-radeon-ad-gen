// Created by Metrum AI for AMD

import { C, gradient, shadow, radius } from "../../tokens";
import { Box, T, Label, Card } from "../primitives";
import { brandPresets, fieldStyle, fontOptions } from "../../lib/brief";
import "../../css/brief/BriefBrandSection.css";

export default function BriefBrandSection({
  brand, brandOpen, setBrandOpen, selectedPreset, applyPreset, startCustom,
  updateBrand, addColor, removeColor, updateColorHex, updateColorLabel,
  addFont, removeFont, updateFont, uploadBrandLogo,
}) {
  const openLogoPicker = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => uploadBrandLogo(e.target.files?.[0]);
    input.click();
  };

  return (
    <Box className="brief-brand">
      <Label accent={C.blue}>Brand</Label>
      <Box className="brief-brand__presets">
        {brandPresets.map((p, idx) => {
          const active = selectedPreset === idx;
          return (
            <Box key={idx} onClick={() => applyPreset(idx)} className="brief-brand__preset" style={{ padding: "12px 16px", borderRadius: radius.md, background: active ? C.surface : C.elevated, boxShadow: active ? shadow.lg : "none", border: active ? `2px solid ${C.accent}` : "2px solid transparent" }}>
              <Box style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <Box style={{ width: 28, height: 28, borderRadius: 8, background: C.hover, border: `1px solid ${C.border}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <T s={9} w={800} c={C.white}>{p.name.slice(0, 2).toUpperCase()}</T>
                </Box>
                <T s={13} w={active ? 700 : 500} c={active ? C.white : C.text}>{p.name}</T>
              </Box>
              <Box style={{ display: "flex", gap: 4, marginBottom: 6 }}>
                {p.colors.map((c, ci) => <Box key={ci} style={{ width: 16, height: 16, borderRadius: 4, background: c.hex, border: `1px solid ${C.borderLight}` }} />)}
              </Box>
              <T s={10} c={C.dim}>{p.fonts[0]}</T>
            </Box>
          );
        })}
        <Box onClick={startCustom} className="brief-brand__custom" style={{ padding: "12px 16px", borderRadius: radius.md, background: selectedPreset === -1 ? C.surface : C.elevated, boxShadow: selectedPreset === -1 ? shadow.lg : "none", border: selectedPreset === -1 ? `2px solid ${C.accent}` : `2px dashed ${C.border}` }}>
          <T s={18} c={selectedPreset === -1 ? C.accent : C.dim} style={{ marginBottom: 4, opacity: selectedPreset === -1 ? 1 : 0.5 }}>+</T>
          <T s={11} w={600} c={selectedPreset === -1 ? C.accent : C.dim}>Custom</T>
        </Box>
      </Box>

      <Card style={{ padding: 0, overflow: "hidden", boxShadow: brandOpen ? shadow.lg : shadow.md }}>
        <Box onClick={() => setBrandOpen(!brandOpen)} className="brief-brand__summaryHeader" style={{ padding: "16px 22px" }}>
          <Box className="brief-brand__summaryMain">
            <Box style={{ width: 38, height: 38, borderRadius: radius.md, background: brand.logo ? "transparent" : `linear-gradient(135deg, ${brand.colors[0]?.hex || C.accent}20, ${brand.colors[0]?.hex || C.accent}08)`, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
              {brand.logo ? <img src={brand.logo} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : <T s={11} w={800} c={brand.colors[0]?.hex || C.accent}>{(brand.name || "?").slice(0, 2).toUpperCase()}</T>}
            </Box>
            <Box>
              <T s={14} w={600}>{brand.name || "Untitled Brand"}</T>
              <T s={11} c={C.dim}>{brand.colors.length} colors / {brand.fonts.length} fonts -- click to {brandOpen ? "collapse" : "edit"}</T>
            </Box>
          </Box>
          <Box className="brief-brand__swatches">
            <Box className="brief-brand__swatchRow">
              {brand.colors.map((c, i) => <Box key={i} style={{ width: 20, height: 20, borderRadius: 5, background: c.hex, border: `1px solid ${C.borderLight}` }} />)}
            </Box>
            <T s={14} c={C.dim} style={{ transition: "transform 0.2s ease", transform: brandOpen ? "rotate(180deg)" : "rotate(0deg)" }}>{"▾"}</T>
          </Box>
        </Box>

        {brandOpen && (
          <Box className="brief-brand__editor" style={{ padding: "0 22px 22px", borderTop: `1px solid ${C.borderLight}` }}>
            <Box style={{ paddingTop: 20 }}>
              <Box className="brief-brand__fieldBlock">
                <T s={12} c={C.text} w={600} style={{ marginBottom: 8 }}>Brand Name</T>
                <input type="text" value={brand.name} onChange={(e) => updateBrand("name", e.target.value)} placeholder="Enter brand name..." style={fieldStyle} />
              </Box>

              <Box className="brief-brand__fieldBlock">
                <T s={12} c={C.text} w={600} style={{ marginBottom: 8 }}>Logo</T>
                {brand.logo ? (
                  <Box style={{ display: "flex", alignItems: "center", gap: 14, background: C.elevated, borderRadius: radius.sm, padding: 12 }}>
                    <img src={brand.logo} alt="Logo" style={{ width: 48, height: 48, objectFit: "contain", borderRadius: 8, background: C.surface, padding: 4 }} />
                    <Box style={{ flex: 1 }}>
                      <T s={12} c={C.text} w={500}>Logo uploaded</T>
                      <T s={10} c={C.dim}>Click remove to change</T>
                    </Box>
                    <Box onClick={() => updateBrand("logo", null)} style={{ cursor: "pointer", padding: "5px 12px", borderRadius: 6, background: C.redSoft }}>
                      <T s={11} c={C.red} w={600}>Remove</T>
                    </Box>
                  </Box>
                ) : (
                  <Box onClick={openLogoPicker} style={{ border: `2px dashed ${C.border}`, borderRadius: radius.sm, padding: "24px 16px", textAlign: "center", cursor: "pointer", background: C.elevated, transition: "border-color 0.2s ease, background 0.2s ease" }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = C.accent; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = C.border; }}>
                    <T s={20} c={C.dim} style={{ marginBottom: 6, opacity: 0.4 }}>+</T>
                    <T s={12} c={C.dim}>Click to upload logo</T>
                  </Box>
                )}
              </Box>

              <Box className="brief-brand__fieldBlock">
                <Box className="brief-brand__rowBetween">
                  <T s={12} c={C.text} w={600}>Brand Colors</T>
                  <Box onClick={addColor} style={{ cursor: "pointer", padding: "4px 12px", borderRadius: 6, background: C.blueSoft }}><T s={11} c={C.blue} w={600}>+ Add</T></Box>
                </Box>
                <Box className="brief-brand__stack">
                  {brand.colors.map((color, idx) => (
                    <Box key={idx} className="brief-brand__colorItem" style={{ padding: "8px 10px", borderRadius: radius.sm, background: C.elevated }}>
                      <Box style={{ position: "relative", flexShrink: 0 }}>
                        <Box style={{ width: 36, height: 36, borderRadius: 8, background: color.hex, cursor: "pointer", boxShadow: `0 2px 8px ${color.hex}30` }} />
                        <input type="color" value={color.hex} onChange={(e) => updateColorHex(idx, e.target.value)} style={{ position: "absolute", top: 0, left: 0, width: 36, height: 36, opacity: 0, cursor: "pointer" }} />
                      </Box>
                      <Box className="brief-brand__colorInputs">
                        <input type="text" value={color.label} onChange={(e) => updateColorLabel(idx, e.target.value)} style={{ ...fieldStyle, padding: "2px 6px", fontSize: 11, fontWeight: 700, background: "transparent", border: "none", color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em" }} />
                        <input type="text" value={color.hex} onChange={(e) => updateColorHex(idx, e.target.value)} style={{ ...fieldStyle, padding: "2px 6px", fontFamily: "'Inter', monospace", fontSize: 12, background: "transparent", border: "none" }} />
                      </Box>
                      {brand.colors.length > 1 && <Box onClick={() => removeColor(idx)} style={{ cursor: "pointer", padding: "4px 8px", borderRadius: 6, background: C.redSoft, flexShrink: 0 }}><T s={11} c={C.red}>{"✕"}</T></Box>}
                    </Box>
                  ))}
                </Box>
              </Box>

              <Box>
                <Box className="brief-brand__rowBetween">
                  <T s={12} c={C.text} w={600}>Fonts</T>
                  <Box onClick={addFont} style={{ cursor: "pointer", padding: "4px 12px", borderRadius: 6, background: C.tealSoft }}><T s={11} c={C.teal} w={600}>+ Add</T></Box>
                </Box>
                <Box className="brief-brand__stack">
                  {brand.fonts.map((font, idx) => (
                    <Box key={idx} className="brief-brand__fontItem">
                      <select value={font} onChange={(e) => updateFont(idx, e.target.value)} style={{ ...fieldStyle, flex: 1, appearance: "none", WebkitAppearance: "none", backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center", paddingRight: 36, cursor: "pointer" }}>
                        <option value="" disabled style={{ background: C.surface, color: C.dim }}>Select a font...</option>
                        {fontOptions.map((f) => <option key={f} value={f} style={{ background: C.surface, color: C.white }}>{f}</option>)}
                      </select>
                      {brand.fonts.length > 1 && <Box onClick={() => removeFont(idx)} style={{ cursor: "pointer", padding: "4px 8px", borderRadius: 6, background: C.redSoft, flexShrink: 0 }}><T s={11} c={C.red}>{"✕"}</T></Box>}
                    </Box>
                  ))}
                </Box>
              </Box>

              <Box className="brief-brand__editorFooter" style={{ borderTop: `1px solid ${C.borderLight}` }}>
                <button onClick={(e) => { e.stopPropagation(); setBrandOpen(false); }} disabled={!brand.name.trim()} style={{ width: "100%", padding: "11px 20px", borderRadius: radius.sm, border: "none", background: brand.name.trim() ? gradient.amd : C.elevated, color: brand.name.trim() ? "#fff" : C.dim, fontSize: 13, fontWeight: 600, cursor: brand.name.trim() ? "pointer" : "not-allowed", fontFamily: "'Inter', sans-serif", transition: "opacity 0.2s ease" }}>
                  {selectedPreset === -1 ? "Save Custom Brand" : "Done"}
                </button>
              </Box>
            </Box>
          </Box>
        )}
      </Card>
    </Box>
  );
}
