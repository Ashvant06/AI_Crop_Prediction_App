import { useState } from "react";

const initialSurvey = {
  preferred_crops: [],
  irrigation_method: "drip",
  risk_appetite: "medium",
  satisfaction_score: 4,
  notes: ""
};

const cropOptions = ["rice", "wheat", "maize", "soybean", "cotton", "sugarcane"];

function SurveyPanel({ onSubmit, loading }) {
  const [survey, setSurvey] = useState(initialSurvey);

  const toggleCrop = (crop) => {
    setSurvey((prev) => {
      const hasCrop = prev.preferred_crops.includes(crop);
      return {
        ...prev,
        preferred_crops: hasCrop
          ? prev.preferred_crops.filter((item) => item !== crop)
          : [...prev.preferred_crops, crop]
      };
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit(survey);
  };

  return (
    <section className="card">
      <div className="card-head">
        <h3>Farmer Survey</h3>
        <p>Track preferences and planning confidence</p>
      </div>
      <form onSubmit={handleSubmit} className="survey-form">
        <div className="chip-wrap">
          {cropOptions.map((crop) => (
            <button
              type="button"
              key={crop}
              onClick={() => toggleCrop(crop)}
              className={survey.preferred_crops.includes(crop) ? "chip chip-active" : "chip"}
            >
              {crop}
            </button>
          ))}
        </div>
        <label>
          <span>Irrigation Method</span>
          <select
            value={survey.irrigation_method}
            onChange={(event) => setSurvey((prev) => ({ ...prev, irrigation_method: event.target.value }))}
          >
            <option value="drip">Drip</option>
            <option value="sprinkler">Sprinkler</option>
            <option value="flood">Flood</option>
            <option value="rainfed">Rainfed</option>
          </select>
        </label>
        <label>
          <span>Risk Appetite</span>
          <select
            value={survey.risk_appetite}
            onChange={(event) => setSurvey((prev) => ({ ...prev, risk_appetite: event.target.value }))}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          <span>Satisfaction (1-5)</span>
          <input
            type="range"
            min={1}
            max={5}
            value={survey.satisfaction_score}
            onChange={(event) =>
              setSurvey((prev) => ({ ...prev, satisfaction_score: Number(event.target.value) }))
            }
          />
          <small>{survey.satisfaction_score}/5</small>
        </label>
        <label>
          <span>Notes</span>
          <textarea
            value={survey.notes}
            onChange={(event) => setSurvey((prev) => ({ ...prev, notes: event.target.value }))}
            rows={4}
            placeholder="Any local challenge or objective for the next season..."
          />
        </label>
        <button type="submit" className="primary-btn" disabled={loading}>
          {loading ? "Saving..." : "Save Survey"}
        </button>
      </form>
    </section>
  );
}

export default SurveyPanel;
