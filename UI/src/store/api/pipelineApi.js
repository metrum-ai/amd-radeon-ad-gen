// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { baseApi } from "./baseApi";

export const pipelineApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    triggerPhase1: builder.mutation({
      query: ({ id }) => ({
        url: `/api/campaigns/${id}/strategize`,
        method: "POST",
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: "Campaign", id },
        { type: "PipelineStatus", id },
      ],
    }),
    triggerPhase2: builder.mutation({
      query: (id) => ({
        url: `/api/campaigns/${id}/generate`,
        method: "POST",
      }),
      invalidatesTags: (result, error, id) => [
        { type: "Campaign", id },
        { type: "PipelineStatus", id },
      ],
    }),
    getPipelineStatus: builder.query({
      query: (id) => `/api/campaigns/${id}/pipeline-status`,
      providesTags: (result, error, id) => [{ type: "PipelineStatus", id }],
    }),
  }),
});

export const {
  useTriggerPhase1Mutation,
  useTriggerPhase2Mutation,
  useGetPipelineStatusQuery,
} = pipelineApi;
