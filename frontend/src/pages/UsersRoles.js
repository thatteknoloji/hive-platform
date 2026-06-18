import React, { useEffect, useState } from "react";
import API from "../api";

const ROLES = ["super_admin", "admin", "seo_manager", "editor", "viewer"];

export default function UsersRoles() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ email: "", name: "", role: "viewer", password: "hive123" });
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const res = await API.get("/api/users");
      setItems(res.data?.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Users yüklenemedi");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createUser = async () => {
    try {
      await API.post("/api/users", form);
      setForm({ email: "", name: "", role: "viewer", password: "hive123" });
      load();
    } catch (e) {
      setError(e?.response?.data?.detail || "Kullanıcı eklenemedi");
    }
  };

  return (
    <div className="modul-card">
      <h2>Users & Roles</h2>
      {error && <div className="hata">{error}</div>}
      <div className="form-row" style={{ marginBottom: 16 }}>
        <input placeholder="E-posta" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input placeholder="İsim" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <input placeholder="Şifre" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button className="btn btn-primary" onClick={createUser}>Kullanıcı Ekle</button>
      </div>
      <table className="sites-table">
        <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Last Login</th></tr></thead>
        <tbody>
          {items.map((u) => (
            <tr key={u.user_id}>
              <td>{u.email}</td>
              <td>{u.name}</td>
              <td>{u.role}</td>
              <td>{u.status}</td>
              <td>{u.last_login_at || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
