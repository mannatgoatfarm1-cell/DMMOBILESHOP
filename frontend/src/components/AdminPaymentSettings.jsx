import { useEffect, useState } from "react";
import { Banknote, Building2, CreditCard, KeyRound, Landmark, Percent, Save, ShieldCheck, Smartphone, Wallet } from "lucide-react";
import { api, apiError } from "@/api";
import { hindiError, hindiFeedback } from "@/lib/adminFeedback";

const METHOD_ROWS = [
  ["upi_enabled", "UPI", "Google Pay, PhonePe, Paytm आदि", Smartphone],
  ["card_enabled", "Credit / Debit Card", "Visa, Mastercard, RuPay", CreditCard],
  ["netbanking_enabled", "Net Banking", "सभी बड़े बैंक", Building2],
  ["cod_enabled", "Cash on Delivery", "डिलीवरी पर नकद भुगतान", Banknote],
  ["wallet_enabled", "MobileCart Wallet", "वॉलेट बैलेंस से भुगतान", Wallet],
];

export default function AdminPaymentSettings() {
  const [settings, setSettings] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/api/admin/payment-settings")
      .then(({ data }) => setSettings({ ...data, razorpay_key_secret: "", razorpay_webhook_secret: "" }))
      .catch((error) => hindiError(apiError(error)));
  }, []);

  const set = (key, value) => setSettings((current) => ({ ...current, [key]: value }));

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.put("/api/admin/payment-settings", {
        razorpay_key_id: settings.razorpay_key_id || "",
        razorpay_key_secret: settings.razorpay_key_secret || "",
        razorpay_webhook_secret: settings.razorpay_webhook_secret || "",
        mode: settings.mode,
        upi_enabled: settings.upi_enabled,
        upi_id: settings.upi_id || "",
        card_enabled: settings.card_enabled,
        netbanking_enabled: settings.netbanking_enabled,
        cod_enabled: settings.cod_enabled,
        wallet_enabled: settings.wallet_enabled,
        partial_payment_enabled: settings.partial_payment_enabled,
        partial_payment_percent: Number(settings.partial_payment_percent) || 100,
      });
      setSettings({ ...data, razorpay_key_secret: "", razorpay_webhook_secret: "" });
      hindiFeedback("पेमेंट सेटिंग्स सेव होकर लाइव हो गईं");
    } catch (error) {
      hindiError(apiError(error));
    } finally {
      setBusy(false);
    }
  };

  if (!settings) return <div className="empty-state" data-testid="payment-settings-loading"><ShieldCheck size={30} /><h3>Loading payment settings…</h3></div>;

  return (
    <form className="admin-manager pay-settings" onSubmit={save} data-testid="payment-settings-form">
      <section className="admin-panel pay-connection"><div className="panel-head"><div><span className="pay-kicker"><ShieldCheck size={14} /> PAYMENT CONTROL</span><h2>Razorpay connection</h2><span>Keys secure रहती हैं; customer को कभी दिखाई नहीं जातीं।</span></div><span className={`pay-mode-badge ${settings.mode}`} data-testid="payment-mode-badge">{settings.mode === "live" ? "LIVE MODE" : "TEST MODE"}</span></div><div className="pay-mode-tabs" data-testid="razorpay-mode-select"><button type="button" className={settings.mode === "test" ? "active" : ""} onClick={() => set("mode", "test")} data-testid="razorpay-mode-test-button">Test mode</button><button type="button" className={settings.mode === "live" ? "active" : ""} onClick={() => set("mode", "live")} data-testid="razorpay-mode-live-button">Live mode</button></div><div className="pay-grid"><label className="pay-field"><span><KeyRound size={13} /> Key ID</span><input value={settings.razorpay_key_id || ""} onChange={(event) => set("razorpay_key_id", event.target.value)} placeholder="rzp_test_... / rzp_live_..." data-testid="razorpay-key-id-input" /></label><label className="pay-field"><span><KeyRound size={13} /> Key Secret</span><input type="password" value={settings.razorpay_key_secret || ""} onChange={(event) => set("razorpay_key_secret", event.target.value)} placeholder={settings.razorpay_key_secret_set ? "Saved securely — enter only to replace" : "Enter Key Secret"} data-testid="razorpay-key-secret-input" /></label><label className="pay-field pay-field-wide"><span><ShieldCheck size={13} /> Webhook Secret <em>Optional</em></span><input type="password" value={settings.razorpay_webhook_secret || ""} onChange={(event) => set("razorpay_webhook_secret", event.target.value)} placeholder={settings.razorpay_webhook_secret_set ? "Saved securely — enter only to replace" : "Enter webhook signing secret"} data-testid="razorpay-webhook-secret-input" /></label></div></section>

      <section className="admin-panel"><div className="panel-head"><div><span className="pay-kicker"><CreditCard size={14} /> CHECKOUT METHODS</span><h2>Customer payment choices</h2><span>Switch off करने पर method checkout से तुरंत हटेगा।</span></div></div><div className="upi-collection"><span className="upi-collection-icon"><Landmark size={19} /></span><label className="pay-field"><span>Merchant UPI ID</span><input value={settings.upi_id || ""} onChange={(event) => set("upi_id", event.target.value)} placeholder="yourstore@bank" data-testid="merchant-upi-id-input" /></label><small>UPI ID optional है; valid ID save होने पर UPI collection details ready रहेंगी।</small></div><div className="pay-methods">
          {METHOD_ROWS.map(([key, title, sub, Icon]) => (
            <label key={key} className={`pay-method ${settings[key] ? "on" : ""}`} data-testid={`payment-method-${key}`}>
              <span className="pay-method-icon"><Icon size={17} /></span>
              <span className="pay-method-copy"><b>{title}</b><small>{sub}</small></span>
              <input type="checkbox" checked={!!settings[key]} onChange={(event) => set(key, event.target.checked)} data-testid={`toggle-${key}`} />
              <span className="pay-switch" />
            </label>
          ))}
        </div>
      </section>

      <section className="admin-panel pay-advance-panel">
        <div className="panel-head"><div><h2>Partial / Advance Payment</h2><span>ग्राहक बुकिंग पर सिर्फ़ कुछ प्रतिशत अभी दे, बाकी बाद में।</span></div><Percent size={18} /></div>
        <div className="pay-partial">
          <label className={`pay-method ${settings.partial_payment_enabled ? "on" : ""}`} data-testid="payment-method-partial">
            <span className="pay-method-icon"><Percent size={17} /></span>
            <span className="pay-method-copy"><b>Partial payment चालू करें</b><small>Advance percent नीचे सेट करें</small></span>
            <input type="checkbox" checked={!!settings.partial_payment_enabled} onChange={(event) => set("partial_payment_enabled", event.target.checked)} data-testid="toggle-partial-payment" />
            <span className="pay-switch" />
          </label>
          <label className="pay-field partial-percent"><span>Advance amount (%)</span><div className="advance-input"><input type="range" min="10" max="100" value={settings.partial_payment_percent} onChange={(event) => set("partial_payment_percent", event.target.value)} disabled={!settings.partial_payment_enabled} data-testid="partial-percent-slider" /><input type="number" min="10" max="100" value={settings.partial_payment_percent} onChange={(event) => set("partial_payment_percent", event.target.value)} disabled={!settings.partial_payment_enabled} data-testid="partial-percent-input" /><b>%</b></div></label>
        </div>
      </section>

      <button className="primary-btn pay-save" disabled={busy} data-testid="save-payment-settings-button"><Save size={15} /> {busy ? "सेव हो रहा है…" : "सेटिंग्स सेव करें और लाइव करें"}</button>
    </form>
  );
}
