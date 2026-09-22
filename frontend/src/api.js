import axios from "axios";

export const api = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
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