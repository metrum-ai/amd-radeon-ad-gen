// Created by Metrum AI for AMD

import { baseApi } from "./baseApi";

export const assetApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAssetUrl: builder.query({
      query: (assetUrl) => ({
        url: "/api/assets/url",
        params: { asset_url: assetUrl },
      }),
      providesTags: (result, error, assetUrl) => [{ type: "AssetUrl", id: assetUrl }],
    }),
  }),
});

export const { useGetAssetUrlQuery, useLazyGetAssetUrlQuery } = assetApi;
