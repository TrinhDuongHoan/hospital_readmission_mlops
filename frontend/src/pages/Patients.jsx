import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Eye,
  RefreshCw,
  Search,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import {
  deletePatient,
  getPatientPredictions,
  getPatients,
  predictPatient,
} from "../services/api";
import {
  formatFieldLabel,
  formatPrediction,
  formatProbability,
  getRiskPresentation,
} from "../utils/clinicalDisplay";

const patientDetailGroups = [
  {
    title: "Patient details",
    fields: ["id", "gender", "age", "race", "doctor_full_name"],
  },
  {
    title: "Hospital visit",
    fields: [
      "admission_type_id",
      "discharge_disposition_id",
      "admission_source_id",
      "time_in_hospital",
    ],
  },
  {
    title: "Clinical activity",
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
    title: "Diagnosis",
    fields: ["diag_1", "diag_2", "diag_3", "max_glu_serum", "A1Cresult"],
  },
  {
    title: "Treatment",
    fields: ["metformin", "insulin", "change", "diabetesMed"],
  },
];

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

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [predictionResult, setPredictionResult] = useState(null);
  const [patientPredictions, setPatientPredictions] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [genderFilter, setGenderFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");

  async function loadPatients() {
    try {
      setError("");
      const data = await getPatients();
      setPatients(data);
    } catch (err) {
      setError("Cannot load patients.");
    }
  }

  useEffect(() => {
    loadPatients();
  }, []);

  function handleSelectPatient(patient) {
    setSelectedPatient(patient);
    setPredictionResult(null);
    setPatientPredictions([]);
    setMessage("");
    setError("");
    setIsDetailOpen(true);
  }

  function closeDetailModal() {
    setIsDetailOpen(false);
  }

  async function handleDelete(patientId) {
    const confirmed = window.confirm(`Delete patient #${patientId}?`);

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setMessage("");

      await deletePatient(patientId);

      setMessage(`Deleted patient #${patientId}`);

      if (selectedPatient?.id === patientId) {
        setSelectedPatient(null);
        setPredictionResult(null);
        setPatientPredictions([]);
        setIsDetailOpen(false);
      }

      await loadPatients();
    } catch (err) {
      setError("Cannot delete patient.");
    }
  }

  async function handlePredict(patient) {
    try {
      setError("");
      setMessage("");
      setPredictionResult(null);
      setSelectedPatient(patient);

      const result = await predictPatient(patient.id);
      setPredictionResult(result);

      const logs = await getPatientPredictions(patient.id);
      setPatientPredictions(logs);
    } catch (err) {
      setError(err.response?.data?.detail || "Cannot predict this patient.");
    }
  }

  async function handleViewPredictions(patient) {
    try {
      setError("");
      setSelectedPatient(patient);
      setPredictionResult(null);

      const logs = await getPatientPredictions(patient.id);
      setPatientPredictions(logs);
    } catch (err) {
      setError("Cannot load patient predictions.");
    }
  }

  const filteredPatients = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return patients
      .filter((patient) => {
        const matchesSearch =
          !normalizedSearch ||
          String(patient.id).includes(normalizedSearch) ||
          patient.age?.toLowerCase().includes(normalizedSearch) ||
          patient.race?.toLowerCase().includes(normalizedSearch) ||
          patient.gender?.toLowerCase().includes(normalizedSearch);

        const matchesGender =
          genderFilter === "all" || patient.gender === genderFilter;

        return matchesSearch && matchesGender;
      })
      .sort((left, right) => {
        if (sortBy === "oldest") {
          return new Date(left.created_at) - new Date(right.created_at);
        }

        if (sortBy === "stay-desc") {
          return (right.time_in_hospital || 0) - (left.time_in_hospital || 0);
        }

        return new Date(right.created_at) - new Date(left.created_at);
      });
  }, [genderFilter, patients, searchTerm, sortBy]);

  return (
    <section className="page">
      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="card patient-browser">
          <div className="table-header">
            <div>
              <h3>Patient Directory</h3>
              <p>
                Showing {filteredPatients.length} of {patients.length} patients.
              </p>
            </div>

            <button className="secondary-button" onClick={loadPatients}>
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>

          <div className="filter-bar">
            <label className="search-field">
              <span>Search</span>
              <div>
                <Search size={16} />
                <input
                  placeholder="Patient ID, age, race, gender"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                />
              </div>
            </label>

            <label>
              <span>Gender</span>
              <select
                value={genderFilter}
                onChange={(event) => setGenderFilter(event.target.value)}
              >
                <option value="all">All</option>
                <option value="Female">Female</option>
                <option value="Male">Male</option>
                <option value="Unknown/Invalid">Unknown</option>
              </select>
            </label>

            <label>
              <span>Sort</span>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="stay-desc">Longest stay</option>
              </select>
            </label>
          </div>

          <div className="patient-card-grid">
            {filteredPatients.map((patient) => (
              <button
                type="button"
                className={`patient-card ${
                  selectedPatient?.id === patient.id ? "active" : ""
                }`}
                key={patient.id}
                onClick={() => handleSelectPatient(patient)}
              >
                <div className="patient-card-top">
                  <div className="patient-avatar">
                    <UserRound size={20} />
                  </div>

                  <div>
                    <h4>Patient #{patient.id}</h4>
                    <span>{patient.gender} · {patient.age}</span>
                  </div>
                </div>

                <div className="patient-card-body">
                  <p>
                  <strong>Race or Ethnicity</strong>
                    <span>{patient.race || "N/A"}</span>
                  </p>

                  <p>
                    <strong>Length of Stay</strong>
                    <span>{patient.time_in_hospital} days</span>
                  </p>

                  <p>
                    <strong>Recorded Diagnoses</strong>
                    <span>{patient.number_diagnoses}</span>
                  </p>
                </div>

                <span className="view-hint">
                  <Eye size={14} />
                  View profile
                </span>
              </button>
            ))}

            {filteredPatients.length === 0 && (
              <div className="task-empty">No matching patients found.</div>
            )}
          </div>
      </div>

      {isDetailOpen && selectedPatient && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={closeDetailModal}
        >
          <div
            className="patient-detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="patient-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3 id="patient-detail-title">Patient #{selectedPatient.id}</h3>
                <p>
                  {selectedPatient.gender} · {selectedPatient.age} ·{" "}
                  {selectedPatient.race}
                </p>
              </div>

              <button
                type="button"
                className="icon-button"
                aria-label="Close patient details"
                onClick={closeDetailModal}
              >
                <X size={20} />
              </button>
            </div>

            <div className="patient-detail-grid">
              {patientDetailGroups.map((group) => (
                <div className="patient-detail-section" key={group.title}>
                  <h4>{group.title}</h4>

                  <div className="detail-list">
                    {group.fields.map((field) => (
                      <div key={field}>
                        <span>{formatFieldLabel(field)}</span>
                        <strong>{selectedPatient[field] ?? "N/A"}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="patient-actions modal-actions">
              <button
                className="secondary-button"
                onClick={() => handlePredict(selectedPatient)}
              >
                <Eye size={16} />
                Run prediction
              </button>

              <button
                className="secondary-button"
                onClick={() => handleViewPredictions(selectedPatient)}
              >
                <ClipboardList size={16} />
                Logs
              </button>

              <button
                className="danger-button"
                onClick={() => handleDelete(selectedPatient.id)}
              >
                <Trash2 size={16} />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {predictionResult && selectedPatient && (
        <div className="card result-card">
          <PredictionSummary result={predictionResult} />

          <h3>Patient #{selectedPatient.id} Prediction Details</h3>

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

      {patientPredictions.length > 0 && selectedPatient && (
        <div className="card">
          <h3>Prediction History for Patient #{selectedPatient.id}</h3>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Checked At</th>
                  <th>Prediction</th>
                  <th>Readmission Chance</th>
                  <th>Priority Level</th>
                  <th>Model</th>
                </tr>
              </thead>

              <tbody>
                {patientPredictions.map((log) => (
                  <tr key={log.id}>
                    <td>{log.id}</td>
                    <td>{new Date(log.created_at).toLocaleString()}</td>
                    <td>{formatPrediction(log.prediction)}</td>
                    <td>{formatProbability(log.readmission_probability)}</td>
                    <td>
                      <span className={`risk-pill ${log.risk_level}`}>
                        {
                          getRiskPresentation(
                            log.risk_level,
                            log.readmission_probability
                          ).label
                        }
                      </span>
                    </td>
                    <td>{log.model_name}</td>
                  </tr>
                ))}

                {patientPredictions.length === 0 && (
                  <tr>
                    <td colSpan="6" className="empty-cell">
                      No prediction logs for this patient.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
