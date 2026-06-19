import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
    <div className="auth-container">
      <h1>Welcome back</h1>
      <p className="subtitle">Sign in to your account</p>

      {error && <div className="msg error">{error}</div>}

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
          {loading ? "Signing in…" : "Sign In"}
        </button>
      </form>

      <div className="auth-link">
        Don't have an account? <Link to="/signup">Sign up</Link>
      </div>
    </div>
  );
}
