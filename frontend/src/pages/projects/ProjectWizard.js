import React, { useMemo, useState } from "react";
import API from "../../api";
import {
  HiveShell,
  HiveAlert,
  HivePanel,
  HiveField,
  HiveInput,
  HiveBtn,
} from "../../components/HiveModuleUI";
import { PROJECT_SECTORS, DEPLOY_MODES, sectorLabel, deployLabel } from "../../config/projectSectors";
import {
  BRAND_PERSONALITIES,
  DESIGN_DNA,
  COLOR_IDENTITIES,
  CONVERSION_GOALS,
  personalityLabels,
  designDnaLabel,
  colorIdentityLabel,
  conversionGoalLabel,
  buildDesignPayload,
} from "../../config/brandWizard";
import DesignPreview from "./DesignPreview";

const STEPS = [
  { id: 1, key: "sector", label: "Sector", headline: "Hangi sektörde marka yaratıyorsun?" },
  { id: 2, key: "business_dna", label: "Business DNA", headline: "İşletmeni anlat" },
  { id: 3, key: "personality", label: "Brand Personality", headline: "Markanın kişiliği" },
  { id: 4, key: "design_dna", label: "Design DNA", headline: "Sitenin görsel karakteri" },
  { id: 5, key: "color", label: "Color Identity", headline: "Renk kimliği" },
  { id: 6, key: "conversion", label: "Conversion Goal", headline: "Sitenin ana amacı" },
  { id: 7, key: "creative", label: "AI Director", headline: "AI Creative Director" },
  { id: 8, key: "deploy", label: "Deploy", headline: "Dağıtım modu" },
  { id: 9, key: "review", label: "Review", headline: "Marka özeti" },
];

const TOTAL = STEPS.length;

const EMPTY = {
  sector: "",
  name: "",
  business_brief: "",
  brand_personality: [],
  design_dna: "",
  color_identity: "",
  custom_color: "#6366f1",
  conversion_goal: "",
  creative_director_brief: "",
  deploy_mode: "hive_cloud",
};

function apiError(e) {
  return e?.response?.data?.detail || e?.hiveMessage || e?.message || "Bilinmeyen hata";
}

function deriveName(form) {
  if (form.name.trim().length >= 2) return form.name.trim();
  const brief = form.business_brief.trim();
  if (brief.length >= 6) {
    const snippet = brief.split(/[.!?]/)[0].trim().slice(0, 48);
    return snippet || sectorLabel(form.sector);
  }
  return `${sectorLabel(form.sector)} Markası`;
}

function toggleInList(list, id) {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}

function WizardStepHeader({ step }) {
  const current = STEPS.find((s) => s.id === step);
  const pct = Math.round((step / TOTAL) * 100);
  return (
    <div className="hive-brand-wizard-header">
      <div className="hive-brand-wizard-progress">
        <div className="hive-brand-wizard-progress-track">
          <div className="hive-brand-wizard-progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="hive-brand-wizard-progress-label">Adım {step} / {TOTAL}</span>
      </div>
      <h3 className="hive-brand-wizard-headline">{current?.headline}</h3>
      <p className="hive-brand-wizard-sub">{current?.label}</p>
    </div>
  );
}

function SelectCard({ selected, onClick, icon, title, desc, multi }) {
  return (
    <button type="button" className={`hive-brand-card ${selected ? "selected" : ""} ${multi ? "multi" : ""}`} onClick={onClick}>
      <span className="hive-brand-card-icon">{icon}</span>
      <span className="hive-brand-card-title">{title}</span>
      {desc && <span className="hive-brand-card-desc">{desc}</span>}
      {multi && selected && <span className="hive-brand-card-check">✓</span>}
    </button>
  );
}

function ReviewCard({ icon, label, value }) {
  return (
    <div className="hive-brand-review-card">
      <span className="hive-brand-review-icon">{icon}</span>
      <div>
        <div className="hive-brand-review-label">{label}</div>
        <div className="hive-brand-review-value">{value || "—"}</div>
      </div>
    </div>
  );
}

