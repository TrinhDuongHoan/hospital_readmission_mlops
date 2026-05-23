import {
  Activity,
  BarChart3,
  ExternalLink,
  Gauge,
  GitBranch,
  LineChart,
  RefreshCw,
} from "lucide-react";
import { useMemo, useState } from "react";

const services = {
  grafana: {
    key: "grafana",
    name: "System Dashboards",
    subtitle: "Grafana monitoring views",
    icon: Gauge,
    url:
      import.meta.env.VITE_GRAFANA_URL ||
      "/tools/grafana/d/hospital-readmission-mlops/hospital-readmission-mlops?orgId=1&from=now-1h&to=now&refresh=10s&kiosk&var-cache=mlops-v3",
    openUrl:
      import.meta.env.VITE_GRAFANA_HOME_URL ||
      "/tools/grafana/d/hospital-readmission-mlops/hospital-readmission-mlops?orgId=1&from=now-1h&to=now&refresh=10s&kiosk&var-cache=mlops-v3",
  },
  prometheus: {
    key: "prometheus",
    name: "System Metrics",
    subtitle: "Prometheus metrics explorer",
    icon: LineChart,
    url:
      import.meta.env.VITE_PROMETHEUS_URL ||
      "/tools/prometheus/query?g0.expr=sum%20by%20(source)%20(rate(prediction_requests_total%5B5m%5D))&g0.tab=0",
    openUrl: import.meta.env.VITE_PROMETHEUS_HOME_URL || "/tools/prometheus/query",
  },
  mlflow: {
    key: "mlflow",
    name: "Model Runs",
    subtitle: "MLflow experiments and model versions",
    icon: BarChart3,
    url: import.meta.env.VITE_MLFLOW_EMBED_URL || "/tools/mlflow/",
    openUrl: import.meta.env.VITE_MLFLOW_URL || "/tools/mlflow/",
  },
  airflow: {
    key: "airflow",
    name: "Pipelines",
    subtitle: "Airflow DAGs and scheduled workflows",
    icon: GitBranch,
    url: import.meta.env.VITE_AIRFLOW_EMBED_URL || "/tools/airflow/",
    openUrl: import.meta.env.VITE_AIRFLOW_URL || "/tools/airflow/",
  },
};

export default function Observability({ serviceKey }) {
  const activeService = services[serviceKey] || services.grafana;
  const ActiveIcon = activeService.icon;
  const [frameVersion, setFrameVersion] = useState(Date.now());
  const frameUrl = useMemo(() => {
    const separator = activeService.url.includes("?") ? "&" : "?";
    return `${activeService.url}${separator}frameVersion=${frameVersion}`;
  }, [activeService.url, frameVersion]);

  return (
    <section className="page observability-page">
      <div className="card observability-shell">
        <div className="observability-header">
          <div>
            <div className="observability-title">
              <ActiveIcon size={22} />
              <h3>{activeService.name}</h3>
            </div>
            <p>{activeService.subtitle}</p>
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
              href={activeService.openUrl}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink size={16} />
              Open
            </a>
          </div>
        </div>

        <div className="observability-frame-wrap">
          <iframe
            key={`${activeService.key}-${frameVersion}`}
            src={frameUrl}
            title={`${activeService.name} embedded view`}
          />

          <div className="frame-fallback">
            <Activity size={18} />
            <span>{activeService.name} is loading...</span>
          </div>
        </div>
      </div>
    </section>
  );
}
