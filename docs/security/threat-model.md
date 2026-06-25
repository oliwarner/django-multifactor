# Threat model

`django-multifactor` is **a second layer of defence**. It assumes you already
have a working primary authentication system (passwords, SSO, whatever) and
adds friction for attackers who have compromised primary credentials. This
page lays out what the package protects against and — more importantly —
what it does not.

## What MFA defends against

| Threat | How MFA helps |
| --- | --- |
| **Password reuse / leak** | An attacker with the user's password cannot authenticate to your site without also possessing their second factor. The most important benefit of MFA. |
| **Phishing (with FIDO2)** | FIDO2 keys are bound to the registering domain. A phishing site cannot relay the WebAuthn challenge. TOTP and fallback OTP do **not** offer this guarantee. |
| **Credential stuffing** | Bulk-tried credentials fail at the MFA step. |
| **Brute force against passwords** | As above. Rate-limit MFA endpoints too — see below. |
| **Stolen session cookies (partially)** | `RECHECK` periodically re-challenges, so a stolen session has a finite useful lifetime. Not a substitute for `HttpOnly` + `Secure` cookies. |

## What MFA does **not** defend against

| Threat | Why MFA doesn't help (or only weakly helps) |
| --- | --- |
| **Server-side compromise** | Once the attacker is `root` on your server, sessions can be forged. MFA has no answer for this. Defence is host hardening. |
| **Database compromise** | TOTP secrets are stored plaintext (RFC 6238 requires the verifier to have them). An attacker with `SELECT *` can compute future codes forever. Encrypt at rest if your threat model demands it; see [TOTP guide](../guides/totp.md). |
| **Session hijacking before recheck** | A stolen authenticated session works until `RECHECK_MAX` elapses or `max_age` triggers. Pair with strong cookie hardening. |
| **Insider abuse** | An admin can disable any user's factors via the `MultifactorUserAdmin` inline. Limit admin access; log changes. |
| **Phishing (with TOTP or fallback)** | A user typing their 6-digit code on a phishing page reveals it within its 30-second validity window. Only FIDO2 prevents this. |
| **Email account takeover (with email fallback)** | If your fallback is email, an attacker who has compromised the user's inbox can complete MFA. Mitigated by the fan-out design — see [fallback risks](fallback-risks.md). |
| **SIM-swap attacks (with SMS fallback)** | The attacker can social-engineer the user's mobile carrier to receive the SMS. SMS fallback is convenient but well-known to be vulnerable. |
| **Lost devices / unrevoked keys** | A `UserKey` row marked `enabled=True` keeps working until an admin flips it off. There is no automatic "revoke on suspicious activity" in this package. Build it yourself with signals if required. |

## The "user has factors, just not active" gap

If a user has registered factors but **all their session-level factor
entries have expired** (e.g. `RECHECK_MAX` elapsed), they will be challenged
again. During the brief window between expiration and the next protected-view
hit, they are still "logged in" from Django's perspective. If you want
**every** request to be MFA-fresh, lower `max_age` on your decorators.

## Trust assumptions worth writing down

1. **The Django session is the source of truth** for "is this user
   MFA-authenticated right now?". Session security ≈ MFA security. Set
   `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`,
   `SESSION_COOKIE_SAMESITE = "Lax"` (or stricter).
2. **`MULTIFACTOR["BYPASS"]`, if set, is a security boundary.** Audit it.
   See [conditional bypass](../guides/conditional-bypass.md).
3. **Templates may be overridden.** A bad override can re-introduce CSRF
   tokens, mishandle the FIDO2 JSON, or leak secrets. Keep overrides
   minimal.
4. **The user's email is trusted by the default fallback.** If your `User`
   model lets users set their own email without verification, fallback
   trust is correspondingly weak.

## Defence in depth checklist

- [ ] HTTPS everywhere (HSTS preload if possible).
- [ ] `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT = True`.
- [ ] Rate limiter on `multifactor:*` URLs.
- [ ] `RECHECK = True` with a `RECHECK_MAX` matching your risk appetite.
- [ ] `max_age` on the most sensitive views.
- [ ] Email verification for the email-fallback path.
- [ ] Monitoring on `UserKey.objects.create` (new factors registered) and
      `UserKey.objects.filter(enabled=False).update(...)` (factors disabled).
- [ ] Admin audit log for any `MultifactorUserAdmin` inline changes.

## Reporting a security issue

See [Disclosure](disclosure.md).
