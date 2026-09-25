import { useState, useMemo, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Search, ShoppingCart, ChevronRight, Heart, Star, Gavel, Smartphone, Laptop, Watch, Tablet,
  Apple, Headphones, Gamepad2, Camera, LayoutGrid, Percent, Clock, Radio, ShieldCheck, Wallet,
  RotateCcw, BadgeCheck, Truck, PackageOpen, Flame,
  ArrowRight, TrendingUp, RefreshCw, Wrench, Cpu, Phone, Globe, MessageCircle,
} from "lucide-react";

const money = (v = 0) => `₹${Number(v).toLocaleString("en-IN")}`;
const rateFor = (id = "") => {
  const seed = [...String(id)].reduce((t, c) => t + c.charCodeAt(0), 0);
  return { stars: (4 + (seed % 9) / 10).toFixed(1), count: `${4 + (seed % 12)}.${seed % 9}K` };
};

/* ========== Animation Utilities ========== */
const fadeUp = { initial: { opacity: 0, y: 30 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, margin: "-40px" }, transition: { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } };
const fadeScale = { initial: { opacity: 0, scale: 0.95 }, whileInView: { opacity: 1, scale: 1 }, viewport: { once: true, margin: "-40px" }, transition: { duration: 0.5 } };
const staggerContainer = { whileInView: { transition: { staggerChildren: 0.06 } }, viewport: { once: true, margin: "-40px" } };
const staggerItem = { initial: { opacity: 0, y: 20 }, whileInView: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const CATEGORIES = [
  { label: "Mobiles & Phones", slug: "mobiles", icon: Smartphone, sub: "Latest Models" },
  { label: "Mobile Parts", slug: "accessories", icon: Wrench, sub: "Display, Battery, ICs" },
  { label: "Accessories", slug: "accessories", icon: Headphones, sub: "Cases, Chargers, Cables" },
  { label: "Smart Watches", slug: "smartwatch", icon: Watch, sub: "Apple & Android" },
  { label: "Laptops & Computers", slug: "laptops", icon: Laptop, sub: "Work, Study, Gaming" },
  { label: "Gaming", slug: "gaming", icon: Gamepad2, sub: "Consoles & Accessories" },
  { label: "Tablets", slug: "tablets", icon: Tablet, sub: "iPad, Samsung, More" },
  { label: "Cameras", slug: "cameras", icon: Camera, sub: "Pro & Mirrorless" },
];
const HOT_CATEGORIES = [
  { label: "Mobile Parts", sub: "Display | Battery | IC", icon: Cpu, slug: "accessories" },
  { label: "Accessories", sub: "Cases | Chargers | Cables", icon: Headphones, slug: "accessories" },
  { label: "Smart Watches", sub: "Fitness | Health | Style", icon: Watch, slug: "smartwatch" },
  { label: "Refurbished Phones", sub: "Certified | Tested | Warranty", icon: RefreshCw, slug: "mobiles" },
  { label: "Compare Phones", sub: "Find the Perfect Match", icon: Smartphone, slug: "" },
  { label: "Sell Your Phone", sub: "Get Best Value", icon: TrendingUp, slug: "" },
];
const BRANDS = [
  { label: "Apple", icon: Apple }, { label: "Samsung", icon: Smartphone }, { label: "OnePlus", icon: Cpu },
  { label: "Mi", icon: Tablet }, { label: "Vivo", icon: Camera }, { label: "Oppo", icon: Radio },
  { label: "Realme", icon: Watch }, { label: "Google Pixel", icon: Globe }, { label: "Motorola", icon: Headphones },
  { label: "Nothing", icon: Gamepad2 }, { label: "Asus", icon: Laptop },
];
const BADGES = ["Bestseller", "New Launch", "Hot Deal", "Assured", "Top Rated", "Value"];
const FEATURED_ORDER = ["iphone", "samsung", "macbook", "boat-airdopes-141", "pixel-7", "nothing-phone-2"];

/* ========== Countdown Timer ========== */
function AnimatedCountdown({ testId = "flash-countdown" }) {
  const [left, setLeft] = useState(12 * 3600 + 45 * 60 + 30);
  useEffect(() => { const t = setInterval(() => setLeft(v => v > 0 ? v - 1 : 12 * 3600), 1000); return () => clearInterval(t); }, []);
  const pad = v => String(v).padStart(2, "0");
  const h = pad(Math.floor(left / 3600)), m = pad(Math.floor((left % 3600) / 60)), s = pad(left % 60);
  return (
    <div className="countdown" data-testid={testId}>
      <motion.span key={`h-${h}`} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>{h}</motion.span>:
      <motion.span key={`m-${m}`} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>{m}</motion.span>:
      <motion.span key={`s-${s}`} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>{s}</motion.span>
    </div>
  );
}

/* ========== Reusable Sale Shelves ========== */
function SaleShelf({ id, title, eyebrow, icon: Icon, products, onAdd, to, tone = "cyan", showTimer = false }) {
  return (
    <motion.section {...fadeUp} className={`flash-wrap sale-shelf sale-shelf-${tone}`} data-testid={`${id}-section`}>
      <div className="section-title sale-shelf-title">
        <div className="sale-heading"><span className="sale-heading-icon"><Icon size={18} /></span><div><span className="sale-kicker">{eyebrow}</span><h2>{title}</h2></div></div>
        {showTimer && <div className="flash-timer" data-testid={`${id}-timer`}><Clock size={14} /> Ends in <AnimatedCountdown testId={`${id}-countdown`} /></div>}
        <Link to={to} data-testid={`view-${id}-link`}>View All <ChevronRight size={15} /></Link>
      </div>
      <motion.div className="product-grid grid-6 flash-grid" {...staggerContainer}>
        {products.map((product) => (
          <motion.article className="flash-card" key={`${id}-${product.id}`} variants={staggerItem} data-testid={`${id}-card-${product.id}`} whileHover={{ y: -5 }}>
            <span className="flash-off">{product.off || "LIVE DEAL"}</span>
            <Link to={`/product/${product.id}`} data-testid={`${id}-product-${product.id}`}><img src={product.image} alt={product.name} /></Link>
            <b>{product.name}</b><strong>{money(product.price)}</strong>
            <button onClick={() => onAdd(product)} data-testid={`${id}-add-${product.id}`}><ShoppingCart size={13} /> Grab Deal</button>
          </motion.article>
        ))}
      </motion.div>
    </motion.section>
  );
}

function MajorSaleSections({ products, onAdd, sections = [] }) {
  const sales = [
    { id: "mobile-parts-deals", title: "Mobile Parts Deals", eyebrow: "REPAIR ESSENTIALS", icon: Wrench, category: "accessories", tone: "blue" },
    { id: "today-deals", title: "Today's Deals", eyebrow: "ENDS TONIGHT", icon: Flame, category: "mobiles", tone: "orange", showTimer: true },
    { id: "deal-of-the-day", title: "Deal of the Day", eyebrow: "FEATURED PICK", icon: Clock, category: "", tone: "purple", showTimer: true },
    { id: "new-stock", title: "New Stock", eyebrow: "JUST LANDED", icon: Smartphone, category: "", tone: "green" },
    { id: "stock-clearance", title: "Stock Clearance Sale", eyebrow: "LAST CHANCE", icon: Percent, category: "", tone: "red" },
  ];
  const shelfProducts = (category, offset) => {
    const preferred = category ? products.filter((product) => product.category_slug === category) : products;
    const source = [...preferred, ...products.filter((product) => !preferred.some((item) => item.id === product.id))];
    return [...source.slice(offset), ...source.slice(0, offset)].slice(0, 6);
  };
  return (
    <div className="major-sale-sections" data-testid="major-sale-sections">
      {sales.map((sale, index) => {
        const setting = sections.find((section) => section.id === sale.id) || {};
        if (setting.active === false) return null;
        return <SaleShelf key={sale.id} {...sale} title={setting.title || sale.title} eyebrow={setting.eyebrow || sale.eyebrow} products={shelfProducts(sale.category, index)} onAdd={onAdd} to={sale.category ? `/category?category=${sale.category}` : "/category?sort=price_desc"} />;
      })}
    </div>
  );
}

/* ========== Glass Product Card ========== */
function GlassProductCard({ product, onAdd, onWish, badge, index = 0 }) {
  if (!product) return null;
  const rating = rateFor(product.id);
  const outOfStock = product.stock <= 0;
  return (
    <motion.article className="product-card" variants={staggerItem} data-testid={`product-card-${product.id}`}
      whileHover={{ y: -8, transition: { duration: 0.25 } }}>
      {outOfStock ? <span className="stock-badge out" data-testid={`out-of-stock-${product.id}`}>OUT OF STOCK</span> : badge && <span className="card-badge">{badge}</span>}
      <button className="wish" onClick={() => onWish(product.id)} data-testid={`wishlist-${product.id}`} aria-label={`Save ${product.name}`}><Heart size={15} /></button>
      <Link to={`/product/${product.id}`} data-testid={`product-link-${product.id}`} className="product-media"><img src={product.image} alt={product.name} /></Link>
      <div className="product-info">
        <Link to={`/product/${product.id}`}><h4>{product.name}</h4></Link>
        <p>{product.sub}</p>
        <div className="rating-line"><span className="stars"><Star size={12} fill="currentColor" /> {rating.stars}</span><small>({rating.count})</small></div>
        <div className="price-row"><strong>{money(product.price)}</strong><del>{money(product.old)}</del><em>{product.off}</em></div>
      </div>
      <motion.button className="add-cart-btn" disabled={outOfStock} onClick={() => onAdd(product)} data-testid={`add-product-${product.id}`}
        whileTap={{ scale: 0.95 }}>{outOfStock ? "Out of Stock" : <><ShoppingCart size={14} /> Add to Cart</>}</motion.button>
    </motion.article>
  );
}

/* ========== Trust Strip ========== */
function TrustStrip() {
  const items = [
    [ShieldCheck, "100% Original", "Products"],
    [Wallet, "Secure Payments", "UPI | Card | Wallet"],
    [Truck, "Fast Shipping", "Pan India"],
    [RotateCcw, "Easy Returns", "Within 7 Days"],
    [Headphones, "24x7 Support", "Always Here"],
    [BadgeCheck, "Best Wholesale Prices", "For Businesses"],
  ];
  return (
    <motion.div {...fadeUp} className="f-trust-strip" style={{ display: "flex", flexWrap: "wrap", gap: "12px", justifyContent: "center", margin: "24px 0", padding: "16px", borderRadius: "16px", background: "var(--glass-bg)", backdropFilter: "blur(14px)", border: "1px solid var(--glass-border)" }}>
      {items.map(([Icon, title, sub]) => (
        <div key={title} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 14px" }}>
          <Icon size={18} style={{ color: "var(--neon-blue)" }} />
          <span style={{ fontSize: "11px" }}><b style={{ color: "#e2eafc", display: "block" }}>{title}</b><small style={{ color: "#8fa5c4", fontSize: "9px" }}>{sub}</small></span>
        </div>
      ))}
    </motion.div>
  );
}

/* ========== Hot Selling Categories ========== */
function HotSellingCategories({ title = "Hot Selling Categories" }) {
  return (
    <motion.section {...fadeUp} style={{ margin: "30px 0" }} data-testid="hot-selling-categories">
      <div className="section-title"><h2><Flame size={20} style={{ color: "var(--gold)", marginRight: 8 }} />{title}</h2></div>
      <div className="f-hot-cats">
        {HOT_CATEGORIES.map(c => {
          const Icon = c.icon;
          return (
            <motion.div key={c.label} whileHover={{ y: -3 }}>
              <Link to={c.slug ? `/category?category=${c.slug}` : "/category"} className="f-hot-cat" data-testid={`hot-cat-${c.label.toLowerCase().replace(/\s/g, "-")}`}>
                <Icon size={20} />
                <span><b>{c.label}</b><small>{c.sub}</small></span>
                <ChevronRight size={14} style={{ color: "#6b7f9e", marginLeft: "auto" }} />
              </Link>
            </motion.div>
          );
        })}
      </div>
    </motion.section>
  );
}

/* ========== Quad Promo (Auction, Wholesale, Trade-In, Price Drop) ========== */
function QuadPromo() {
  return (
    <motion.div {...fadeUp} className="f-quad-grid" data-testid="futuristic-quad-grid">
      <Link to="/auctions" className="f-quad-card f-quad-auction" data-testid="quad-auction-zone">
        <Gavel size={22} style={{ color: "var(--neon-purple)", marginBottom: 8 }} />
        <h3>Auction Zone</h3>
        <p>Live Bidding | Real Deals</p>
        <span className="f-promo-btn">Join Auction <ArrowRight size={12} /></span>
      </Link>
      <Link to="/category" className="f-quad-card f-quad-wholesale" data-testid="quad-wholesale">
        <PackageOpen size={22} style={{ color: "var(--neon-blue)", marginBottom: 8 }} />
        <h3>Wholesale for Business</h3>
        <p>Bulk Orders | Special Pricing | Dedicated Support</p>
        <span className="f-promo-btn">Apply for Wholesale <ArrowRight size={12} /></span>
      </Link>
      <Link to="/sell" className="f-quad-card f-quad-trade" data-testid="quad-trade-in">
        <RefreshCw size={22} style={{ color: "var(--neon-green)", marginBottom: 8 }} />
        <h3>Trade-In</h3>
        <p>Upgrade with Benefits</p>
        <span className="f-promo-btn">Exchange Now <ArrowRight size={12} /></span>
      </Link>
      <Link to="/category?sort=price_desc" className="f-quad-card f-quad-radar" data-testid="quad-price-radar">
        <TrendingUp size={22} style={{ color: "var(--gold)", marginBottom: 8 }} />
        <h3>Price Drop Radar</h3>
        <p>Track Price Drops & Grab the Best Deals</p>
        <span className="f-promo-btn">Explore Now <ArrowRight size={12} /></span>
      </Link>
    </motion.div>
  );
}

/* ========== Top Brands ========== */
function BrandsSection({ title = "Top Brands" }) {
  return (
    <motion.section {...fadeUp} style={{ margin: "28px 0" }} data-testid="top-brands-section">
      <div className="section-title"><h2><Star size={18} style={{ color: "var(--gold)", marginRight: 8 }} />{title}</h2></div>
      <div className="f-brands-row">
        {BRANDS.map(({ label, icon: Icon }) => (
          <motion.div key={label} whileHover={{ y: -3, scale: 1.02 }}>
            <Link to="/category" className="f-brand-icon" data-testid={`brand-icon-${label.toLowerCase().replace(/\s/g, "-")}`} aria-label={`Shop ${label}`} title={label}><Icon size={22} /></Link>
          </motion.div>
        ))}
      </div>
    </motion.section>
  );
}

/* ========== Trending + Why Choose + Reviews ========== */
function TrendingReviewsSection({ products, onAdd, onWish }) {
  const [tab, setTab] = useState("All");
  const tabs = ["All", "Mobiles", "Parts", "Accessories"];
  const filtered = products.filter(p => tab === "All" || p.category_slug === tab.toLowerCase());
  const display = (filtered.length ? filtered : products).slice(0, 4);
  const reviews = [
    { name: "Rohit Sharma", text: "Best pricing, genuine product, fast delivery. Highly recommended!", stars: 5 },
    { name: "Neha Verma", text: "Quality products and amazing support. Will shop again!", stars: 5 },
    { name: "Amit Kumar", text: "Mobile as described. Very happy with purchase.", stars: 4 },
  ];
  return (
    <motion.div {...fadeUp} className="f-triple-grid" data-testid="trending-reviews-section">
      <section>
        <div className="section-title" style={{ flexWrap: "wrap" }}>
          <h2>Trending Products</h2>
          <div className="pill-tabs">
            {tabs.map(t => <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)} data-testid={`trending-tab-${t.toLowerCase()}`}>{t}</button>)}
          </div>
          <Link to="/category" data-testid="trending-view-all">View All <ChevronRight size={15} /></Link>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
          {display.map(p => (
            <Link to={`/product/${p.id}`} key={p.id} data-testid={`trending-product-${p.id}`} style={{ display: "flex", alignItems: "center", gap: 10, padding: 10, borderRadius: 12, background: "var(--glass-bg)", border: "1px solid var(--glass-border)", backdropFilter: "blur(12px)", textDecoration: "none" }}>
              <img src={p.image} alt={p.name} style={{ width: 50, height: 50, borderRadius: 8, objectFit: "cover", background: "rgba(10,18,35,0.5)" }} />
              <div><b style={{ fontSize: 11, color: "#e2eafc", display: "block" }}>{p.name}</b><strong style={{ fontSize: 14, color: "var(--neon-cyan)" }}>{money(p.price)}</strong></div>
            </Link>
          ))}
        </div>
      </section>

      <section data-testid="why-choose-section">
        <div className="section-title"><h2 style={{ fontSize: 16 }}>Why Choose DMMobile Shop?</h2></div>
        <div style={{ display: "grid", gap: 8 }}>
          {[["100% Original Products", "No Fake, No Duplicate"], ["Best Prices", "Wholesale & Retail"], ["Fast & Safe Delivery", "Pan India"], ["Easy Returns", "Hassle Free"], ["Dedicated Support", "24x7 Help"]].map(([t, s]) => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
              <ShieldCheck size={14} style={{ color: "var(--neon-green)", flexShrink: 0 }} />
              <span><b style={{ color: "#e2eafc" }}>{t}</b><br /><small style={{ color: "#8fa5c4", fontSize: 9 }}>{s}</small></span>
            </div>
          ))}
        </div>
      </section>

      <section data-testid="customer-reviews-section">
        <div className="section-title"><h2 style={{ fontSize: 16 }}>Customer Reviews</h2></div>
        <div className="f-reviews-grid">
          {reviews.map(r => (
            <div className="f-review-card" key={r.name} data-testid={`review-${r.name.toLowerCase().replace(/\s/g, "-")}`}>
              <div className="f-review-head">
                <span className="f-review-avatar">{r.name[0]}</span>
                <div><b>{r.name}</b><div className="f-review-stars">{Array.from({ length: r.stars }, (_, i) => <Star key={i} size={11} fill="currentColor" />)}</div></div>
              </div>
              <p>"{r.text}"</p>
            </div>
          ))}
        </div>
      </section>
    </motion.div>
  );
}

