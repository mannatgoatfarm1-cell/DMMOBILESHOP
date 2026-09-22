# DEALKR Authentication Test Playbook

1. Authenticate as the seeded admin using the credentials in `memory/test_credentials.md`.
2. Confirm `/api/auth/me` returns the signed-in user using cookies.
3. Register a fresh customer, then test profile, address, cart, order, wishlist, and bid calls.
4. Confirm a customer receives `403` for every `/api/admin/*` route.
5. Confirm an unauthenticated request receives `401` for private routes.
6. Verify invalid passwords are rejected and five failed attempts trigger a temporary lockout.