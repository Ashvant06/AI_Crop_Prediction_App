import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const PredictionPage = lazy(() => import("./pages/PredictionPage"));
const SurveyPage = lazy(() => import("./pages/SurveyPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const AssistantPage = lazy(() => import("./pages/AssistantPage"));

function PageLoader() {
  return <p className="status-line">Loading page...</p>;
}

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to="/overview" replace /> : <Navigate to="/login" replace />}
        />
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/prediction" element={<PredictionPage />} />
            <Route path="/survey" element={<SurveyPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
