import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

function AppLayout() {
  return (
    <div className="dashboard-layout">
      <Navbar />
      <main className="dashboard-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
