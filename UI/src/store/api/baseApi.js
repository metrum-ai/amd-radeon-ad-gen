// Created by Metrum AI for AMD

import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

const API_BASE = import.meta.env.VITE_API_URL || "/backend";

export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE,
    prepareHeaders: (headers) => {
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      return headers;
    },
  }),
  tagTypes: [
    "Brand",
    "Campaign",
    "CampaignList",
    "PipelineStatus",
    "AssetUrl",
    "Export",
    "Capabilities",
    "ProviderHealth",
    "Health",
  ],
  endpoints: () => ({}),
});