/* ========== Blog Section ========== */
function BlogSection() {
  const blogs = [
    { title: "Best Smartphones Under 30000", desc: "Our top picks for the best value phones this year." },
    { title: "iPhone vs Samsung: Which is Better?", desc: "A detailed comparison of the two biggest rivals." },
    { title: "Mobile Accessories You Must Have", desc: "Essential accessories every smartphone owner needs." },
  ];
  return (
    <motion.section {...fadeUp} data-testid="blog-section">
      <div className="section-title"><h2>Latest from Our Blog</h2></div>
      <div className="f-blog-grid">
        {blogs.map(b => (
          <Link to="/category" className="f-blog-card" key={b.title} data-testid={`blog-${b.title.toLowerCase().replace(/\s/g, "-").slice(0, 20)}`}>
            <div className="f-blog-img"><Globe size={30} /></div>
            <h4>{b.title}</h4>
            <p>{b.desc}</p>
            <small style={{ color: "var(--neon-blue)", fontSize: 10, fontWeight: 700, marginTop: 8, display: "inline-flex", alignItems: "center", gap: 4 }}>Read More <ChevronRight size={12} /></small>
          </Link>
        ))}
      </div>
    </motion.section>
  );
}

/* ========== Community + WhatsApp + Newsletter ========== */
function BottomSections() {
  return (
    <motion.div {...fadeUp} className="f-bottom-grid" data-testid="bottom-sections">
      <div className="f-community-card" data-testid="community-section">
        <h3>Join Our Community</h3>
        <p>Follow us for latest deals, updates & offers</p>
        <div className="f-social-links">
          {["YT", "IG", "FB", "TW", "TG"].map(s => <a key={s} href="#" data-testid={`social-${s.toLowerCase()}`}><MessageCircle size={16} /></a>)}
        </div>
      </div>
      <div className="f-whatsapp-card" data-testid="whatsapp-section">
        <Phone size={22} style={{ color: "var(--neon-green)", marginBottom: 8 }} />
        <h3>Get Exclusive Offers</h3>
        <p>Join WhatsApp Channel for Latest Deals | New Arrivals | Exclusive Offers</p>
        <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} style={{ padding: "10px 18px", borderRadius: 10, border: "none", background: "var(--neon-green)", color: "#0a2015", fontWeight: 800, fontSize: 12, cursor: "pointer" }} data-testid="join-whatsapp-btn">Join Now <ChevronRight size={13} /></motion.button>
      </div>
      <div className="f-newsletter-card" data-testid="newsletter-section">
        <h3>Subscribe to Our Newsletter</h3>
        <p>Get the latest deals, offers and updates.</p>
        <div className="f-newsletter-form">
          <input placeholder="Enter your email address" data-testid="newsletter-email-input" />
          <button data-testid="newsletter-subscribe-btn">Subscribe</button>
        </div>
      </div>
    </motion.div>
  );
}

