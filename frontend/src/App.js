import { useCallback, useEffect, useMemo, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { Toaster, toast } from "sonner";
import {
  Search, ShoppingCart, MapPin, ChevronRight, ChevronLeft, ChevronDown, Sparkles, Gavel, Heart, UserRound,
  Menu, X, Plus, ArrowLeft, Minus, Trash2, Check, Star, Store, Zap, Clock, Download, Apple as AppleIcon,
  Smartphone, Laptop, Watch, Tablet, Headphones, Gamepad2, Camera, Home as HomeIcon, Percent, LayoutGrid,
  Truck, RotateCcw, ShieldCheck, BadgeCheck, LoaderCircle, LogOut, Wallet, Tag,
} from "lucide-react";
import { api, apiError, cardProduct } from "@/api";
import AdminWorkspace from "@/components/AdminWorkspace";
import "@/App.css";

const money = (value = 0) => `₹${Number(value).toLocaleString("en-IN")}`;

const NAV_CATEGORIES = [
  { label: "Mobiles", slug: "mobiles", icon: Smartphone },
  { label: "Laptops", slug: "laptops", icon: Laptop },
  { label: "Smart Watches", slug: "smartwatch", icon: Watch },
  { label: "Tablets", slug: "tablets", icon: Tablet },
  { label: "Accessories", slug: "accessories", icon: LayoutGrid },
  { label: "Gaming", slug: "gaming", icon: Gamepad2 },
  { label: "Cameras", slug: "cameras", icon: Camera },
  { label: "Audio", slug: "audio", icon: Headphones },
  { label: "Home & Living", slug: "home-living", icon: HomeIcon },
];
const CIRCLE_CATEGORIES = [
  { label: "Mobiles", slug: "mobiles", icon: Smartphone },
  { label: "Laptops", slug: "laptops", icon: Laptop },
  { label: "Smart Watches", slug: "smartwatch", icon: Watch },
  { label: "Tablets", slug: "tablets", icon: Tablet },
  { label: "Accessories", slug: "accessories", icon: LayoutGrid },
  { label: "Gaming", slug: "gaming", icon: Gamepad2 },
  { label: "Cameras", slug: "cameras", icon: Camera },
  { label: "Audio", slug: "audio", icon: Headphones },
  { label: "Wearables", slug: "smartwatch", icon: Watch },
  { label: "Home & Living", slug: "home-living", icon: HomeIcon },
  { label: "Deals", slug: "", icon: Percent },
  { label: "More", slug: "", icon: LayoutGrid },
];
const HERO_PHONE = "https://static.prod-images.emergentagent.com/jobs/4d8ba7d6-4cc2-48fd-a329-88470c3b0d75/images/29f5c8a586dbdda9921a2bd753139bccf4cd74c5f0004bb94e7b3148cb72b303.jpeg";
const PREOWNED = "https://static.prod-images.emergentagent.com/jobs/4d8ba7d6-4cc2-48fd-a329-88470c3b0d75/images/f47e5c206f6b238efb5c3026aeb05d74e6898d9d040b4d0cb4249239ca99bbb8.jpeg";

const BADGES = ["Bestseller", "New Launch", "Hot Deal", "Assured", "Top Rated", "Value"];
const rateFor = (id = "") => {
  const seed = [...String(id)].reduce((total, char) => total + char.charCodeAt(0), 0);
  return { stars: (4 + (seed % 9) / 10).toFixed(1), count: `${(4 + (seed % 12))}.${seed % 9}K` };
};

function Brand({ small = false }) {
  return (
    <div className={`brand ${small ? "brand-sm" : ""}`}>
      <span className="brand-mark"><ShoppingCart size={small ? 18 : 22} strokeWidth={2.4} /></span>
      <span className="brand-text"><b>MobileCart</b><small>Buy Smarter. Live Better.</small></span>
    </div>
  );
}
function Loading({ label = "Loading deals…" }) {
  return <div className="empty-state" data-testid="loading-state"><LoaderCircle className="spin" size={30} /><h3>{label}</h3></div>;
}

function Topbar({ cartCount, wishCount = 0, user, onSearch, onLogout, onMenu }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const submit = (event) => { if (event.key === "Enter" && query.trim()) { onSearch(query.trim()); navigate(`/category?search=${encodeURIComponent(query.trim())}`); } };
  return (
    <header className="topbar">
      <div className="topbar-row">
        <button className="icon-btn mobile-only" onClick={onMenu} data-testid="mobile-menu-button"><Menu size={20} /></button>
        <Link to="/" data-testid="brand-home-link"><Brand /></Link>
        <label className="search">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={submit} data-testid="store-search-input" placeholder="Search for iPhones, Laptops, Smartwatches..." />
        </label>
        <button className="deliver" data-testid="deliver-to-button"><MapPin size={16} /><span>Deliver to<b>New Delhi 110085</b></span><ChevronDown size={13} /></button>
        <div className="top-actions">
          <button className="top-link" onClick={() => navigate("/account")} data-testid="wishlist-button"><span className="ic"><Heart size={20} />{wishCount > 0 && <i>{wishCount}</i>}</span></button>
          <Link className="top-link" to="/cart" data-testid="cart-header-button"><span className="ic"><ShoppingCart size={20} />{cartCount > 0 && <i>{cartCount}</i>}</span></Link>
          {user
            ? <button className="top-link acct" onClick={onLogout} data-testid="account-logout-button"><UserRound size={20} /><span className="acct-copy"><small>Hi,</small><b>{user.name.split(" ")[0]}</b></span></button>
            : <Link className="top-link acct" to="/login" data-testid="account-login-link"><UserRound size={20} /><span className="acct-copy"><small>Login /</small><b>Register</b></span></Link>}
          <Link className="sell-btn" to="/sell" data-testid="sell-button">Sell on MobileCart</Link>
        </div>
      </div>
      <nav className="cat-nav">
        <button className="all-cats" onClick={() => navigate("/category")} data-testid="all-categories-button"><Menu size={15} /> All Categories</button>
        {NAV_CATEGORIES.map((category) => (
          <Link key={category.label} to={category.slug ? `/category?category=${category.slug}` : "/category"} data-testid={`nav-cat-${category.slug || category.label.toLowerCase()}`}>{category.label}</Link>
        ))}
        <Link to="/category" className="more-cat" data-testid="nav-cat-more">More <ChevronDown size={12} /></Link>
      </nav>
    </header>
  );
}

function FooterBar() {
  return (
    <footer className="footer-bar">
      <Brand small />
      <div className="footer-feats">
        {[[Truck, "Free Delivery", "All Over India"], [RotateCcw, "Easy Returns", "7-Day Policy"], [ShieldCheck, "Secure Payments", "UPI, Cards, Wallet"], [BadgeCheck, "Verified Sellers", "100% Trusted"]].map(([Icon, title, sub]) => (
          <div className="footer-feat" key={title}><Icon size={20} /><span><b>{title}</b><small>{sub}</small></span></div>
        ))}
      </div>
      <div className="footer-app">
        <button className="download-btn" data-testid="download-app-button"><Download size={16} /> Download Our App</button>
        <div className="app-badges"><span>▶ Shop Anytime</span><AppleIcon size={16} /></div>
      </div>
    </footer>
  );
}

function ProductCard({ product, onAdd, onWish, badge }) {
  const rating = rateFor(product.id);
  return (
    <article className="product-card" data-testid={`product-card-${product.id}`}>
      {badge && <span className="card-badge">{badge}</span>}
      <button className="wish" onClick={() => onWish(product.id)} data-testid={`wishlist-${product.id}`} aria-label={`Save ${product.name}`}><Heart size={15} /></button>
      <Link to={`/product/${product.id}`} data-testid={`product-link-${product.id}`} className="product-media">
        <img src={product.image} alt={product.name} />
      </Link>
      <div className="product-info">
        <Link to={`/product/${product.id}`}><h4>{product.name}</h4></Link>
        <p>{product.sub}</p>
        <div className="rating-line"><span className="stars"><Star size={12} fill="currentColor" /> {rating.stars}</span><small>({rating.count})</small></div>
        <div className="price-row"><strong>{money(product.price)}</strong><del>{money(product.old)}</del><em>{product.off}</em></div>
      </div>
      <button className="add-cart-btn" onClick={() => onAdd(product)} data-testid={`add-product-${product.id}`}><ShoppingCart size={14} /> Add to Cart</button>
    </article>
  );
}

function SectionTitle({ title, action = "View All", to = "/category", extra }) {
  return <div className="section-title"><h2>{title}</h2>{extra}<Link to={to} data-testid={`view-${title.toLowerCase().replaceAll(" ", "-")}-link`}>{action} <ChevronRight size={15} /></Link></div>;
}

function Countdown() {
  const [left, setLeft] = useState(12 * 3600 + 45 * 60 + 30);
  useEffect(() => { const timer = setInterval(() => setLeft((value) => (value > 0 ? value - 1 : 12 * 3600)), 1000); return () => clearInterval(timer); }, []);
  const pad = (value) => String(value).padStart(2, "0");
  return (
    <div className="countdown" data-testid="flash-countdown">
      <span>{pad(Math.floor(left / 3600))}</span>:<span>{pad(Math.floor((left % 3600) / 60))}</span>:<span>{pad(left % 60)}</span>
    </div>
  );
}

function StoreHome({ products, auctions, onAdd, onWish, common }) {
  const [slide, setSlide] = useState(0);
  const [tab, setTab] = useState("All");
  const order = ["iphone", "samsung", "macbook", "boat-airdopes-141", "pixel-7", "nothing-phone-2"];
  const display = useMemo(() => [...products].sort((a, b) => (order.indexOf(a.id) + 99) % 99 - (order.indexOf(b.id) + 99) % 99), [products]);
  const heroDeals = display.slice(0, 3);
  const trending = display.filter((product) => tab === "All" || product.category_slug === tab.toLowerCase().replace(" ", ""));
  useEffect(() => { const timer = setInterval(() => setSlide((value) => (value + 1) % 4), 4000); return () => clearInterval(timer); }, []);
  if (!display.length) return <><Topbar {...common} /><main className="store-page"><Loading /></main><FooterBar /></>;

  return (
    <>
      <Topbar {...common} />
      <main className="store-page">
        <section className="hero-grid">
          <div className="hero-banner" data-testid="hero-banner">
            <div className="hero-copy">
              <span className="eyebrow">PREMIUM TECH. SMARTER PRICES.</span>
              <h1>Upgrade<br /><span className="grad">Your World</span></h1>
              <p className="hero-sub">New &amp; Pre-owned Devices • Verified Sellers • Best Deals</p>
              <div className="hero-badge"><b>{display[0].name}</b><span>Up to <em>40% OFF</em></span></div>
              <div className="hero-cta">
                <Link to="/category" className="primary-btn" data-testid="hero-shop-now">Shop Now <ChevronRight size={15} /></Link>
                <Link to="/sell" className="ghost-btn" data-testid="hero-sell-device">Sell Your Device</Link>
              </div>
              <div className="hero-trust">
                {[[ShieldCheck, "Verified Products"], [Wallet, "Secure Payments"], [RotateCcw, "7-Day Return"], [BadgeCheck, "Trusted Sellers"]].map(([Icon, label]) => (
                  <span key={label}><Icon size={15} /> {label}</span>
                ))}
              </div>
            </div>
            <img src={HERO_PHONE} alt="Featured device" className="hero-phone" />
            <button className="hero-arrow left" onClick={() => setSlide((slide + 3) % 4)} data-testid="hero-prev"><ChevronLeft size={18} /></button>
            <button className="hero-arrow right" onClick={() => setSlide((slide + 1) % 4)} data-testid="hero-next"><ChevronRight size={18} /></button>
            <div className="hero-dots">{[0, 1, 2, 3].map((dot) => <i key={dot} className={dot === slide ? "on" : ""} />)}</div>
          </div>
          <aside className="hot-deals" data-testid="hot-deals">
            <div className="hot-head"><b>Today's Hot Deals</b><Link to="/category?sort=price_desc" data-testid="hot-deals-view-all">View All <ChevronRight size={13} /></Link></div>
            {heroDeals.map((product) => (
              <div className="hot-item" key={product.id} data-testid={`hot-deal-${product.id}`}>
                <img src={product.image} alt={product.name} />
                <div className="hot-copy"><b>{product.name}</b><small>{product.sub}</small><strong>{money(product.price)}</strong><em>{product.off}</em></div>
                <button onClick={() => onAdd(product)} data-testid={`hot-add-${product.id}`}><ShoppingCart size={15} /></button>
              </div>
            ))}
          </aside>
        </section>

        <section className="circle-row">
          {CIRCLE_CATEGORIES.map((category) => {
            const Icon = category.icon;
            return (
              <Link key={category.label} to={category.slug ? `/category?category=${category.slug}` : "/category"} className="circle-cat" data-testid={`circle-${category.label.toLowerCase().replace(/ & | /g, "-")}`}>
                <span className="circle-icon"><Icon size={22} /></span>
                <small>{category.label}</small>
              </Link>
            );
          })}
        </section>

        <section className="promo-row">
          <div className="promo promo-a" data-testid="promo-iphone">
            <div><b>Biggest iPhone Deals</b><span>Up to <em>40% OFF</em></span><Link to="/category?category=mobiles" className="promo-btn">Shop iPhones <ChevronRight size={13} /></Link></div>
            <img src={display[0].image} alt="iPhone deals" />
          </div>
          <div className="promo promo-b" data-testid="promo-laptops">
            <div><b>Laptops for Work &amp; Play</b><span>Top Brands. Great Prices.</span><Link to="/category?category=laptops" className="promo-btn">Explore Laptops <ChevronRight size={13} /></Link></div>
            <img src={display.find((product) => product.category_slug === "laptops")?.image || display[2].image} alt="Laptops" />
          </div>
          <div className="promo promo-c" data-testid="promo-preowned">
            <div><b>Certified Pre-Owned</b><span>Same Performance. Better Value.</span>
              <div className="promo-ticks"><span><Check size={11} /> Quality Checked</span><span><Check size={11} /> 6 Months Warranty</span><span><Check size={11} /> Best Price</span></div>
              <Link to="/category" className="promo-btn">Shop Pre-Owned <ChevronRight size={13} /></Link>
            </div>
            <img src={PREOWNED} alt="Pre-owned devices" />
          </div>
        </section>

        <section className="trending-wrap">
          <div className="trending-main">
            <div className="section-title trending-head">
              <h2>Trending Products</h2>
              <div className="pill-tabs">
                {["All", "Mobiles", "Laptops", "Smart Watches", "Accessories", "Tablets", "Gaming"].map((label) => (
                  <button key={label} className={tab === label ? "on" : ""} onClick={() => setTab(label)} data-testid={`trending-tab-${label.toLowerCase().replace(" ", "-")}`}>{label}</button>
                ))}
              </div>
              <Link to="/category" data-testid="trending-view-all">View All <ChevronRight size={15} /></Link>
            </div>
            <div className="product-grid grid-5">
              {(trending.length ? trending : display).map((product, index) => (
                <ProductCard product={product} onAdd={onAdd} onWish={onWish} badge={BADGES[index % BADGES.length]} key={product.id} />
              ))}
            </div>
          </div>
          <aside className="why-choose" data-testid="why-choose">
            <b>Why Choose MobileCart?</b>
            {[[BadgeCheck, "Verified Sellers", "Only trusted & verified sellers"], [ShieldCheck, "Quality Checked", "Every product inspected"], [Percent, "Best Prices", "Unbeatable deals on top brands"], [Wallet, "Secure Payments", "100% safe & encrypted"], [RotateCcw, "7-Day Returns", "Hassle-free returns"], [Headphones, "Dedicated Support", "We're here to help"]].map(([Icon, title, sub]) => (
              <div className="why-row" key={title}><span><Icon size={16} /></span><div><b>{title}</b><small>{sub}</small></div></div>
            ))}
          </aside>
        </section>

        <section className="flash-wrap">
          <SectionTitle title="Flash Deals" action="View All" to="/category?sort=price_desc" extra={<div className="flash-timer"><Clock size={14} /> Ends in <Countdown /></div>} />
          <div className="product-grid grid-6 flash-grid">
            {display.map((product, index) => (
              <article className="flash-card" key={product.id} data-testid={`flash-card-${product.id}`}>
                <span className="flash-off">{product.off}</span>
                <Link to={`/product/${product.id}`}><img src={product.image} alt={product.name} /></Link>
                <b>{product.name}</b><strong>{money(product.price)}</strong>
                <button onClick={() => onAdd(product)} data-testid={`flash-add-${product.id}`}>Grab Deal</button>
              </article>
            ))}
          </div>
        </section>

        <section className="lower-grid">
          <div className="brands-panel">
            <SectionTitle title="Top Brands" action="View All" to="/category" />
            <div className="brand-row">
              {["Apple", "Samsung", "OnePlus", "Mi", "boAt"].map((brand) => (
                <Link to="/category" className="brand-chip" key={brand} data-testid={`brand-${brand.toLowerCase()}`}>{brand}</Link>
              ))}
            </div>
          </div>
          <div className="recent-panel">
            <SectionTitle title="Recently Viewed" action="View All" to="/category" />
            <div className="recent-row">
              {display.slice(0, 5).map((product) => (
                <Link to={`/product/${product.id}`} className="recent-item" key={product.id} data-testid={`recent-${product.id}`}><img src={product.image} alt={product.name} /></Link>
              ))}
            </div>
          </div>
        </section>

        {auctions[0] && (
          <section className="auction-teaser" data-testid="auction-teaser">
            <div className="auction-teaser-copy"><span className="live-pill">LIVE AUCTION</span><h3>{auctions[0].product?.name}</h3><small>Current Bid</small><strong>{money(auctions[0].current_bid)}</strong><Link to="/auctions" className="primary-btn" data-testid="auction-teaser-bid">Bid Now <Gavel size={14} /></Link></div>
            <img src={auctions[0].product?.image} alt="Auction" />
          </section>
        )}
      </main>
      <FooterBar />
      <BottomNav />
    </>
  );
}

function BottomNav({ active = "Home" }) {
  const items = [["Home", "/", HomeIcon], ["Categories", "/category", LayoutGrid], ["AI Deals", "/category?sort=price_desc", Sparkles], ["Auction", "/auctions", Gavel], ["Account", "/account", UserRound]];
  return <nav className="bottom-nav">{items.map(([label, to, Icon]) => <Link className={active === label ? "active" : ""} to={to} key={label} data-testid={`bottom-nav-${label.toLowerCase().replace(" ", "-")}`}><Icon size={19} /><span>{label}</span></Link>)}</nav>;
}

function ProductPage({ onAdd, onWish, common }) {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { setLoading(true); api.get(`/api/products/${id}`).then(({ data }) => setProduct(cardProduct(data))).catch(() => toast.error("Product could not be found")).finally(() => setLoading(false)); }, [id]);
  if (loading) return <><Topbar {...common} /><main className="detail-page"><Loading /></main><FooterBar /></>;
  if (!product) return <Navigate to="/" replace />;
  const rating = rateFor(product.id);
  return (
    <>
      <Topbar {...common} />
      <main className="detail-page">
        <Link to="/" className="back-link" data-testid="product-back-link"><ArrowLeft size={16} /> Back to store</Link>
        <div className="detail-grid">
          <div className="detail-image"><img src={product.image} alt={product.name} /><button onClick={() => onWish(product.id)} data-testid="detail-wishlist" aria-label="Save product"><Heart /></button></div>
          <div className="detail-copy">
            <span className="eyebrow">MOBILECART ASSURED</span>
            <h1>{product.name}</h1>
            <p className="subline">{product.sub} <span className="verified"><BadgeCheck size={13} /> Assured</span></p>
            <div className="rating"><Star size={14} fill="currentColor" /> {rating.stars} <span>({rating.count} Reviews)</span></div>
            <div className="price-line"><strong>{money(product.price)}</strong><del>{money(product.old)}</del><em>{product.off}</em></div>
            <small className="emi">EMI from {money(Math.round(product.price / 20))}/month</small>
            <div className="chips">{(product.variants?.length ? product.variants.map((variant) => variant.name) : ["Assured", "In Stock", "Fast Delivery"]).map((value) => <button key={value} data-testid={`variant-${String(value).toLowerCase().replaceAll(" ", "-")}`}>{value}</button>)}</div>
            <div className="delivery"><MapPin size={18} /><span>Deliver to <b>New Delhi 110085</b><small>Free delivery in 3-5 days</small></span><Link to="/account" data-testid="change-address-button">Change</Link></div>
            <div className="seller"><Store size={20} /><div>Sold by <b>CellPoint Store</b></div><strong>Top Rated Seller<br />4.7 ★</strong></div>
            <div className="detail-actions">
              <button className="ghost-btn" onClick={() => onAdd(product)} data-testid="detail-add-to-cart">Add to Cart</button>
              <button className="primary-btn" onClick={() => onAdd(product, true)} data-testid="detail-buy-now">Buy Now</button>
            </div>
          </div>
        </div>
      </main>
      <FooterBar />
      <BottomNav active="" />
    </>
  );
}

