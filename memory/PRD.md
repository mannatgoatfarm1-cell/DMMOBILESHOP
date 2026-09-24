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

## Implemented — 2026-09-24
- Completed and validated the rich MobileCart admin workspace: live dashboard metrics, quick filtering/ranking across product, user, wallet, auction, category, and managed-content tables, plus Hindi feedback for admin save actions.
- Added the admin Quality Check editor (grade plus pass/fail/unknown device checks) and customer-facing QC Report on product detail pages, including pass/defect totals and a defects-only filter.
- Added dynamic Razorpay payment settings with masked secret fields, test/live mode, payment-method switches, partial-payment controls, public checkout configuration, and server-side protection against disabled checkout methods.
- Hardened live catalog reads with cache-busting product detail requests, no-store server response headers, and overlap-free one-second polling. Immediate create-to-customer QC verification now passes.
- QA: production frontend build passes; Python compilation passes; Iteration 12 backend suite passes 7/8. The only failed check is preview-gateway credentialed OPTIONS handling, which rejects the configured preview origin before the app; same-origin MobileCart login/API journeys work.
- Added a persistent Light / Dark swipe switch inside the customer Profile hub. The selected theme applies instantly across customer-facing header, cards, checkout, and account surfaces and persists after reload.
- Rebuilt the storefront announcement strip as an auto-scrolling Live Update ticker with a mobile icon label and per-announcement mobile icons. It pauses on hover and respects reduced-motion browser settings.
- Redesigned the Admin Add Product QC editor: compact condition-grade chips and per-check icon-only Pass / Defect / Not-checked controls replace the oversized selection rows. QC create/update persistence and customer-facing read-through are verified.
- Redesigned Razorpay & Payments with a secure connection panel, Test/Live segmented controls, compact payment method cards, advance-payment slider, and admin-only Merchant UPI ID input. UPI IDs are validated, persisted, never exposed publicly, and secrets remain masked.
- Strengthened Profile Light Mode secondary-text contrast across wallet, account cards, product metadata, and header copy. Automated checks confirm sampled text meets WCAG AA contrast and preference persists after reload.
- QA Iteration 13: frontend flows passed; backend 6/7 passed. The one outstanding failure remains the external preview gateway rejecting credentialed auth OPTIONS preflight before app routing. **Razorpay real checkout remains unconfigured; no external payment was attempted.**
- Stabilized admin search behavior: matching rows now preserve their original catalog order while typing, product search only considers product name/URL slug (not broad category/tag text), provides an explicit no-results message, and admin product API ordering is fixed by creation date instead of changing after every edit.
- Completed a visual readability pass: increased small-text sizing and contrast in admin workspace controls, strengthened light-mode account/wallet copy, and restored high-contrast gold text for the dark MobileCart Gold banner when Light Mode is active. Fresh browser verification confirms the banner heading/body and profile text are visible.
- Added complete customer/admin order foundations: My Orders list/detail/tracking, downloadable PDF invoices, and admin order drawer with status/tracking updates. Admin Users now stays dark and includes an authorized profile drawer with wallet, saved addresses, orders, returns, and Active/Suspend control.
- Corrected authentication lockout behavior: five failed attempts now block even a correct password for 15 minutes. Public preview gateway CORS preflight remains blocked upstream despite app-local CORS passing; this is an ingress/platform issue.
- Implemented stock-aware shopping: zero-stock products show Out of Stock and disable add/buy actions; cart quantity updates validate stock server-side. Failed/cancelled UPI payment orders transition to `payment_failed`, retain history, record a failure timeline event, and restore reserved stock once.
- Restored and polished Wishlist: header button routes to and scrolls to the saved-products panel; saved products, coupons, and returns now have readable card layouts in light/dark modes.
- Enabled live Razorpay configuration through existing Admin settings and integrated Razorpay Standard Checkout client flow: UPI QR/app selection (Google Pay, PhonePe, Paytm supported by Razorpay), server-created provider order, server-side signature verification, and no order confirmation prior to verification. Live external payment was intentionally not executed during QA.
- QA Iteration 16: 6/6 backend tests passed for stock, payment failure recovery, secret masking, wishlist, categories, and user/order regression. Checkout hook crash was fixed afterward; build and browser smoke test confirm UPI section now renders and no success state appears before payment verification. Third-party react-razorpay package produces non-blocking source-map warnings during production build.
- Rebranded key customer surfaces to **DM Mobile / DMobileMart**, with a mobile-device brand icon, “Powered by DMobileMart-Muskan” footer label, and working Shipping, Returns & Refunds, Privacy, and Terms policy routes.
- Added IMEI and barcode inputs to Admin Add Product. Values are captured into the order-item snapshot and printed on the DMobileMart customer invoice PDF, so later product edits cannot alter a past bill.
- Added secure direct-transfer architecture: admin manages UPI/account name/account number/IFSC and method toggle; customer must upload an image-only payment proof; order becomes `payment_review`; admin can view the protected screenshot and Capture (confirmed) or Reject (failed + stock restored exactly once). Manual transfer is currently **safely disabled** until a real bank account and IFSC are entered in Admin → Razorpay & Payments.
- Checkout now displays available coupons as one-click apply pills alongside typed coupon entry. Fixed a critical Apply-click crash by coercing coupon input to a safe normalized string; invalid coupon now returns feedback without crashing checkout.
- QA Iteration 17: backend suite 7/7 passed covering identifiers, categories, secure payment settings, proof upload/review, capture/reject, invoice output and stock restore. Frontend coupon crash was fixed afterward and browser smoke confirmed invalid coupons do not crash checkout. **Real Razorpay transaction remains MOCKED/not executed to prevent live charges.**
- Expanded the DMobileMart category and support experience: existing Flipkart-style category circles/filter routes were regression-tested and stay stable across live polling; DMobile/DMobileMart branding was applied to storefront, auth, account, admin control, invoice download filename and footer policy links.
- Added product warranty days (365-day default for new admin products), warranty snapshotting into order items, and secure warranty return claims. Customer claim flow requires a reason, exactly two front/back photos, and a max-one-minute video client check; no-warranty orders display a clear No warranty state.
- Return evidence is private: public media access is blocked, only admin review endpoints can retrieve it. Admin can approve/disapprove exactly once with a mandatory customer-visible reason; backend validates ownership, file formats/sizes, warranty eligibility, and evidence count.
- Added MongoDB-backed customer/admin live chat with one-second polling, thread isolation, customer floating support panel, and Admin → Support Tickets inbox/reply console. Chat backend roundtrip/isolation tests pass.
- Checkout wallet option now shows current available balance and an Add money account entry point. Full self-serve wallet top-up/payment reconciliation and the requested dedicated admin live-cart monitor remain P1 work.
- QA Iteration 18: 9/9 backend tests passed for categories, product warranty fields, return evidence privacy/decision idempotency, chat role isolation/roundtrip, and wallet method visibility. Added explicit warranty-days admin control after QA feedback; production build passed. React-Razorpay package still emits non-blocking source-map warnings.

