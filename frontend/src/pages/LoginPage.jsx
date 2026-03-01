import { Navigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";

function LoginPage() {
  const { isAuthenticated, authLoading, authError, loginWithGoogleCredential, loginAsDemo } = useAuth();
  const { t } = useLanguage();
  const rawClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
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
              onSuccess={(credentialResponse) =>
                credentialResponse.credential ? loginWithGoogleCredential(credentialResponse.credential) : Promise.resolve(false)
              }
              onError={() => {
                // keep lightweight client-side error handling
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
      </section>
    </main>
  );
}

export default LoginPage;
