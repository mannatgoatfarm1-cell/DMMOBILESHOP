# DEALKR Product Record

## Original Problem Statement
Build the same design website and web admin panel as the provided DEALKR reference screens.

## Architecture Decisions
- Responsive React single-page experience with customer storefront routes and `/admin` dashboard route.
- Local demo state is used for products, cart, checkout, auction bidding, and admin metrics so the visual prototype works immediately without credentials or live services.
- Visual system follows the reference: deep navy surfaces, electric purple/blue accents, INR formatting, product photography, compact data-dense admin panels.

## User Personas
- Deal-focused customer browsing electronics, auctions, AI deals, and bulk-buy offers.
- DealKR operations admin managing products, orders, vendors, campaigns, payments, and customer app content.

## Core Requirements (Static)
- Customer home page with search, categories, hero deal, flash deals, auction preview, stock, bulk-buy, AI picks, and mobile navigation.
- Product detail, cart, demo checkout, auction bidding, and category browsing flows.
- Admin dashboard with metrics, revenue chart, order status, recent activity, recent orders, categories, and full navigation inventory.
- Match reference styling, shading, spacing, imagery, DEALKR branding, and ₹ currency examples.

## Implemented — 2026-09-22
- Replaced the starter splash screen with a complete DEALKR storefront and responsive admin dashboard.
- Added functional demo routes: storefront, category browsing, product detail, cart, checkout success, auctions, and `/admin`.
- Added local cart state, quantity/remove behavior, checkout payment selection, order confirmation, auction bid increment, toast feedback, responsive bottom navigation, and mobile admin menu.
- Added descriptive `data-testid` attributes throughout interactive flows and verified production build plus desktop/mobile screens.
- Fixed the product-detail header cart navigation so it opens the cart flow correctly.

## Prioritized Backlog
- P0: Keep the storefront and admin visual flows stable.
- P1: Connect products, orders, vendors, and campaigns to persistent backend data.
- P1: Add admin editing forms and customer account/order history persistence.
- P2: Add real payments, authentication, notifications, and live auction synchronization.

## Next Tasks
1. Replace local demo data with FastAPI/MongoDB product and order endpoints.
2. Add admin CRUD forms for products, vendors, campaigns, and categories.
3. Add customer sign-in, saved items, and persistent order history.
4. Connect a payment provider and real-time auction events when production behavior is needed.