import { useState } from "react";

const ACRE_TO_HECTARE = 0.404686;
const ACRE_PER_HECTARE = 2.47105;
const QUINTAL_PER_TON = 10;

const defaultForm = {
  crop: "rice",
  state: "karnataka",
  district: "",
  year: 2026,
  area_acres: 2.5,
  rainfall_mm: 850,
  temperature_c: 25,
  humidity_pct: 65,
  nitrogen: 70,
  phosphorus: 40,
  potassium: 40,
  soil_ph: 6.5,
  pesticides_kg: 30,
  previous_yield_quintal_acre: 12
};

function NumericInput({ name, label, value, onChange, step = 0.1, min }) {
  return (
    <label>
      <span>{label}</span>
      <input
        type="number"
        name={name}
        value={value}
        step={step}
        min={min}
        onChange={onChange}
      />
    </label>
  );
}

function PredictionForm({ onPredict, onRecommend, loading }) {
  const [formData, setFormData] = useState(defaultForm);

  const toApiPayload = () => {
    const areaHectares = formData.area_acres * ACRE_TO_HECTARE;
    const previousYieldTonHectare =
      (formData.previous_yield_quintal_acre * ACRE_PER_HECTARE) / QUINTAL_PER_TON;
    const pesticidesTonnes = formData.pesticides_kg / 1000;

    return {
      crop: formData.crop,
      state: formData.state,
      district: formData.district,
      year: formData.year,
      area_hectares: Number(areaHectares.toFixed(4)),
      rainfall_mm: formData.rainfall_mm,
      temperature_c: formData.temperature_c,
      humidity_pct: formData.humidity_pct,
      nitrogen: formData.nitrogen,
      phosphorus: formData.phosphorus,
      potassium: formData.potassium,
      soil_ph: formData.soil_ph,
      pesticides_tonnes: Number(pesticidesTonnes.toFixed(5)),
      previous_yield_ton_hectare: Number(previousYieldTonHectare.toFixed(4))
    };
  };

  const handleChange = (event) => {
    const { name, value, type } = event.target;
    const normalizedValue = type === "number" ? Number(value) : value;
    setFormData((prev) => ({ ...prev, [name]: normalizedValue }));
  };

  const handlePredict = async (event) => {
    event.preventDefault();
    await onPredict(toApiPayload());
  };

  const handleRecommend = async () => {
    await onRecommend({ ...toApiPayload(), top_n: 5 });
  };

  return (
    <section className="card">
      <div className="card-head">
        <h3>Yield Prediction</h3>
        <p>India-friendly inputs: area in acres and yield in quintals.</p>
      </div>
      <form className="form-grid" onSubmit={handlePredict}>
        <label>
          <span>Crop</span>
          <select name="crop" value={formData.crop} onChange={handleChange}>
            <option value="rice">Rice</option>
            <option value="wheat">Wheat</option>
            <option value="maize">Maize</option>
            <option value="soybean">Soybean</option>
            <option value="cotton">Cotton</option>
            <option value="sugarcane">Sugarcane</option>
          </select>
        </label>
        <label>
          <span>State</span>
          <input name="state" value={formData.state} onChange={handleChange} />
        </label>
        <label>
          <span>District</span>
          <input name="district" value={formData.district} onChange={handleChange} />
        </label>
        <NumericInput name="year" label="Year" value={formData.year} onChange={handleChange} step={1} min={2000} />
        <NumericInput
          name="area_acres"
          label="Area (acres)"
          value={formData.area_acres}
          onChange={handleChange}
          step={0.1}
          min={0.1}
        />
        <NumericInput
          name="rainfall_mm"
          label="Rainfall (mm)"
          value={formData.rainfall_mm}
          onChange={handleChange}
          step={1}
          min={0}
        />
        <NumericInput
          name="temperature_c"
          label="Temperature (C)"
          value={formData.temperature_c}
          onChange={handleChange}
          step={0.1}
        />
        <NumericInput
          name="humidity_pct"
          label="Humidity (%)"
          value={formData.humidity_pct}
          onChange={handleChange}
          step={0.1}
        />
        <NumericInput name="nitrogen" label="Nitrogen N (kg/ha)" value={formData.nitrogen} onChange={handleChange} />
        <NumericInput
          name="phosphorus"
          label="Phosphorus P (kg/ha)"
          value={formData.phosphorus}
          onChange={handleChange}
        />
        <NumericInput name="potassium" label="Potassium K (kg/ha)" value={formData.potassium} onChange={handleChange} />
        <NumericInput name="soil_ph" label="Soil pH" value={formData.soil_ph} onChange={handleChange} />
        <NumericInput
          name="pesticides_kg"
          label="Pesticides Used (kg)"
          value={formData.pesticides_kg}
          onChange={handleChange}
        />
        <NumericInput
          name="previous_yield_quintal_acre"
          label="Previous Yield (quintal/acre)"
          value={formData.previous_yield_quintal_acre}
          onChange={handleChange}
        />
        <div className="form-actions">
          <button type="submit" className="primary-btn" disabled={loading}>
            {loading ? "Predicting..." : "Predict Yield"}
          </button>
          <button type="button" className="secondary-btn" onClick={handleRecommend} disabled={loading}>
            Recommend Crops
          </button>
        </div>
      </form>
    </section>
  );
}

export default PredictionForm;
