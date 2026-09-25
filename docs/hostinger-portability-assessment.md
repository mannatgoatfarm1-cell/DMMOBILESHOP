# DMobileMart Hostinger Portability Assessment

**Scope:** Phase 1 is read-only planning. Do not point a Hostinger process at the production Atlas cluster or run migrations/seeds until the backup gate in the runbook has passed.

## Current runtime architecture

| Area | Current implementation | Hostinger-independent target | Phase 2 work |
|---|---|---|---|
| Frontend | React/CRACO, preview API URL in `REACT_APP_BACKEND_URL` | Static React build served by Nginx | Build with the production API origin; remove preview URL |
| API | FastAPI/Uvicorn, supervisor in preview | Gunicorn/Uvicorn systemd service behind Nginx | Add production service unit and health checks |
| Database | Motor/MongoDB; current workspace env is local MongoDB | Existing owner-controlled MongoDB Atlas cluster | Set Atlas URI and production DB name only; no import, migration, reseed, or replacement |
| Auth | Email/password JWT cookies, refresh cookies, self-owned Google OAuth code flow | Same application-owned JWT system and owner-owned Google Cloud OAuth client | Register production domain/origin/redirect URI in Google Cloud |
| Payments | Razorpay SDK plus wallet/manual UPI proof flow | Owner Razorpay account/webhook secret | Move keys to VPS secret file; register production webhook URL |
| Uploads | Admin upload code calls Emergent integration proxy/object storage | VPS-backed media under `/var/lib/dmobilemart/uploads` **or** owner S3-compatible bucket | Replace storage adapter; preserve existing media URLs/read access strategy |
| Background work | Platform `.emergent/cron` watcher infrastructure | systemd timer or Ubuntu cron | Inventory actual business jobs before enabling one; no platform cron at runtime |

## Production blockers and required cutover changes

### P0 — must resolve before a Hostinger launch

1. **Emergent upload proxy** — `INTEGRATION_PROXY_URL` and `EMERGENT_LLM_KEY` currently initialize object storage. Replace `init_storage`, upload, and media retrieval helpers in `backend/server.py` with a VPS local-volume adapter or owner-controlled S3/MinIO adapter. Do not ship either Emergent value to Hostinger.
2. **Preview URLs** — remove the preview value from frontend build environment, backend `FRONTEND_URL`, CORS allowlist, Google allowed origins, and any test-only callback URLs.
3. **Atlas connection** — current workspace `.env` uses local MongoDB. Hostinger production must use the owner-supplied Atlas SRV URI and exact existing production DB name. Never run a dump restore, seed, delete, or schema-reset command against it.
4. **Seed/mutation guard** — backend startup currently has seed/normalization behavior. Add an explicit `APP_ENV=production` guard so production Atlas startup never inserts catalog data or updates documents automatically.
5. **Static media** — frontend currently references some `static.prod-images.emergentagent.com` images. Mirror these to owner storage or replace with owner-controlled URLs before independence cutover.
6. **Emergent browser tooling** — remove the Emergent script from `frontend/public/index.html` and Emergent visual-edit/overlay build dependencies from the production build path.

### P1 — owner configuration before go-live

- Create a self-owned Google Cloud OAuth Web Client. Register `https://<domain>` as an authorized JavaScript origin and `https://<domain>/auth/google` as an authorized redirect URI.
- Configure Razorpay live keys and webhook secret in the VPS secret file. Validate HMAC/webhook processing before accepting payments.
- Configure direct-transfer bank/UPI details via Admin → Razorpay & Payments, then protect access to that admin account.
- Configure transactional email/password-reset delivery. Current reset implementation logs the link; this is not suitable for production delivery.
- Configure Atlas Network Access with the VPS static IPv4 only, a dedicated least-privilege DB user, TLS, and Atlas backups.

## Dependencies that are safe to retain

- React, FastAPI, Motor, MongoDB Atlas, PyJWT, bcrypt, Authlib, Razorpay SDK, ReportLab, and standard Nginx/systemd tooling.
- Existing customer/admin UI, MongoDB schema, JWT session behavior, payments, auctions, QC reports, and manual UPI proof workflow.

## Explicit non-goals for Phase 1

- No Atlas data changes.
- No VPS deployment, DNS change, credential rotation, or payment switch-over.
- No removal of current customer/admin functionality.

## Phase 2 acceptance criteria

- A staging Hostinger domain runs without `emergentagent.com`, `assets.emergent.sh`, `customer-assets.emergentagent.com`, `INTEGRATION_PROXY_URL`, or `EMERGENT_LLM_KEY` in the runtime path.
- Atlas data counts/checksums match the pre-cutover read-only baseline.
- Upload, Google login, Razorpay, manual transfer proof, wallet, checkout, admin, auction, and QC flows pass on staging.