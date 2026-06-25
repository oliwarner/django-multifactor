# TOTP troubleshooting

TOTP problems usually trace back to clocks, secrets, or transcription. This
page lists the symptoms and what to try.

## Symptom: "Could not validate key, please try again"

Both during enrolment and during challenge. Five suspects, in order of
likelihood:

### 1. Clock drift on the server

`pyotp.TOTP(...).verify(code, valid_window=60)` allows ±60 thirty-second
steps (~30 minutes either side). If verification still fails, your server
clock is more than 30 minutes off.

Check:

```bash
date --utc
# or, on macOS
date -u
```

Compare with <https://time.is/>. If it's wrong, fix NTP. Don't increase
`valid_window` further as a workaround — at large values you weaken the
factor (more codes are valid simultaneously).

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

### 5. The window has been tightened in a subclass

If you've subclassed `factors.totp.Auth` to enforce `valid_window=1`, you've
got a much tighter timing window (±30 s instead of ±30 min) and will see
more rejections. Verify your override.

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
- Increase `valid_window` from its default 60 to give more leeway (the
  package's default is already very generous).

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
