// Created by Metrum AI for AMD

import { configureStore } from "@reduxjs/toolkit";

import { baseApi } from "./api/baseApi";
import campaignSessionReducer from "./sessionSlice";

export const store = configureStore({
  reducer: {
    [baseApi.reducerPath]: baseApi.reducer,
    campaignSession: campaignSessionReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(baseApi.middleware),
});
