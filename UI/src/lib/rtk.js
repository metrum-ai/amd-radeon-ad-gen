// Created by Metrum AI for AMD

export function getRtkErrorMessage(error, fallback = "Request failed") {
  if (!error) return fallback;

  if (typeof error === "string") return error;

  if (error?.data) {
    if (typeof error.data === "string") return error.data;
    if (typeof error.data.detail === "string") return error.data.detail;
    try {
      return JSON.stringify(error.data.detail || error.data);
    } catch {
      return fallback;
    }
  }

  if (typeof error?.error === "string") return error.error;
  if (typeof error?.message === "string") return error.message;

  return fallback;
}

export function normalizePipelineStatus(data) {
  return Array.isArray(data) ? data : data?.stages || [];
}
