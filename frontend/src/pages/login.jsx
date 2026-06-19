import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import "../auth.css";

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

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const googleBtnRef = useRef(null);

  async function handleGoogleCredential(response) {
    setError("");
    setLoading(true);
    try {
      const res = await axios.post("/api/auth/google/", { id_token: response.credential });
      localStorage.setItem("access_token", res.data.access);
      localStorage.setItem("refresh_token", res.data.refresh);
      navigate("/dashboard");
    } catch (err) {
      if (!err.response) {
        setError("Cannot reach server. Make sure the Django backend is running.");
      } else {
        setError(err.response.data?.error || "Google login failed.");
      }
      setLoading(false);
    }
  }

  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      if (!window.google || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
      });
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: "outline",
        size: "large",
        width: googleBtnRef.current.offsetWidth,
      });
    };
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, []);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await axios.post("/api/login/", form);
      localStorage.setItem("access_token", res.data.access);
      localStorage.setItem("refresh_token", res.data.refresh);
      navigate("/dashboard");
    } catch (err) {
      if (!err.response) {
        setError("Cannot reach server. Make sure the Django backend is running.");
      } else {
        setError(err.response.data?.detail || "Invalid email or password.");
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
              <i className="bi bi-person-lock me-2" aria-hidden="true"></i>
              Citizen and Officer Login
            </h2>
          </div>

          <div className="auth-card-body">
            {error && (
              <div className="alert alert-danger d-flex align-items-start gap-2" role="alert">
                <i className="bi bi-exclamation-triangle-fill mt-1 flex-shrink-0" aria-hidden="true"></i>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
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
                  placeholder="Enter registered email"
                  autoComplete="email"
                  required
                />
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
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  required
                />
              </div>

              <button type="submit" className="btn-gov" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Signing in…
                  </>
                ) : (
                  <>
                    <i className="bi bi-box-arrow-in-right me-2" aria-hidden="true"></i>
                    Login to Portal
                  </>
                )}
              </button>
            </form>

            {/* ── OR divider ── */}
            <div style={{ display: "flex", alignItems: "center", margin: "20px 0 16px" }}>
              <div style={{ flex: 1, height: 1, background: "#d1d5db" }} />
              <span style={{ margin: "0 12px", fontSize: 12, color: "#9ca3af", fontWeight: 600 }}>OR</span>
              <div style={{ flex: 1, height: 1, background: "#d1d5db" }} />
            </div>

            {/* ── Google Sign-In button ── */}
            <div ref={googleBtnRef} style={{ width: "100%" }} />
          </div>

          <div className="auth-footer-link">
            New user?&nbsp;
            <Link to="/signup">Register for an account</Link>
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
