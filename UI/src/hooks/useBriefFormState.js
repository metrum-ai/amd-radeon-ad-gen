// Created by Metrum AI for AMD

import { useMemo, useState } from "react";
import { brandPresets, colorLabels, defaultTones } from "../lib/brief";

function readFileAsDataUrl(file, onLoad) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => onLoad(ev.target.result);
  reader.readAsDataURL(file);
}

export default function useBriefFormState() {
  const [submitting, setSubmitting] = useState(false);
  const [productDescription, setProductDescription] = useState("");
  const [campaignObjective, setCampaignObjective] = useState("");
  const [validationError, setValidationError] = useState(null);
  const [tones, setTones] = useState(["Bold"]);
  const [customToneInput, setCustomToneInput] = useState("");
  const [brandOpen, setBrandOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [marketDataEnabled, setMarketDataEnabled] = useState(true);
  const [refImage, setRefImage] = useState(null);
  const [brand, setBrand] = useState({
    name: brandPresets[0].name,
    logo: null,
    colors: [...brandPresets[0].colors],
    fonts: [...brandPresets[0].fonts],
    refFiles: [],
  });

  const customTones = useMemo(() => tones.filter((t) => !defaultTones.includes(t)), [tones]);

  const toggleTone = (tone) => {
    setTones((prev) => prev.includes(tone) ? prev.filter((x) => x !== tone) : [...prev, tone]);
  };

  const addCustomTone = () => {
    const val = customToneInput.trim();
    if (val && !tones.includes(val)) {
      setTones((prev) => [...prev, val]);
    }
    setCustomToneInput("");
  };

  const applyPreset = (idx) => {
    const p = brandPresets[idx];
    setSelectedPreset(idx);
    setBrand((prev) => ({
      ...prev,
      name: p.name,
      logo: null,
      colors: p.colors.map((c) => ({ ...c })),
      fonts: [...p.fonts],
    }));
    setBrandOpen(false);
  };

  const startCustom = () => {
    setSelectedPreset(-1);
    setBrand((prev) => ({
      ...prev,
      name: "",
      logo: null,
      colors: [{ hex: "#6366f1", label: "Primary" }],
      fonts: ["Inter"],
    }));
    setBrandOpen(true);
  };

  const updateBrand = (key, val) => setBrand((prev) => ({ ...prev, [key]: val }));

  const updateColorHex = (idx, hex) => {
    const next = [...brand.colors];
    next[idx] = { ...next[idx], hex };
    updateBrand("colors", next);
  };

  const updateColorLabel = (idx, label) => {
    const next = [...brand.colors];
    next[idx] = { ...next[idx], label };
    updateBrand("colors", next);
  };

  const addColor = () => {
    const usedLabels = brand.colors.map((c) => c.label);
    const nextLabel = colorLabels.find((l) => !usedLabels.includes(l)) || `Color ${brand.colors.length + 1}`;
    updateBrand("colors", [...brand.colors, { hex: "#888888", label: nextLabel }]);
  };

  const removeColor = (idx) => updateBrand("colors", brand.colors.filter((_, i) => i !== idx));

  const updateFont = (idx, val) => {
    const next = [...brand.fonts];
    next[idx] = val;
    updateBrand("fonts", next);
  };

  const addFont = () => updateBrand("fonts", [...brand.fonts, ""]);
  const removeFont = (idx) => updateBrand("fonts", brand.fonts.filter((_, i) => i !== idx));

  const uploadBrandLogo = (file) => readFileAsDataUrl(file, (data) => updateBrand("logo", data));
  const uploadReferenceImage = (file) => readFileAsDataUrl(file, setRefImage);

  return {
    submitting, setSubmitting,
    productDescription, setProductDescription,
    campaignObjective, setCampaignObjective,
    validationError, setValidationError,
    tones, setTones, customToneInput, setCustomToneInput, customTones,
    brandOpen, setBrandOpen, selectedPreset, setSelectedPreset, marketDataEnabled, setMarketDataEnabled,
    refImage, setRefImage, brand, setBrand,
    toggleTone, addCustomTone, applyPreset, startCustom, updateBrand,
    updateColorHex, updateColorLabel, addColor, removeColor, updateFont, addFont, removeFont,
    uploadBrandLogo, uploadReferenceImage,
  };
}
