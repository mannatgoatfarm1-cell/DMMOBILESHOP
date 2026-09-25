import { useCallback, useEffect, useState } from "react";
import { Check, Eye, EyeOff, ImagePlus, LayoutTemplate, Upload } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/api";

export default function AdminStorefrontManager() {
  const [config, setConfig] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try { const { data } = await api.get("/api/admin/storefront"); setConfig(data); }
    catch (error) { toast.error(apiError(error)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const updateHero = (key, value) => setConfig((current) => ({ ...current, hero: { ...current.hero, [key]: value } }));
  const updateSection = (id, key, value) => setConfig((current) => ({ ...current, sections: current.sections.map((section) => section.id === id ? { ...section, [key]: value } : section) }));
  const uploadHero = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData(); body.append("file", file);
      const { data } = await api.post("/api/admin/uploads", body, { headers: { "Content-Type": "multipart/form-data" } });
      updateHero("image_url", data.url); toast.success("Banner image uploaded");
    } catch (error) { toast.error(apiError(error)); }
    finally { setBusy(false); event.target.value = ""; }
  };
  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/api/admin/storefront", config);
      setConfig(data); localStorage.setItem("mobilecart-live-update", String(Date.now())); toast.success("Website changes are live");
    } catch (error) { toast.error(apiError(error)); }
    finally { setBusy(false); }
  };
  if (!config) return <div className="empty-state" data-testid="storefront-manager-loading"><LayoutTemplate size={28} /><h3>Loading website controls…</h3></div>;
  return (
    <div className="storefront-manager" data-testid="storefront-manager">
      <section className="admin-panel storefront-hero-editor">
        <div className="panel-head"><div><h2>Homepage banner</h2><span>Edit the first customer-facing banner and upload its image.</span></div><ImagePlus size={19} /></div>
        <div className="storefront-hero-layout">
          <div className="storefront-form-grid">
            <label>Eyebrow<input value={config.hero.eyebrow} onChange={(event) => updateHero("eyebrow", event.target.value)} data-testid="storefront-hero-eyebrow-input" /></label>
            <label>Title<input value={config.hero.title} onChange={(event) => updateHero("title", event.target.value)} data-testid="storefront-hero-title-input" /></label>
            <label>Highlight<input value={config.hero.highlight} onChange={(event) => updateHero("highlight", event.target.value)} data-testid="storefront-hero-highlight-input" /></label>
            <label>Supporting text<input value={config.hero.description} onChange={(event) => updateHero("description", event.target.value)} data-testid="storefront-hero-description-input" /></label>
            <label>Banner image URL<input value={config.hero.image_url} onChange={(event) => updateHero("image_url", event.target.value)} placeholder="Upload an image or paste a URL" data-testid="storefront-hero-image-url-input" /></label>
            <label className="compact-upload" data-testid="storefront-hero-upload-label"><Upload size={14} /> Upload banner image<input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadHero} data-testid="storefront-hero-upload-input" /></label>
          </div>
          <div className="storefront-image-preview" data-testid="storefront-hero-preview">{config.hero.image_url ? <img src={config.hero.image_url} alt="Homepage banner preview" /> : <ImagePlus size={28} />}</div>
        </div>
      </section>
      <section className="admin-panel storefront-section-editor">
        <div className="panel-head"><div><h2>Homepage sections</h2><span>Change heading text or hide any section from the customer website.</span></div><span data-testid="storefront-section-count">{config.sections.length} sections</span></div>
        <div className="storefront-section-grid">
          {config.sections.map((section) => <article key={section.id} className={section.active ? "active" : "hidden"} data-testid={`storefront-section-${section.id}`}>
            <div><b>{section.label}</b><button type="button" onClick={() => updateSection(section.id, "active", !section.active)} data-testid={`toggle-storefront-section-${section.id}`}>{section.active ? <><Eye size={14} /> Live</> : <><EyeOff size={14} /> Hidden</>}</button></div>
            <label>Section title<input value={section.title} onChange={(event) => updateSection(section.id, "title", event.target.value)} placeholder={section.label} data-testid={`storefront-section-title-${section.id}`} /></label>
            <label>Small label<input value={section.eyebrow} onChange={(event) => updateSection(section.id, "eyebrow", event.target.value)} placeholder="Optional small label" data-testid={`storefront-section-eyebrow-${section.id}`} /></label>
          </article>)}
        </div>
      </section>
      <div className="storefront-save-bar"><span>Changes publish to the storefront immediately after saving.</span><button className="primary-btn" type="button" onClick={save} disabled={busy} data-testid="save-storefront-button"><Check size={15} /> {busy ? "Publishing…" : "Publish website changes"}</button></div>
    </div>
  );
}