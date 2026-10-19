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
   checks it against the codes for the current time step and
   `MULTIFACTOR["TOTP_WINDOW"]` steps either side of it, and on success
   creates a `UserKey` row with the secret in `properties["secret_key"]`.

`TOTP_WINDOW` defaults to `1` — the previous, current and next 30-second step,
so about ±30 seconds of clock drift — as recommended by RFC 6238. Earlier
releases hard-coded 60 steps (±30 minutes, 121 valid codes), which made
guessing a code about 40 times easier. If you relied on that tolerance, see
[Upgrading](upgrading.md) and the [settings reference](../reference/settings.md#totp-window).

Every accepted code is stored as `properties["last_step"]` on the key. A code
for that step, or an earlier one, is rejected, so a code that was observed
can't be replayed.

## Changing the verification window

Set it in your settings; no subclassing is needed:

```python
MULTIFACTOR = {
    "TOTP_WINDOW": 3,  # ±90 seconds. Default is 1.
}
```

## Customising verification further

If you need different behaviour entirely, subclass `Create` and `Auth`:

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
A subclass that replaces `verify_login` bypasses the replay protection in the
stock `Auth`, so only do this if you have a reason the settings can't cover.
The attempt limiting still applies because it lives in `Auth.post`.

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

- **Keep attempt limiting on.** A 6-digit code has only 1,000,000
  possibilities. The built-in limit (5 failures in 5 minutes locks the user out
  for 30, per user) is recorded in the database; see
  [attempt limiting](../reference/settings.md#attempt-limiting).
- **Also rate-limit `multifactor:totp_auth` per IP** with
  [`django-ratelimit`](https://django-ratelimit.readthedocs.io/) or your CDN.
  The built-in limit is per user.
- **Don't display the secret after registration.** The default template does
  not, but a custom template might. Resist.
- **Pair with fallback OTP** for the "I lost my phone" case (else you have
  no recovery path that doesn't require an admin).

## See also

- [FIDO2](fido2.md) — the phishing-resistant alternative.
- [TOTP troubleshooting](../debugging/totp-troubleshooting.md) — clock drift,
  QR scanning issues.
- Implementation: `multifactor/factors/totp.py`.
