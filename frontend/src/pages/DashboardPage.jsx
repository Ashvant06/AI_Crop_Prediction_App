import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import PredictionForm from "../components/PredictionForm";
import SurveyPanel from "../components/SurveyPanel";
import ActivityCharts from "../components/ActivityCharts";
import ChatbotWidget from "../components/ChatbotWidget";
import { chatApi, dashboardApi, predictionApi, surveyApi } from "../api/client";

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [charts, setCharts] = useState(null);
  const [activities, setActivities] = useState([]);
  const [predictionResult, setPredictionResult] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [surveyLoading, setSurveyLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [lastPredictionInput, setLastPredictionInput] = useState(null);

  const summaryCards = useMemo(
    () => [
      { label: "Predictions", value: summary?.total_predictions ?? 0 },
      { label: "Recommendations", value: summary?.total_recommendations ?? 0 },
      { label: "Surveys", value: summary?.total_surveys ?? 0 },
      {
        label: "Latest Yield (q/acre)",
        value: summary?.latest_yield_quintal_acre != null ? summary.latest_yield_quintal_acre : "-"
      }
    ],
    [summary]
  );

  const refreshDashboard = async () => {
    const [summaryRes, chartsRes, activitiesRes] = await Promise.all([
      dashboardApi.getSummary(),
      dashboardApi.getCharts(),
      dashboardApi.getActivities()
    ]);
    setSummary(summaryRes.data);
    setCharts(chartsRes.data);
    setActivities(activitiesRes.data);
  };

  useEffect(() => {
    refreshDashboard().catch((error) => {
      setErrorMessage(error?.response?.data?.detail || "Failed to load dashboard data.");
    });
  }, []);

  const handlePredict = async (payload) => {
    setLoading(true);
    setErrorMessage("");
    setStatusMessage("");
    try {
      setLastPredictionInput(payload);
      const response = await predictionApi.predict(payload);
      setPredictionResult(response.data);
      setStatusMessage("Yield prediction saved.");
      await refreshDashboard();
    } catch (error) {
      setErrorMessage(error?.response?.data?.detail || "Prediction failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRecommend = async (payload) => {
    setLoading(true);
    setErrorMessage("");
    setStatusMessage("");
    try {
      setLastPredictionInput(payload);
      const response = await predictionApi.recommend(payload);
      setRecommendations(response.data.recommendations);
      setStatusMessage("Crop recommendations generated.");
      await refreshDashboard();
    } catch (error) {
      setErrorMessage(error?.response?.data?.detail || "Recommendation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleSurveySubmit = async (payload) => {
    setSurveyLoading(true);
    setErrorMessage("");
    setStatusMessage("");
    try {
      await surveyApi.submit(payload);
      setStatusMessage("Survey saved.");
      await refreshDashboard();
    } catch (error) {
      setErrorMessage(error?.response?.data?.detail || "Survey save failed.");
    } finally {
      setSurveyLoading(false);
    }
  };

  const handleAskAssistant = async ({ message, history }) => {
    try {
      const response = await chatApi.sendMessage({
        message,
        history,
        context: {
          prediction_defaults: lastPredictionInput || undefined
        }
      });
      await refreshDashboard();
      return {
        reply: response.data.reply,
        usedTools: response.data.used_tools || [],
        toolSummaries: response.data.tool_summaries || []
      };
    } catch (error) {
      return {
        reply: error?.response?.data?.detail || "Assistant is temporarily unavailable.",
        usedTools: [],
        toolSummaries: []
      };
    }
  };

  return (
    <div className="dashboard-layout">
      <Navbar />
      <main className="dashboard-content">
        <section className="summary-grid">
          {summaryCards.map((card) => (
            <article className="summary-card" key={card.label}>
              <p>{card.label}</p>
              <h2>{card.value}</h2>
            </article>
          ))}
        </section>

        {statusMessage ? <p className="status-line">{statusMessage}</p> : null}
        {errorMessage ? <p className="error-line">{errorMessage}</p> : null}

        <section className="content-grid">
          <div className="column">
            <PredictionForm onPredict={handlePredict} onRecommend={handleRecommend} loading={loading} />

            <section className="card">
              <div className="card-head">
                <h3>Latest AI Output</h3>
              </div>
              {predictionResult ? (
                <div className="prediction-result">
                  <p>
                    Predicted Yield: <strong>{predictionResult.predicted_yield_quintal_acre} q/acre</strong>
                  </p>
                  <p>
                    Yield (hectare): <strong>{predictionResult.predicted_yield_quintal_hectare} q/ha</strong>
                  </p>
                  <p>
                    Total Forecast: <strong>{predictionResult.predicted_total_quintals} quintals</strong>
                  </p>
                  <p>
                    Area: <strong>{predictionResult.area_acres} acre ({predictionResult.area_hectares} ha)</strong>
                  </p>
                  <p>Model: {predictionResult.model_used}</p>
                  <small>{formatDate(predictionResult.created_at)}</small>
                </div>
              ) : (
                <p className="muted">Run your first prediction to view result details.</p>
              )}

              {recommendations.length > 0 ? (
                <div className="recommendation-list">
                  <h4>Top Crop Recommendations</h4>
                  <ul>
                    {recommendations.map((item) => (
                      <li key={item.crop}>
                        <span>{item.crop}</span>
                        <strong>{item.predicted_yield_quintal_acre} q/acre</strong>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          </div>

          <div className="column">
            <SurveyPanel onSubmit={handleSurveySubmit} loading={surveyLoading} />

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
                  <p className="muted">No activities yet.</p>
                )}
              </div>
            </section>
          </div>
        </section>

        <ActivityCharts chartData={charts} />
      </main>

      <ChatbotWidget onAsk={handleAskAssistant} />
    </div>
  );
}

export default DashboardPage;
