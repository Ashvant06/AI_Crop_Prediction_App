import { useEffect, useMemo, useState } from "react";
import ActivityCharts from "../components/ActivityCharts";
import { dashboardApi } from "../api/client";
import { useLanguage } from "../context/LanguageContext";

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function DashboardPage() {
  const { t } = useLanguage();
  const [summary, setSummary] = useState(null);
  const [charts, setCharts] = useState(null);
  const [activities, setActivities] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  const summaryCards = useMemo(
    () => [
      { label: t("summaryPredictions"), value: summary?.total_predictions ?? 0 },
      { label: t("summaryRecommendations"), value: summary?.total_recommendations ?? 0 },
      { label: t("summarySurveys"), value: summary?.total_surveys ?? 0 },
      {
        label: t("summaryLatestYield"),
        value: summary?.latest_yield_quintal_acre != null ? summary.latest_yield_quintal_acre : "-",
      },
    ],
    [summary, t]
  );

  useEffect(() => {
    let mounted = true;
    const refreshDashboard = async () => {
      try {
        const [summaryRes, chartsRes, activitiesRes] = await Promise.all([
          dashboardApi.getSummary(),
          dashboardApi.getCharts(),
          dashboardApi.getActivities(),
        ]);
        if (!mounted) return;
        setSummary(summaryRes.data);
        setCharts(chartsRes.data);
        setActivities(activitiesRes.data);
      } catch (error) {
        if (!mounted) return;
        setErrorMessage(error?.response?.data?.detail || "Failed to load dashboard data.");
      }
    };
    refreshDashboard();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="page-stack">
      <section className="summary-grid">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <p>{card.label}</p>
            <h2>{card.value}</h2>
          </article>
        ))}
      </section>

      {errorMessage ? <p className="error-line">{errorMessage}</p> : null}

      <section className="card">
        <div className="card-head">
          <h3>Activity Log</h3>
        </div>
        <div className="activity-list">
          {activities.length ? (
            activities.map((activity) => (
              <article key={activity.id}>
                <p>{activity.detail}</p>
                <small>
                  {activity.activity_type} | {formatDate(activity.created_at)}
                </small>
              </article>
            ))
          ) : (
            <p className="muted">{t("noData")}</p>
          )}
        </div>
      </section>

      <ActivityCharts chartData={charts} />
    </div>
  );
}

export default DashboardPage;
