import React, { useCallback, useEffect, useState } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveBtn,
  HiveEmptyState,
  HiveField,
  HiveInput,
  HivePanel,
  HiveSelect,
  HiveTable,
  HiveToast,
  HiveSkeleton,
  HiveLabelWithTip,
} from "../components/HiveModuleUI";
import HiveApiErrorCard from "../components/HiveApiErrorCard";

const ROLES = [
  { id: "super_admin", label: "Super Admin", tip: "Tüm modüller ve kullanıcı yönetimi" },
  { id: "admin", label: "Admin", tip: "Campaign, Authority, Publisher, Projects" },
  { id: "seo_manager", label: "SEO Manager", tip: "Mission Control, Citation, Rank" },
  { id: "editor", label: "Editor", tip: "Publisher ve içerik modülleri" },
  { id: "viewer", label: "Viewer", tip: "Salt okunur — Mission Control" },
];

const ROLE_CONCEPTS = Object.fromEntries(
  ROLES.map((r) => [r.id, { label: r.label, text: r.tip }]),
);

function apiError(e) {
  return e?.response?.data?.detail || e?.message || "İşlem başarısız";
}

export default function UsersRoles({ onNavigate }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [form, setForm] = useState({ email: "", name: "", role: "viewer", password: "" });

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get("/api/users");
      setItems(res.data?.items || []);
    } catch (e) {
      setError(apiError(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const createUser = async () => {
    if (!form.email.trim() || !form.name.trim()) {
      setError("E-posta ve isim zorunludur.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await API.post("/api/users", form);
      setForm({ email: "", name: "", role: "viewer", password: "" });
      setToast("Kullanıcı oluşturuldu.");
      await load();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: "email", label: "E-posta" },
    { key: "name", label: "İsim" },
    { key: "role", label: "Rol" },
    { key: "status", label: "Durum" },
    { key: "last_login_at", label: "Son Giriş", render: (row) => row.last_login_at || "—" },
  ];

  return (
    <HiveShell
      title="Users & Roles"
      subtitle="RBAC — ekip üyeleri ve modül izinleri"
      actions={(
        <HiveBtn variant="secondary" size="sm" onClick={() => onNavigate?.("hive_academy")}>
          Academy Rehberi
        </HiveBtn>
      )}
    >
      <HiveToast message={toast} onClose={() => setToast("")} />
      {error && <HiveApiErrorCard errorInfo={error} />}

      <HivePanel title="Yeni kullanıcı">
        <div className="hive-form-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))" }}>
          <HiveField label="E-posta">
            <HiveInput
              placeholder="user@firma.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </HiveField>
          <HiveField label="İsim">
            <HiveInput
              placeholder="Ad Soyad"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </HiveField>
          <HiveField label={<HiveLabelWithTip label="Rol" conceptKey={form.role} concepts={ROLE_CONCEPTS} />}>
            <HiveSelect value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {ROLES.map((r) => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </HiveSelect>
          </HiveField>
          <HiveField label="Geçici şifre" title="İlk girişten sonra değiştirilmeli">
            <HiveInput
              type="password"
              placeholder="Min. 6 karakter"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </HiveField>
        </div>
        <HiveBtn onClick={createUser} disabled={saving}>
          {saving ? "Kaydediliyor…" : "Kullanıcı Ekle"}
        </HiveBtn>
      </HivePanel>

      <HivePanel title="Kullanıcılar">
        {loading ? (
          <HiveSkeleton lines={5} />
        ) : items.length === 0 ? (
          <HiveEmptyState
            icon="👥"
            title="Henüz kullanıcı yok"
            description="İlk ekip üyesini yukarıdaki formdan ekleyin."
            why="Demo için en az bir viewer ve bir seo_manager hesabı önerilir."
            academyLabel="Users Rehberi"
            onAcademy={() => onNavigate?.("hive_academy")}
          />
        ) : (
          <HiveTable columns={columns} rows={items} />
        )}
      </HivePanel>

      <HiveAlert type="info">
        İzinler <code>panel_identity.py</code> ve <code>rbac.js</code> ile uygulanır.
        Menüde görünmeyen modül = rol yetkisi yok.
      </HiveAlert>
    </HiveShell>
  );
}
