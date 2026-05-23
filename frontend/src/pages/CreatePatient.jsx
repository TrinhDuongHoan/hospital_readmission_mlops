import { useState } from "react";
import { AlertTriangle, CheckCircle2, RotateCcw, Save } from "lucide-react";
import { createPatient, predictPatient } from "../services/api";
import {
  fieldHelp,
  formatFieldLabel,
  formatOptionLabel,
  formatPrediction,
  formatProbability,
  getRiskPresentation,
} from "../utils/clinicalDisplay";

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
    title: "Patient details",
    description: "Basic demographics used by the readmission model.",
    fields: ["race", "gender", "age"],
  },
  {
    title: "Hospital visit",
    description: "How the patient entered and left the hospital.",
    fields: [
      "admission_type_id",
      "discharge_disposition_id",
      "admission_source_id",
      "time_in_hospital",
    ],
  },
  {
    title: "Clinical activity",
    description: "Care intensity during the admission.",
    fields: [
      "num_lab_procedures",
      "num_procedures",
      "num_medications",
      "number_outpatient",
      "number_emergency",
      "number_inpatient",
      "number_diagnoses",
    ],
  },
  {
    title: "Diagnosis and treatment",
    description: "Diagnosis codes and diabetes-related treatment signals.",
    fields: [
      "diag_1",
      "diag_2",
      "diag_3",
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

const selectOptions = {
  race: [
    "Caucasian",
    "AfricanAmerican",
    "Asian",
    "Hispanic",
    "Other",
    "Unknown",
  ],
  gender: ["Female", "Male", "Unknown/Invalid"],
  age: [
    "[0-10)",
    "[10-20)",
    "[20-30)",
    "[30-40)",
    "[40-50)",
    "[50-60)",
    "[60-70)",
    "[70-80)",
    "[80-90)",
    "[90-100)",
  ],
  max_glu_serum: ["None", "Norm", ">200", ">300"],
  A1Cresult: ["None", "Norm", ">7", ">8"],
  change: ["Ch", "No"],
  diabetesMed: ["Yes", "No"],
};

function FormField({ field, value, onChange }) {
  const options = selectOptions[field];
  const help = fieldHelp[field];

  if (options) {
    return (
      <label>
        <span>{formatFieldLabel(field)}</span>
        <select
          value={value}
          onChange={(event) => onChange(field, event.target.value)}
        >
          {options.map((option) => (
            <option key={option} value={option}>
              {formatOptionLabel(option)}
            </option>
          ))}
        </select>
        {help && <small className="field-help">{help}</small>}
      </label>
    );
  }

  return (
    <label>
      <span>{formatFieldLabel(field)}</span>
      <input
        min={numericFields.has(field) ? 0 : undefined}
        type={numericFields.has(field) ? "number" : "text"}
        value={value}
        onChange={(event) => onChange(field, event.target.value)}
      />
      {help && <small className="field-help">{help}</small>}
    </label>
  );
}

function PredictionSummary({ result }) {
  const risk = getRiskPresentation(
    result.risk_level,
    result.readmission_probability
  );
  const Icon = risk.level === "high" ? AlertTriangle : CheckCircle2;

  return (
    <div className={`risk-summary ${risk.level}`}>
      <div className="risk-summary-icon">
        <Icon size={24} />
      </div>

      <div className="risk-summary-body">
        <span>{risk.label}</span>
        <h3>{risk.title}</h3>
        <p>{risk.action}</p>
      </div>

      <div className="risk-summary-score">
        <span>Readmission chance</span>
        <strong>{formatProbability(result.readmission_probability)}</strong>
      </div>
    </div>
  );
}

export default function CreatePatient() {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [createdPatient, setCreatedPatient] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);

  function handleChange(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: numericFields.has(field) ? Number(value) : value,
    }));
  }

  function resetForm() {
    setForm(initialForm);
    setError("");
    setMessage("");
    setCreatedPatient(null);
    setPredictionResult(null);
  }

  async function handleCreatePatient(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");
      setMessage("");
      setCreatedPatient(null);
      setPredictionResult(null);

      const patient = await createPatient(form);
      const prediction = await predictPatient(patient.id);

      setCreatedPatient(patient);
      setPredictionResult(prediction);
      setMessage(`Created patient #${patient.id} and completed prediction.`);
      setForm(initialForm);
    } catch (err) {
      setError(err.response?.data?.detail || "Cannot create and predict patient.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <form className="card form-card create-patient-card" onSubmit={handleCreatePatient}>
        <div className="form-header">
          <div>
            <h3>New Patient Intake</h3>
            <p>Enter the clinical profile once, then save and run the readmission check.</p>
          </div>

          <div className="form-actions">
            <button className="secondary-button" type="button" onClick={resetForm}>
              <RotateCcw size={16} />
              Reset
            </button>

            <button className="primary-button" disabled={loading}>
              <Save size={16} />
              {loading ? "Saving..." : "Save and Predict"}
            </button>
          </div>
        </div>

        {fieldGroups.map((group) => (
          <div className="form-section" key={group.title}>
            <h4>{group.title}</h4>
            <p className="section-intro">{group.description}</p>

            <div className="form-grid">
              {group.fields.map((field) => (
                <FormField
                  field={field}
                  key={field}
                  onChange={handleChange}
                  value={form[field]}
                />
              ))}
            </div>
          </div>
        ))}
      </form>

      {createdPatient && predictionResult && (
        <div className="card result-card create-result-card">
          <PredictionSummary result={predictionResult} />

          <h3>Patient #{createdPatient.id} Prediction Details</h3>

          <div className="result-grid">
            <div>
              <p>Prediction</p>
              <strong>{formatPrediction(predictionResult.prediction)}</strong>
            </div>

            <div>
              <p>Readmission Chance</p>
              <strong>{formatProbability(predictionResult.readmission_probability)}</strong>
            </div>

            <div>
              <p>Priority Level</p>
              <strong className={`risk ${predictionResult.risk_level}`}>
                {
                  getRiskPresentation(
                    predictionResult.risk_level,
                    predictionResult.readmission_probability
                  ).label
                }
              </strong>
            </div>

            <div>
              <p>Model</p>
              <strong>{predictionResult.model_name}</strong>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
