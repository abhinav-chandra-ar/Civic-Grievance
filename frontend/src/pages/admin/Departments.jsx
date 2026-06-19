import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import DepartmentForm from "../../components/admin/DepartmentForm";
import {
  getDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
} from "../../services/departmentService";
import "../../auth.css";
import "../../styles/departments.css";

const DEPT_ICONS = {
  "KSEB":                  "bi-lightning-charge-fill",
  "KWA":                   "bi-droplet-fill",
  "PWD":                   "bi-signpost-2-fill",
  "Public Health":         "bi-hospital-fill",
  "Local Self Government": "bi-buildings-fill",
};

function deptIcon(name) {
  return DEPT_ICONS[name] ?? "bi-building-fill";
}

export default function Departments() {
  const navigate = useNavigate();

  const [departments, setDepartments]   = useState([]);
  const [loading, setLoading]           = useState(true);
  const [formLoading, setFormLoading]   = useState(false);
  const [error, setError]               = useState("");
  const [success, setSuccess]           = useState("");
  const [accessDenied, setAccessDenied] = useState(false);

  // showForm = true opens the add/edit modal
  const [showForm, setShowForm]       = useState(false);
  // editTarget = null → add mode; department object → edit mode
  const [editTarget, setEditTarget]   = useState(null);
  // deleteTarget = department to confirm deletion
  const [deleteTarget, setDeleteTarget] = useState(null);

  // On mount: verify the user is ADMIN, then load departments
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { navigate("/"); return; }

    axios
      .get("/api/me/", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (res.data.role !== "ADMIN") {
          setAccessDenied(true);
          setLoading(false);
        } else {
          fetchDepartments();
        }
      })
      .catch(() => navigate("/"));
  }, []);

  async function fetchDepartments() {
    setLoading(true);
    setError("");
    try {
      const data = await getDepartments();
      setDepartments(data);
    } catch {
      setError("Failed to load departments. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // Called by DepartmentForm on submit
  async function handleSave(formData) {
    setFormLoading(true);
    setError("");
    setSuccess("");
    try {
      if (editTarget) {
        await updateDepartment(editTarget.id, formData);
        setSuccess(`"${formData.name}" updated successfully.`);
      } else {
        await createDepartment(formData);
        setSuccess(`"${formData.name}" added successfully.`);
      }
      closeForm();
      await fetchDepartments();
    } catch (err) {
      // Show the first validation error from the backend, or a generic message
      const detail =
        err.response?.data?.name?.[0] ||
        err.response?.data?.detail ||
        "Operation failed. Please try again.";
      setError(detail);
    } finally {
      setFormLoading(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setError("");
    setSuccess("");
    try {
      await deleteDepartment(deleteTarget.id);
      setSuccess(`"${deleteTarget.name}" deleted successfully.`);
      setDeleteTarget(null);
      await fetchDepartments();
    } catch {
      setError("Failed to delete department. It may be in use.");
      setDeleteTarget(null);
    }
  }

  function openAdd() {
    setEditTarget(null);
    setError("");
    setSuccess("");
    setShowForm(true);
  }

  function openEdit(dept) {
    setEditTarget(dept);
    setError("");
    setSuccess("");
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditTarget(null);
  }

  // ── Access Denied screen ──────────────────────────────────────────────────
  if (accessDenied) {
    return (
      <div className="access-denied-page">
        <div className="access-denied-box">
          <i className="bi bi-shield-lock-fill text-danger" style={{ fontSize: 52 }} />
          <h3 className="mt-3 fw-bold">Access Denied</h3>
          <p className="text-muted">You do not have permission to view this page.</p>
          <button className="btn btn-primary mt-2" onClick={() => navigate("/dashboard")}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // ── Main page ─────────────────────────────────────────────────────────────
  return (
    <div className="admin-page">

      {/* Government header */}
      <header className="gov-header">
        <div className="gov-header-inner">
          <div className="gov-header-text">
            <span className="system-name">Civic Grievance Management System</span>
            <span className="system-tagline">Government of Kerala &nbsp;|&nbsp; Admin Panel</span>
          </div>
        </div>
      </header>

      {/* Admin navigation bar */}
      <nav className="admin-nav">
        <Link to="/dashboard" className="admin-nav-link">
          <i className="bi bi-speedometer2 me-1" />Dashboard
        </Link>
        <Link to="/admin/departments" className="admin-nav-link active">
          <i className="bi bi-building me-1" />Departments
        </Link>
      </nav>

      {/* Page content */}
      <main className="admin-content">
        <div className="admin-card">

          {/* Card header: title + Add button */}
          <div className="admin-card-header">
            <div>
              <h1 className="admin-title">Department Management</h1>
              <p className="admin-subtitle">
                Manage government departments registered in the system.
              </p>
            </div>
            <button className="btn-gov btn-gov-auto" onClick={openAdd}>
              <i className="bi bi-plus-lg me-1" />Add Department
            </button>
          </div>

          {/* Alert messages */}
          {error && (
            <div className="alert alert-danger d-flex align-items-center gap-2" role="alert">
              <i className="bi bi-exclamation-triangle-fill flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="alert alert-success d-flex align-items-center gap-2" role="alert">
              <i className="bi bi-check-circle-fill flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Table / loading / empty states */}
          {loading ? (
            <div className="admin-state-box">
              <div className="spinner-border text-primary" role="status" />
              <span className="mt-2 text-muted">Loading departments…</span>
            </div>
          ) : departments.length === 0 ? (
            <div className="admin-state-box">
              <i className="bi bi-building-slash" style={{ fontSize: 40, color: "#9ca3af" }} />
              <p className="text-muted mt-2">No departments found. Add one to get started.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table admin-table mb-0">
                <thead>
                  <tr>
                    <th style={{ width: 60 }}>#</th>
                    <th>Department Name</th>
                    <th>Description</th>
                    <th style={{ width: 160 }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((dept, index) => (
                    <tr key={dept.id}>
                      <td>{index + 1}</td>
                      <td className="dept-name">
                        <i className={`bi ${deptIcon(dept.name)} me-2`} />
                        {dept.name}
                      </td>
                      <td className="dept-desc">
                        {dept.description || <span className="text-muted">—</span>}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm btn-outline-primary me-2"
                          onClick={() => openEdit(dept)}
                        >
                          <i className="bi bi-pencil me-1" />Edit
                        </button>
                        <button
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => setDeleteTarget(dept)}
                        >
                          <i className="bi bi-trash me-1" />Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

        </div>
      </main>

      {/* Government footer */}
      <footer className="gov-footer">
        © 2025 Government of Kerala &nbsp;·&nbsp; Civic Grievance Management System &nbsp;·&nbsp; All rights reserved
      </footer>

      {/* ── Add / Edit modal ───────────────────────────────────────────── */}
      {showForm && (
        <div
          className="modal-overlay"
          onClick={(e) => e.target === e.currentTarget && closeForm()}
        >
          <div className="modal-box">
            {/* key forces DepartmentForm to remount when switching add↔edit */}
            <DepartmentForm
              key={editTarget ? editTarget.id : "new"}
              department={editTarget}
              onSave={handleSave}
              onCancel={closeForm}
              loading={formLoading}
            />
          </div>
        </div>
      )}

      {/* ── Delete confirmation modal ───────────────────────────────────── */}
      {deleteTarget && (
        <div
          className="modal-overlay"
          onClick={(e) => e.target === e.currentTarget && setDeleteTarget(null)}
        >
          <div className="modal-box text-center">
            <i
              className="bi bi-exclamation-triangle-fill text-danger"
              style={{ fontSize: 44 }}
            />
            <h5 className="mt-3 fw-bold">Confirm Deletion</h5>
            <p className="text-muted mt-2">
              Are you sure you want to delete{" "}
              <strong>{deleteTarget.name}</strong>?<br />
              This action cannot be undone.
            </p>
            <div className="d-flex justify-content-center gap-2 mt-4">
              <button
                className="btn btn-secondary"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                <i className="bi bi-trash me-1" />Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
