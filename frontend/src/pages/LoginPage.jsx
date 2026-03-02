import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";

function LoginPage() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [name, setName] = useState("");
  const [clientAuthError, setClientAuthError] = useState("");
  const { isAuthenticated, authLoading, authError, loginWithPhone, loginAsDemo } = useAuth();
  const { t } = useLanguage();

  const handlePhoneSignIn = async (event) => {
    event.preventDefault();
    setClientAuthError("");

    const normalizedPhone = String(phoneNumber || "").replace(/[\s()-]/g, "").trim();
    const digitsOnly = normalizedPhone.replace(/\D/g, "");

    if (!normalizedPhone) {
      setClientAuthError("Enter a phone number to continue.");
      return;
    }

    if (digitsOnly.length < 10 || digitsOnly.length > 15) {
      setClientAuthError("Phone number must contain 10 to 15 digits.");
      return;
    }

    await loginWithPhone({
      phoneNumber: normalizedPhone,
      name: name.trim() || "Farmer"
    });
  };

  if (isAuthenticated) {
    return <Navigate to="/overview" replace />;
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <p className="eyebrow">Agriculture Intelligence Platform</p>
        <h1>{t("loginHeading")}</h1>
        <p>{t("loginDesc")}</p>
        <form className="phone-login-form" onSubmit={handlePhoneSignIn}>
          <label>
            <span>{t("phoneNumberLabel")}</span>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              placeholder={t("phoneNumberPlaceholder")}
              autoComplete="tel"
              inputMode="tel"
              required
            />
          </label>
          <label>
            <span>{t("farmerNameLabel")}</span>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("farmerNamePlaceholder")}
              autoComplete="name"
            />
          </label>
          <button type="submit" className="primary-btn demo-btn" disabled={authLoading}>
            {t("signInWithPhone")}
          </button>
        </form>
        <button type="button" className="secondary-btn demo-btn" onClick={loginAsDemo} disabled={authLoading}>
          {t("demoMode")}
        </button>
        {authLoading ? <p className="status-line">{t("authenticating")}</p> : null}
        {authError ? <p className="error-line">{authError}</p> : null}
        {clientAuthError ? <p className="error-line">{clientAuthError}</p> : null}
      </section>
    </main>
  );
}

export default LoginPage;
