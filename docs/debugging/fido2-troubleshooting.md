# FIDO2 troubleshooting

FIDO2 / WebAuthn fails opaquely. The package logs a stack trace on
registration failure but the user-facing message is generic. This page is a
triage tree for the most common causes.

## Diagnostic preflight

Before reaching for stack traces, confirm:

| Check | How |
| --- | --- |
| Page is on HTTPS (or `localhost`) | Open the page; look at the address bar. WebAuthn refuses anything else. |
| `FIDO_SERVER_ID` matches the URL bar | `print(settings.MULTIFACTOR["FIDO_SERVER_ID"])` matches the domain you're typing. |
| JavaScript console | Open DevTools → Console. WebAuthn errors land here verbatim. |
| Server log for `multifactor.factors.fido2` | Enable `DEBUG`-level logging (see [Logging](logging.md)). |

90% of FIDO2 failures are caught by one of those four.

## Symptom → cause

### "An error occurred trying to register" / browser console: `SecurityError`

**Almost always RP ID mismatch.**

The page is at `https://app.example.com/...` but `FIDO_SERVER_ID` is set to
`example.com` (or vice versa). The browser refuses to issue a credential.

Fix: set `FIDO_SERVER_ID` to either the page's domain exactly, or a
registrable parent domain (e.g. `example.com` is valid for `app.example.com`).

### "navigator.credentials.create is not a function"

The browser is too old or doesn't support WebAuthn. Check at
<https://caniuse.com/webauthn>. Fall back to TOTP for those users.

### "User cancelled the operation"

The user dismissed the OS prompt — pressed Cancel on the Touch ID dialog,
unplugged the YubiKey, etc. Not a bug; retry.

### "Bad credentials" / `InvalidStateError`

The key the user is presenting is already registered against this account.
WebAuthn refuses to double-register. Suggest the user pick a different key
or rename the existing one.

### Registration succeeds, but auth fails with the same key

Most common cause: `FIDO_SERVER_ID` was changed between registration and
authentication. The package stores the RP ID in `UserKey.properties["domain"]`
at registration; auth filters keys by `properties__domain=request.get_host()`.
If they don't match, the key is silently excluded.

Diagnostic SQL:

```sql
SELECT user_id, properties->>'domain', enabled
FROM multifactor_userkey
WHERE key_type = 'FIDO2';
```

If `domain` doesn't match your current host, you have stale keys. Either
revert `FIDO_SERVER_ID` or have users re-enrol.

### Auth works on first try, fails on the second

Session state lost between the GET (start) and POST (complete) of the
challenge. See [common issues](common-issues.md#users-see-the-login-message-every-page-load).

The challenge state is stored in `request.session["fido_state"]`. If your
session doesn't persist between requests (multiple processes, signed-cookie
overflow, CDN session stripping), this is your problem.

### Cross-subdomain key behaviour

A key registered with `FIDO_SERVER_ID="example.com"` works on any subdomain
because the RP ID is a *suffix*. A key registered with
`FIDO_SERVER_ID="app.example.com"` does **not** work on
`other.example.com`.

Pick the narrowest RP ID consistent with your topology — subdomain takeover
otherwise hands over MFA for the whole apex.

### USB key works, Touch ID doesn't (or vice versa)

The package uses `user_verification="discouraged"` — the most permissive
setting. If you've subclassed `factors.fido2.Authenticate` to require
verification, only keys with PINs or biometrics will pass. The default does
not require this.

### Safari fails when Chrome works

Safari is stricter about RP ID format and rejects mixed IPv4/hostname
configurations. The browser console will tell you specifically; check
DevTools → Console. Often the fix is to use the hostname (e.g.
`localhost`) rather than `127.0.0.1`.

### "navigator.credentials.create" hangs forever

The browser is waiting for a key that isn't there — common when a USB key
gets unplugged mid-challenge. The OS prompt should time out after ~60s.

## Reproducing locally

To test FIDO2 locally with a real domain (e.g. for a key that requires a
non-localhost RP ID):

```bash
# Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8000

# ngrok
ngrok http 8000
```

Then set `MULTIFACTOR["FIDO_SERVER_ID"] = "abcd1234.trycloudflare.com"`
(or whatever ngrok prints) and reload. The bundled testsite reads
`os.environ["DOMAIN"]` for exactly this purpose:

```bash
DOMAIN=abcd1234.trycloudflare.com python testsite/manage.py runserver
```

## When to read the package source

`multifactor/factors/fido2.py` is ~120 lines. Useful breakpoints when
stepping through:

- `Register.get()` line 53 — start of registration; `state` is written here.
- `Register.post()` line 67 — `register_complete` raises here on failure.
- `Authenticate.get()` line 96 — start of auth; `state` is written here.
- `Authenticate.post()` line 105 — `authenticate_complete` raises here.

The `except:` at line 85 swallows registration errors and emits a generic
500-style JSON response. The exception is logged at ERROR level — enable
the `multifactor.factors.fido2` logger (see [Logging](logging.md)) to see
the underlying traceback.

## See also

- [FIDO2 guide](../guides/fido2.md) — happy-path setup.
- [Logging](logging.md) — turning on the package's loggers.