function CartPage({ cart, onAdd, onSet, onRemove, common }) {
  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  return (
    <>
      <Topbar {...common} />
      <main className="cart-page">
        <div className="cart-head"><div><span className="eyebrow">YOUR BAG</span><h1>My Cart <small>({common.cartCount} items)</small></h1></div><Link to="/" data-testid="continue-shopping-link">Continue shopping <ChevronRight size={16} /></Link></div>
        <div className="cart-layout">
          <section className="cart-items">
            {cart.length ? cart.map((item) => (
              <div className="cart-item" key={`${item.id}-${item.variant_sku || "base"}`} data-testid={`cart-item-${item.id}`}>
                <img src={item.image} alt="" />
                <div className="cart-item-copy"><b>{item.name}</b><small>{item.sub}</small><strong>{money(item.price)}</strong></div>
                <button onClick={() => onRemove(item.id)} data-testid={`remove-cart-${item.id}`} aria-label={`Remove ${item.name}`}><Trash2 size={16} /></button>
                <div className="quantity"><button onClick={() => onSet(item, item.quantity - 1)} data-testid={`decrease-${item.id}`}><Minus size={13} /></button><span>{item.quantity}</span><button onClick={() => onAdd(item)} data-testid={`increase-${item.id}`}><Plus size={13} /></button></div>
              </div>
            )) : <div className="empty-state"><ShoppingCart size={38} /><h3>Your cart is waiting</h3><Link to="/" className="primary-btn" data-testid="empty-cart-shop-button">Explore deals</Link></div>}
          </section>
          <aside className="summary">
            <h3>Order Summary</h3>
            <div><span>Subtotal</span><b>{money(total)}</b></div>
            <div><span>Platform fee</span><b>₹99</b></div>
            <div><span>Delivery</span><b className="green-text">FREE</b></div>
            <hr />
            <div className="total"><span>Total</span><strong>{money(total + (cart.length ? 99 : 0))}</strong></div>
            <Link to="/checkout" className="primary-btn full" data-testid="proceed-checkout-button">Proceed to Checkout <ChevronRight size={17} /></Link>
            <small className="secure"><ShieldCheck size={12} /> Secure checkout · 100% protected</small>
          </aside>
        </div>
      </main>
      <FooterBar />
      <BottomNav active="" />
    </>
  );
}

