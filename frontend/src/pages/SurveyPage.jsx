import { useState } from "react";
import SurveyPanel from "../components/SurveyPanel";
import { surveyApi } from "../api/client";
import { useLocationData } from "../context/LocationContext";
import { useLanguage } from "../context/LanguageContext";

function SurveyPage() {
  const { t } = useLanguage();
  const { coords, place } = useLocationData();
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleSurveySubmit = async (payload) => {
    setLoading(true);
    setErrorMessage("");
    setStatusMessage("");
    try {
      await surveyApi.submit({
        ...payload,
        user_latitude: coords.latitude,
        user_longitude: coords.longitude,
        user_locality: place.locality || place.district || "",
      });
      setStatusMessage("Survey saved for your region.");
    } catch (error) {
      setErrorMessage(error?.response?.data?.detail || "Survey save failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="card">
        <div className="card-head">
          <h3>{t("surveyTitle")}</h3>
          <p>
            Location-aware survey for {place.locality || place.district || "your area"}, {place.state || "Tamil Nadu"}
          </p>
        </div>
        {statusMessage ? <p className="status-line">{statusMessage}</p> : null}
        {errorMessage ? <p className="error-line">{errorMessage}</p> : null}
      </section>

      <SurveyPanel
        onSubmit={handleSurveySubmit}
        loading={loading}
        regionLabel={`${place.locality || place.district || "Tamil Nadu"}, ${place.state || "Tamil Nadu"}`}
      />
    </div>
  );
}

export default SurveyPage;