export default function ProjectWizard({ onNavigate }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const projectName = useMemo(() => deriveName(form), [form]);

  const canNext = () => {
    if (step === 1) return Boolean(form.sector);
    if (step === 2) return form.business_brief.trim().length >= 12;
    if (step === 3) return form.brand_personality.length > 0;
    if (step === 4) return Boolean(form.design_dna);
    if (step === 5) return Boolean(form.color_identity);
    if (step === 6) return Boolean(form.conversion_goal);
    if (step === 7) return form.creative_director_brief.trim().length >= 10;
    if (step === 8) return Boolean(form.deploy_mode);
    return true;
  };

  const next = () => {
    if (!canNext()) {
      setError("Lütfen bu adımı tamamlayın.");
      return;
    }
    setError("");
    setStep((s) => Math.min(TOTAL, s + 1));
  };

  const back = () => {
    setError("");
    setStep((s) => Math.max(1, s - 1));
  };

  const createProject = async () => {
    setCreating(true);
    setError("");
    try {
      const res = await API.post("/api/v3/projects", {
        name: projectName,
        sector: form.sector,
        domain: "",
        business_brief: form.business_brief.trim(),
        design: buildDesignPayload(form),
        deploy_mode: form.deploy_mode,
        status: "draft",
      });
      const pid = res.data?.project?.id;
      if (!pid) throw new Error("Proje oluşturulamadı");
      onNavigate(`/projects/${pid}`);
    } catch (e) {
      setError(apiError(e));
      setCreating(false);
    }
  };

  return (
    <div className="hive-brand-wizard">
      <HiveShell
        title="Marka Yarat"
        subtitle="İşletmen için dijital kimlik ve site DNA'sı oluştur"
        actions={<HiveBtn onClick={() => onNavigate("/projects")}>İptal</HiveBtn>}
      >
        {error && <HiveAlert type="error">{error}</HiveAlert>}

        <div className="hive-brand-wizard-steps">
          {STEPS.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`hive-brand-wizard-step ${step === s.id ? "active" : ""} ${step > s.id ? "done" : ""}`}
              onClick={() => s.id < step && setStep(s.id)}
              disabled={s.id > step}
            >
              <span className="hive-brand-wizard-step-num">{s.id}</span>
              <span className="hive-brand-wizard-step-label">{s.label}</span>
            </button>
          ))}
        </div>

        <WizardStepHeader step={step} />

        {step === 1 && (
          <HivePanel>
            <div className="hive-sector-grid hive-brand-sector-grid">
              {PROJECT_SECTORS.map((s) => (
                <SelectCard
                  key={s.id}
                  selected={form.sector === s.id}
                  onClick={() => setForm({ ...form, sector: s.id })}
                  icon={s.icon}
                  title={s.label}
                />
              ))}
            </div>
          </HivePanel>
        )}

        {step === 2 && (
          <HivePanel>
            <HiveField label="Marka / işletme adı (opsiyonel)">
              <HiveInput
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Örn: Karaburun Boutique Hotel"
              />
            </HiveField>
            <HiveField label="İşletmeni anlat" required>
              <textarea
                className="hive-input hive-brand-textarea"
                rows={6}
                value={form.business_brief}
                onChange={(e) => setForm({ ...form, business_brief: e.target.value })}
                placeholder={"Karaburun'da deniz manzaralı lüks butik otel.\n\nİzmir merkezde çalışan diş kliniği.\n\nTürkiye geneli çalışan e-ticaret markası."}
              />
            </HiveField>
            <p className="hive-brand-hint">Bu metin AI tarafından içerik, tasarım ve CTA önerilerinde kullanılacak.</p>
          </HivePanel>
        )}

        {step === 3 && (
          <HivePanel>
            <p className="hive-brand-hint">Birden fazla seçebilirsin — markanın tonunu birlikte tanımlarlar.</p>
            <div className="hive-brand-card-grid hive-brand-card-grid--personality">
              {BRAND_PERSONALITIES.map((p) => (
                <SelectCard
                  key={p.id}
                  multi
                  selected={form.brand_personality.includes(p.id)}
                  onClick={() => setForm({ ...form, brand_personality: toggleInList(form.brand_personality, p.id) })}
                  icon={p.icon}
                  title={p.label}
                  desc={p.desc}
                />
              ))}
            </div>
          </HivePanel>
        )}

        {step === 4 && (
          <div className="hive-brand-split">
            <HivePanel>
              <div className="hive-brand-card-grid hive-brand-card-grid--design">
                {DESIGN_DNA.map((d) => (
                  <SelectCard
                    key={d.id}
                    selected={form.design_dna === d.id}
                    onClick={() => setForm({ ...form, design_dna: d.id })}
                    icon={d.icon}
                    title={d.label}
                    desc={d.tagline}
                  />
                ))}
              </div>
            </HivePanel>
            <div className="hive-brand-preview-sticky">
              <DesignPreview
                designDna={form.design_dna}
                colorIdentity={form.color_identity}
                customColor={form.custom_color}
              />
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="hive-brand-split">
            <HivePanel>
              <div className="hive-brand-card-grid hive-brand-card-grid--color">
                {COLOR_IDENTITIES.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className={`hive-brand-color-card ${form.color_identity === c.id ? "selected" : ""}`}
                    onClick={() => setForm({ ...form, color_identity: c.id })}
                  >
                    <div className="hive-brand-swatch-row">
                      {c.swatch.map((hex) => (
                        <span key={hex} className="hive-brand-swatch" style={{ background: hex }} />
                      ))}
                    </div>
                    <span className="hive-brand-card-icon">{c.icon}</span>
                    <span className="hive-brand-card-title">{c.label}</span>
                  </button>
                ))}
              </div>
              {form.color_identity === "custom" && (
                <HiveField label="Özel renk">
                  <input
                    type="color"
                    className="hive-brand-color-picker"
                    value={form.custom_color}
                    onChange={(e) => setForm({ ...form, custom_color: e.target.value })}
                  />
                </HiveField>
              )}
            </HivePanel>
            <div className="hive-brand-preview-sticky">
              <DesignPreview
                designDna={form.design_dna}
                colorIdentity={form.color_identity}
                customColor={form.custom_color}
              />
            </div>
          </div>
        )}

        {step === 6 && (
          <HivePanel>
            <div className="hive-brand-card-grid">
              {CONVERSION_GOALS.map((g) => (
                <SelectCard
                  key={g.id}
                  selected={form.conversion_goal === g.id}
                  onClick={() => setForm({ ...form, conversion_goal: g.id })}
                  icon={g.icon}
                  title={g.label}
                  desc={g.desc}
                />
              ))}
            </div>
          </HivePanel>
        )}

        {step === 7 && (
          <HivePanel>
            <h4 className="hive-brand-creative-title">Bu site nasıl hissettirmeli?</h4>
            <textarea
              className="hive-input hive-brand-textarea hive-brand-creative-input"
              rows={7}
              value={form.creative_director_brief}
              onChange={(e) => setForm({ ...form, creative_director_brief: e.target.value })}
              placeholder="Misafir siteye girdiğinde lüks, güven ve kalite hissetmeli. Rakiplerden daha modern görünmeli. Rezervasyon dönüşümü yüksek olmalı."
            />
            <p className="hive-brand-hint">
              AI bu metni renk, tipografi, hero yapısı, CTA dili ve sayfa yapısı önerilerinde kullanacak.
            </p>
            <HiveBtn
              style={{ marginTop: 12 }}
              disabled={!form.sector || !form.business_brief.trim()}
              onClick={async () => {
                setError("");
                try {
                  const res = await API.post("/api/v3/creative-director/suggest", {
                    sector: form.sector,
                    business_brief: form.business_brief,
                    creative_brief: form.creative_director_brief,
                    use_llm: true,
                  });
                  const s = res.data?.suggestions || {};
                  setForm((f) => ({
                    ...f,
                    design_dna: s.design_dna || f.design_dna,
                    color_identity: s.color_identity || f.color_identity,
                    brand_personality: s.brand_personality?.length ? s.brand_personality : f.brand_personality,
                    conversion_goal: s.conversion_goal || f.conversion_goal,
                  }));
                } catch (e) {
                  setError(apiError(e));
                }
              }}
            >
              AI Önerilerini Uygula
            </HiveBtn>
          </HivePanel>
        )}

        {step === 8 && (
          <HivePanel>
            <div className="hive-deploy-grid hive-brand-deploy-grid">
              {DEPLOY_MODES.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  className={`hive-deploy-card hive-brand-deploy-card ${form.deploy_mode === d.id ? "selected" : ""}`}
                  onClick={() => setForm({ ...form, deploy_mode: d.id })}
                >
                  <strong>{d.label}</strong>
                  <span>{d.desc}</span>
                </button>
              ))}
            </div>
          </HivePanel>
        )}

        {step === 9 && (
          <HivePanel>
            <p className="hive-brand-review-intro">
              <strong>{projectName}</strong> markası oluşturulmaya hazır.
            </p>
            <div className="hive-brand-review-grid">
              <ReviewCard icon="🏷" label="Sector" value={sectorLabel(form.sector)} />
              <ReviewCard icon="🧬" label="Brand Personality" value={personalityLabels(form.brand_personality).join(" · ")} />
              <ReviewCard icon="◆" label="Design DNA" value={designDnaLabel(form.design_dna)} />
              <ReviewCard icon="🎨" label="Color Identity" value={colorIdentityLabel(form.color_identity)} />
              <ReviewCard icon="🎯" label="Conversion Goal" value={conversionGoalLabel(form.conversion_goal)} />
              <ReviewCard icon="☁" label="Deploy Mode" value={deployLabel(form.deploy_mode)} />
            </div>
            <div className="hive-brand-review-preview-wrap">
              <DesignPreview
                designDna={form.design_dna}
                colorIdentity={form.color_identity}
                customColor={form.custom_color}
              />
            </div>
            <div className="hive-brand-review-brief">
              <div className="hive-brand-review-label">Business DNA</div>
              <p>{form.business_brief}</p>
              <div className="hive-brand-review-label">AI Creative Director</div>
              <p>{form.creative_director_brief}</p>
            </div>
            <HiveBtn variant="primary" className="hive-brand-create-btn" onClick={createProject} disabled={creating}>
              {creating ? "Marka oluşturuluyor..." : "✦ Markayı Oluştur"}
            </HiveBtn>
          </HivePanel>
        )}

        {step < TOTAL && (
          <div className="hive-brand-wizard-nav">
            <HiveBtn onClick={back} disabled={step === 1}>Geri</HiveBtn>
            <HiveBtn variant="primary" onClick={next} disabled={!canNext()}>Devam Et →</HiveBtn>
          </div>
        )}
        {step === TOTAL && (
          <div className="hive-brand-wizard-nav">
            <HiveBtn onClick={back} disabled={creating}>Geri</HiveBtn>
          </div>
        )}
      </HiveShell>
    </div>
  );
}
