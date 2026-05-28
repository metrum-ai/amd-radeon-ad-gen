// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { baseApi } from "./baseApi";

export const exportApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    triggerExport: builder.mutation({
      query: (id) => ({
        url: `/api/campaigns/${id}/export`,
        method: "POST",
      }),
      invalidatesTags: (result, error, id) => [{ type: "Export", id }],
    }),
    getExports: builder.query({
      query: (id) => `/api/campaigns/${id}/exports`,
      providesTags: (result, error, id) => [{ type: "Export", id }],
    }),
  }),
});

export const { useTriggerExportMutation, useGetExportsQuery, useLazyGetExportsQuery } = exportApi;
