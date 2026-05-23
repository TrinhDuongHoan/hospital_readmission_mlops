import { useEffect, useState } from "react";
import { Play, RefreshCw, Workflow } from "lucide-react";
import { getPipelines, triggerPipeline } from "../services/api";

function formatDate(value) {
  if (!value) return "N/A";

  return new Date(value).toLocaleString();
}

function getStateClass(state) {
  if (state === "success") return "success";
  if (state === "running") return "running";
  if (state === "failed") return "failed";
  if (state === "queued") return "queued";

  return "unknown";
}

export default function Pipelines() {
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [triggeringDag, setTriggeringDag] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadPipelines() {
    try {
      setLoading(true);
      setError("");

      const data = await getPipelines();
      setPipelines(data.pipelines || []);
    } catch (err) {
      setError("Cannot load MLOps pipeline status.");
    } finally {
      setLoading(false);
    }
  }

  async function handleTrigger(dagId) {
    try {
      setTriggeringDag(dagId);
      setMessage("");
      setError("");

      await triggerPipeline(dagId);

      setMessage(`Triggered DAG: ${dagId}`);

      setTimeout(() => {
        loadPipelines();
      }, 1500);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || `Cannot trigger DAG: ${dagId}`);
    } finally {
      setTriggeringDag("");
    }
  }

  useEffect(() => {
    loadPipelines();
  }, []);

  return (
    <section className="page">
      <div className="card">
        <div className="table-header">
          <div>
            <h3>MLOps Pipeline Control Center</h3>
            <p>
              Trigger and monitor Airflow DAGs directly from the application UI.
            </p>
          </div>

          <button className="secondary-button" onClick={loadPipelines}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {message && <div className="alert success">{message}</div>}
        {error && <div className="alert error">{error}</div>}

        {loading ? (
          <div className="loading">Loading pipelines...</div>
        ) : (
          <div className="pipeline-grid">
            {pipelines.map((pipeline) => {
              const latestRun = pipeline.latest_run;
              const state = pipeline.state || "no_runs";

              return (
                <div className="pipeline-card" key={pipeline.dag_id}>
                  <div className="pipeline-icon">
                    <Workflow size={24} />
                  </div>

                  <div className="pipeline-content">
                    <div className="pipeline-title-row">
                      <h4>{pipeline.name}</h4>
                      <span className={`state-pill ${getStateClass(state)}`}>
                        {state}
                      </span>
                    </div>

                    <p>{pipeline.description}</p>

                    <div className="pipeline-meta">
                      <div>
                        <span>DAG ID</span>
                        <strong>{pipeline.dag_id}</strong>
                      </div>

                      <div>
                        <span>Last Run</span>
                        <strong>{formatDate(latestRun?.start_date)}</strong>
                      </div>

                      <div>
                        <span>Run ID</span>
                        <code>{latestRun?.dag_run_id || "N/A"}</code>
                      </div>
                    </div>

                    <div className="task-list">
                      <h5>Tasks in DAG</h5>

                      {pipeline.tasks && pipeline.tasks.length > 0 ? (
                        pipeline.tasks.map((task) => (
                          <div className="task-row" key={task.task_id}>
                            <div>
                              <strong>{task.task_id}</strong>
                              <span>
                                {task.start_date
                                  ? `Started: ${formatDate(task.start_date)}`
                                  : "Not started"}
                              </span>
                            </div>

                            <span className={`state-pill ${getStateClass(task.state)}`}>
                              {task.state || "none"}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="task-empty">No task instances found for latest run.</div>
                      )}
                    </div>

                    <button
                      className="primary-button"
                      disabled={triggeringDag === pipeline.dag_id}
                      onClick={() => handleTrigger(pipeline.dag_id)}
                    >
                      <Play size={16} />
                      {triggeringDag === pipeline.dag_id ? "Triggering..." : "Run Pipeline"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
