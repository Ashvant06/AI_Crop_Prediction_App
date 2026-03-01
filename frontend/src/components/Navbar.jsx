import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { useLocationData } from "../context/LocationContext";
import WeatherTimeWidget from "./WeatherTimeWidget";

const navItems = [
  { to: "/overview", icon: "Home", key: "navOverview" },
  { to: "/prediction", icon: "Seed", key: "navPrediction" },
  { to: "/survey", icon: "Form", key: "navSurvey" },
  { to: "/dashboard", icon: "Chart", key: "navDashboard" },
  { to: "/assistant", icon: "AI", key: "navAssistant" },
];

function Navbar() {
  const { user, logout } = useAuth();
  const { t, isTamil, toggleLanguage } = useLanguage();
  const { loading, error, requestLocation } = useLocationData();

  return (
    <header className="topbar">
      <div className="brand-area">
        <div className="brand">
          <span className="brand-mark">AgroAI TN</span>
          <p className="brand-sub">{t("appSubtitle")}</p>
        </div>
        <nav className="top-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-chip active" : "nav-chip")}
            >
              <span>{item.icon}</span>
              <span>{t(item.key)}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="topbar-actions">
        <WeatherTimeWidget />
        <button type="button" className="ghost-btn" onClick={requestLocation}>
          {loading ? t("locationPending") : error ? t("locationError") : t("requestLocation")}
        </button>
        <button type="button" className="ghost-btn" onClick={toggleLanguage}>
          {isTamil ? t("switchToEnglish") : t("switchToTamil")}
        </button>
        <div className="profile-chip">
          {user?.picture ? <img src={user.picture} alt={user.name} /> : null}
          <div>
            <p>{user?.name || "Farmer"}</p>
            <small>{user?.email || ""}</small>
          </div>
        </div>
        <button type="button" onClick={logout} className="ghost-btn">
          {t("signOut")}
        </button>
      </div>
    </header>
  );
}

export default Navbar;
