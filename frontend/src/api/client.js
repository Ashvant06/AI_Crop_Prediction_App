import axios from "axios";

const normalizeEnvValue = (value) => {
  const normalized = String(value || "").trim();
  if (normalized.length >= 2) {
    const hasSingleQuotes = normalized.startsWith("'") && normalized.endsWith("'");
    const hasDoubleQuotes = normalized.startsWith('"') && normalized.endsWith('"');
    if (hasSingleQuotes || hasDoubleQuotes) {
      return normalized.slice(1, -1).trim();
    }
  }
  return normalized;
};

export const API_BASE_URL = normalizeEnvValue(import.meta.env.VITE_API_BASE_URL) || "http://localhost:8000";
const TOKEN_KEY = "crop_ai_token";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const setAccessToken = (token) => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearAccessToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

export const getAccessToken = () => localStorage.getItem(TOKEN_KEY);

export const authApi = {
  googleLogin: (credential) => apiClient.post("/auth/google", { credential }),
  devLogin: (payload) => apiClient.post("/auth/dev", payload)
};

export const predictionApi = {
  predict: (payload) => apiClient.post("/prediction/predict", payload),
  recommend: (payload) => apiClient.post("/prediction/recommend", payload)
};

export const surveyApi = {
  submit: (payload) => apiClient.post("/survey/submit", payload)
};

export const dashboardApi = {
  getSummary: () => apiClient.get("/dashboard/summary"),
  getCharts: () => apiClient.get("/dashboard/charts"),
  getActivities: () => apiClient.get("/dashboard/activities")
};

export const chatApi = {
  sendMessage: (payload) => apiClient.post("/chat/message", payload, { timeout: 60000 })
};

export const newsApi = {
  getOverview: (limit = 9) => apiClient.get(`/news/overview?limit=${limit}`)
};

export default apiClient;
