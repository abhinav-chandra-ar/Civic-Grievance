import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";

const ROLES = [
  { value: "CITIZEN", label: "Citizen" },
  { value: "JUNIOR_OFFICER", label: "Junior Officer" },
  { value: "SENIOR_OFFICER", label: "Senior Officer" },
  { value: "ADMIN", label: "Admin" },
];

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    phone: "",
    role: "CITIZEN",
    password: "",
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
      setMessage({ type: "success", text: "Account created! Redirecting to login…" });
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
          : "Signup failed. Please check your details.";
        setMessage({ type: "error", text });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <h1>Create account</h1>
      <p className="subtitle">Join the civic grievance platform</p>

      {message && <div className={`msg ${message.type}`}>{message.text}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            placeholder="you@example.com"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="full_name">Full Name</label>
          <input
            id="full_name"
            type="text"
            name="full_name"
            value={form.full_name}
            onChange={handleChange}
            placeholder="Jane Doe"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="phone">Phone</label>
          <input
            id="phone"
            type="tel"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            placeholder="+91 9876543210"
          />
        </div>

        <div className="form-group">
          <label htmlFor="role">Role</label>
          <select id="role" name="role" value={form.role} onChange={handleChange}>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            placeholder="••••••••"
            required
          />
        </div>

        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Creating account…" : "Sign Up"}
        </button>
      </form>

      <div className="auth-link">
        Already have an account? <Link to="/">Sign in</Link>
      </div>
    </div>
  );
}
