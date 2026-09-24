import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bell, ChevronRight, CreditCard, Gavel, LayoutDashboard, Menu, Package, Settings, ShoppingCart, Tags, TrendingUp, TrendingUp as TrendUp, Users, WalletCards, X } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/api";
import AdminProductManager from "@/components/AdminProductManager";
import AdminResourceManager from "@/components/AdminResourceManager";
import AdminWalletManager from "@/components/AdminWalletManager";
import AdminPaymentSettings from "@/components/AdminPaymentSettings";
import { AdminOrderManager } from "@/components/OrderViews";
import { AdminChatManager } from "@/components/LiveChat";
import AdminReturnManager from "@/components/AdminReturnManager";
import { CategoryManager, UserManager, WorkflowManager } from "@/components/AdminOperationsManager";

const sectionGroups = [
  ["dashboard", "Dashboard", "dashboard", LayoutDashboard], ["users", "Users", "users", Users], ["vendors", "Vendors", "resource", Users], ["products", "Products", "products", Package], ["categories", "Categories", "categories", Tags], ["brands", "Brands", "resource", Tags], ["orders", "Orders", "orders", Package], ["payments", "Payments", "payments", WalletCards], ["razorpay-settings", "Razorpay & Payments", "payment-settings", CreditCard], ["wallet-withdrawals", "Wallet & Withdrawals", "wallet", WalletCards], ["auctions", "Auctions", "auctions", Gavel], ["campaigns", "Campaigns", "resource", TrendingUp], ["coupons", "Coupons", "resource", Tags], ["announcements", "Announcements", "resource", Bell], ["subscriptions", "Subscriptions", "resource", Package], ["app-manager", "App Manager", "resource", LayoutDashboard], ["banners", "Banners", "resource", Tags], ["notifications", "Notifications", "resource", Bell], ["returns-refunds", "Returns & Refunds", "returns", Package], ["shipping", "Shipping", "resource", Package], ["gst-tax", "GST & Tax", "resource", Tags], ["reports-analytics", "Reports & Analytics", "reports", TrendingUp], ["support-tickets", "Support Tickets", "support", Bell], ["admin-users", "Admin Users", "admin-users", Users], ["settings", "Settings", "resource", Settings],
];
const money = (value = 0) => `₹${Number(value).toLocaleString("en-IN")}`;

function Sidebar({ active, open, onClose }) { return <aside className={`admin-sidebar ${open ? "open" : ""}`} data-testid="admin-sidebar"><div className="admin-brand"><Link to="/admin" data-testid="admin-brand-link"><div className="brand"><span className="brand-mark"><Package size={20} /></span><span className="brand-text"><b>DM Mobile</b><small>DMobileMart Control</small></span></div></Link><button onClick={onClose} className="mobile-only icon-btn" data-testid="close-admin-menu"><X /></button></div><nav>{sectionGroups.map(([id, label, , Icon]) => <Link to={id === "dashboard" ? "/admin" : `/admin/${id}`} className={active === id ? "active" : ""} key={id} data-testid={`admin-nav-${id}`}><Icon />{label}</Link>)}</nav><div className="admin-user" data-testid="admin-user-info"><span>AD</span><div><b>Admin</b><small>Live control enabled</small></div><ChevronRight size={16} /></div></aside>; }

function Header({ title, onMenu, query, setQuery }) { return <header className="admin-top"><button className="mobile-only icon-btn" onClick={onMenu} data-testid="admin-menu-button"><Menu /></button><div><h1>{title}</h1><p data-testid="admin-page-subtitle">Every saved change updates DM Mobile live data.</p></div><label className="admin-quick-find"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`Find in ${title}`} data-testid="admin-section-search-input" /></label><div className="admin-actions"><span className="live-pill" data-testid="admin-live-status">LIVE DATA</span><Link to="/" data-testid="admin-store-link">View Store</Link></div></header>; }

const STATUS_COLORS = { delivered: "#20d6a2", confirmed: "#28b4db", packed: "#8050ef", shipped: "#4f8cff", payment_pending: "#f39c33", pending: "#f39c33", cancelled: "#ec526d" };
const statusColor = (status) => STATUS_COLORS[status] || "#7c8bb0";
const prettyStatus = (status = "") => status.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

