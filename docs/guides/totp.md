# TOTP authenticators

TOTP — Time-based One-time Password, RFC 6238 — is the "code from an
authenticator app" factor. It is the easiest factor to roll out: any
authenticator app on any phone works. It is also the easiest to phish.

## Configuration

```python
MULTIFACTOR = {
    "TOKEN_ISSUER_NAME": "My Django App",  # label shown next to the account in the app
}
```

`TOKEN_ISSUER_NAME` is what the user's authenticator displays. Pick something
recognisable — "Acme HR Portal" rather than "django".

## How it works under the hood

1. The user visits the **Add TOTP** page.
2. `multifactor.factors.totp.Create` calls `pyotp.random_base32()` to make a
   new secret.
3. It builds an `otpauth://` provisioning URI:

   ```text
   otpauth://totp/{username}?secret={base32}&issuer=My%20Django%20App
   ```

4. That URI is rendered as a QR code in the template.
5. The user scans the QR. Their app now generates a fresh 6-digit code every
   30 seconds derived from `HMAC-SHA1(secret, floor(time/30))`.
6. The user types the current code; the server runs
   `pyotp.TOTP(secret).verify(token, valid_window=60)` and, on success,
   creates a `UserKey` row with the secret in `properties["secret_key"]`.

The `valid_window=60` value is 60 *steps* either side of "now" — about ±30
minutes. That's deliberately generous so users with bad device clocks aren't
locked out. Source: `multifactor/factors/totp.py:13`.

## Tightening the verification window

If you want stricter timing, subclass `Create` and `Auth`:

```python
# myapp/totp_strict.py
from multifactor.factors import totp


class StrictCreate(totp.Create):
    pass


class StrictAuth(totp.Auth):
    def verify_login(self, token):
        from multifactor.models import KeyTypes, UserKey
        import pyotp

        for key in UserKey.objects.filter(
            user=self.request.user, key_type=str(KeyTypes.TOTP), enabled=True
        ):
            if pyotp.TOTP(key.properties["secret_key"]).verify(token, valid_window=1):
                return key
```

Then mount your URL ahead of `multifactor.urls` to override the named routes.
A `valid_window=1` (±30 seconds) is the RFC-recommended default; anything
larger trades security for clock-drift forgiveness.

## Where the secret lives

`UserKey.properties["secret_key"]` stores the base32-encoded TOTP secret. This
is by design: TOTP verification cannot be done without the secret, so it
cannot be hashed. Treat your database as secret.

If your threat model demands secret-at-rest encryption, options include:

- An application-level encrypted JSON field (e.g.
  [`django-encrypted-fields`](https://pypi.org/project/django-encrypted-fields/))
  applied to `UserKey.properties` — requires a migration and code changes
  in `factors.totp`.
- A KMS / Vault that the app fetches on each verification — more disruptive
  but better for compliance.
- Database-level transparent encryption (Postgres `pgcrypto`, MySQL TDE).

`django-multifactor` ships none of these out of the box.

## Migrating users between authenticator apps

Authenticator app users frequently want to move from app A to app B.
`django-multifactor` does not surface an "export key" feature deliberately —
displaying the raw secret again would be a credential-leak vector.

The standard recovery path is:

1. User reads the QR/secret from their existing app (most apps support this).
2. Adds it to their new app.
3. Discards the old app.

If they have lost access to their existing app entirely, treat it as a key
loss: delete the old `UserKey` via the admin and have them re-enrol.

## Hardening recommendations

- **Rate-limit `multifactor:totp_auth`.** A 6-digit code has only 1,000,000
  possibilities, and the `valid_window=60` means each verification check
  covers many of them. Without rate-limiting, brute force is feasible.
  [`django-ratelimit`](https://django-ratelimit.readthedocs.io/) or your CDN
  is fine.
- **Don't display the secret after registration.** The default template does
  not, but a custom template might. Resist.
- **Pair with fallback OTP** for the "I lost my phone" case (else you have
  no recovery path that doesn't require an admin).

## See also

- [FIDO2](fido2.md) — the phishing-resistant alternative.
- [TOTP troubleshooting](../debugging/totp-troubleshooting.md) — clock drift,
  QR scanning issues.
- Implementation: `multifactor/factors/totp.py`.
