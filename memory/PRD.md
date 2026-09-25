# DMMobile Shop — Product Requirements Document

## Original Problem Statement
Build a production-ready e-commerce platform "DMMobile Shop" (formerly MobileCart). Scope includes product browsing, cart, checkout, auctions, admin management, and a customer account hub.

## Current Design Direction
**"DMMobile Shop 2080 — Future Glass Marketplace"** — A dark futuristic glassmorphism theme with AI-style animations using Framer Motion. All customer-facing pages use dark (#060912) background with neon blue/cyan/purple accents, glass cards, and smooth scroll animations.

## Core Architecture
- **Frontend**: React, Tailwind CSS, Framer Motion, Shadcn UI
- **Backend**: FastAPI, Python, PyJWT (Access + Refresh tokens in cookies), Razorpay SDK
- **Database**: MongoDB
- **Architecture**: Monolithic Frontend with component splits, 1-second live sync

## Key Files
- `/app/frontend/src/App.js` — Main app, routing, shared components (Topbar, FooterBar, ProductCard, BottomNav)
- `/app/frontend/src/components/FuturisticHome.jsx` — New futuristic homepage (38+ sections)
- `/app/frontend/src/futuristic-2080.css` — Dark glass theme CSS (overrides App.css)
- `/app/frontend/src/api.js` — Axios config with refresh token interceptors
- `/app/backend/server.py` — FastAPI backend, all models & APIs

## What's Been Implemented

### Phase 1 — Core E-commerce (DONE)
- Product browsing, search, filtering
- Cart management, checkout flow
- Customer auth (register/login/JWT refresh)
- Admin panel (products, orders, users, settings)
- Razorpay payment integration
- Category management, product variants

### Phase 2 — Advanced Features (DONE)
- Live Auction system with bidding
- UPI manual payment flow (Admin sets UPI, QR generated for customers)
- QC Report workflow
- Return & refund system
- Coupon/discount system
- Announcement strips

### Phase 3 — UI Redesign: 2080 Future Glass (DONE — Sept 25, 2026)
- Complete customer website redesign to dark futuristic glassmorphism
- 38+ homepage sections: Hero, Trust Strip, Flash Sale, Deal of Day, Top Selling, Hot Selling Categories, Quad Promo (Auction/Wholesale/Trade-In/Price Drop), Top Brands, Trending Products, Why Choose, Customer Reviews, Blog, Community, WhatsApp, Newsletter, Footer
- AI-style animations with Framer Motion (scroll reveal, stagger, hover effects)
- Glass product cards with neon glow and shimmer on hover
- Mobile responsive with bottom navigation
- Admin panel completely untouched and preserved
- All existing backend data, APIs, auth flows preserved
- Testing: 100% pass rate (15/15 features verified)

### Customer Homepage Cleanup (DONE — Sept 25, 2026)
- Removed customer-facing Top Selling / Deal of the Day, Save Money Deal, Bulk Deal, Today Deal, and New Stock Deal sections.
- Removed AI Deals entry points from customer mobile navigation and account hub, plus AI wording from the sell-device screen.
- Removed the obsolete duplicate deal-row component; backend, MongoDB data, and Admin panel were not modified.
- Smoke-tested the live customer homepage: all removed section test IDs returned zero and the page loaded successfully.

### Major Sale Shelves (DONE — Sept 25, 2026)
- Reintroduced promotional merchandising as six consistent Future Glass shelves: Flash Deals, Mobile Parts Deals, Today's Deals, Deal of the Day, New Stock, and Stock Clearance Sale.
- Each shelf uses live product data, unique sale styling, responsive six-card rows, product links, and working add-to-cart controls.
- Verified the live storefront: all six shelves render once and the Mobile Parts / Today's Deals rows render six cards each.
- Reordered all six shelves directly below the customer hero banner in this sequence: Flash Deals, Mobile Parts Deals, Today's Deals, Deal of the Day, New Stock, Stock Clearance Sale.
- Moved Top Brands directly below the hero banner and converted its visible brand-label pills into an icon-only rail.

### Live Chat Experience (DONE — Sept 25, 2026)
- Customer live support no longer opens automatically; signed-in customers must manually open the support button.
- Reduced the Admin Support Tickets live-chat workspace to a compact 400px panel with scrollable conversation threads.
- Added accurate unread customer-message badges, clearing the count when an admin opens that conversation.

### Storefront Content Management (DONE — Sept 25, 2026)
- Added a dedicated Admin → Storefront workspace for homepage banner copy, banner image upload/preview, and publishing website changes.
- Admin can edit headings/labels and show or hide each of 16 customer-facing homepage sections; the public homepage syncs these settings live.
- Reused the configured secure media upload flow and verified an admin publish updates the customer hero and section visibility, then restores correctly.
- Moved the admin chat reply composer above the message thread for faster support replies.

### Homepage Navigation Placement (DONE — Sept 25, 2026)
- Removed the Top Brands rail and its obsolete CMS control.
- Moved customer category navigation directly below the hero banner, ahead of Flash Deals and the remaining sale shelves.

### Mobile Storefront Polish (DONE — Sept 25, 2026)
- Removed mobile horizontal page overflow and tightened hero/category sizing for a true viewport-fit layout.
- Converted every sale shelf—including New Stock and Stock Clearance—into a manual touch-swipe rail with snap alignment; disabled automatic hero-dot movement.
- Verified at 390px: document width remains 390px and the New Stock rail scrolls from a 338px viewport across 1012px of products.

### Hero Rendering Fix (DONE — Sept 25, 2026)
- Fixed the hero accent line that was rendering as cyan/purple blank blocks on desktop and mobile.
- Replaced unstable gradient-text clipping with a compact neon accent treatment; verified heading height reduced to 154px with no background block.

### Connected Sale Routing & Auth/Data Lock (DONE — Sept 25, 2026)
- Each sale shelf View All now opens its own catalog collection: Flash, Mobile Parts, Today, Deal of the Day, New Stock, or Stock Clearance.
- Products now carry explicit homepage sale placements. Admin → Products shows six selectable placements during add/edit and displays every saved product’s live placement.
- Added refresh-cookie session bootstrap and `/auth/me` retry recovery to prevent access-token expiry from forcing re-authentication; verified signed-in session restoration after an invalid access token.
- Locked customer identity updates and address deletion at the API layer (423 Locked) so user data cannot be changed or removed through standard flows.

### Auction Detail & QC Flow (DONE — Sept 25, 2026)
- Refined the auction journey with explicit Choose Device → Review QC → Place Live Bid → Win & Pay steps.
- Added a clickable QC Report action inside every auction bid detail, presenting grade, real inspection checks, pass/fail/unknown state, device image, and verification messaging.
- Verified customer flow: auction card → bid detail → QC report → back to active live-bidding panel.

### Auction Winner Payment (IN PROGRESS — Sept 25, 2026)
- Added a protected winner-only order endpoint: only the confirmed winner of a closed auction can create an order; it supports Razorpay, DMobileMart Wallet, or personal UPI proof payment states.
- Wallet payment debits the existing wallet atomically; personal UPI requires the existing Admin-configured UPI ID; Razorpay uses the existing order verification endpoints.
- Remaining: expose this protected winner order flow in the customer Auction UI with dedicated win/payment screen and personal-QR proof form.

## Pending Tasks (Prioritized)

### P1 — High Priority
1. **Wallet Add Money Flow** — Razorpay top-up verification/credit workflow
2. **Admin Live Control Board** — Unified dashboard (Pending Returns, Open Chats, Pending Payments, Active Carts)
3. **AI Assistant/Deal Engine** — Requires integration_playbook_expert_v2
4. **Refer & Earn / Retain & Earn** — Loyalty system

### P2 — Medium Priority
5. **Bulk Buy Feature** — B2B ordering flow
6. **Price Tracker** — Historical price tracking and alerts
7. **Google OAuth** — Customer social login (requires Client ID)

### P3 — Refactoring
8. Backend `server.py` approaching 2000 lines — needs route splitting
9. Frontend `App.js` — Extract remaining shared components

## Known Issues
- Preview Gateway CORS 400 — Platform/infrastructure limitation, not app code
- 401 console warnings when not logged in (expected behavior)

## DB Schema
- users: {id, email, username, role, balance, active}
- products: {id, name, stock, category_slug, active, warranty_days}
- settings: {id, type, config} (Razorpay keys, manual UPI config)
- orders: {id, user_id, items, status, total, payment_method, payment_proof_url}
- returns: {id, order_id, reason, photos, video, admin_decision}
- auctions: {id, product_id, current_bid, ends_at, status}
