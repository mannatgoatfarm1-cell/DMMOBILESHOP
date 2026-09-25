import axios from "axios";

export const api = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL,
  withCredentials: true,
  headers: { Accept: "application/json" },
});

let refreshInFlight = null;
const authFreeEndpoints = ["/api/auth/login", "/api/auth/register", "/api/auth/refresh", "/api/auth/me", "/api/auth/forgot-password", "/api/auth/reset-password"];

api.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) delete config.headers["Content-Type"];
  return config;
});

api.interceptors.response.use((response) => response, async (error) => {
  const request = error.config;
  const isAuthFreeRequest = authFreeEndpoints.some((endpoint) => request?.url?.includes(endpoint));
  if (error?.response?.status !== 401 || !request || request._sessionRetried || isAuthFreeRequest) return Promise.reject(error);
  request._sessionRetried = true;
  try {
    if (!refreshInFlight) refreshInFlight = axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/auth/refresh`, {}, { withCredentials: true }).finally(() => { refreshInFlight = null; });
    await refreshInFlight;
    return api(request);
  } catch (refreshError) {
    window.dispatchEvent(new Event("mobilecart:session-expired"));
    return Promise.reject(error);
  }
});

export function apiError(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || String(item)).join(" ");
  return "Something went wrong. Please try again.";
}

export const cardProduct = (product) => ({
  ...product,
  image: product.images?.[0] || "",
  old: product.original_price,
});