function AddressForm({ onDone }) {
  const [form, setForm] = useState({ label: "HOME", recipient_name: "", phone: "", line1: "", line2: "", city: "New Delhi", state: "Delhi", postal_code: "", country: "India" });
  const [busy, setBusy] = useState(false);
  const save = async (event) => { event.preventDefault(); setBusy(true); try { await api.post("/api/auth/me/addresses", form); await onDone(); toast.success("Address saved"); } catch (error) { toast.error(apiError(error)); } finally { setBusy(false); } };
  return (
    <form className="checkout-section address-form" onSubmit={save} data-testid="address-form">
      <h3>Delivery address</h3>
      {[["recipient_name", "Full name"], ["phone", "Phone number"], ["line1", "Address line"], ["city", "City"], ["state", "State"], ["postal_code", "PIN code"]].map(([key, label]) => (
        <input key={key} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} placeholder={label} required data-testid={`address-${key}-input`} />
      ))}
      <button className="primary-btn" disabled={busy} data-testid="save-address-button">{busy ? "Saving…" : "Save address"}</button>
    </form>
  );
}

function Checkout({ cart, user, refreshUser, refreshCart, common }) {
  const [paid, setPaid] = useState(false);
  const [method, setMethod] = useState("upi");
  const [busy, setBusy] = useState(false);
  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0) + 99;
  const address = user?.addresses?.[0];
  const place = async () => {
    if (!address) return; setBusy(true);
    try { const { data } = await api.post("/api/orders", { address_id: address.id, payment_method: method }); setPaid(data); await refreshCart(); toast.success("Order placed successfully"); }
    catch (error) { toast.error(apiError(error)); } finally { setBusy(false); }
  };
  return (
    <>
      <Topbar {...common} />
      <main className="checkout-page">
        <Link to="/cart" className="back-link" data-testid="checkout-back-link"><ArrowLeft size={16} /> Back to cart</Link>
        <div className="checkout-steps"><span className="done">1<br /><small>Address</small></span><i /><span className="active">2<br /><small>Payment</small></span><i /><span>3<br /><small>Place Order</small></span></div>
        {paid ? (
          <div className="success-state" data-testid="order-success"><div className="success-icon"><Check /></div><h1>Order placed!</h1><p>Your order #{paid.order_number} is confirmed. We'll keep you posted.</p><Link to="/account" className="primary-btn" data-testid="success-orders-button">View my orders</Link></div>
        ) : !address ? <AddressForm onDone={refreshUser} /> : (
          <div className="checkout-grid">
            <section>
              <div className="checkout-section"><h3>Delivery address <Link to="/account" data-testid="change-checkout-address">Change</Link></h3><div className="address-card"><b>{address.label}</b><p>{address.recipient_name}</p><span>{address.line1}<br />{address.city} - {address.postal_code}<br />{address.phone}</span></div></div>
              <div className="checkout-section"><h3>Payment Options</h3>
                {[["upi", "UPI", "Pay using any UPI app"], ["card", "Credit / Debit Card", "Visa, Mastercard, RuPay"], ["net_banking", "Net Banking", "All major banks"], ["wallet", "Wallet", "Paytm, PhonePe, Amazon Pay"], ["cod", "COD", "Cash on Delivery"]].map(([value, label, detail]) => (
                  <label className="payment-option" key={value}><input type="radio" name="payment" checked={method === value} onChange={() => setMethod(value)} data-testid={`payment-${value}`} /><span>{label}<small>{detail}</small></span><ChevronRight size={15} /></label>
                ))}
              </div>
            </section>
            <aside className="summary">
              <h3>Payment Summary</h3>
              <div><span>Items total</span><b>{money(total - 99)}</b></div>
              <div><span>Platform fee</span><b>₹99</b></div>
              <div><span>Delivery</span><b className="green-text">FREE</b></div>
              <hr />
              <div className="total"><span>Payable Now</span><strong>{money(total)}</strong></div>
              <button onClick={place} disabled={busy || !cart.length} className="primary-btn full" data-testid="place-order-button">{busy ? "Placing order…" : method === "cod" ? "Place COD Order" : `Pay ${money(total)} Now`}</button>
              <small className="secure"><ShieldCheck size={12} /> 100% secure payment</small>
            </aside>
          </div>
        )}
      </main>
      <FooterBar />
    </>
  );
}

