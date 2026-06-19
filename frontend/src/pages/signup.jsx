import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import "../auth.css";

const ROLES = [
  { value: "CITIZEN",        label: "Citizen" },
  { value: "JUNIOR_OFFICER", label: "Junior Officer" },
  { value: "SENIOR_OFFICER", label: "Senior Officer" },
  { value: "ADMIN",          label: "Admin" },
];

const Emblem = () => (
  <svg className="gov-emblem" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <circle cx="26" cy="26" r="25" stroke="#c8a84b" strokeWidth="2" fill="#1a3a6b" />
    <circle cx="26" cy="26" r="10" stroke="#c8a84b" strokeWidth="1.5" fill="none" />
    {[0,30,60,90,120,150,180,210,240,270,300,330,360].map((deg, i) => {
      const rad = (deg * Math.PI) / 180;
      const x1 = 26 + 10 * Math.cos(rad);
      const y1 = 26 + 10 * Math.sin(rad);
      const x2 = 26 + 14 * Math.cos(rad);
      const y2 = 26 + 14 * Math.sin(rad);
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#c8a84b" strokeWidth="1.2" />;
    })}
    <text x="26" y="44" textAnchor="middle" fill="#c8a84b" fontSize="6" fontWeight="bold" fontFamily="serif">
      KERALA
    </text>
  </svg>
);

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email:     "",
    full_name: "",
    phone:     "",
    role:      "CITIZEN",
    password:  "",
  });
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage(null);
    setLoading(true);
    try {
      await axios.post("/api/signup/", form);
      setMessage({ type: "success", text: "Account created successfully! Redirecting to login…" });
      setTimeout(() => navigate("/"), 1500);
    } catch (err) {
      if (!err.response) {
        setMessage({ type: "error", text: "Cannot reach server. Make sure the Django backend is running." });
      } else {
        const data = err.response.data;
        const firstKey = data && Object.keys(data)[0];
        const val = firstKey && data[firstKey];
        const text = val
          ? `${firstKey}: ${Array.isArray(val) ? val[0] : val}`
          : "Registration failed. Please check your details.";
        setMessage({ type: "error", text });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      {/* ── Government header ── */}
      <header className="gov-header">
        <div className="gov-header-inner">
          <Emblem />
          <div className="gov-header-text">
            <span className="system-name">Civic Grievance Management System</span>
            <span className="system-tagline">Government of Kerala &nbsp;|&nbsp; Public Grievance Portal</span>
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="auth-content">
        <div className="auth-card">
          <div className="auth-card-header">
            <h2>
              <i className="bi bi-person-plus-fill me-2" aria-hidden="true"></i>
              New User Registration
            </h2>
          </div>

          <div className="auth-card-body">
            {message && (
              <div
                className={`alert ${message.type === "success" ? "alert-success" : "alert-danger"} d-flex align-items-start gap-2`}
                role="alert"
              >
                <i
                  className={`bi ${message.type === "success" ? "bi-check-circle-fill" : "bi-exclamation-triangle-fill"} mt-1 flex-shrink-0`}
                  aria-hidden="true"
                ></i>
                <span>{message.text}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="mb-3">
                <label htmlFor="full_name" className="form-label">
                  Full Name <span className="text-danger">*</span>
                </label>
                <input
                  id="full_name"
                  type="text"
                  name="full_name"
                  className="form-control"
                  value={form.full_name}
                  onChange={handleChange}
                  placeholder="As per official records"
                  autoComplete="name"
                  required
                />
              </div>

              <div className="mb-3">
                <label htmlFor="email" className="form-label">
                  Email Address <span className="text-danger">*</span>
                </label>
                <input
                  id="email"
                  type="email"
                  name="email"
                  className="form-control"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="Enter a valid email address"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="mb-3">
                <label htmlFor="phone" className="form-label">
                  Mobile Number
                </label>
                <input
                  id="phone"
                  type="tel"
                  name="phone"
                  className="form-control"
                  value={form.phone}
                  onChange={handleChange}
                  placeholder="e.g. 9876543210"
                  autoComplete="tel"
                />
              </div>

              <div className="mb-3">
                <label htmlFor="role" className="form-label">
                  User Category <span className="text-danger">*</span>
                </label>
                <select
                  id="role"
                  name="role"
                  className="form-select"
                  value={form.role}
                  onChange={handleChange}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
                <div className="form-text" style={{ fontSize: "12px", color: "#6b7280" }}>
                  Select the category that applies to your role in the system.
                </div>
              </div>

              <div className="mb-4">
                <label htmlFor="password" className="form-label">
                  Password <span className="text-danger">*</span>
                </label>
                <input
                  id="password"
                  type="password"
                  name="password"
                  className="form-control"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Create a strong password"
                  autoComplete="new-password"
                  required
                />
              </div>

              <button type="submit" className="btn-gov" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Registering…
                  </>
                ) : (
                  <>
                    <i className="bi bi-person-check-fill me-2" aria-hidden="true"></i>
                    Register Account
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="auth-footer-link">
            Already registered?&nbsp;
            <Link to="/">Login to your account</Link>
          </div>
        </div>

        <p className="mt-3 text-center" style={{ fontSize: "12px", color: "#6b7280" }}>
          This is a secure government portal. Unauthorised access is prohibited.
        </p>
      </main>

      {/* ── Footer ── */}
      <footer className="gov-footer">
        © 2025 Government of Kerala &nbsp;·&nbsp; Civic Grievance Management System &nbsp;·&nbsp; All rights reserved
      </footer>
    </div>
  );
}