function Dashboard() {
  const [data, setData] = useState(null);
  useEffect(() => { const fetchDash = () => api.get(`/api/admin/dashboard?_live=${Date.now()}`).then(({ data: response }) => setData(response)).catch((error) => toast.error(apiError(error))); fetchDash(); const timer = setInterval(fetchDash, 5000); return () => clearInterval(timer); }, []);
  if (!data) return <div className="empty-state" data-testid="admin-dashboard-loading"><Package size={30} /><h3>Loading live dashboard…</h3></div>;
  const { metrics, recent_orders: orders, order_statuses: statuses, activities, top_categories: categories = [], revenue_series: series = [] } = data;
  const totalStatus = Object.values(statuses).reduce((sum, value) => sum + value, 0) || 1;
  let cursor = 0;
  const donutStops = Object.entries(statuses).map(([status, count]) => { const start = (cursor / totalStatus) * 100; cursor += count; const end = (cursor / totalStatus) * 100; return `${statusColor(status)} ${start}% ${end}%`; });
  const donutStyle = { background: `conic-gradient(${donutStops.length ? donutStops.join(",") : "#1a2b48 0 100%"})` };
  const maxRevenue = Math.max(1, ...series.map((point) => point.value));
  const statCards = [
    ["Total revenue", money(metrics.total_revenue), WalletCards, "purple"],
    ["Total orders", metrics.total_orders, Package, "blue"],
    ["Total users", metrics.total_users, Users, "cyan"],
    ["Total vendors", metrics.total_vendors ?? 0, Users, "green"],
    ["Total products", metrics.total_products, Tags, "amber"],
    ["Total auctions", metrics.total_auctions, Gavel, "pink"],
  ];
  return (
    <div data-testid="admin-dashboard">
      <div className="admin-stats">
        {statCards.map(([label, value, Icon, tone]) => (
          <section className={`stat stat-${tone}`} key={label} data-testid={`metric-${label.toLowerCase().replaceAll(" ", "-")}`}>
            <span className="stat-icon"><Icon /></span>
            <small>{label}</small>
            <strong>{value}</strong>
            <em className="stat-trend"><TrendUp size={11} /> Live</em>
          </section>
        ))}
      </div>
      <div className="admin-grid">
        <section className="admin-panel">
          <div className="panel-head"><div><h2>Revenue Overview</h2><span>पिछले 7 दिन की लाइव कमाई</span></div><strong>{money(metrics.total_revenue)}</strong></div>
          <div className="chart" data-testid="revenue-chart">
            <div className="bars">{series.map((point) => <span key={point.label} style={{ height: `${Math.max(6, (point.value / maxRevenue) * 100)}%` }} title={`${point.label}: ${money(point.value)}`} />)}</div>
            <div className="chart-labels">{series.map((point) => <em key={point.label}>{point.label}</em>)}</div>
          </div>
        </section>
        <section className="admin-panel">
          <div className="panel-head"><div><h2>Order Status</h2><span>{totalStatus} orders</span></div></div>
          <div className="donut" style={donutStyle} data-testid="order-status-donut"><strong>{totalStatus}<small>Total</small></strong></div>
          <div className="legend">{Object.entries(statuses).length ? Object.entries(statuses).map(([status, count]) => <span key={status}><i style={{ background: statusColor(status) }} /> {prettyStatus(status)} <b>{count}</b></span>) : <span>No orders yet</span>}</div>
        </section>
        <section className="admin-panel">
          <div className="panel-head"><div><h2>Top Categories</h2><span>Published products</span></div></div>
          {categories.length ? categories.map((category) => <div className="category-row" key={category.name} data-testid={`top-category-${category.name}`}><span><Tags size={15} /></span><b>{category.name}</b><strong>{category.count}</strong></div>) : <p className="admin-empty-copy">No categories yet</p>}
        </section>
      </div>
      <div className="admin-lower">
        <section className="admin-panel table-panel">
          <div className="panel-head"><div><h2>Recent Orders</h2><span>Website orders update automatically</span></div><Link to="/admin/orders" data-testid="dashboard-orders-link">Manage orders</Link></div>
          <table data-testid="dashboard-orders-table"><thead><tr><th>Order</th><th>Total</th><th>Payment</th><th>Status</th><th>Date</th></tr></thead><tbody>{orders.length ? orders.map((order) => <tr key={order.id}><td>{order.order_number}</td><td>{money(order.total)}</td><td><span className="pay-pill" style={{ color: order.payment?.method === "cod" ? "#ffbd65" : "#39d7a4" }}>{(order.payment?.method || "—").toUpperCase()}</span></td><td><span className="status-chip" style={{ color: statusColor(order.status), background: `${statusColor(order.status)}22` }}>{prettyStatus(order.status)}</span></td><td>{new Date(order.created_at).toLocaleDateString("en-IN")}</td></tr>) : <tr><td colSpan="5">No live orders yet</td></tr>}</tbody></table>
        </section>
        <section className="admin-panel">
          <div className="panel-head"><div><h2>Recent Activities</h2><span>Live system feed</span></div></div>
          {activities.map((activity) => <div className="activity" key={activity.title}><i><Bell size={12} /></i><span><b>{activity.title}</b><small>{activity.detail}</small></span><time>{activity.time}</time></div>)}
        </section>
      </div>
    </div>
  );
}

function Content({ section, query }) { const item = sectionGroups.find(([id]) => id === section) || sectionGroups[0]; const [, label, type] = item; if (type === "dashboard" || type === "reports") return <Dashboard />; if (type === "products") return <AdminProductManager query={query} />; if (type === "orders") return <AdminOrderManager query={query} />; if (type === "returns") return <AdminReturnManager query={query} />; if (type === "support") return <AdminChatManager query={query} />; if (type === "payment-settings") return <AdminPaymentSettings />; if (type === "wallet") return <AdminWalletManager query={query} />; if (type === "categories") return <CategoryManager query={query} />; if (type === "users") return <UserManager query={query} />; if (type === "admin-users") return <UserManager admins query={query} />; if (type === "resource") return <AdminResourceManager resource={section} label={label} query={query} />; return <WorkflowManager kind={type} query={query} />; }

export default function AdminWorkspace() { const location = useLocation(); const [open, setOpen] = useState(false); const [query, setQuery] = useState(""); const segment = location.pathname.split("/")[2] || "dashboard"; const active = sectionGroups.some(([id]) => id === segment) ? segment : "dashboard"; const title = sectionGroups.find(([id]) => id === active)?.[1] || "Dashboard"; useEffect(() => setQuery(""), [active]); return <div className="admin-shell"><Sidebar active={active} open={open} onClose={() => setOpen(false)} /><main className="admin-main"><Header title={active === "dashboard" ? "DM Mobile Live Control" : title} onMenu={() => setOpen(true)} query={query} setQuery={setQuery} /><Content section={active} query={query} /></main></div>; }