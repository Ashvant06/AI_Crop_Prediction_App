import { useAuth } from "../context/AuthContext";

function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">AgroAI</span>
        <p className="brand-sub">Crop Yield Prediction System</p>
      </div>
      <div className="topbar-actions">
        <div className="profile-chip">
          {user?.picture ? <img src={user.picture} alt={user.name} /> : null}
          <div>
            <p>{user?.name || "Farmer"}</p>
            <small>{user?.email || ""}</small>
          </div>
        </div>
        <button type="button" onClick={logout} className="ghost-btn">
          Sign out
        </button>
      </div>
    </header>
  );
}

export default Navbar;
