import axios from "axios";

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return { Authorization: `Bearer ${token}` };
}

export async function getDepartments() {
  const res = await axios.get("/api/departments/", { headers: authHeaders() });
  return res.data;
}

export async function createDepartment(data) {
  const res = await axios.post("/api/departments/", data, { headers: authHeaders() });
  return res.data;
}

export async function updateDepartment(id, data) {
  const res = await axios.put(`/api/departments/${id}/`, data, { headers: authHeaders() });
  return res.data;
}

export async function deleteDepartment(id) {
  await axios.delete(`/api/departments/${id}/`, { headers: authHeaders() });
}
