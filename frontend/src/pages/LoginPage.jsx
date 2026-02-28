import { Navigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";

function LoginPage() {
  const { isAuthenticated, authLoading, authError, loginWithGoogleCredential, loginAsDemo } = useAuth();
  const rawClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const hasClientId =
    Boolean(rawClientId) &&
    !rawClientId.includes("your_google_oauth_client_id") &&
    rawClientId.endsWith(".apps.googleusercontent.com");

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <p className="eyebrow">Agriculture Intelligence Platform</p>
        <h1>AI Crop Yield Prediction System</h1>
        <p>
          Sign in with Google to forecast crop yield, store field history, track farm activity, and receive
          AI guidance.
        </p>
        {hasClientId ? (
          <>
            <GoogleLogin
              onSuccess={(credentialResponse) =>
                credentialResponse.credential
                  ? loginWithGoogleCredential(credentialResponse.credential)
                  : Promise.resolve(false)
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
              Continue in Demo Mode
            </button>
          </>
        ) : (
          <>
            <div className="warning-box">
              Set a real Google OAuth Client ID in <code>frontend/.env</code> as{" "}
              <code>VITE_GOOGLE_CLIENT_ID</code>. Also set the same value in{" "}
              <code>backend/.env</code> as <code>GOOGLE_CLIENT_ID</code>.
            </div>
            <button type="button" className="primary-btn demo-btn" onClick={loginAsDemo} disabled={authLoading}>
              Continue in Demo Mode
            </button>
          </>
        )}
        {authLoading ? <p className="status-line">Authenticating...</p> : null}
        {authError ? <p className="error-line">{authError}</p> : null}
      </section>
    </main>
  );
}

export default LoginPage;
