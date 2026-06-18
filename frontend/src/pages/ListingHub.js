import React, { useState, useEffect, useCallback, useRef } from "react";
import API from "../api";
import {
  HiveShell,
  HiveAlert,
  HiveToolbar,
  HiveTabs,
  HivePanel,
  HiveStatGrid,
  HiveFormRow,
  HiveField,
  HiveSelect,
  HiveInput,
  HiveBtn,
  HiveTable,
  HiveCard,
  HiveCode,
  HiveCheck,
} from "../components/HiveModuleUI";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "listings", label: "İlanlar" },
  { id: "editor", label: "İlan Editörü" },
  { id: "media", label: "Medya" },
  { id: "import", label: "Toplu İçe Aktar" },
  { id: "bulkmedia", label: "Toplu Medya" },
  { id: "seo", label: "SEO & GEO" },
  { id: "publish", label: "Yayın & Vitrin" },
];

const STATUSES = ["draft", "review", "active", "passive", "expired", "rejected"];
const PAYMENTS = ["cash", "bank_transfer", "eft", "credit_card", "door_payment", "other"];
const WIZARD_STEPS = [
  "Temel", "Kategori", "Konum", "İletişim", "Fiyat", "Fotoğraf", "Video", "Vitrin", "SEO", "Kalite", "Yayın",
];

const emptyForm = () => ({
  title: "",
  short_description: "",
  description: "",
  main_category: "",
  sub_category: "",
  categories: "",
  services: "",
  country: "Türkiye",
  city: "",
  district: "",
  neighborhood: "",
  address: "",
  latitude: "",
  longitude: "",
  phone: "",
  whatsapp: "",
  email: "",
  website: "",
  price: "",
  currency: "TRY",
  price_hidden: false,
  negotiable: false,
  payment_methods: [],
  video_url: "",
  show_on_home: false,
  home_section: "",
  category_showcase: false,
  city_showcase: false,
  featured: false,
  vip: false,
  sponsored: false,
  slider: false,
  status: "draft",
});

function apiError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (typeof d === "object" && d) return JSON.stringify(d);
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return e?.message || "Bilinmeyen hata";
}

function statusLabel(s) {
  const map = {
    draft: "Taslak",
    review: "İnceleme",
    active: "Aktif",
    passive: "Pasif",
    expired: "Süresi doldu",
    rejected: "Reddedildi",
  };
  return map[s] || s;
}

