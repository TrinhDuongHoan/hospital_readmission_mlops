import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  ClipboardList,
  FilePlus2,
  GitBranch,
  LayoutDashboard,
  LineChart,
  LogOut,
  ShieldAlert,
  UserCog,
  Users,
} from "lucide-react";

import CreatePatient from "./pages/CreatePatient";
import Dashboard from "./pages/Dashboard";
import DoctorOverview from "./pages/DoctorOverview";
import HighRiskPatients from "./pages/HighRiskPatients";
import History from "./pages/History";
import Login from "./pages/Login";
import Observability from "./pages/Observability";
import Patients from "./pages/Patients";
import UsersPage from "./pages/Users";

function getTabsByRole(role) {
  if (role === "admin") {
    return [
      {
        key: "dashboard",
        label: "Dashboard",
        icon: BarChart3,
      },
      {
        key: "history",
        label: "Prediction Logs",
        icon: ClipboardList,
      },
      {
        key: "users",
        label: "Users",
        icon: UserCog,
      },
      {
        key: "prometheus",
        label: "Metrics",
        icon: LineChart,
      },
      {
        key: "mlflow",
        label: "Model Runs",
        icon: BarChart3,
      },
      {
        key: "airflow",
        label: "Pipelines",
        icon: GitBranch,
      },
    ];
  }

  return [
    {
      key: "overview",
      label: "Overview",
      icon: LayoutDashboard,
    },
    {
      key: "create-patient",
      label: "Create Patient",
      icon: FilePlus2,
    },
    {
      key: "patients",
      label: "Patients",
      icon: Users,
    },
    {
      key: "high-risk",
      label: "High Risk",
      icon: ShieldAlert,
    },
  ];
}

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    const savedUser = localStorage.getItem("user");

    if (savedUser) {
      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      setActiveTab(parsedUser.role === "admin" ? "dashboard" : "overview");
    }
  }, []);

  function handleLogin(loggedInUser) {
    setUser(loggedInUser);
    setActiveTab(loggedInUser.role === "admin" ? "dashboard" : "overview");
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
    setActiveTab("overview");
  }

  function renderPage() {
    if (activeTab === "dashboard") {
      return <Dashboard />;
    }

    if (activeTab === "history") {
      return <History />;
    }

    if (activeTab === "users") {
      return <UsersPage currentUser={user} />;
    }

    if (["prometheus", "mlflow", "airflow"].includes(activeTab)) {
      return <Observability serviceKey={activeTab} />;
    }

    if (activeTab === "create-patient") {
      return <CreatePatient />;
    }

    if (activeTab === "overview") {
      return <DoctorOverview onNavigate={setActiveTab} />;
    }

    if (activeTab === "high-risk") {
      return <HighRiskPatients />;
    }

    return <Patients />;
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  const tabs = getTabsByRole(user.role);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo">
            <Activity size={24} />
          </div>
          <div>
            <h1>Readmission MLOps</h1>
            <p>{user.role === "admin" ? "Admin Portal" : "Doctor Portal"}</p>
          </div>
        </div>

        <div className="user-box">
          <strong>{user.full_name || user.username}</strong>
          <span>{user.role}</span>
        </div>

        <nav className="nav">
          {tabs.map((tab) => {
            const Icon = tab.icon;

            return (
              <button
                key={tab.key}
                className={`nav-item ${activeTab === tab.key ? "active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <button className="logout-button" onClick={handleLogout}>
          <LogOut size={18} />
          Logout
        </button>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h2>
              {user.role === "admin"
                ? "Admin Monitoring Console"
                : "Doctor Patient Management"}
            </h2>
            <p>
              {user.role === "admin"
                ? "Monitor predictions, dashboards, and MLOps services."
                : "Create patient records and run readmission predictions."}
            </p>
          </div>
        </header>

        {renderPage()}
      </main>
    </div>
  );
}