function Auctions({ auctions, user, refreshAuctions, common }) {
  const [bidBusy, setBidBusy] = useState(false);
  const auction = auctions[0];
  const placeBid = async () => {
    if (!user) { toast.error("Please sign in to place a bid"); return; }
    setBidBusy(true);
    try { await api.post(`/api/auctions/${auction.id}/bids`, { amount: auction.current_bid + auction.bid_increment }); await refreshAuctions(); toast.success(`Bid placed at ${money(auction.current_bid + auction.bid_increment)}`); }
    catch (error) { toast.error(apiError(error)); } finally { setBidBusy(false); }
  };
  return (
    <>
      <Topbar {...common} />
      <main className="simple-page">
        <div className="page-heading"><div><span className="eyebrow">MOBILECART LIVE</span><h1>Auctions</h1><p>Bid smart. Win better deals.</p></div><div className="tabs"><button className="active" data-testid="auction-live-tab">Live Now</button><button data-testid="auction-upcoming-tab">Upcoming</button><button data-testid="auction-watchlist-tab">Watchlist</button></div></div>
        {!auction ? <Loading label="Loading live auctions…" /> : (
          <div className="auction-detail">
            <div className="auction-visual"><span className="live-pill">LIVE · {auction.bid_count} BIDS</span><img src={auction.product?.image} alt={auction.product?.name} /></div>
            <div className="auction-copy">
              <h2>{auction.product?.name}</h2><p>{auction.product?.sub}</p>
              <div className="bid-stats"><span>Starting Price <b>{money(auction.starting_price)}</b></span><span>Highest Bid <b>{money(auction.current_bid)}</b></span><span>Bid Increment <b>{money(auction.bid_increment)}</b></span></div>
              <div className="bid-progress"><span style={{ width: "68%" }} /></div>
              <small className="green-text">● Live until {new Date(auction.ends_at).toLocaleDateString("en-IN")}</small>
              <button className="primary-btn full" disabled={bidBusy} onClick={placeBid} data-testid="place-bid-button">{bidBusy ? "Submitting…" : `Place Bid ${money(auction.current_bid + auction.bid_increment)}`}</button>
              <div className="auction-footer"><button data-testid="auto-bid-button">Auto Bid</button><button data-testid="watch-auction-button">＋ Watch</button></div>
            </div>
          </div>
        )}
        <SectionTitle title="More Live Auctions" action="View all" />
        <div className="product-grid grid-4">{auctions.slice(1).map((entry) => <ProductCard product={entry.product} onAdd={() => {}} onWish={() => {}} key={entry.id} />)}</div>
      </main>
      <FooterBar />
      <BottomNav active="Auction" />
    </>
  );
}

