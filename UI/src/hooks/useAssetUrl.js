// Copyright Advanced Micro Devices, Inc.
//
// SPDX-License-Identifier: MIT

import { useState, useCallback, useEffect } from "react";
import { useDispatch } from "react-redux";
import { assetApi } from "../store/api/assetApi";

const cache = new Map();
const CACHE_TTL = 50 * 60 * 1000; // 50 minutes (presigned URLs expire in 60min)

/**
 * Converts s3:// URLs to presigned download URLs.
 * Caches results to avoid repeated API calls.
 */
export default function useAssetUrl() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const getUrl = useCallback(async (s3Url) => {
    if (!s3Url) return null;
    if (!s3Url.startsWith("s3://")) return s3Url;

    const cached = cache.get(s3Url);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return cached.url;
    }

    setLoading(true);
    try {
      const result = await dispatch(
        assetApi.endpoints.getAssetUrl.initiate(s3Url, {
          forceRefetch: false,
        })
      ).unwrap();
      const url = result.url || result.download_url || result;
      cache.set(s3Url, { url, ts: Date.now() });
      return url;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const getUrlSync = useCallback((s3Url) => {
    if (!s3Url) return null;
    if (!s3Url.startsWith("s3://")) return s3Url;
    const cached = cache.get(s3Url);
    return cached && Date.now() - cached.ts < CACHE_TTL ? cached.url : null;
  }, []);

  return { getUrl, getUrlSync, loading };
}

/**
 * Hook that resolves a single s3:// URL and returns the presigned URL.
 */
export function useResolvedUrl(s3Url) {
  const [url, setUrl] = useState(null);
  const { getUrl } = useAssetUrl();

  useEffect(() => {
    if (!s3Url) return;
    let cancelled = false;
    getUrl(s3Url).then((resolved) => {
      if (!cancelled) setUrl(resolved);
    });
    return () => { cancelled = true; };
  }, [s3Url, getUrl]);

  return url;
}