## Prioritized Backlog
- P0: Preview gateway rejects credentialed `OPTIONS /api/auth/login` before FastAPI even for the configured preview origin. App-side CORS is configured and same-origin login works; ingress/gateway configuration needs an explicit allowlist change for third-party cross-origin clients.
- P0: Configure outbound email delivery for customer-facing password-reset links; reset tokens are generated securely but currently logged by the backend because no email provider is configured.
- P0: Preview ingress currently rejects credentialed `OPTIONS /api/auth/login` requests before FastAPI; application-level CORS and same-origin login work. Ingress configuration needs an explicit preview-origin allowlist or CORS disabled at gateway.
- P1: Add full admin management screens for product/category/order/auction CRUD and connect the remaining dashboard navigation sections.
- P1: Move uploads to managed object storage before scaling beyond a single application instance.
- P2: Configure real Razorpay Key ID, Key Secret, and Webhook Secret in Admin → Razorpay & Payments, then validate provider checkout, webhooks, refunds, and reconciliation. **Real Razorpay payment is not configured in this environment.**
- P2: Add auction closing scheduler and live bid synchronization.

## Next Tasks
1. Redesign payment settings with Hindi-first status feedback and connect Razorpay once Key ID, Key Secret, and Webhook Secret are supplied.
2. Add outbound email delivery for production password-reset links.
3. Add AI Assistant / Deal Engine through the approved LLM integration flow.
4. Add referrals, bulk-buy and price tracking.
5. Add auction closing scheduler and real-time bid synchronization.
6. Keep QA-created inactive test products cleaned periodically; admin delete currently soft-unpublishes products for audit safety.