# Session model

`django-multifactor` is essentially a thin layer over **the Django session**.
This page explains what gets written, when, and how to read it during
debugging.

## What the session looks like

After a user has authenticated with one or more factors, their session contains:

```python
request.session["multifactor"] = [
    ("FIDO2", 42, 1717450000.0, 1717470000.0),
    ("TOTP", 17, 1717450005.0, 1717471234.0),
]
```

Each tuple is `(key_type, key_id, verified_at, recheck_expiry)`:

| Position | Type | Meaning |
| --- | --- | --- |
| `key_type` | `str \| None` | `"FIDO2"` / `"TOTP"`, or `None` for fallback OTP (which has no `UserKey`). |
| `key_id` | `int \| None` | Primary key of the `UserKey` row, or `None` for fallback. |
| `verified_at` | `float` | `timezone.now().timestamp()` at the moment the challenge succeeded. Used by `max_age` checks. |
| `recheck_expiry` | `float \| False` | Unix timestamp past which this factor is no longer "active". `False` if `RECHECK = False`. |

Tuples whose `recheck_expiry` is in the past are silently filtered out by
`common.active_factors()` — they don't count toward the active factor list and
will not be returned to the decorator. Stale entries are not deleted explicitly;
they're just ignored.

## State machine

```{mermaid}
stateDiagram-v2
    [*] --> Anonymous
    Anonymous --> Authenticated: Django login()
    Authenticated --> Challenged: hit @multifactor_protected
    Challenged --> MFAVerified: factor verified (write_session)
    MFAVerified --> RecheckPending: recheck_expiry set
    RecheckPending --> MFAVerified: hit protected view before expiry
    RecheckPending --> Challenged: hit protected view after expiry
    MFAVerified --> Challenged: max_age elapsed
    MFAVerified --> Anonymous: Django logout()
    Authenticated --> Anonymous: Django logout()
```

```{note}
There is no "MFA logout" — the user becomes un-MFA-authenticated when their
session expires or `RECHECK_MAX` elapses. The session entry is never
explicitly purged. If you need an "MFA logout" feature (e.g. for shared
kiosks), pop `request.session["multifactor"]` from a custom view.
```

## Recheck — controlled invalidation

`RECHECK` is the mechanism that forces users to re-challenge periodically even
when their session is still valid.

```{mermaid}
gantt
    title Recheck timing for a single factor
    dateFormat  X
    axisFormat %M

    section Factor lifetime
    Verified (active)           :done, a1, 0, 180
    Random expiry window (3-6h) :crit, a2, 180, 360
    Stale (re-challenge)        :a3, 360, 600
```

- `RECHECK_MIN` — earliest possible expiry (default 3 hours).
- `RECHECK_MAX` — latest possible expiry (default 6 hours).
- The actual expiry is `verified_at + randint(MIN, MAX)`, picked at the moment
  of verification. The randomness is deliberate — it prevents a deployment-
  wide synchronised re-prompt storm at hour boundaries.

You can disable recheck entirely with `RECHECK = False`, but for production
sites we strongly recommend leaving it on. See
[recheck tuning](../security/recheck-tuning.md).

## How `factors=N` counts

The decorator parameter `factors=N` requires that `len(active_factors(request))
>= N`. Each tuple in `session["multifactor"]` is **one factor**, including the
fallback `(None, None, ...)` tuple.

That means a user who has verified both FIDO2 and TOTP in the same session
satisfies `factors=2`. A user who has verified only TOTP plus the fallback OTP
also satisfies `factors=2` — even though the fallback is a "softer" factor.

If you need to *exclude* the fallback from your factor count, gate on it
explicitly in your view:

```python
@multifactor_protected(factors=1)
def sensitive(request):
    from multifactor.common import active_factors

    if all(f[0] is None for f in active_factors(request)):
        # only fallback OTP — refuse
        return HttpResponseForbidden("Stronger factor required.")
    ...
```

## Other session keys you may see

| Key | Set by / used for |
| --- | --- |
| `multifactor-next` | URL to redirect to after a successful challenge. Set by the decorator/mixin before the redirect; popped by `common.login()`. |
| `fido_state` | The opaque `Fido2Server` state across the GET (challenge) and POST (verify) of a FIDO2 dance. **Must persist across requests** — see [FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md). |
| `multifactor-fallback-otp` | Plaintext OTP for the fallback flow. Cleared on success. |
| `multifactor-fallback-succeeded` | Human-readable string describing which transports sent the OTP (e.g. `"email and sms"`). Displayed back to the user. |
| `multifactor-advertised` | `True` if `advertise=True` has already shown its banner this session; prevents the banner from re-appearing on every page load. |
| `base_username` | Forwarded to `LOGIN_CALLBACK` if set. |

## Inspecting a session

For debugging in production, the [session-debugging](../debugging/session-debugging.md)
guide shows you how to dump these keys live. In dev, the
[Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/) is the
fastest path — its **Request** panel shows the full session dict.

## Where next?

- Detailed troubleshooting: [Session debugging](../debugging/session-debugging.md).
- How active factors are written: [common.write_session](../reference/common.md).
