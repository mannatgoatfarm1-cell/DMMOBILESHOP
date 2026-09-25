# MobileCart authentication testing playbook

1. Confirm MongoDB indexes: `users.email`, sparse `users.username`, `login_attempts.identifier`, and TTL `password_reset_tokens.expires_at`.
2. Sign in as `deepak143` with password `deepak143` through `/api/auth/login` using `{"identifier":"deepak143","password":"deepak143"}`. Confirm `/api/auth/me` returns role `admin`.
3. Register a customer with `name`, `email`, `password`, and matching `confirm_password`; confirm a mismatch returns 422.
4. Request a reset through `/api/auth/forgot-password`; use the logged reset token once at `/api/auth/reset-password` with matching `new_password` and `confirm_password`. Confirm a reused token is rejected.
5. Confirm the admin sign-in view has no registration control, while the customer sign-in view includes registration and forgot-password controls.
6. With valid refresh cookie but invalid access cookie, make a protected API request and confirm `/api/auth/refresh` issues a new access session and the original request retries once.
7. Confirm an invalid refresh cookie ends the session without a retry loop; inactive users and role changes must not refresh.
8. Sign in as admin and upload a JPG, PNG or WebP to `/api/admin/uploads` using multipart field `file`; confirm the returned `/api/media/{id}` image renders successfully.