/* ========== Enhanced Footer ========== */
function FuturisticFooter() {
  return (
    <footer className="f-footer" data-testid="futuristic-footer">
      <div className="f-footer-grid">
        <div className="f-footer-col">
          <div className="f-footer-brand">
            <span className="f-footer-brand-icon"><Smartphone size={20} /></span>
            <div><b>DMMobile Shop</b><small>Mobiles | Parts | Accessories | Wholesale<br />Your Trusted Mobile & Parts Partner</small></div>
          </div>
          <p className="f-footer-desc">DMMobile Shop is your one-stop destination for genuine mobiles, parts, accessories and wholesale solutions. We deliver quality products at the best prices across India.</p>
        </div>
        <div className="f-footer-col">
          <h4>Quick Links</h4>
          {["Home", "Mobiles", "Parts", "Accessories", "Wholesale", "Deals"].map(l => <Link key={l} to={l === "Home" ? "/" : "/category"} data-testid={`footer-link-${l.toLowerCase()}`}>{l}</Link>)}
        </div>
        <div className="f-footer-col">
          <h4>Customer Support</h4>
          {["Help Center", "Track Order", "Return & Refund", "Shipping Policy", "FAQ", "Contact Us"].map(l => <Link key={l} to="/policies/shipping" data-testid={`footer-link-${l.toLowerCase().replace(/\s/g, "-")}`}>{l}</Link>)}
        </div>
        <div className="f-footer-col">
          <h4>Our Services</h4>
          {["Bulk Orders", "Wholesale", "Exchange", "EMI Options", "Warranty Policy", "Price Match"].map(l => <Link key={l} to="/category" data-testid={`footer-link-${l.toLowerCase().replace(/\s/g, "-")}`}>{l}</Link>)}
        </div>
        <div className="f-footer-col">
          <h4>Download Our App</h4>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <span style={{ padding: "8px 14px", borderRadius: 8, background: "rgba(15,25,45,0.6)", border: "1px solid var(--glass-border)", color: "#c0d0eb", fontSize: 10 }}>Google Play</span>
            <span style={{ padding: "8px 14px", borderRadius: 8, background: "rgba(15,25,45,0.6)", border: "1px solid var(--glass-border)", color: "#c0d0eb", fontSize: 10 }}>App Store</span>
          </div>
          <small style={{ color: "#6b7f9e", fontSize: 9 }}>Get exclusive offers & faster ordering</small>
        </div>
      </div>
      <div className="f-footer-bottom">
        <span>&copy; 2080 DMMobile Shop. All rights reserved.</span>
        <div>
          <Link to="/policies/terms" data-testid="footer-terms">Terms & Conditions</Link>
          <Link to="/policies/privacy" data-testid="footer-privacy">Privacy Policy</Link>
        </div>
      </div>
    </footer>
  );
}