function SellPage({ common }) {
  return (
    <>
      <Topbar {...common} />
      <main className="simple-page">
        <div className="page-heading"><div><span className="eyebrow">SELL ON MOBILECART</span><h1>Sell Your Device</h1><p>Turn your old gadgets into instant cash.</p></div></div>
        <div className="sell-grid">
          {[[Smartphone, "Get Instant Quote", "AI-powered price in seconds"], [Truck, "Free Pickup", "Doorstep pickup across India"], [Wallet, "Instant Payment", "Money in your wallet same day"]].map(([Icon, title, sub]) => (
            <div className="sell-card" key={title}><span><Icon size={26} /></span><b>{title}</b><small>{sub}</small></div>
          ))}
        </div>
        <div className="sell-cta"><b>Ready to sell?</b><Link to="/account" className="primary-btn" data-testid="sell-start-button">Start Selling <ChevronRight size={15} /></Link></div>
      </main>
      <FooterBar />
      <BottomNav active="" />
    </>
  );
}

function Login({ setUser }) {
  const navigate = useNavigate(); const location = useLocation();
  const [register, setRegister] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true);
    try {
      const endpoint = register ? "/api/auth/register" : "/api/auth/login";
      const payload = register ? form : { email: form.email, password: form.password };
      const { data } = await api.post(endpoint, payload);
      setUser(data); toast.success(register ? "Account created" : "Welcome back");
      navigate(data.role === "admin" ? "/admin" : new URLSearchParams(location.search).get("next") || "/");
    } catch (error) { toast.error(apiError(error)); } finally { setBusy(false); }
  };
  return (
    <main className="auth-page">
      <Link to="/" data-testid="login-brand-link"><Brand /></Link>
      <form className="auth-card" onSubmit={submit} data-testid="auth-form">
        <span className="eyebrow">MOBILECART ACCOUNT</span>
        <h1>{register ? "Create your account" : "Welcome back"}</h1>
        {register && <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Full name" required data-testid="register-name-input" />}
        <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email address" required data-testid="auth-email-input" />
        <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Password" minLength="8" required data-testid="auth-password-input" />
        <button className="primary-btn full" disabled={busy} data-testid="auth-submit-button">{busy ? "Please wait…" : register ? "Create account" : "Sign in"}</button>
        <button type="button" className="auth-switch" onClick={() => setRegister(!register)} data-testid="auth-switch-button">{register ? "Already have an account? Sign in" : "New to MobileCart? Create account"}</button>
      </form>
    </main>
  );
}

