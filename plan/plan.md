# Hostinger-Independent Production App Plan

The complete DMobileMart application will run from a Hostinger Ubuntu VPS while retaining the existing MongoDB Atlas database in place.
Emergent will remain a development workspace only; the production storefront, API, admin tools, login, uploads, payments, and background services will not require an active Emergent account.

## Who it's for

- Customers using the marketplace, Cart, Orders, Auctions, QC reports, account, and support features.
- Administrators managing storefront content, products, payments, auctions, users, orders, and support.
- The business owner operating the production domain, VPS, Atlas database, and third-party service accounts directly.

## Core features and experience

- Preserve the existing customer website, mobile experience, admin panel, APIs, authentication, payments, uploads, auctions, and data.
- Keep the existing MongoDB Atlas database unchanged: no migration, deletion, reseed, or replacement of production data.
- Make every production runtime service owner-controlled and portable, including authentication, storage, payment callbacks, HTTPS, logs, backups, and scheduled work.
- Remove or replace any runtime dependency that requires Emergent infrastructure, credentials, credits, or subscription access.

## User flow

1. Customers open the production domain over HTTPS and use the same storefront and mobile flows.
2. The VPS serves the customer app and admin panel, while the API connects to the existing Atlas database.
3. Login uses the app's own session system with owner-controlled Google OAuth and existing email/password accounts.
4. Payments communicate directly with owner-controlled Razorpay settings; uploads use durable owner-controlled storage.
5. Admins continue to manage the site through the existing admin panel with no Emergent runtime dependency.

## UI/UX feel

- Keep the existing DMobileMart Future Glass customer design and current admin interface unchanged.
- Preserve all responsive mobile navigation, Orders, Cart, Auctions, checkout, QC, and support experiences.
- Production portability work remains invisible to customers except for more stable login, uploads, and payments.

## Implementation phases

### Phase 1 — Production portability MVP (built now)
- Produce a read-only architecture and dependency assessment of the current project.
- Identify every runtime dependency that would block independent Hostinger operation.
- Prepare a complete Hostinger Ubuntu 24.04 + Nginx + HTTPS + Atlas deployment checklist, secret inventory, operational runbook, and rollback plan.
- Specify the changes needed to remove Emergent runtime dependencies without modifying existing Atlas data.

### Phase 2 — Independent service cutover
- Replace or reconfigure managed authentication, storage, uploads, emails/OTP if used, webhooks, scheduled work, and media delivery with owner-controlled alternatives.
- Configure self-owned Google OAuth, Razorpay, durable storage, backups, monitoring, and production access controls.
- Validate all customer and admin flows against a Hostinger staging deployment connected to Atlas only after backup confirmation.

### Phase 3 — Production launch and operations
- Deploy frontend and API behind Nginx with Let’s Encrypt HTTPS on the production domain.
- Establish monitoring, backup schedules, Atlas IP access controls, log rotation, webhook verification, and rollback procedures.
- Deliver an independent operations handover for future updates and incident recovery.

## Assumptions

- Production runs on Hostinger VPS with Ubuntu 24.04 LTS.
- MongoDB Atlas remains the production database and existing data must not be changed, moved, deleted, or reseeded.
- A production domain is available for Nginx and Let’s Encrypt HTTPS.
- The owner will retain direct ownership of MongoDB Atlas, Google OAuth, Razorpay, email/OTP if required, and storage credentials.
- Google sign-in will use a self-owned Google Cloud OAuth client rather than a managed Emergent sign-in service in production.
- Uploaded media will use durable VPS-backed storage with backups unless an owner-controlled S3-compatible storage account is selected later.
- Existing UI, customer flows, admin functions, and database schema are preserved; this work changes deployment ownership, not product behavior.