// Created by Metrum AI for AMD

import { useState } from "react";
import { C, gradient, shadow, radius } from "../tokens";
import { Box, T, Btn } from "../components/primitives";
import useBriefFormState from "../hooks/useBriefFormState";
import BriefBrandSection from "../components/brief/BriefBrandSection";
import BriefCampaignDetailsSection from "../components/brief/BriefCampaignDetailsSection";
import BriefErrorBanner from "../components/brief/BriefErrorBanner";
import "../css/brief/BriefScreen.css";
import { useCreateBrandMutation, useCreateCampaignMutation } from "../store/api/campaignApi";
import { useTriggerPhase1Mutation } from "../store/api/pipelineApi";
import { useAppDispatch } from "../store/hooks";
import { setBrandId, setCampaignId } from "../store/sessionSlice";
import { getRtkErrorMessage } from "../lib/rtk";

const BriefScreen = ({ onNext }) => {
  const dispatch = useAppDispatch();
  const [requestError, setRequestError] = useState(null);
  const [createBrand] = useCreateBrandMutation();
  const [createCampaign] = useCreateCampaignMutation();
  const [triggerPhase1] = useTriggerPhase1Mutation();
  const {
    submitting,
    setSubmitting,
    productDescription,
    setProductDescription,
    campaignObjective,
    setCampaignObjective,
    validationError,
    setValidationError,
    tones,
    setTones,
    customToneInput,
    setCustomToneInput,
    customTones,
    brandOpen,
    setBrandOpen,
    selectedPreset,
    marketDataEnabled,
    setMarketDataEnabled,
    refImage,
    setRefImage,
    brand,
    toggleTone,
    addCustomTone,
    applyPreset,
    startCustom,
    updateBrand,
    updateColorHex,
    updateColorLabel,
    addColor,
    removeColor,
    updateFont,
    addFont,
    removeFont,
    uploadBrandLogo,
    uploadReferenceImage,
  } = useBriefFormState();

  const handleSubmit = async () => {
    setValidationError(null);
    setRequestError(null);

    if (!brand.name.trim()) {
      setValidationError("Brand name is required.");
      return;
    }
    if (!productDescription.trim()) {
      setValidationError("Product description is required.");
      return;
    }
    if (!campaignObjective.trim()) {
      setValidationError("Campaign objective is required.");
      return;
    }

    setSubmitting(true);
    try {
      const colorsObj = {};
      brand.colors.forEach((c) => {
        colorsObj[c.label.toLowerCase()] = c.hex;
      });
      const fontsObj = {};
      brand.fonts.forEach((f, i) => {
        fontsObj[i === 0 ? "headline" : i === 1 ? "body" : `font_${i}`] = f;
      });

      const brandResult = await createBrand({
        name: brand.name,
        logo_url: brand.logo || null,
        colors: colorsObj,
        fonts: fontsObj,
        user_id: "00000000-0000-0000-0000-000000000001",
      }).unwrap();
      dispatch(setBrandId(brandResult.id));

      const campaignResult = await createCampaign({
        name: `${brand.name} Campaign`,
        brand_id: brandResult.id,
        product_description: productDescription,
        objective: campaignObjective,
        tone: tones.join(", "),
        style: tones.join(", "),
        reference_image_url: refImage || null,
        tracks: { image_text: true, audio_podcast: true, video: false },
        user_id: "00000000-0000-0000-0000-000000000001",
      }).unwrap();
      dispatch(setCampaignId(campaignResult.id));

      await triggerPhase1({
        id: campaignResult.id,
        marketDataEnabled,
      }).unwrap();
      onNext();
    } catch (error) {
      setRequestError(getRtkErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box className="brief-screen">
      <T s={24} w={700} className="brief-screen__title">Campaign Brief</T>
      <T s={13} c={C.muted} className="brief-screen__subtitle">
        Define your brand, objectives, and creative direction.
      </T>

      <BriefBrandSection
        brand={brand}
        brandOpen={brandOpen}
        setBrandOpen={setBrandOpen}
        selectedPreset={selectedPreset}
        applyPreset={applyPreset}
        startCustom={startCustom}
        updateBrand={updateBrand}
        addColor={addColor}
        removeColor={removeColor}
        updateColorHex={updateColorHex}
        updateColorLabel={updateColorLabel}
        addFont={addFont}
        removeFont={removeFont}
        updateFont={updateFont}
        uploadBrandLogo={uploadBrandLogo}
      />

      <BriefCampaignDetailsSection
        productDescription={productDescription}
        setProductDescription={setProductDescription}
        campaignObjective={campaignObjective}
        setCampaignObjective={setCampaignObjective}
        tones={tones}
        setTones={setTones}
        customToneInput={customToneInput}
        setCustomToneInput={setCustomToneInput}
        customTones={customTones}
        toggleTone={toggleTone}
        addCustomTone={addCustomTone}
        refImage={refImage}
        setRefImage={setRefImage}
        uploadReferenceImage={uploadReferenceImage}
        setValidationError={setValidationError}
      />

      <Box className="brief-screen__market-data" style={{ display: "block" }}>
        <Box className="brief-screen__market-card" style={{ borderRadius: radius.md, background: C.elevated }}>
          <Box className="brief-screen__market-row">
            <Box className="brief-screen__market-left">
              <Box
                onClick={() => setMarketDataEnabled(!marketDataEnabled)}
                style={{
                  width: 44,
                  height: 24,
                  borderRadius: 12,
                  background: marketDataEnabled ? gradient.amdH : C.hover,
                  position: "relative",
                  cursor: "pointer",
                  border: `1px solid ${marketDataEnabled ? "transparent" : C.border}`,
                  transition: "all 0.2s ease",
                }}
              >
                <Box style={{
                  width: 18,
                  height: 18,
                  borderRadius: 9,
                  background: "#fff",
                  position: "absolute",
                  top: 3,
                  left: marketDataEnabled ? 23 : 3,
                  boxShadow: shadow.sm,
                  transition: "left 0.2s ease",
                }} />
              </Box>
              <Box>
                <T s={13} w={600} c={marketDataEnabled ? C.white : C.muted}>Inject Market Data</T>
                <T s={11} c={C.dim}>Use Reddit Trends to enrich Strategy Generation</T>
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>

      <BriefErrorBanner message={validationError || requestError} />

      <button
        className="brief-screen__submitButton"
        disabled={submitting}
        onClick={handleSubmit}
        style={{
          padding: "16px 24px",
          borderRadius: radius.md,
          border: "none",
          background: submitting ? C.elevated : gradient.amd,
          color: submitting ? C.dim : "#fff",
          fontSize: 13,
          fontWeight: 600,
          cursor: submitting ? "not-allowed" : "pointer",
          fontFamily: "'Inter', sans-serif",
        }}
      >
        {submitting && (
          <Box style={{
            width: 14,
            height: 14,
            borderRadius: 7,
            border: `2px solid ${C.dim}`,
            borderTopColor: "transparent",
            animation: "spin 0.6s linear infinite",
          }} />
        )}
        {submitting ? "Generating..." : "Generate Strategy"} {!submitting && "→"}
      </button>
    </Box>
  );
};

export default BriefScreen;