export default function ListingHub() {
  const [tab, setTab] = useState("dashboard");
  const [health, setHealth] = useState(null);
  const [listings, setListings] = useState([]);
  const [stats, setStats] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(emptyForm());
  const [wizardStep, setWizardStep] = useState(0);
  const [filterStatus, setFilterStatus] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [importPreview, setImportPreview] = useState(null);
  const [importJobId, setImportJobId] = useState("");
  const [importFormat, setImportFormat] = useState("csv");
  const fileRef = useRef(null);
  const zipRef = useRef(null);
  const mediaRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [h, res] = await Promise.all([
        API.get("/api/listing-hub/health"),
        API.get("/api/listings", { params: { status: filterStatus || undefined, search: search || undefined, limit: 200 } }),
      ]);
      setHealth(h.data);
      setListings(res.data.listings || []);
      setStats(res.data.stats || null);
      setError("");
    } catch (e) {
      setError(apiError(e));
    }
  }, [filterStatus, search]);

  useEffect(() => { refresh(); }, [refresh]);

  const loadListing = async (id) => {
    const res = await API.get(`/api/listing/${id}`);
    const l = res.data.listing;
    setSelected(l);
    setForm({
      ...emptyForm(),
      title: l.title || "",
      short_description: l.short_description || "",
      description: l.description || "",
      main_category: l.main_category || "",
      sub_category: l.sub_category || "",
      categories: (l.categories || []).join(", "),
      services: (l.services || []).join(", "),
      country: l.country || "Türkiye",
      city: l.city || "",
      district: l.district || "",
      neighborhood: l.neighborhood || "",
      address: l.address || "",
      latitude: l.latitude ?? "",
      longitude: l.longitude ?? "",
      phone: l.phone || "",
      whatsapp: l.whatsapp || "",
      email: l.email || "",
      website: l.website || "",
      price: l.price ?? "",
      currency: l.currency || "TRY",
      price_hidden: !!l.price_hidden,
      negotiable: !!l.negotiable,
      payment_methods: l.payment_methods || [],
      video_url: l.video_url || "",
      show_on_home: !!l.show_on_home,
      home_section: l.home_section || "",
      category_showcase: !!l.category_showcase,
      city_showcase: !!l.city_showcase,
      featured: !!l.featured,
      vip: !!l.vip,
      sponsored: !!l.sponsored,
      slider: !!l.slider,
      status: l.status || "draft",
    });
  };

  const payloadFromForm = () => ({
    ...form,
    categories: form.categories.split(",").map((s) => s.trim()).filter(Boolean),
    services: form.services.split(",").map((s) => s.trim()).filter(Boolean),
    price: form.price === "" ? null : Number(form.price),
    latitude: form.latitude === "" ? null : Number(form.latitude),
    longitude: form.longitude === "" ? null : Number(form.longitude),
  });

  const startNewListing = () => {
    setSelected(null);
    setForm(emptyForm());
    setWizardStep(0);
    setTab("editor");
  };

  const openEditor = async (id) => {
    await loadListing(id);
    setWizardStep(0);
    setTab("editor");
  };

  const handleCreate = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("/api/listing/create", payloadFromForm());
      setMessage(`İlan oluşturuldu: ${res.data.listing.ilan_no}`);
      setSelected(res.data.listing);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      await API.put(`/api/listing/update/${selected.id}`, payloadFromForm());
      setMessage("İlan güncellendi");
      await refresh();
      await loadListing(selected.id);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (id) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`/api/listing/publish/${id || selected.id}`);
      setMessage(`Yayınlandı: ${res.data.listing?.wp_url || res.data.listing?.canonical || "OK"}`);
      await refresh();
      if (id || selected?.id) await loadListing(id || selected.id);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleUnpublish = async (id) => {
    setLoading(true);
    try {
      await API.post(`/api/listing/unpublish/${id}`);
      setMessage("Yayından kaldırıldı");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSeo = async () => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      const res = await API.post(`/api/listing/generate-seo/${selected.id}`);
      setSelected(res.data.listing);
      setMessage("SEO üretildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDesc = async () => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      const res = await API.post(`/api/listing/generate-description/${selected.id}`, { use_llm: true });
      const l = res.data.listing;
      setSelected(l);
      setForm((f) => ({ ...f, short_description: l.short_description, description: l.description }));
      setMessage("Açıklama üretildi");
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleQualityGate = async () => {
    if (!selected?.id) return;
    setLoading(true);
    try {
      const res = await API.post(`/api/listing/run-quality-gate/${selected.id}`);
      setSelected(res.data.listing);
      setMessage(`Quality Gate: SEO ${res.data.listing.seo_score} · GEO ${res.data.listing.geo_score}`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleImportPreview = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setLoading(true);
    try {
      const res = await API.post(
        `/api/listing/import-preview?format=${importFormat}`,
        fd,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setImportPreview(res.data);
      setImportJobId(res.data.job_id || "");
      setMessage(`Önizleme: ${res.data.valid_count} geçerli, ${res.data.error_count} hatalı`);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleImportCommit = async () => {
    if (!importJobId) return;
    setLoading(true);
    try {
      const res = await API.post("/api/listing/import-commit", { job_id: importJobId });
      setMessage(`${res.data.created} ilan draft olarak oluşturuldu`);
      setImportPreview(null);
      setImportJobId("");
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleZipUpload = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setLoading(true);
    try {
      const res = await API.post("/api/listing/bulk-media", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(`ZIP: ${res.data.matched} fotoğraf eşleştirildi`);
      await refresh();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const handleMediaUpload = async (file, setCover = false) => {
    if (!file || !selected?.id) return;
    const fd = new FormData();
    fd.append("file", file);
    setLoading(true);
    try {
      await API.post(`/api/listing/upload-media/${selected.id}?set_cover=${setCover}`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(setCover ? "Kapak fotoğrafı yüklendi" : "Fotoğraf yüklendi");
      await loadListing(selected.id);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const togglePayment = (p) => {
    setForm((f) => ({
      ...f,
      payment_methods: f.payment_methods.includes(p)
        ? f.payment_methods.filter((x) => x !== p)
        : [...f.payment_methods, p],
    }));
  };

  const sm = stats?.stats || stats || {};
  const wpOk = health?.wordpress_connected;

  const listingRows = listings.map((l) => ({
    id: l.id,
    ilan_no: l.ilan_no,
    title: l.title || "—",
    location: l.city || l.district || "—",
    status: statusLabel(l.status),
    scores: `${l.seo_score || 0} / ${l.geo_score || 0}`,
    raw: l,
  }));

  const renderWizardFields = () => {
    const step = WIZARD_STEPS[wizardStep];
    if (step === "Temel") {
      return (
        <>
          <HiveField label="Başlık"><HiveInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></HiveField>
          <HiveField label="Kısa Açıklama"><textarea className="hm-input" rows={3} value={form.short_description} onChange={(e) => setForm({ ...form, short_description: e.target.value })} /></HiveField>
          <HiveField label="Detaylı Açıklama"><textarea className="hm-input" rows={5} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></HiveField>
        </>
      );
    }
    if (step === "Kategori") {
      return (
        <>
          <HiveField label="Ana Kategori"><HiveInput value={form.main_category} onChange={(e) => setForm({ ...form, main_category: e.target.value })} /></HiveField>
          <HiveField label="Alt Kategori"><HiveInput value={form.sub_category} onChange={(e) => setForm({ ...form, sub_category: e.target.value })} /></HiveField>
          <HiveField label="Çoklu Kategori (virgülle)"><HiveInput value={form.categories} onChange={(e) => setForm({ ...form, categories: e.target.value })} /></HiveField>
          <HiveField label="Hizmetler (virgülle)"><HiveInput value={form.services} onChange={(e) => setForm({ ...form, services: e.target.value })} /></HiveField>
        </>
      );
    }
    if (step === "Konum") {
      return (
        <HiveFormRow>
          <HiveField label="Şehir"><HiveInput value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></HiveField>
          <HiveField label="İlçe"><HiveInput value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} /></HiveField>
          <HiveField label="Mahalle"><HiveInput value={form.neighborhood} onChange={(e) => setForm({ ...form, neighborhood: e.target.value })} /></HiveField>
          <HiveField label="Adres"><HiveInput value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></HiveField>
          <HiveField label="Enlem"><HiveInput value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} /></HiveField>
          <HiveField label="Boylam"><HiveInput value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} /></HiveField>
        </HiveFormRow>
      );
    }
    if (step === "İletişim") {
      return (
        <HiveFormRow>
          <HiveField label="Telefon"><HiveInput value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></HiveField>
          <HiveField label="WhatsApp"><HiveInput value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} /></HiveField>
          <HiveField label="E-posta"><HiveInput value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></HiveField>
          <HiveField label="Web sitesi"><HiveInput value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} /></HiveField>
        </HiveFormRow>
      );
    }
    if (step === "Fiyat") {
      return (
        <>
          <HiveFormRow>
            <HiveField label="Fiyat"><HiveInput type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></HiveField>
            <HiveField label="Para Birimi">
              <HiveSelect value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option value="TRY">TRY</option>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
              </HiveSelect>
            </HiveField>
          </HiveFormRow>
          <HiveCheck label="Fiyat gizli" checked={form.price_hidden} onChange={(e) => setForm({ ...form, price_hidden: e.target.checked })} />
          <HiveCheck label="Pazarlık yapılabilir" checked={form.negotiable} onChange={(e) => setForm({ ...form, negotiable: e.target.checked })} />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {PAYMENTS.map((p) => (
              <HiveCheck key={p} label={p} checked={form.payment_methods.includes(p)} onChange={() => togglePayment(p)} />
            ))}
          </div>
        </>
      );
    }
    if (step === "Fotoğraf") {
      return (
        <div>
          <p className="hm-empty">Fotoğrafları Medya sekmesinden yükleyin. Önce ilanı kaydedin.</p>
          {selected?.gallery_images?.length > 0 && (
            <ul style={{ fontSize: "0.85rem", lineHeight: 1.8 }}>
              {selected.gallery_images.map((g) => (
                <li key={g.id}>{g.filename}{g.id === selected.cover_image ? " (kapak)" : ""}</li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    if (step === "Video") {
      return (
        <>
          <HiveField label="YouTube URL (boşsa varsayılan video)"><HiveInput value={form.video_url} onChange={(e) => setForm({ ...form, video_url: e.target.value })} /></HiveField>
          {selected?.video_embed_url && <p className="hm-empty">Embed: {selected.video_embed_url}</p>}
          {health?.default_video_url && <p className="hm-empty">Varsayılan: {health.default_video_url}</p>}
        </>
      );
    }
    if (step === "Vitrin") {
      return (
        <div style={{ display: "grid", gap: 6 }}>
          {[
            ["show_on_home", "Ana sayfa"], ["category_showcase", "Kategori vitrini"],
            ["city_showcase", "Şehir vitrini"], ["featured", "Öne çıkan"],
            ["vip", "VIP"], ["sponsored", "Sponsorlu"], ["slider", "Slider"],
          ].map(([key, label]) => (
            <HiveCheck key={key} label={label} checked={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />
          ))}
          <HiveField label="Ana sayfa bölümü"><HiveInput value={form.home_section} onChange={(e) => setForm({ ...form, home_section: e.target.value })} /></HiveField>
        </div>
      );
    }
    if (step === "SEO" && selected) {
      return (
        <div>
          <HiveBtn onClick={handleGenerateSeo} disabled={loading}>SEO Üret</HiveBtn>
          <dl style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
            <dt>Slug</dt><dd>{selected.slug || "—"}</dd>
            <dt>Meta Title</dt><dd>{selected.meta_title || "—"}</dd>
            <dt>Target Keyword</dt><dd>{selected.target_keyword || "—"}</dd>
          </dl>
        </div>
      );
    }
    if (step === "Kalite" && selected) {
      return (
        <div>
          <HiveToolbar>
            <HiveBtn variant="secondary" onClick={handleGenerateDesc} disabled={loading}>AI Açıklama</HiveBtn>
            <HiveBtn onClick={handleQualityGate} disabled={loading}>Quality Gate</HiveBtn>
          </HiveToolbar>
          <HiveStatGrid items={[
            ["SEO", selected.seo_score ?? "—"],
            ["GEO", selected.geo_score ?? "—"],
            ["AEO", selected.aeo_score ?? "—"],
            ["Yayın", selected.publish_allowed ? "✓" : "✗"],
          ]} />
          {selected.publish_blockers?.length > 0 && (
            <HiveAlert type="warn">Bloklayıcılar: {selected.publish_blockers.join(", ")}</HiveAlert>
          )}
        </div>
      );
    }
    if (step === "Yayın" && selected) {
      return (
        <div>
          <HiveBtn onClick={() => handlePublish()} disabled={loading}>WordPress'e Yayınla</HiveBtn>
          <p className="hm-empty" style={{ marginTop: 8 }}>
            WP: {selected.wp_status || "—"}
            {selected.wp_url && <> · <a href={selected.wp_url} target="_blank" rel="noreferrer">canlı sayfa</a></>}
          </p>
        </div>
      );
    }
    return <p className="hm-empty">Önce ilanı kaydedin, sonra ilgili adıma geçin.</p>;
  };

  return (
    <HiveShell
      title="📦 Listing Hub"
      subtitle="Ana ilan yayınlama motoru — CRUD, medya, SEO/GEO/AEO, toplu işlem, WordPress"
    >
      <HiveToolbar>
        <span className={`hm-badge hm-badge-${wpOk ? "low" : "high"}`} style={{ alignSelf: "center" }}>
          WordPress: {wpOk ? "✓ bağlı" : "yerel mod"}
        </span>
        <HiveBtn onClick={startNewListing}>+ Yeni İlan</HiveBtn>
        <HiveBtn variant="secondary" onClick={() => setTab("import")}>Toplu İçe Aktar</HiveBtn>
        <HiveBtn variant="ghost" onClick={refresh} disabled={loading}>Yenile</HiveBtn>
      </HiveToolbar>

      {message && <HiveAlert type="ok">{message}</HiveAlert>}
      {error && <HiveAlert type="err">{error}</HiveAlert>}

      <HiveStatGrid items={[
        ["Toplam", sm.total ?? 0],
        ["Aktif", sm.active ?? 0],
        ["Draft", sm.draft ?? 0],
        ["Yayına Hazır", sm.publish_allowed ?? 0],
        ["Video Eksik", sm.video_missing ?? 0],
        ["Harita Eksik", sm.map_missing ?? 0],
        ["Kapak Eksik", sm.cover_missing ?? 0],
        ["SEO Fail", sm.seo_fail ?? 0],
      ]} />

      <HiveTabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "dashboard" && (
        <HivePanel>
          <HiveFormRow>
            <HiveCard title="Hızlı İşlemler">
              <HiveToolbar>
                <HiveBtn onClick={startNewListing}>Yeni İlan Oluştur</HiveBtn>
                <HiveBtn variant="secondary" onClick={() => setTab("import")}>CSV/Excel İçe Aktar</HiveBtn>
                <HiveBtn variant="secondary" onClick={() => setTab("bulkmedia")}>Toplu Medya ZIP</HiveBtn>
              </HiveToolbar>
            </HiveCard>
            <HiveCard title="Kalite Uyarıları" meta="Yayın öncesi kontrol">
              <HiveStatGrid items={[
                ["Video eksik", sm.video_missing ?? 0],
                ["Harita eksik", sm.map_missing ?? 0],
                ["Kapak eksik", sm.cover_missing ?? 0],
                ["SEO fail", sm.seo_fail ?? 0],
              ]} />
            </HiveCard>
          </HiveFormRow>
          <h4 style={{ margin: "1rem 0 0.5rem" }}>Son İlanlar</h4>
          <HiveTable
            columns={[
              { key: "ilan_no", label: "No" },
              { key: "title", label: "Başlık" },
              { key: "location", label: "Konum" },
              { key: "status", label: "Durum" },
              { key: "scores", label: "SEO/GEO" },
              {
                key: "actions",
                label: "",
                render: (row) => (
                  <HiveBtn size="sm" variant="secondary" onClick={() => openEditor(row.id)}>Düzenle</HiveBtn>
                ),
              },
            ]}
            rows={listingRows.slice(0, 8)}
            emptyText="Henüz ilan yok — Yeni İlan ile başlayın"
          />
        </HivePanel>
      )}

      {tab === "listings" && (
        <HivePanel>
          <HiveToolbar>
            <HiveField label="Durum">
              <HiveSelect value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <option value="">Tüm durumlar</option>
                {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
              </HiveSelect>
            </HiveField>
            <HiveField label="Ara">
              <HiveInput placeholder="Başlık, şehir…" value={search} onChange={(e) => setSearch(e.target.value)} />
            </HiveField>
            <HiveBtn variant="ghost" onClick={refresh}>Filtrele</HiveBtn>
          </HiveToolbar>
          <HiveTable
            columns={[
              { key: "ilan_no", label: "No" },
              { key: "title", label: "Başlık" },
              { key: "location", label: "Şehir" },
              { key: "status", label: "Durum" },
              { key: "scores", label: "Skor" },
              {
                key: "actions",
                label: "İşlem",
                render: (row) => (
                  <span style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <HiveBtn size="sm" variant="secondary" onClick={() => openEditor(row.id)}>Düzenle</HiveBtn>
                    {row.raw.status !== "active" ? (
                      <HiveBtn size="sm" onClick={() => handlePublish(row.id)}>Yayınla</HiveBtn>
                    ) : (
                      <HiveBtn size="sm" variant="ghost" onClick={() => handleUnpublish(row.id)}>Kaldır</HiveBtn>
                    )}
                  </span>
                ),
              },
            ]}
            rows={listingRows}
            emptyText="İlan bulunamadı"
          />
        </HivePanel>
      )}

      {tab === "editor" && (
        <HivePanel>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            {WIZARD_STEPS.map((s, i) => (
              <HiveBtn
                key={s}
                size="sm"
                variant={wizardStep === i ? "primary" : "secondary"}
                onClick={() => setWizardStep(i)}
              >
                {i + 1}. {s}
              </HiveBtn>
            ))}
          </div>
          <HiveCard
            title={selected ? `Düzenle: ${selected.ilan_no}` : "Yeni İlan"}
            meta={selected ? `ID ${selected.id}` : "Sihirbaz adımlarını tamamlayın"}
          >
            <div style={{ display: "grid", gap: "0.75rem" }}>{renderWizardFields()}</div>
            <HiveToolbar>
              <HiveBtn variant="ghost" disabled={wizardStep === 0} onClick={() => setWizardStep((s) => s - 1)}>Geri</HiveBtn>
              <HiveBtn variant="secondary" disabled={wizardStep >= WIZARD_STEPS.length - 1} onClick={() => setWizardStep((s) => s + 1)}>İleri</HiveBtn>
              <HiveBtn onClick={selected ? handleUpdate : handleCreate} disabled={loading}>
                {selected ? "Güncelle" : "Oluştur"}
              </HiveBtn>
              {selected && (
                <HiveBtn variant="secondary" onClick={() => { setSelected(null); setForm(emptyForm()); setWizardStep(0); }}>
                  Yeni ilana geç
                </HiveBtn>
              )}
            </HiveToolbar>
          </HiveCard>
        </HivePanel>
      )}

      {tab === "import" && (
        <HivePanel>
          <HiveCard title="Toplu İçe Aktar" meta="CSV, JSON, XML veya Excel">
            <HiveField label="Format">
              <HiveSelect value={importFormat} onChange={(e) => setImportFormat(e.target.value)}>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xml">XML</option>
                <option value="xlsx">Excel</option>
              </HiveSelect>
            </HiveField>
            <input type="file" ref={fileRef} accept=".csv,.json,.xml,.xlsx" className="hm-input" style={{ marginTop: 8 }} />
            <HiveToolbar>
              <HiveBtn variant="secondary" onClick={() => handleImportPreview(fileRef.current?.files?.[0])} disabled={loading}>Önizleme</HiveBtn>
              <HiveBtn onClick={handleImportCommit} disabled={loading || !importJobId}>Commit (Draft)</HiveBtn>
            </HiveToolbar>
            {importPreview && (
              <HiveCode>{JSON.stringify({
                preview: importPreview.preview?.slice(0, 5),
                errors: importPreview.errors?.slice(0, 5),
              }, null, 2)}</HiveCode>
            )}
          </HiveCard>
        </HivePanel>
      )}

      {tab === "bulkmedia" && (
        <HivePanel>
          <HiveCard title="Toplu Medya ZIP" meta="10001_1.jpg · 10001_cover.jpg · ILANNO-10001-1.png">
            <input type="file" accept=".zip" ref={zipRef} className="hm-input" />
            <HiveBtn onClick={() => handleZipUpload(zipRef.current?.files?.[0])} disabled={loading} style={{ marginTop: 8 }}>
              ZIP Yükle ve Eşleştir
            </HiveBtn>
          </HiveCard>
        </HivePanel>
      )}

      {tab === "media" && (
        <HivePanel>
          <HiveCard
            title="Medya Yöneticisi"
            meta={selected ? `${selected.ilan_no} — ${selected.title}` : "Önce İlan Editörü'nden bir ilan seçin"}
          >
            {!selected && (
              <HiveAlert type="warn">Medya yüklemek için bir ilan düzenleyin.</HiveAlert>
            )}
            <input
              type="file"
              accept="image/*"
              ref={mediaRef}
              className="hm-input"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleMediaUpload(f, false); }}
            />
            <HiveToolbar>
              <HiveBtn
                variant="secondary"
                disabled={!selected}
                onClick={() => { const f = mediaRef.current?.files?.[0]; if (f) handleMediaUpload(f, true); }}
              >
                Kapak Olarak Yükle
              </HiveBtn>
            </HiveToolbar>
            {selected?.gallery_images?.length > 0 && (
              <ul style={{ marginTop: "1rem", fontSize: "0.85rem", lineHeight: 1.8 }}>
                {selected.gallery_images.map((g) => (
                  <li key={g.id}>{g.filename}{g.id === selected.cover_image ? " ★ kapak" : ""}</li>
                ))}
              </ul>
            )}
            {selected?.map_embed_url && (
              <p className="hm-empty">Harita embed hazır</p>
            )}
          </HiveCard>
        </HivePanel>
      )}

      {tab === "seo" && (
        <HivePanel>
          {selected ? (
            <HiveCard title={`SEO & GEO — ${selected.ilan_no}`} meta={selected.title}>
              <HiveToolbar>
                <HiveBtn variant="secondary" onClick={handleGenerateDesc} disabled={loading}>AI Açıklama</HiveBtn>
                <HiveBtn variant="secondary" onClick={handleGenerateSeo} disabled={loading}>SEO Üret</HiveBtn>
                <HiveBtn onClick={handleQualityGate} disabled={loading}>Quality Gate</HiveBtn>
              </HiveToolbar>
              <HiveStatGrid items={[
                ["SEO", selected.seo_score ?? "—"],
                ["GEO", selected.geo_score ?? "—"],
                ["AEO", selected.aeo_score ?? "—"],
              ]} />
              <dl style={{ fontSize: "0.85rem", marginTop: "1rem" }}>
                <dt>Slug</dt><dd>{selected.slug || "—"}</dd>
                <dt>Meta Title</dt><dd>{selected.meta_title || "—"}</dd>
                <dt>Meta Description</dt><dd>{selected.meta_description || "—"}</dd>
                <dt>GEO Keywords</dt><dd>{(selected.geo_keywords || []).join(", ") || "—"}</dd>
              </dl>
              {selected.schema_jsonld && (
                <HiveCode>{JSON.stringify(selected.schema_jsonld, null, 2)?.slice(0, 1200)}</HiveCode>
              )}
            </HiveCard>
          ) : (
            <HiveAlert type="warn">SEO sekmesi için İlanlar'dan bir ilan seçip düzenleyin.</HiveAlert>
          )}
        </HivePanel>
      )}

      {tab === "publish" && (
        <HivePanel>
          <HiveCard title="Yayında Olan İlanlar" meta={`${listings.filter((l) => l.status === "active").length} aktif`}>
            {listings.filter((l) => l.status === "active").length === 0 ? (
              <p className="hm-empty">Aktif ilan yok</p>
            ) : (
              <ul style={{ fontSize: "0.85rem", lineHeight: 1.9 }}>
                {listings.filter((l) => l.status === "active").map((l) => (
                  <li key={l.id}>
                    <strong>{l.ilan_no}</strong> — {l.title}
                    {l.featured && " ⭐"}
                    {l.vip && " VIP"}
                    {l.wp_url && <> · <a href={l.wp_url} target="_blank" rel="noreferrer">canlı</a></>}
                  </li>
                ))}
              </ul>
            )}
          </HiveCard>
        </HivePanel>
      )}
    </HiveShell>
  );
}
