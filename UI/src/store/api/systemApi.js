// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { baseApi } from "./baseApi";

export const systemApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    health: builder.query({
      query: () => "/health",
      providesTags: ["Health"],
    }),
    providerHealth: builder.query({
      query: () => "/api/health/providers",
      providesTags: ["ProviderHealth"],
    }),
    getCapabilities: builder.query({
      query: () => "/api/health/capabilities",
      providesTags: ["Capabilities"],
    }),
  }),
});

export const {
  useHealthQuery,
  useProviderHealthQuery,
  useGetCapabilitiesQuery,
  useLazyGetCapabilitiesQuery,
} = systemApi;
