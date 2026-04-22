// Created by Metrum AI for AMD

import { baseApi } from "./baseApi";

export const campaignApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    createBrand: builder.mutation({
      query: (body) => ({
        url: "/api/brands",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Brand"],
    }),
    listBrands: builder.query({
      query: (userId) => ({
        url: "/api/brands",
        params: userId ? { user_id: userId } : undefined,
      }),
      providesTags: ["Brand"],
    }),
    getBrand: builder.query({
      query: (id) => `/api/brands/${id}`,
      providesTags: (result, error, id) => [{ type: "Brand", id }],
    }),
    updateBrand: builder.mutation({
      query: ({ id, data }) => ({
        url: `/api/brands/${id}`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: "Brand", id }, "Brand"],
    }),
    deleteBrand: builder.mutation({
      query: (id) => ({
        url: `/api/brands/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Brand"],
    }),

    createCampaign: builder.mutation({
      query: (body) => ({
        url: "/api/campaigns",
        method: "POST",
        body,
      }),
      invalidatesTags: ["CampaignList"],
    }),
    listCampaigns: builder.query({
      query: (userId) => ({
        url: "/api/campaigns",
        params: userId ? { user_id: userId } : undefined,
      }),
      providesTags: ["CampaignList"],
    }),
    getCampaign: builder.query({
      query: (id) => `/api/campaigns/${id}`,
      providesTags: (result, error, id) => [{ type: "Campaign", id }],
    }),
    updateCampaign: builder.mutation({
      query: ({ id, data }) => ({
        url: `/api/campaigns/${id}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: "Campaign", id }],
    }),
    updateCampaignStatus: builder.mutation({
      query: ({ id, status }) => ({
        url: `/api/campaigns/${id}`,
        method: "PATCH",
        body: { status },
      }),
      invalidatesTags: (result, error, { id }) => [{ type: "Campaign", id }],
    }),
    deleteCampaign: builder.mutation({
      query: (id) => ({
        url: `/api/campaigns/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["CampaignList"],
    }),
  }),
});

export const {
  useCreateBrandMutation,
  useListBrandsQuery,
  useGetBrandQuery,
  useUpdateBrandMutation,
  useDeleteBrandMutation,
  useCreateCampaignMutation,
  useListCampaignsQuery,
  useGetCampaignQuery,
  useUpdateCampaignMutation,
  useUpdateCampaignStatusMutation,
  useDeleteCampaignMutation,
} = campaignApi;
