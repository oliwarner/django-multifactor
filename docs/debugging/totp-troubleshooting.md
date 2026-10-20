# TOTP troubleshooting

TOTP problems usually trace back to clocks, secrets, or transcription. This
page lists the symptoms and what to try.

## Symptom: "Could not validate key, please try again"

Both during enrolment and during challenge. Five suspects, in order of
likelihood:

### 1. Clock drift on the server

By default only the previous, current and next 30-second step are accepted
(`MULTIFACTOR["TOTP_WINDOW"] = 1`, ±30 seconds). If verification fails, your
server clock, or the user's, is probably more than 30 seconds off. Releases
before the security update accepted ±30 minutes, so drift that used to be
tolerated now fails.

Check:

```bash
date --utc
# or, on macOS
date -u
```

Compare with <https://time.is/>. If it's wrong, fix NTP. Avoid raising
`TOTP_WINDOW` as a workaround — each step you add makes more codes valid
simultaneously and so makes guessing easier. If you must, `3` (±90 seconds) is
the most we'd suggest, and `60` restores the old, weak behaviour.

### 2. Clock drift on the user's device

Less common because phones sync to network time automatically. But:

- A jailbroken/rooted phone may have NTP disabled.
- A phone in Airplane Mode for days may drift noticeably.

Have the user open a clock app and compare to <https://time.is/> from
another device.

### 3. The user is reading the wrong row

If the user has multiple accounts in their authenticator app, they may be
scanning the row for a different site. `TOKEN_ISSUER_NAME` controls the
label — set it to something distinctive ("Acme Production" rather than
"Django").

### 4. The QR was scanned from a stale page

If the user reloaded `/multifactor/totp/new/` mid-setup, the generated
secret changed but their phone is still trying the old one. Have them
delete the entry in their authenticator and re-scan the current QR.

### 5. The code was already used

Each accepted code, and every earlier one, is rejected afterwards to prevent
replay. A user who types the same code twice, or whose enrolment code is
reused to log in straight away, must wait for the next 30-second code.

## Symptom: "Too many failed attempts"

After `MAX_ATTEMPTS` failed TOTP or fallback attempts within `ATTEMPT_PERIOD`
the user is logged out and locked out until `LOCKOUT_PERIOD` has passed since
their latest failure. Every attempt is stored as an `AuthAttempt` (visible in
the Django admin) and lockouts are logged at `WARNING` on the
`multifactor.throttle` logger.

To lift a lockout early, delete that user's recent failures, in the admin or
from a Django shell:

```python
from multifactor.models import AuthAttempt

AuthAttempt.objects.filter(user__username="alice", outcome="failure").delete()
```

## Symptom: QR code won't scan

- **Display too small.** Some authenticator apps need the QR to fill ~30% of
  the screen. Increase the rendered size in your override template.
- **Bad contrast.** Black-on-white is mandatory. If you've themed the page,
  ensure the QR isn't drawn over a coloured background.
- **The user is on the same device.** Authenticator apps scan via the
  camera; they can't scan a QR shown on the same phone. Use the secret
  string (the package displays it under the QR) and type it in manually.

## Symptom: "the user added TOTP but their phone shows expired codes"

The user is enrolled but their phone clock is wrong — see "Clock drift on
the user's device" above.

Another less-common cause: the user's TOTP app supports both 30-second and
60-second window codes. The package uses the default 30-second window —
if the app is configured for 60 seconds, codes won't match. This is rare
with mainstream apps (Authy, Google Authenticator, 1Password).

## Symptom: TOTP enrolment succeeds but auth fails immediately

Three things to check:

1. **`UserKey.objects.filter(user=..., key_type="TOTP", enabled=True)` returns rows.**
   If not, the enrolment didn't actually persist. Inspect Django logs for
   write errors.
2. **`properties["secret_key"]` is a valid base32 string.** Run
   `pyotp.TOTP(key.properties["secret_key"]).now()` — should produce a
   6-digit code. If it raises, the secret is corrupted.
3. **The same secret is on the user's app.** Have them open the entry — most
   apps display the current code. Compare with the server output of the
   line above.

## Symptom: codes match on the server's clock but the user types something different

Almost always: **the user is reading the previous code as it counts down**.
Authenticator codes refresh every 30 seconds. If the user starts reading at
0:29 of a window, by the time they finish typing the code may have rolled
over.

Mitigation:

- Display a countdown alongside the input.
- Raise `MULTIFACTOR["TOTP_WINDOW"]` from its default of `1` to `3` for a little
  more leeway. Don't go much higher; see [clock drift](#1-clock-drift-on-the-server).

## Inspecting from a Django shell

```python
from multifactor.models import UserKey, KeyTypes
import pyotp

user_keys = UserKey.objects.filter(
    user__username="alice", key_type=KeyTypes.TOTP, enabled=True
)
for k in user_keys:
    totp = pyotp.TOTP(k.properties["secret_key"])
    print(
        k.pk,
        "now=",
        totp.now(),
        "previous=",
        totp.at(totp.timecode(__import__("time").time()) - 1),
    )
```

The `now()` output should match what Alice's phone is currently showing.

## See also

- [TOTP guide](../guides/totp.md) — happy-path setup.
- [Common issues](common-issues.md).
