import { useState, useEffect } from "react";

export default function DepartmentForm({ department, onSave, onCancel, loading }) {
  const [form, setForm] = useState({ name: "", description: "" });

  // Populate form when editing, clear it when adding
  useEffect(() => {
    if (department) {
      setForm({ name: department.name, description: department.description });
    } else {
      setForm({ name: "", description: "" });
    }
  }, [department]);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSave(form);
  }

  const isEdit = Boolean(department);

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h5 className="modal-form-title">
        <i className={`bi ${isEdit ? "bi-pencil-square" : "bi-plus-circle"} me-2`} />
        {isEdit ? "Edit Department" : "Add Department"}
      </h5>

      <div className="mb-3">
        <label htmlFor="dept-name" className="form-label fw-semibold">
          Department Name <span className="text-danger">*</span>
        </label>
        <input
          id="dept-name"
          type="text"
          name="name"
          className="form-control"
          value={form.name}
          onChange={handleChange}
          placeholder="e.g. KSEB"
          required
          autoFocus
        />
      </div>

      <div className="mb-4">
        <label htmlFor="dept-desc" className="form-label fw-semibold">
          Description
        </label>
        <textarea
          id="dept-desc"
          name="description"
          className="form-control"
          value={form.description}
          onChange={handleChange}
          placeholder="Brief description of this department"
          rows={3}
        />
      </div>

      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={loading}>
          Cancel
        </button>
        <button type="submit" className="btn-gov btn-gov-auto" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true" />
              Saving…
            </>
          ) : (
            isEdit ? "Update Department" : "Add Department"
          )}
        </button>
      </div>
    </form>
  );
}
