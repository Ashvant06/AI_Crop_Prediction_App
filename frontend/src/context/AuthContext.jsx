import { createContext, useContext, useMemo, useState } from "react";
import { API_BASE_URL, authApi, clearAccessToken, setAccessToken } from "../api/client";

const USER_KEY = "crop_ai_user";
const AuthContext = createContext(null);

const extractErrorDetail = (error, fallbackMessage) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && typeof item.msg === "string") return item.msg;
        try {
          return JSON.stringify(item);
        } catch {
          return "";
        }
      })
      .filter(Boolean)
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    if (typeof detail.message === "string" && detail.message.trim()) {
      return detail.message;
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return fallbackMessage;
    }
  }
  if (error?.message === "Network Error") {
    return `Cannot reach backend API at ${API_BASE_URL}. Check VITE_API_BASE_URL and backend CORS settings.`;
  }
  return fallbackMessage;
};

const getStoredUser = () => {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const loginWithGoogleCredential = async (credential) => {
    setAuthLoading(true);
    setAuthError("");
    try {
      const response = await authApi.googleLogin(credential);
      const { access_token, user: userProfile } = response.data;
      setAccessToken(access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(userProfile));
      setUser(userProfile);
      return true;
    } catch (error) {
      const detail = extractErrorDetail(error, "Google sign-in failed.");
      setAuthError(detail);
      return false;
    } finally {
      setAuthLoading(false);
    }
  };

  const loginAsDemo = async () => {
    setAuthLoading(true);
    setAuthError("");
    try {
      const response = await authApi.devLogin({
        name: "Demo Farmer",
        email: "demo.farmer@local.dev"
      });
      const { access_token, user: userProfile } = response.data;
      setAccessToken(access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(userProfile));
      setUser(userProfile);
      return true;
    } catch (error) {
      const detail = extractErrorDetail(error, "Demo sign-in failed.");
      setAuthError(detail);
      return false;
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = () => {
    clearAccessToken();
    localStorage.removeItem(USER_KEY);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      authLoading,
      authError,
      loginWithGoogleCredential,
      loginAsDemo,
      logout
    }),
    [user, authLoading, authError]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
};
