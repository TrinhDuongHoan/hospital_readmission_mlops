import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const grafanaDashboardPath =
  "/tools/grafana/d/hospital-readmission-mlops/hospital-readmission-mlops?orgId=1&from=now-1h&to=now&refresh=10s&kiosk&var-cache=mlops-v3";

function removeFrameHeaders(proxy) {
  proxy.on("proxyRes", (proxyRes) => {
    delete proxyRes.headers["x-frame-options"];
    delete proxyRes.headers["content-security-policy"];
    delete proxyRes.headers["content-security-policy-report-only"];
  });
}

function configureGrafanaProxy(proxy) {
  removeFrameHeaders(proxy);

  const setForwardedHeaders = (proxyReq, req) => {
    const host = req.headers.host;

    if (host) {
      proxyReq.setHeader("X-Forwarded-Host", host);
      proxyReq.setHeader("X-Forwarded-Proto", "http");
    }
  };

  proxy.on("proxyReq", setForwardedHeaders);
  proxy.on("proxyReqWs", setForwardedHeaders);
}

function grafanaHomeRedirect() {
  return {
    name: "grafana-home-redirect",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === "/tools/grafana" || req.url === "/tools/grafana/") {
          res.statusCode = 302;
          res.setHeader("Cache-Control", "no-store");
          res.setHeader("Location", grafanaDashboardPath);
          res.end();
          return;
        }

        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [grafanaHomeRedirect(), react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/tools/grafana": {
        target: "http://grafana:3000",
        changeOrigin: false,
        ws: true,
        configure: configureGrafanaProxy,
      },
      "/tools/prometheus": {
        target: "http://prometheus:9090",
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/tools\/prometheus/, "") || "/",
        configure: removeFrameHeaders,
      },
      "/tools/mlflow": {
        target: "http://mlflow:5000",
        changeOrigin: true,
        ws: true,
        configure: removeFrameHeaders,
      },
      "/tools/airflow": {
        target: "http://airflow-webserver:8080",
        changeOrigin: true,
        ws: true,
        configure: removeFrameHeaders,
      },
    },
  },
});
