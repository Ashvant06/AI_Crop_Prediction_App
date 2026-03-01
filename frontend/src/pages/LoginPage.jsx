import { useState } from "react";
import { Navigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";

function LoginPage() {
  const [clientAuthError, setClientAuthError] = useState("");
  const { isAuthenticated, authLoading, authError, loginWithGoogleCredential, loginAsDemo } = useAuth();
  const { t } = useLanguage();
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
  const rawClientId = normalizeEnvValue(import.meta.env.VITE_GOOGLE_CLIENT_ID);
  const hasClientId =
    Boolean(rawClientId) &&
    !rawClientId.includes("your_google_oauth_client_id") &&
    rawClientId.endsWith(".apps.googleusercontent.com");

  if (isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <p className="eyebrow">Agriculture Intelligence Platform</p>
        <h1>{t("loginHeading")}</h1>
        <p>{t("loginDesc")}</p>
        {hasClientId ? (
          <>
            <GoogleLogin
              onSuccess={async (credentialResponse) => {
                setClientAuthError("");
                const credential = credentialResponse?.credential;
                if (!credential) {
                  setClientAuthError("Google sign-in did not return a valid credential. Please try again.");
                  return;
                }
                await loginWithGoogleCredential(credential);
              }}
              onError={() => {
                setClientAuthError("Google sign-in popup failed. Allow popups and try again.");
              }}
              text="signin_with"
              size="large"
              shape="pill"
              width={300}
            />
            <button type="button" className="secondary-btn demo-btn" onClick={loginAsDemo} disabled={authLoading}>
              {t("demoMode")}
            </button>
          </>
        ) : (
          <>
            <div className="warning-box">
              Set a real Google OAuth Client ID in <code>frontend/.env</code> as <code>VITE_GOOGLE_CLIENT_ID</code>.
              Also set the same value in backend env as <code>GOOGLE_CLIENT_ID</code>.
            </div>
            <button type="button" className="primary-btn demo-btn" onClick={loginAsDemo} disabled={authLoading}>
              {t("demoMode")}
            </button>
          </>
        )}
        {authLoading ? <p className="status-line">{t("authenticating")}</p> : null}
        {authError ? <p className="error-line">{authError}</p> : null}
        {clientAuthError ? <p className="error-line">{clientAuthError}</p> : null}
      </section>
    </main>
  );
}

export default LoginPage;
