# MobileCart Product Record

## Original Problem Statement
Build a production-ready MobileCart storefront and web admin panel with product browsing, cart, checkout, auctions, and marketplace administration in a dark luxury visual style.

## Architecture Decisions
- Responsive React single-page experience with customer storefront routes and `/admin` dashboard route.
- React storefront and admin dashboard use FastAPI APIs at `REACT_APP_BACKEND_URL`; MongoDB is the source of truth for catalog, customers, carts, orders, auctions, and admin metrics.
- JWT access and refresh cookies secure customer and administrator sessions. All admin routes require the server-side `admin` role.
- Image uploads are validated and stored behind an authenticated API endpoint. Payment records use provider-ready fields for a later Razorpay integration.
- Visual system follows the MobileCart direction: deep navy surfaces, electric purple/blue accents, INR formatting, product photography, compact data-dense admin panels.

## User Personas
- Deal-focused customer browsing electronics, auctions, AI deals, and bulk-buy offers.
- DealKR operations admin managing products, orders, vendors, campaigns, payments, and customer app content.

## Core Requirements (Static)
- Customer home page with search, categories, hero deal, flash deals, auction preview, stock, bulk-buy, AI picks, and mobile navigation.
- Product detail, cart, demo checkout, auction bidding, and category browsing flows.
- Admin dashboard with metrics, revenue chart, order status, recent activity, recent orders, categories, and full navigation inventory.
- Match reference styling, shading, spacing, imagery, DEALKR branding, and ₹ currency examples.

## Implemented — 2026-09-22 to 2026-09-23
- Replaced the starter splash screen with a complete MobileCart storefront and responsive admin dashboard.
- Added functional demo routes: storefront, category browsing, product detail, cart, checkout success, auctions, and `/admin`.
- Added local cart state, quantity/remove behavior, checkout payment selection, order confirmation, auction bid increment, toast feedback, responsive bottom navigation, and mobile admin menu.
- Added descriptive `data-testid` attributes throughout interactive flows and verified production build plus desktop/mobile screens.
- Fixed the product-detail header cart navigation so it opens the cart flow correctly.
- Replaced all mocked storefront data with seeded MongoDB catalog records and production-style FastAPI routes for products, categories, search, filters, pagination, carts, wishlists, checkout orders, auction bids/history, and admin operations.
- Added customer signup/login, httpOnly JWT sessions, addresses, profile management, seeded administrator access, role checks, brute-force sign-in lockout, and structured API validation/error responses.
- Added MongoDB indexes, data validation, protected image upload support, order tracking/payment architecture, and live admin dashboard metrics.
- Validated real customer and administrator journeys end-to-end. Fixed auth lockout keying and stable logout response handling; backend regression suite now passes 10/10 and production frontend build passes.
- Rebranded storefront/admin visuals and product imagery for MobileCart.
- Seeded the requested administrator account: username `deepak143`, password `deepak143`, super-admin role.
- Added username-or-email sign-in, customer-only registration, matching re-enter-password validation, and one-time password-reset tokens with one-hour expiry.
- Added Forgot Password controls to customer and administrator login views; admin login has no registration control.
- Fixed the header profile action so it opens `/account`; sign-out remains available only in Account.
- Fixed null-product handling on `/auctions`, preventing the prior route crash.
- Added product image zoom/lightbox and category-based Similar Products to product detail pages.
- Iteration 4 validation: requested frontend flows passed, 7/8 backend checks passed. Local credentialed CORS preflight passes; external preview OPTIONS preflight is rejected by the gateway although same-origin browser authentication and direct login work.
- Added persistent object-storage backed admin media uploads, full admin workspace controls, wallet credit/debit ledger, coupon validation, customer wallet account view, and 1-second catalog/category/auction storefront synchronization.
- Added MobileCart branded favicon.ico, PNG favicon sizes, Apple Touch Icon, Android/PWA icons, manifest, and page metadata.
- Added Google OAuth customer login with the provided Google OAuth client. Customer login page has Google sign-in; admin login remains password-only. Browser redirect now reaches Google sign-in without redirect URI mismatch; real post-consent verification requires an authorized Google test account.
- Rebuilt the customer Account hub with wallet, Gold, transactions, orders, saved-addresses and explicit sign-out control.
- Fixed StoreHome unsafe product-image reads and the Account `Package` runtime import error that could interrupt a successful sign-in.
- Fixed email/password reliability: valid credentials now clear stale failed-attempt records and immediately restore the session; wrong passwords retain the rate-limit protection. Login displays a persistent, readable error message.
- Iteration 10 validated repeat customer/admin email login, valid-password recovery after lockout, visible auth errors, profile/account session persistence, and no Account runtime overlay.

## Prioritized Backlog
- P0: Validate external preview gateway CORS behavior if a separate-origin client must access APIs; current MobileCart frontend uses same-origin API calls and works.
- P0: Configure outbound email delivery for customer-facing password-reset links; reset tokens are generated securely but currently logged by the backend because no email provider is configured.
- P0: Preview ingress currently rejects credentialed `OPTIONS /api/auth/login` requests before FastAPI; application-level CORS and same-origin login work. Ingress configuration needs an explicit preview-origin allowlist or CORS disabled at gateway.
- P1: Add full admin management screens for product/category/order/auction CRUD and connect the remaining dashboard navigation sections.
- P1: Move uploads to managed object storage before scaling beyond a single application instance.
- P2: Integrate Razorpay payment creation, verification, webhooks, refunds, and reconciliation.
- P2: Add auction closing scheduler and live bid synchronization.

## Next Tasks
1. Redesign payment settings with Hindi-first status feedback and connect Razorpay once Key ID, Key Secret, and Webhook Secret are supplied.
2. Add outbound email delivery for production password-reset links.
3. Add AI Assistant / Deal Engine through the approved LLM integration flow.
4. Add referrals, bulk-buy and price tracking.
5. Add auction closing scheduler and real-time bid synchronization.