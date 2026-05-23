import { useEffect, useState } from "react";
import { AlertTriangle, FilePlus2, ShieldAlert, Users } from "lucide-react";
import { getHighRiskPatients, getPatients } from "../services/api";
import {
  formatProbability,
  getRiskPresentation,
} from "../utils/clinicalDisplay";

function StatCard({ title, value, subtitle, icon: Icon }) {
  return (
    <div className="card stat-card">
      <div className="stat-icon">
        <Icon size={22} />
      </div>
      <p className="stat-title">{title}</p>
      <h3>{value}</h3>
      <span>{subtitle}</span>
    </div>
  );
}

export default function DoctorOverview({ onNavigate }) {
  const [patients, setPatients] = useState([]);
  const [highRiskPatients, setHighRiskPatients] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadOverview() {
    try {
      setLoading(true);
      setError("");

      const [patientsData, highRiskData] = await Promise.all([
        getPatients(),
        getHighRiskPatients(5),
      ]);

      setPatients(patientsData);
      setHighRiskPatients(highRiskData);
    } catch (err) {
      setError("Cannot load doctor overview.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  const highRiskCount = highRiskPatients.filter(
    (patient) => patient.risk_level === "high"
  ).length;

  return (
    <section className="page">
      {error && <div className="alert error">{error}</div>}

      <div className="grid stats-grid">
        <StatCard
          title="My Patients"
          value={patients.length}
          subtitle="Stored patient profiles"
          icon={Users}
        />

        <StatCard
          title="High Risk"
          value={highRiskCount}
          subtitle="Need priority follow-up"
          icon={ShieldAlert}
        />

        <StatCard
          title="Latest Predictions"
          value={highRiskPatients.length}
          subtitle="Patients with prediction logs"
          icon={AlertTriangle}
        />

        <div className="card action-card">
          <div className="stat-icon">
            <FilePlus2 size={22} />
          </div>
          <p className="stat-title">Next Action</p>
          <h3>Create Patient</h3>
          <span>Add a profile and run prediction in one flow.</span>
          <button
            type="button"
            className="primary-button"
            onClick={() => onNavigate("create-patient")}
          >
            Create Profile
          </button>
        </div>
      </div>

      <div className="grid two-columns">
        <div className="card">
          <div className="table-header">
            <div>
              <h3>Priority Patients</h3>
              <p>Latest patients sorted by predicted readmission chance.</p>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() => onNavigate("high-risk")}
            >
              View All
            </button>
          </div>

          {loading ? (
            <div className="loading">Loading priority patients...</div>
          ) : (
            <div className="compact-list">
              {highRiskPatients.slice(0, 5).map((patient) => (
                <div className="compact-row" key={patient.id}>
                  <div>
                    <strong>Patient #{patient.id}</strong>
                    <span>
                      {patient.gender} · {patient.age} · {patient.race}
                    </span>
                  </div>

                  <span
                    className={`risk-pill ${patient.risk_level || "low"}`}
                    title={
                      getRiskPresentation(
                        patient.risk_level,
                        patient.readmission_probability
                      ).label
                    }
                  >
                    {formatProbability(patient.readmission_probability)}
                  </span>
                </div>
              ))}

              {highRiskPatients.length === 0 && (
                <div className="task-empty">No prediction logs yet.</div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <h3>Workflow</h3>
          <div className="workflow-list">
            <button type="button" onClick={() => onNavigate("create-patient")}>
              <strong>1. Create patient profile</strong>
              <span>Save demographics, visit details and clinical activity.</span>
            </button>

            <button type="button" onClick={() => onNavigate("patients")}>
              <strong>2. Review patient database</strong>
              <span>Open patient details, rerun predictions and view logs.</span>
            </button>

            <button type="button" onClick={() => onNavigate("high-risk")}>
              <strong>3. Follow up high-risk patients</strong>
              <span>Prioritize cases with elevated readmission chance.</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