function Account({ user, setUser, common }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { if (user) api.get("/api/orders").then(({ data }) => setOrders(data.items)).catch((error) => toast.error(apiError(error))).finally(() => setLoading(false)); }, [user]);
  if (!user) return <Navigate to="/login?next=/account" replace />;
  return (
    <>
      <Topbar {...common} />
      <main className="simple-page account-page">
        <div className="page-heading"><div><span className="eyebrow">MY MOBILECART</span><h1>{user.name}</h1><p>{user.email}</p></div><button className="ghost-btn" onClick={async () => { await api.post("/api/auth/logout"); setUser(null); }} data-testid="account-signout-button"><LogOut size={15} /> Sign out</button></div>
        <section className="checkout-section"><h3>Saved addresses</h3>{user.addresses?.length ? user.addresses.map((address) => <div className="address-card" key={address.id} data-testid={`saved-address-${address.id}`}><b>{address.label}</b><p>{address.recipient_name}</p><span>{address.line1}, {address.city} - {address.postal_code}</span></div>) : <p>No saved addresses yet. Add one during checkout.</p>}</section>
        <section className="admin-panel table-panel orders-panel"><div className="panel-head"><h2>My Orders</h2></div>{loading ? <Loading label="Loading orders…" /> : <table data-testid="orders-table"><thead><tr><th>Order ID</th><th>Total</th><th>Status</th><th>Date</th></tr></thead><tbody>{orders.length ? orders.map((order) => <tr key={order.id}><td>{order.order_number}</td><td>{money(order.total)}</td><td className={`status-${order.status}`}>{order.status.replaceAll("_", " ")}</td><td>{new Date(order.created_at).toLocaleDateString("en-IN")}</td></tr>) : <tr><td colSpan="4">No orders yet</td></tr>}</tbody></table>}</section>
      </main>
      <FooterBar />
      <BottomNav active="Account" />
    </>
  );
}

