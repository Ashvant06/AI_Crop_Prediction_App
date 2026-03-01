import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { LanguageProvider } from "./context/LanguageContext";
import { LocationProvider } from "./context/LocationContext";
import "./styles.css";

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

const googleClientId = normalizeEnvValue(import.meta.env.VITE_GOOGLE_CLIENT_ID);

ReactDOM.createRoot(document.getElementById("root")).render(
  <GoogleOAuthProvider clientId={googleClientId}>
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          <LocationProvider>
            <App />
          </LocationProvider>
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  </GoogleOAuthProvider>
);
