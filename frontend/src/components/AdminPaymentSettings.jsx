import { useEffect, useState } from "react";
import { CreditCard, KeyRound, Percent, ShieldCheck, Save, Wallet, Smartphone, Banknote, Building2 } from "lucide-react";
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
      <section className="admin-panel">
        <div className="panel-head"><div><h2>Razorpay Keys</h2><span>अपनी Razorpay keys यहाँ डालें — सेव करते ही customer website पर लाइव पेमेंट चालू।</span></div>
          <span className={`pay-mode-badge ${settings.mode}`} data-testid="payment-mode-badge">{settings.mode === "live" ? "LIVE MODE" : "TEST MODE"}</span>
        </div>
        <div className="pay-grid">
          <label className="pay-field"><span><KeyRound size={13} /> Key ID</span><input value={settings.razorpay_key_id || ""} onChange={(event) => set("razorpay_key_id", event.target.value)} placeholder="rzp_test_xxxxxxxx / rzp_live_xxxxxxxx" data-testid="razorpay-key-id-input" /></label>
          <label className="pay-field"><span><KeyRound size={13} /> Key Secret</span><input type="password" value={settings.razorpay_key_secret || ""} onChange={(event) => set("razorpay_key_secret", event.target.value)} placeholder={settings.razorpay_key_secret_set ? "•••••••• (saved — बदलने के लिए नया डालें)" : "Key Secret डालें"} data-testid="razorpay-key-secret-input" /></label>
          <label className="pay-field"><span><ShieldCheck size={13} /> Webhook Secret</span><input type="password" value={settings.razorpay_webhook_secret || ""} onChange={(event) => set("razorpay_webhook_secret", event.target.value)} placeholder={settings.razorpay_webhook_secret_set ? "•••••••• (saved)" : "Webhook Secret (optional)"} data-testid="razorpay-webhook-secret-input" /></label>
          <label className="pay-field"><span>Mode</span><select value={settings.mode} onChange={(event) => set("mode", event.target.value)} data-testid="razorpay-mode-select"><option value="test">Test Mode</option><option value="live">Live Mode</option></select></label>
        </div>
      </section>

      <section className="admin-panel">
        <div className="panel-head"><div><h2>Payment Methods</h2><span>Checkout पर कौन-कौन से विकल्प customer को दिखें।</span></div></div>
        <div className="pay-methods">
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

      <section className="admin-panel">
        <div className="panel-head"><div><h2>Partial / Advance Payment</h2><span>ग्राहक बुकिंग पर सिर्फ़ कुछ प्रतिशत अभी दे, बाकी बाद में।</span></div><Percent size={18} /></div>
        <div className="pay-partial">
          <label className={`pay-method ${settings.partial_payment_enabled ? "on" : ""}`} data-testid="payment-method-partial">
            <span className="pay-method-icon"><Percent size={17} /></span>
            <span className="pay-method-copy"><b>Partial payment चालू करें</b><small>Advance percent नीचे सेट करें</small></span>
            <input type="checkbox" checked={!!settings.partial_payment_enabled} onChange={(event) => set("partial_payment_enabled", event.target.checked)} data-testid="toggle-partial-payment" />
            <span className="pay-switch" />
          </label>
          <label className="pay-field partial-percent"><span>Advance percent अभी लें (%)</span>
            <input type="number" min="10" max="100" value={settings.partial_payment_percent} onChange={(event) => set("partial_payment_percent", event.target.value)} disabled={!settings.partial_payment_enabled} data-testid="partial-percent-input" />
          </label>
        </div>
      </section>

      <button className="primary-btn pay-save" disabled={busy} data-testid="save-payment-settings-button"><Save size={15} /> {busy ? "सेव हो रहा है…" : "सेटिंग्स सेव करें और लाइव करें"}</button>
    </form>
  );
}