/* ========== MAIN HOMEPAGE EXPORT ========== */
export function FuturisticHome({ products, auctions, onAdd, onWish, common, announcements = [], homeConfig = null, Topbar, FooterBar, BottomNav, Loading }) {
  const navigate = useNavigate();
  const [slide, setSlide] = useState(0);
  const display = useMemo(() => [...products].sort((a, b) => (FEATURED_ORDER.indexOf(a.id) + 99) % 99 - (FEATURED_ORDER.indexOf(b.id) + 99) % 99), [products]);
  const primary = display[0] || null;
  const heroDeals = display.slice(0, 3);
  const sections = homeConfig?.sections || [];
  const section = (id) => sections.find((item) => item.id === id) || {};
  const isVisible = (id) => section(id).active !== false;
  const hero = homeConfig?.hero || {};

  useEffect(() => { const t = setInterval(() => setSlide(v => (v + 1) % 4), 5000); return () => clearInterval(t); }, []);

  if (!display.length) return <><Topbar {...common} /><main className="store-page"><Loading /></main><FooterBar /></>;

  return (
    <>
      <Topbar {...common} />

      {/* Announcement Strip */}
      {announcements.length > 0 && (
        <section className="announcement-strip" data-testid="website-announcement-strip">
          <div className="announcement-label" data-testid="website-announcement-label"><Smartphone size={14} /><span>LIVE UPDATE</span></div>
          <div className="announcement-viewport"><div className="announcement-track"><div className="announcement-group">{announcements.slice(0, 6).map(a => <Link to="/category" key={a.id} data-testid={`announcement-${a.id}`}><Smartphone size={13} /><b>{a.title}</b>{a.description && <small>{a.description}</small>}</Link>)}</div><div className="announcement-group announcement-copy" aria-hidden="true">{announcements.slice(0, 6).map(a => <span key={`copy-${a.id}`}><Smartphone size={13} /><b>{a.title}</b>{a.description && <small>{a.description}</small>}</span>)}</div></div></div>
        </section>
      )}

      <main className="store-page futuristic-home marketplace-home" data-testid="futuristic-home">
        {/* Stage: Category Rail + Hero */}
        <div className="marketplace-stage">
          <aside className="marketplace-category-rail" data-testid="marketplace-category-rail">
            <b>Top Categories</b>
            {CATEGORIES.map(c => {
              const Icon = c.icon;
              return <Link key={c.slug + c.label} to={`/category?category=${c.slug}`} data-testid={`marketplace-rail-${c.slug}`}><Icon size={15} /><span>{c.label}</span></Link>;
            })}
            <Link to="/auctions" className="rail-auction" data-testid="marketplace-rail-auctions"><Gavel size={15} /><span>Live Auction</span></Link>
            <Link to="/category?sort=price_desc" className="rail-deals" data-testid="marketplace-rail-deals"><Percent size={15} /><span>Deals & Offers</span></Link>
          </aside>

          {/* Hero + Side Cards */}
          <section className="hero-grid">
            <motion.div className="hero-banner" data-testid="hero-banner" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}>
              <div className="hero-copy">
                <motion.span className="eyebrow" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.5 }}>{hero.eyebrow || "DMMobile Shop · 2080 → 2080"}</motion.span>
                <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.6 }}>
                  {hero.title || primary?.name || "Premium Tech"}<br /><span className="grad">{hero.highlight || "Bigger. Brighter. Smarter."}</span>
                </motion.h1>
                <motion.p className="hero-sub" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>{hero.description || "Smarter Deals | Bigger Savings | Future Ready"}</motion.p>
                <motion.div className="hero-badge" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
                  <b>Starting at</b><span style={{ fontSize: 22, fontWeight: 800 }}>{money(primary?.price || 79999)}</span>
                </motion.div>
                <motion.div className="hero-cta" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}>
                  <Link to="/category" className="primary-btn" data-testid="hero-shop-now">Shop Now <ChevronRight size={15} /></Link>
                  <Link to="/sell" className="ghost-btn" data-testid="hero-sell-device">Sell Your Device</Link>
                </motion.div>
                <motion.div className="hero-trust" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
                  {[[ShieldCheck, "100% Original"], [Wallet, "Secure Pay"], [RotateCcw, "Easy Return"], [BadgeCheck, "Trusted"]].map(([Icon, l]) => <span key={l}><Icon size={14} /> {l}</span>)}
                </motion.div>
              </div>
              {(hero.image_url || primary?.image) && <img src={hero.image_url || primary?.image} alt="Featured device" className="hero-phone" />}
              <div className="hero-dots">{[0, 1, 2, 3].map(d => <i key={d} className={d === slide ? "on" : ""} />)}</div>
            </motion.div>

            {/* Right side cards */}
            <aside className="hot-deals" data-testid="hot-deals">
              <div className="hot-head">
                <b style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "var(--neon-green)", boxShadow: "0 0 10px var(--neon-green)", animation: "neonPulse 2s infinite" }} />
                  Live Auction
                </b>
                <Link to="/auctions" data-testid="hot-deals-view-all">Join Now <ChevronRight size={13} /></Link>
              </div>
              {auctions[0] && (
                <div style={{ textAlign: "center", padding: "8px 0" }}>
                  <img src={auctions[0].product?.image} alt={auctions[0].product?.name} style={{ width: 80, height: 80, objectFit: "cover", borderRadius: 12, margin: "0 auto 8px", display: "block", background: "rgba(10,18,35,0.5)" }} />
                  <b style={{ fontSize: 12, color: "#e2eafc" }}>{auctions[0].product?.name}</b>
                  <strong style={{ display: "block", fontSize: 18, color: "var(--neon-cyan)", margin: "4px 0" }}>{money(auctions[0].current_bid)}</strong>
                  <small style={{ color: "#8fa5c4", fontSize: 10 }}>Current Bid</small>
                </div>
              )}
              <div style={{ borderTop: "1px solid rgba(100,160,255,0.06)", paddingTop: 10, marginTop: 8 }}>
                <div className="hot-head"><b>Wholesale</b><Link to="/category" data-testid="wholesale-link">Start Now <ChevronRight size={13} /></Link></div>
                <small style={{ color: "#8fa5c4", fontSize: 10 }}>Best Rates for Businesses</small>
              </div>
            </aside>
          </section>
        </div>

        {/* Top Brands — directly below the hero banner */}
        {isVisible("top-brands") && <BrandsSection title={section("top-brands").title || "Top Brands"} />}

        {/* Sale Shelves — directly below the hero banner */}
        {isVisible("flash-deals") && <SaleShelf id="flash-deals" title={section("flash-deals").title || "Flash Deals"} eyebrow={section("flash-deals").eyebrow || "LIMITED TIME"} icon={Flame} products={display.slice(0, 6)} onAdd={onAdd} to="/category?sort=price_desc" tone="pink" showTimer />}
        <MajorSaleSections products={display} onAdd={onAdd} sections={sections} />

        {/* Trust Strip */}
        {isVisible("trust-strip") && <TrustStrip />}

        {/* Hot Selling Categories */}
        {isVisible("hot-categories") && <HotSellingCategories title={section("hot-categories").title || "Hot Selling Categories"} />}

        {/* Quad Promo: Auction, Wholesale, Trade-In, Price Drop */}
        {isVisible("marketplace-services") && <QuadPromo />}

        {/* Category Circles */}
        {isVisible("category-navigation") && <motion.section {...fadeUp} className="circle-row" data-testid="category-circles">
          {CATEGORIES.slice(0, 10).map(c => {
            const Icon = c.icon;
            return (
              <Link key={c.label} to={`/category?category=${c.slug}`} className="circle-cat" data-testid={`circle-${c.label.toLowerCase().replace(/\s|&/g, "-")}`}>
                <motion.span className="circle-icon" whileHover={{ scale: 1.1, y: -4 }}><Icon size={22} /></motion.span>
                <small>{c.label.split(" ")[0]}</small>
              </Link>
            );
          })}
        </motion.section>}

        {/* Promo Banners */}
        {isVisible("promo-banners") && <motion.section {...fadeUp} className="promo-row" data-testid="promo-banners">
          <div className="promo promo-a" data-testid="promo-iphone">
            <div><b>Biggest iPhone Deals</b><span>Up to <em>40% OFF</em></span><Link to="/category?category=mobiles" className="promo-btn">Shop iPhones <ChevronRight size={13} /></Link></div>
            {primary?.image && <img src={primary.image} alt="iPhone deals" />}
          </div>
          <div className="promo promo-b" data-testid="promo-laptops">
            <div><b>Laptops for Work & Play</b><span>Top Brands. Great Prices.</span><Link to="/category?category=laptops" className="promo-btn">Explore Laptops <ChevronRight size={13} /></Link></div>
          </div>
          <div className="promo promo-c" data-testid="promo-preowned">
            <div><b>Certified Pre-Owned</b><span>Same Performance. Better Value.</span><Link to="/category" className="promo-btn">Shop Pre-Owned <ChevronRight size={13} /></Link></div>
          </div>
        </motion.section>}

        {/* Trending + Why Choose + Reviews */}
        {isVisible("product-insights") && <TrendingReviewsSection products={display} onAdd={onAdd} onWish={onWish} />}

        {/* Auction Teaser */}
        {isVisible("auction-teaser") && auctions[0] && (
          <motion.section {...fadeScale} className="auction-teaser" data-testid="auction-teaser">
            <div className="auction-teaser-copy">
              <span className="live-pill">LIVE AUCTION</span>
              <h3>{auctions[0].product?.name}</h3>
              <small>Current Bid</small>
              <strong>{money(auctions[0].current_bid)}</strong>
              <Link to="/auctions" className="primary-btn" data-testid="auction-teaser-bid">Bid Now <Gavel size={14} /></Link>
            </div>
            {auctions[0].product?.image && <img src={auctions[0].product.image} alt="Auction" />}
          </motion.section>
        )}

        {/* Blog */}
        {isVisible("blog") && <BlogSection />}

        {/* Community + WhatsApp + Newsletter */}
        {isVisible("customer-community") && <BottomSections />}
      </main>

      <FuturisticFooter />
      <BottomNav />
    </>
  );
}

