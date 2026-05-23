import { useState } from "react";
import { Activity, Lock } from "lucide-react";
import { login } from "../services/api";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("doctor01");
  const [password, setPassword] = useState("doctor123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      const data = await login(username, password);

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      onLogin(data.user);
    } catch (err) {
      setError("Login failed. Please check username or password.");
    } finally {
      setLoading(false);
    }
  }

  function fillDoctor() {
    setUsername("doctor01");
    setPassword("doctor123");
  }

  function fillAdmin() {
    setUsername("admin01");
    setPassword("admin123");
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <Activity size={28} />
        </div>

        <h1>Hospital Readmission MLOps</h1>
        <p>Login as Doctor or Admin to access the system.</p>

        {error && <div className="alert error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <label>
            <span>Username</span>
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="doctor01"
            />
          </label>

          <label>
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="doctor123"
            />
          </label>

          <button className="primary-button login-button" disabled={loading}>
            <Lock size={16} />
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="login-demo">
          <button type="button" onClick={fillDoctor}>
            Doctor demo
          </button>

          <button type="button" onClick={fillAdmin}>
            Admin demo
          </button>
        </div>

        <div className="login-hint">
          <p>
            Doctor: <strong>doctor01 / doctor123</strong>
          </p>
          <p>
            Admin: <strong>admin01 / admin123</strong>
          </p>
        </div>
      </div>
    </div>
  );
}