function CategoryPage({ products, onAdd, onWish, common, refreshProducts, categories }) {
  const location = useLocation();
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const value = new URLSearchParams();
    if (params.get("category")) value.set("category", params.get("category"));
    if (params.get("search")) value.set("query", params.get("search"));
    if (params.get("sort")) value.set("sort", params.get("sort"));
    refreshProducts(value.toString() ? `?${value}` : "");
  }, [location.search, refreshProducts]);
  return (
    <>
      <Topbar {...common} />
      <main className="simple-page">
        <div className="page-heading"><div><span className="eyebrow">SHOP BY CATEGORY</span><h1>Find your next favourite</h1></div></div>
        <div className="cat-chip-row">{categories.map((category) => <Link to={`/category?category=${category.slug}`} key={category.id} data-testid={`catalog-category-${category.slug}`}>{category.name}</Link>)}</div>
        <div className="product-grid grid-4 category-products">{products.map((product, index) => <ProductCard product={product} onAdd={onAdd} onWish={onWish} badge={BADGES[index % BADGES.length]} key={product.id} />)}</div>
      </main>
      <FooterBar />
      <BottomNav active="Categories" />
    </>
  );
}

function AdminRoute({ user }) { return user?.role === "admin" ? <AdminWorkspace /> : <Navigate to="/login?next=/admin" replace />; }

