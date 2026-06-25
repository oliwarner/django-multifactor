# Factors overview

`django-multifactor` ships three "kinds" of factor: FIDO2 / WebAuthn, TOTP, and
fallback OTP. The first two are first-class — users register them as
`UserKey` rows and they count toward the factor totals you require with
`factors=N`. The third is the "lost phone" escape hatch.

## At a glance

|  | **FIDO2 / WebAuthn** | **TOTP** | **Fallback OTP** |
| --- | --- | --- | --- |
| Strength | Phishing-resistant. Strongest of the three. | Shared-secret. Strong if the secret stays on the phone. | Only as strong as the transport (email/SMS/etc). |
| Hardware needed | A security key, biometric sensor, or platform authenticator. | Any smartphone or password manager. | Nothing — uses email by default. |
| User experience | One tap. | Open app, type 6 digits. | Wait for email, type code. |
| Phishing resistance | **Yes** — keys are scoped to the registering domain. | No — codes can be entered on a phishing page. | No. |
| Replay resistance | Yes (challenge/response). | Within ~60s window. | Within ~ session window. |
| Lost-credential recovery | Register multiple keys or rely on fallback. | Re-scan QR code (admin reset). | The fallback itself is the recovery — no further fallback. |
| Where the secret lives | On the user's authenticator. Public key only in DB. | On the user's device **and** in `UserKey.properties.secret_key`. | One-shot random in `request.session`. |

## FIDO2 / WebAuthn

**Use when:** you can mandate hardware, or want phishing-resistant auth for
staff/admins.

FIDO2 keys are domain-bound. A key registered against `app.example.com` will
not work against `staging.example.com`. This is a feature — it stops phishing
domains accepting genuine keys — but it means:

- You need a stable production domain (or accept that staging needs its own
  keys).
- Local dev happens on `localhost` — modern browsers permit WebAuthn there
  without HTTPS.
- The package stores the registering domain in `UserKey.properties["domain"]`
  and filters by it at auth time (`factors/fido2.py:46`).

Implementation: `multifactor/factors/fido2.py`. Uses the
[Yubico `fido2`](https://github.com/Yubico/python-fido2) library.

```{tip}
Encourage users to register **two** FIDO2 keys (e.g. a YubiKey on their
keyring and a backup in a desk drawer). Losing the only registered key is
the most common path to a panic call to support.
```

## TOTP

**Use when:** you can't mandate hardware but want something stronger than
email codes.

TOTP is RFC 6238 — a SHA1 HMAC of the current 30-second time window with a
shared secret. The user pairs their authenticator app by scanning a QR code
that encodes:

```
otpauth://totp/{username}?secret={base32}&issuer={TOKEN_ISSUER_NAME}
```

The secret is generated once via `pyotp.random_base32()` and stored in
`UserKey.properties["secret_key"]`. The verification window is ±60 seconds
of "now" (i.e. ~5 codes either side) — generous to absorb clock drift. See
[TOTP troubleshooting](../debugging/totp-troubleshooting.md) for tightening it.

Implementation: `multifactor/factors/totp.py`. Uses the
[`pyotp`](https://pyauth.github.io/pyotp/) library.

```{warning}
TOTP secrets are stored in the database **in plaintext**. This is unavoidable
given how TOTP works — verification requires the secret. Treat your DB as
secret. Encrypt at rest if your threat model demands it.
```

## Fallback OTP

**Use when:** users lose access to their primary factors.

The fallback is a numeric OTP delivered out-of-band — by default, via email
to `user.email`. The full delivery story (parallel fan-out, transport
predicates, custom callables) is documented in the
[custom fallback guide](../guides/custom-fallback.md).

Key fact for the threat model: **fallback transports are by definition less
secure than the primary factors**. Email accounts get hacked. SIMs get
swapped. The package compensates with **fan-out** — by sending to all
enabled transports simultaneously the legitimate user is alerted even if
one channel has been quietly compromised. See
[fallback risks](../security/fallback-risks.md).

Implementation: `multifactor/factors/fallback.py`.

## How to disable a factor type

```python
MULTIFACTOR = {
    "FACTORS": ["FIDO2"],  # remove "TOTP" from the picker
    "FALLBACKS": {},  # disable fallback entirely
}
```

`FACTORS` controls only the **add-new-factor** picker. Existing factors of a
removed type keep working until you delete them through the admin (or
expose a self-service delete in your UI — there isn't one by default).

## Where next?

- Hardening checklist per factor: [security best practices](../security/best-practices.md).
- Adding a custom transport: [custom fallback guide](../guides/custom-fallback.md).
