import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/");
      return;
    }
    axios
      .get("/api/me/", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => setUser(res.data))
      .catch(() => {
        setError("Session expired. Please log in again.");
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setTimeout(() => navigate("/"), 2000);
      });
  }, [navigate]);

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/");
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="msg error">{error}</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="dashboard-container">
        <p style={{ color: "#6b7280" }}>Loading…</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <h1>Dashboard</h1>

      <div className="profile-card">
        <div className="profile-row">
          <span className="label">Name</span>
          <span className="value">{user.full_name}</span>
        </div>
        <div className="profile-row">
          <span className="label">Email</span>
          <span className="value">{user.email}</span>
        </div>
        <div className="profile-row">
          <span className="label">Phone</span>
          <span className="value">{user.phone || "—"}</span>
        </div>
        <div className="profile-row">
          <span className="label">Role</span>
          <span className="value">
            <span className="role-badge">{user.role}</span>
          </span>
        </div>
      </div>

      {user.role === "ADMIN" && (
        <div className="quick-actions">
          <p className="quick-actions-label">Admin Quick Actions</p>
          <button className="btn-action" onClick={() => navigate("/admin/departments")}>
            Manage Departments
          </button>
          <button className="btn-action" disabled>
            Officer Management <span className="coming-soon">Coming Soon</span>
          </button>
          <button className="btn-action" disabled>
            Reports <span className="coming-soon">Coming Soon</span>
          </button>
        </div>
      )}

      <button className="btn-logout" onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}
