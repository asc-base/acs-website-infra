# Password reset

The portal requests a reset link from the core service. The core service sends it by email, and the portal accepts the token at `/auth/reset-password?token=...`.

## Configure each environment

Set these variables in the core service's staging or production deployment environment. Compose requires the URL and SMTP host, username, password and sender; the port defaults to `587` and secure transport defaults to `false`.

| Variable | Example or default |
| --- | --- |
| `FRONTEND_RESET_PASSWORD_URL` | `https://<environment-portal-host>/auth/reset-password` |
| `MAIL_HOST` | SMTP host supplied by your mail provider |
| `MAIL_PORT` | `587` |
| `MAIL_SECURE` | `false` |
| `MAIL_USER` | SMTP username |
| `MAIL_PASS` | SMTP password, stored as a deployment secret |
| `MAIL_FROM` | Verified sender address |

Production's reset URL is `https://acs.kmutt.ac.th/auth/reset-password`. Set staging to the staging portal's HTTPS URL. Keep SMTP credentials in the deployment secret store.

## Verify before deployment

1. Confirm the environment's reset URL opens the portal reset page and the core service has working SMTP settings.
2. Request a reset for a test account and confirm the email link uses that environment's portal host.
3. Open the link, set a new password, and sign in with it.
4. Open the same link again and confirm the portal reports that the link is invalid or expired.

The reset token is one-time use. The portal does not display a credential in the request response; the reset link arrives by email.
