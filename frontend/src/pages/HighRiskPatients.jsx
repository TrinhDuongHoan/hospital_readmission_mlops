import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, UserRound } from "lucide-react";
import { getHighRiskPatients } from "../services/api";
import {
  formatProbability,
  getRiskPresentation,
} from "../utils/clinicalDisplay";

function formatDate(value) {
  if (!value) return "N/A";

  return new Date(value).toLocaleString();
}

export default function HighRiskPatients() {
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadHighRiskPatients() {
    try {
      setLoading(true);
      setError("");

      const data = await getHighRiskPatients(100);
      setPatients(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Cannot load high-risk patients.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHighRiskPatients();
  }, []);

  return (
    <section className="page">
      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <div className="table-header">
          <div>
            <h3>Readmission Priority List</h3>
            <p>Patients are sorted by the latest predicted readmission chance.</p>
          </div>

          <button className="secondary-button" onClick={loadHighRiskPatients}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading high-risk patients...</div>
        ) : (
          <div className="priority-list">
            {patients.map((patient, index) => {
              const probability = patient.readmission_probability || 0;
              const risk = getRiskPresentation(patient.risk_level, probability);

              return (
                <div className="priority-card" key={patient.id}>
                  <div className="priority-rank">{index + 1}</div>

                  <div className="priority-main">
                    <div className="patient-card-top">
                      <div className="patient-avatar warning-avatar">
                        <UserRound size={20} />
                      </div>

                      <div>
                        <h4>Patient #{patient.id}</h4>
                        <span>
                          {patient.gender} · {patient.age} · {patient.race}
                        </span>
                      </div>
                    </div>

                    <div className="priority-meta">
                      <div>
                        <span>Readmission Chance</span>
                        <strong>{formatProbability(probability)}</strong>
                      </div>

                      <div>
                        <span>Priority</span>
                        <strong className={`risk ${risk.level}`}>
                          {risk.label}
                        </strong>
                      </div>

                      <div>
                        <span>Last Checked</span>
                        <strong>{formatDate(patient.predicted_at)}</strong>
                      </div>

                      <div>
                        <span>Length of Stay</span>
                        <strong>{patient.time_in_hospital} days</strong>
                      </div>

                      <div>
                        <span>Recorded Diagnoses</span>
                        <strong>{patient.number_diagnoses}</strong>
                      </div>
                    </div>
                  </div>

                  <div className={`priority-alert ${risk.level}`}>
                    <AlertTriangle size={18} />
                    {risk.action}
                  </div>
                </div>
              );
            })}

            {patients.length === 0 && (
              <div className="task-empty">No predicted patients found.</div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
