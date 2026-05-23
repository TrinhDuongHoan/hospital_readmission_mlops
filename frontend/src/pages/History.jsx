import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getPredictionLogs } from "../services/api";
import {
  formatPrediction,
  formatProbability,
  getRiskPresentation,
} from "../utils/clinicalDisplay";

export default function History() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  async function loadLogs() {
    try {
      setError("");
      const data = await getPredictionLogs(100);
      setLogs(data);
    } catch (err) {
      setError("Cannot load prediction history.");
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <section className="page">
      <div className="card">
        <div className="table-header">
          <div>
            <h3>Clinical Prediction History</h3>
            <p>Recent readmission checks across patient profiles.</p>
          </div>

          <button className="secondary-button" onClick={loadLogs}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {error && <div className="alert error">{error}</div>}

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
                <th>Age</th>
                <th>Gender</th>
              </tr>
            </thead>

            <tbody>
              {logs.map((log) => (
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
                  <td>{log.request_json?.age || "N/A"}</td>
                  <td>{log.request_json?.gender || "N/A"}</td>
                </tr>
              ))}

              {logs.length === 0 && (
                <tr>
                  <td colSpan="8" className="empty-cell">
                    No prediction logs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
