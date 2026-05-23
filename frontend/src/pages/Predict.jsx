import { useState } from "react";
import { predictReadmission } from "../services/api";

const initialForm = {
  race: "Caucasian",
  gender: "Female",
  age: "[50-60)",
  admission_type_id: 1,
  discharge_disposition_id: 1,
  admission_source_id: 7,
  time_in_hospital: 4,
  num_lab_procedures: 43,
  num_procedures: 0,
  num_medications: 12,
  number_outpatient: 0,
  number_emergency: 0,
  number_inpatient: 1,
  diag_1: "250",
  diag_2: "401",
  diag_3: "414",
  number_diagnoses: 8,
  max_glu_serum: "None",
  A1Cresult: "None",
  change: "Ch",
  diabetesMed: "Yes",
};

const fieldGroups = [
  {
    title: "Patient Information",
    fields: ["race", "gender", "age"],
  },
  {
    title: "Admission Information",
    fields: [
      "admission_type_id",
      "discharge_disposition_id",
      "admission_source_id",
      "time_in_hospital",
    ],
  },
  {
    title: "Clinical Information",
    fields: [
      "num_lab_procedures",
      "num_procedures",
      "num_medications",
      "number_outpatient",
      "number_emergency",
      "number_inpatient",
      "diag_1",
      "diag_2",
      "diag_3",
      "number_diagnoses",
      "max_glu_serum",
      "A1Cresult",
      "change",
      "diabetesMed",
    ],
  },
];

const numericFields = new Set([
  "admission_type_id",
  "discharge_disposition_id",
  "admission_source_id",
  "time_in_hospital",
  "num_lab_procedures",
  "num_procedures",
  "num_medications",
  "number_outpatient",
  "number_emergency",
  "number_inpatient",
  "number_diagnoses",
]);

function formatLabel(field) {
  return field
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function Predict() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: numericFields.has(field) ? Number(value) : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const data = await predictReadmission(form);
      setResult(data);
    } catch (err) {
      setError("Prediction failed. Please check API logs or input values.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <form className="card form-card" onSubmit={handleSubmit}>
        <div className="form-header">
          <div>
            <h3>Patient Readmission Prediction</h3>
            <p>Enter patient information to predict 30-day readmission risk.</p>
          </div>

          <button className="primary-button" disabled={loading}>
            {loading ? "Predicting..." : "Predict"}
          </button>
        </div>

        {fieldGroups.map((group) => (
          <div className="form-section" key={group.title}>
            <h4>{group.title}</h4>

            <div className="form-grid">
              {group.fields.map((field) => (
                <label key={field}>
                  <span>{formatLabel(field)}</span>
                  <input
                    type={numericFields.has(field) ? "number" : "text"}
                    value={form[field]}
                    onChange={(event) => handleChange(field, event.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>
        ))}
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="card result-card">
          <h3>Prediction Result</h3>

          <div className="result-grid">
            <div>
              <p>Prediction</p>
              <strong>
                {result.prediction === 1
                  ? "Readmission Risk"
                  : "No Readmission Risk"}
              </strong>
            </div>

            <div>
              <p>Probability</p>
              <strong>
                {(result.readmission_probability * 100).toFixed(2)}%
              </strong>
            </div>

            <div>
              <p>Risk Level</p>
              <strong className={`risk ${result.risk_level}`}>
                {result.risk_level}
              </strong>
            </div>

            <div>
              <p>Model</p>
              <strong>{result.model_name}</strong>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}