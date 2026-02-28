import { createContext, useContext, useMemo, useState } from "react";
import { authApi, clearAccessToken, setAccessToken } from "../api/client";

const USER_KEY = "crop_ai_user";
const AuthContext = createContext(null);

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
      const detail = error?.response?.data?.detail || "Google sign-in failed.";
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
      const detail = error?.response?.data?.detail || "Demo sign-in failed.";
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
