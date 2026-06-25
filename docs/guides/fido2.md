# FIDO2 / WebAuthn

FIDO2 (a.k.a. WebAuthn) is the strongest factor `django-multifactor` ships.
This guide covers configuring it correctly and the deployment requirements
that bite people on first roll-out.

## What you need

- **HTTPS in production.** WebAuthn refuses to operate over plain HTTP except
  against `localhost`. There is no workaround — buy a cert or use a reverse
  proxy that terminates TLS.
- **A stable Relying Party ID (RP ID).** This is the registrable domain users
  see in the address bar — `example.com`, or `auth.example.com` if you serve
  the MFA flows from a subdomain.
- **A modern browser.** All current Chrome, Firefox, Safari, and Edge versions
  support WebAuthn.

## Configuration

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": "example.com",  # exact domain users see
    "FIDO_SERVER_NAME": "My Django App",  # display name in the browser prompt
    "FIDO_SERVER_ICON": None,  # optional URL to an icon (rarely shown)
}
```

```{important}
The RP ID is a **suffix match** against the page's origin. A site on
`app.example.com` may use either `app.example.com` or `example.com` as its
RP ID, but **not** `other.example.com`. Picking `example.com` lets keys
registered on one subdomain work across all subdomains — handy, but means
any subdomain takeover compromises all of them. Pick the narrowest RP ID
that fits your topology.
```

## Local development

For local dev, `localhost` is a magic value that works without HTTPS:

```python
MULTIFACTOR = {
    "FIDO_SERVER_ID": "localhost",
    "FIDO_SERVER_NAME": "MyApp (dev)",
}
```

Drive the dev server on `http://localhost:8000/` (not `127.0.0.1`, which is
not the same origin as `localhost` for WebAuthn purposes).

For multi-developer scenarios where you need a real domain — for instance to
test a USB key — use [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel/)
or [ngrok](https://ngrok.com/) and set `FIDO_SERVER_ID` to the temporary
hostname they give you. The `testsite/testsite/settings.py` shipped in this
repo reads it from the `DOMAIN` environment variable for exactly this reason.

## How keys are stored

Each registered FIDO2 key creates one `UserKey` row with:

- `key_type = "FIDO2"`
- `properties["device"]` — the credential's `AttestedCredentialData`,
  websafe-base64 encoded.
- `properties["type"]` — `"public-key"` (currently the only WebAuthn type).
- `properties["domain"]` — the RP ID at the time of registration.

The domain is checked at auth time (`factors/fido2.py:46`). A key registered
against `example.com` will not authenticate against `staging.example.com`.

```{warning}
If you change `FIDO_SERVER_ID` after users have registered keys, **all
existing keys become unusable** for those users. They will be asked to
register again — and may end up locked out if you don't have fallback
configured.
```

## Registering multiple keys per user

Strongly encourage users to register two keys — a primary and a backup. The
current `Add factor` flow allows unlimited registrations; the management page
lists them all and lets users name them.

You can also bulk-import keys from existing inventories by creating `UserKey`
rows directly, but the binary `properties["device"]` is non-trivial to
synthesise outside the registration ceremony. In practice this means "ask
users to register manually" rather than "bulk provision".

## What the user sees

- **Security key:** browser shows "Touch your security key to register",
  user taps the key's button.
- **Touch ID / Windows Hello:** browser shows the OS sheet ("Use Touch ID
  to sign in to MyApp"), user uses the biometric.
- **NFC:** "Tap your security key on the back of your device" (mobile only).

The text and exact UX vary by browser and OS — none of this is in your
control.

## Hardening recommendations

- Set `user_verification="required"` if you want PIN/biometric on the key
  itself (the default in this package is `"discouraged"` for usability).
  Override by subclassing `factors.fido2.Authenticate` if you need this.
- Cap the number of FIDO2 keys per user in your own code if you have a
  policy. `django-multifactor` does not enforce a maximum.
- Monitor `UserKey.objects.filter(key_type="FIDO2", added_on__gte=…)` —
  unexpected new keys are a red flag for account takeover.

## Troubleshooting

The single most common failure mode is **RP ID mismatch**. See the
[FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md) page for the
full triage tree (HTTPS, RP ID, browser console errors, CSRF).

## See also

- [TOTP](totp.md) — the lower-friction alternative.
- [FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md).
- Implementation: `multifactor/factors/fido2.py`.
