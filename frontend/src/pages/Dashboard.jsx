import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Brain,
  Database,
  ExternalLink,
  Gauge,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { getDashboardStats, getModelInfo } from "../services/api";

const grafanaDashboardUrl =
  import.meta.env.VITE_GRAFANA_URL ||
  "/tools/grafana/d/hospital-readmission-mlops/hospital-readmission-mlops?orgId=1&from=now-1h&to=now&refresh=10s&kiosk&var-cache=mlops-v3";

const grafanaOpenUrl =
  import.meta.env.VITE_GRAFANA_HOME_URL ||
  "/tools/grafana/d/hospital-readmission-mlops/hospital-readmission-mlops?orgId=1&from=now-1h&to=now&refresh=10s&kiosk&var-cache=mlops-v3";

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

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [error, setError] = useState("");
  const [frameVersion, setFrameVersion] = useState(Date.now());

  const grafanaFrameUrl = useMemo(() => {
    const separator = grafanaDashboardUrl.includes("?") ? "&" : "?";
    return `${grafanaDashboardUrl}${separator}frameVersion=${frameVersion}`;
  }, [frameVersion]);

  async function loadData() {
    try {
      setError("");

      const [statsData, modelData] = await Promise.all([
        getDashboardStats(),
        getModelInfo(),
      ]);

      setStats(statsData);
      setModelInfo(modelData);
    } catch (err) {
      setError("Cannot load dashboard data. Please check FastAPI service.");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (error) {
    return (
      <section className="page">
        <div className="alert error">{error}</div>
      </section>
    );
  }

  if (!stats) {
    return (
      <section className="page">
        <div className="loading">Loading dashboard...</div>
      </section>
    );
  }

  const totalRisk =
    stats.low_risk_count + stats.medium_risk_count + stats.high_risk_count || 1;

  const lowPercent = (stats.low_risk_count / totalRisk) * 100;
  const mediumPercent = (stats.medium_risk_count / totalRisk) * 100;
  const highPercent = (stats.high_risk_count / totalRisk) * 100;

  return (
    <section className="page">
      <div className="grid stats-grid">
        <StatCard
          title="Total Predictions"
          value={stats.total_predictions}
          subtitle="Prediction requests"
          icon={Database}
        />

        <StatCard
          title="Average Probability"
          value={`${(stats.avg_probability * 100).toFixed(2)}%`}
          subtitle="Average readmission risk"
          icon={TrendingUp}
        />

        <StatCard
          title="Positive Cases"
          value={stats.positive_predictions}
          subtitle="Predicted readmission"
          icon={AlertTriangle}
        />

        <StatCard
          title="Current Model"
          value="Production"
          subtitle={modelInfo?.model_name || "HospitalReadmissionModel"}
          icon={Brain}
        />
      </div>

      <div className="grid two-columns">
        <div className="card">
          <h3>Risk Distribution</h3>

          <div className="risk-bars">
            <div>
              <div className="risk-bar-label">
                <span>Low Risk</span>
                <strong>{stats.low_risk_count}</strong>
              </div>
              <div className="bar-bg">
                <div className="bar low" style={{ width: `${lowPercent}%` }} />
              </div>
            </div>

            <div>
              <div className="risk-bar-label">
                <span>Medium Risk</span>
                <strong>{stats.medium_risk_count}</strong>
              </div>
              <div className="bar-bg">
                <div
                  className="bar medium"
                  style={{ width: `${mediumPercent}%` }}
                />
              </div>
            </div>

            <div>
              <div className="risk-bar-label">
                <span>High Risk</span>
                <strong>{stats.high_risk_count}</strong>
              </div>
              <div className="bar-bg">
                <div className="bar high" style={{ width: `${highPercent}%` }} />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Model Information</h3>

          <div className="model-box">
            <p>Model name</p>
            <strong>{modelInfo?.model_name || "HospitalReadmissionModel"}</strong>

            <p>Model version</p>
            <strong>{modelInfo?.model_version || "N/A"}</strong>

            <p>Model URI</p>
            <code>{modelInfo?.model_uri || "N/A"}</code>
          </div>
        </div>
      </div>

      <div className="card observability-shell dashboard-monitoring">
        <div className="observability-header">
          <div>
            <div className="observability-title">
              <Gauge size={22} />
              <h3>Grafana Monitoring</h3>
            </div>
            <p>Production metrics and inference health</p>
          </div>

          <div className="observability-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={() => setFrameVersion(Date.now())}
              title="Reload frame"
            >
              <RefreshCw size={16} />
            </button>

            <a
              className="secondary-button"
              href={grafanaOpenUrl}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink size={16} />
              Open
            </a>
          </div>
        </div>

        <div className="observability-frame-wrap dashboard-frame-wrap">
          <iframe
            key={`grafana-${frameVersion}`}
            src={grafanaFrameUrl}
            title="Grafana monitoring dashboard"
          />

          <div className="frame-fallback">
            <span>Grafana is loading...</span>
          </div>
        </div>
      </div>
    </section>
  );
}