function App() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [auctions, setAuctions] = useState([]);
  const [cart, setCart] = useState([]);
  const [wishCount, setWishCount] = useState(0);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const refreshProducts = useCallback(async (params = "") => { try { const { data } = await api.get(`/api/products${params}`); setProducts(data.items.map(cardProduct)); } catch (error) { toast.error(apiError(error)); } }, []);
  const refreshAuctions = useCallback(async () => { try { const { data } = await api.get("/api/auctions"); setAuctions(data.map((entry) => ({ ...entry, product: entry.product ? cardProduct(entry.product) : null }))); } catch (error) { toast.error(apiError(error)); } }, []);
  const refreshCart = useCallback(async () => { if (!user) { setCart([]); return; } try { const { data } = await api.get("/api/cart"); setCart(data.items.map((item) => ({ ...cardProduct(item.product), quantity: item.quantity, variant_sku: item.variant_sku }))); } catch (error) { if (error.response?.status === 401) setUser(null); else toast.error(apiError(error)); } }, [user]);
  const refreshWish = useCallback(async () => { if (!user) { setWishCount(0); return; } try { const { data } = await api.get("/api/wishlist"); setWishCount(data.length); } catch { setWishCount(0); } }, [user]);
  const refreshUser = useCallback(async () => { try { const { data } = await api.get("/api/auth/me"); setUser(data); return data; } catch { return null; } }, []);
  useEffect(() => { api.get("/api/auth/me").then(({ data }) => setUser(data)).catch(() => setUser(null)).finally(() => setAuthLoading(false)); api.get("/api/categories").then(({ data }) => setCategories(data)).catch(() => setCategories([])); refreshProducts(); refreshAuctions(); }, [refreshProducts, refreshAuctions]);
  useEffect(() => { if (!authLoading) { refreshCart(); refreshWish(); } }, [authLoading, user, refreshCart, refreshWish]);
  const add = async (product, buyNow = false) => { if (!user) { toast.error("Please sign in to save your cart"); navigate("/login?next=/cart"); return; } try { await api.post("/api/cart/items", { product_id: product.id, quantity: 1 }); await refreshCart(); toast.success(`${product.name} added to cart`); if (buyNow) navigate("/cart"); } catch (error) { toast.error(apiError(error)); } };
  const setQuantity = async (item, quantity) => { try { if (quantity < 1) await api.delete(`/api/cart/items/${item.id}`); else await api.patch(`/api/cart/items/${item.id}`, { product_id: item.id, quantity }); await refreshCart(); } catch (error) { toast.error(apiError(error)); } };
  const remove = async (id) => { try { await api.delete(`/api/cart/items/${id}`); await refreshCart(); toast.success("Removed from cart"); } catch (error) { toast.error(apiError(error)); } };
  const wish = async (id) => { if (!user) { navigate("/login"); return; } try { await api.put(`/api/wishlist/${id}`); await refreshWish(); toast.success("Saved to wishlist"); } catch (error) { toast.error(apiError(error)); } };
  const logout = async () => { try { await api.post("/api/auth/logout"); } finally { setUser(null); setCart([]); setWishCount(0); navigate("/"); toast.success("Signed out"); } };
  const common = { cartCount: cart.reduce((sum, item) => sum + item.quantity, 0), wishCount, user, onSearch: (query) => refreshProducts(`?query=${encodeURIComponent(query)}`), onLogout: logout, onMenu: () => navigate("/account") };
  if (authLoading) return <Loading label="Connecting to MobileCart…" />;
  return (
    <>
      <Toaster theme="dark" position="bottom-right" />
      <Routes>
        <Route path="/login" element={<Login setUser={setUser} />} />
        <Route path="/admin/*" element={<AdminRoute user={user} />} />
        <Route path="/product/:id" element={<ProductPage onAdd={add} onWish={wish} common={common} />} />
        <Route path="/cart" element={user ? <CartPage cart={cart} onAdd={add} onSet={setQuantity} onRemove={remove} common={common} /> : <Navigate to="/login?next=/cart" replace />} />
        <Route path="/checkout" element={user ? <Checkout cart={cart} user={user} refreshUser={refreshUser} refreshCart={refreshCart} common={common} /> : <Navigate to="/login?next=/checkout" replace />} />
        <Route path="/auctions" element={<Auctions auctions={auctions} user={user} refreshAuctions={refreshAuctions} common={common} />} />
        <Route path="/sell" element={<SellPage common={common} />} />
        <Route path="/account" element={<Account user={user} setUser={setUser} common={common} />} />
        <Route path="/category" element={<CategoryPage products={products} onAdd={add} onWish={wish} common={common} refreshProducts={refreshProducts} categories={categories} />} />
        <Route path="*" element={<StoreHome products={products} auctions={auctions} onAdd={add} onWish={wish} common={common} />} />
      </Routes>
    </>
  );
}

export default function Root() { return <BrowserRouter><App /></BrowserRouter>; }
