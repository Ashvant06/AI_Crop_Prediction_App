import { useState } from "react";
import PredictionForm from "../components/PredictionForm";
import { predictionApi } from "../api/client";
import { useLocationData } from "../context/LocationContext";
import { useLanguage } from "../context/LanguageContext";

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function PredictionPage() {
  const { t } = useLanguage();
  const { coords, place } = useLocationData();
  const [loading, setLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const withLocation = (payload) => ({
    ...payload,
    user_latitude: coords.latitude,
    user_longitude: coords.longitude,
    user_locality: place.locality || place.district || "",
    state: payload.state || place.state || "Tamil Nadu",
    district: payload.district || place.district || "",
  });

  const handlePredict = async (payload) => {
    setLoading(true);
    setErrorMessage("");
    setStatusMessage("");
    try {
      const response = await predictionApi.predict(withLocation(payload));
      setPredictionResult(response.data);
      setStatusMessage("Yield prediction saved.");
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
      const response = await predictionApi.recommend(withLocation(payload));
      setRecommendations(response.data.recommendations || []);
      setStatusMessage("Crop recommendations generated.");
    } catch (error) {
      setErrorMessage(error?.response?.data?.detail || "Recommendation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <PredictionForm
        onPredict={handlePredict}
        onRecommend={handleRecommend}
        loading={loading}
        defaultLocation={{ state: place.state || "Tamil Nadu", district: place.district || "" }}
      />

      {statusMessage ? <p className="status-line">{statusMessage}</p> : null}
      {errorMessage ? <p className="error-line">{errorMessage}</p> : null}

      <section className="card">
        <div className="card-head">
          <h3>{t("recommendationTitle")}</h3>
          <p>Latest output for your current region</p>
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
          <p className="muted">{t("noData")}</p>
        )}

        {recommendations.length > 0 ? (
          <div className="recommendation-list">
            <h4>{t("recommendationTitle")}</h4>
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
  );
}

export default PredictionPage;
