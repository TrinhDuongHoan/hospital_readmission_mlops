import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export async function login(username, password) {
  const response = await api.post("/auth/login", {
    username,
    password,
  });

  return response.data;
}

export async function getMe() {
  const response = await api.get("/auth/me");
  return response.data;
}

export async function getUsers(limit = 100) {
  const response = await api.get(`/users?limit=${limit}`);
  return response.data;
}

export async function createUser(payload) {
  const response = await api.post("/users", payload);
  return response.data;
}

export async function updateUser(userId, payload) {
  const response = await api.put(`/users/${userId}`, payload);
  return response.data;
}

export async function setUserActive(userId, isActive) {
  const response = await api.patch(`/users/${userId}/status`, {
    is_active: isActive,
  });
  return response.data;
}

export async function getDashboardStats() {
  const response = await api.get("/dashboard-stats");
  return response.data;
}

export async function getPredictionLogs(limit = 50) {
  const response = await api.get(`/prediction-logs?limit=${limit}`);
  return response.data;
}

export async function predictReadmission(payload) {
  const response = await api.post("/predict", payload);
  return response.data;
}

export async function getModelInfo() {
  const response = await api.get("/model-info");
  return response.data;
}

export async function getPipelines() {
  const response = await api.get("/mlops/pipelines");
  return response.data;
}

export async function triggerPipeline(dagId) {
  const response = await api.post(`/mlops/pipelines/${dagId}/trigger`);
  return response.data;
}

export async function getPatients() {
  const response = await api.get("/patients");
  return response.data;
}

export async function getHighRiskPatients(limit = 100) {
  const response = await api.get(`/patients/high-risk?limit=${limit}`);
  return response.data;
}

export async function createPatient(payload) {
  const response = await api.post("/patients", payload);
  return response.data;
}

export async function updatePatient(patientId, payload) {
  const response = await api.put(`/patients/${patientId}`, payload);
  return response.data;
}

export async function deletePatient(patientId) {
  const response = await api.delete(`/patients/${patientId}`);
  return response.data;
}

export async function predictPatient(patientId) {
  const response = await api.post(`/patients/${patientId}/predict`);
  return response.data;
}

export async function getPatientPredictions(patientId) {
  const response = await api.get(`/patients/${patientId}/predictions`);
  return response.data;
}
