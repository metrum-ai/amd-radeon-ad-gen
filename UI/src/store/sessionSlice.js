// Created by Metrum AI for AMD

import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  brandId: null,
  campaignId: null,
};

const sessionSlice = createSlice({
  name: "campaignSession",
  initialState,
  reducers: {
    setBrandId(state, action) {
      state.brandId = action.payload;
    },
    setCampaignId(state, action) {
      state.campaignId = action.payload;
    },
    resetSession(state) {
      state.brandId = null;
      state.campaignId = null;
    },
  },
});

export const { setBrandId, setCampaignId, resetSession } = sessionSlice.actions;

export const selectBrandId = (state) => state.campaignSession.brandId;
export const selectCampaignId = (state) => state.campaignSession.campaignId;

export default sessionSlice.reducer;
