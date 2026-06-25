# Session debugging

The session is the source of truth for "is this user MFA-authenticated right
now?". When users are challenged unexpectedly — or *not* challenged when you
expect them to be — this is where to look first.

## Quick inspection from the shell

```python
# python manage.py shell
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
import pprint

User = get_user_model()
user = User.objects.get(username="alice")

# Find Alice's sessions
for s in Session.objects.all():
    data = s.get_decoded()
    if data.get("_auth_user_id") == str(user.pk):
        pprint.pprint(data)
```

What to look for:

- `multifactor` — list of `(key_type, key_id, verified_at, recheck_expiry)`
  tuples. Empty list → no active factors.
- `multifactor-next` — URL the user is heading to after MFA. Present during a
  pending challenge.
- `fido_state` — opaque WebAuthn state between GET and POST of a FIDO2 dance.
- `multifactor-fallback-otp` — current fallback OTP (sensitive! Stays in the
  session until the user enters it correctly).
- `multifactor-advertised` — flag set when `advertise=True` has shown its
  banner.

## Inspecting the session inside a request

Use `MultiFactorMixin` to annotate `self` in a CBV, or
`active_factors(request)` directly in a function view:

```python
from multifactor.common import active_factors, has_multifactor, is_bypassed


def whoami(request):
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "username": str(request.user),
            "has_factors": has_multifactor(request),
            "active_factors": active_factors(request),
            "bypass": is_bypassed(request),
        }
    )
```

Wire this to a `/_debug/whoami/` URL in dev settings only. Remove for
production.

## Django Debug Toolbar

The toolbar's **Request** panel shows the full session dict on every page
load. It's the fastest path for visual inspection during development. The
bundled `testsite/` enables it by default.

## Why does my factor disappear after a few hours?

Look at the tuple's `recheck_expiry` (fourth element). If it's `False`,
`RECHECK` is disabled and the factor lasts the lifetime of the session. If
it's a float, that's the Unix timestamp past which the factor stops counting.

```python
import time

factors = request.session.get("multifactor", [])
for ktype, kid, verified, expiry in factors:
    ttl = expiry - time.time() if expiry else float("inf")
    print(f"{ktype} key={kid} verified_ago={time.time()-verified:.0f}s ttl={ttl:.0f}s")
```

If `ttl` is negative, that factor has expired and `active_factors()` will
filter it out next time it's called.

## Why is `active_factors` empty after the user just verified?

Five possibilities:

1. **Session not persisting.** The next request is on a different process
   with a different session store, or the cookie is being rejected.
2. **`SESSION_COOKIE_DOMAIN` misconfigured.** Cookie was set on
   `app.example.com` but the next request goes to `example.com`. The
   cookies don't match.
3. **Cookie size overflow.** If you're using `signed_cookies` and the
   `fido_state` blob exceeds 4 KB (rare but possible), the cookie is dropped.
   Switch to a server-side session backend.
4. **Session SECRET_KEY rotated.** Old sessions are dropped silently.
5. **Concurrent logout from another tab.** Killed all session data.

Reproduce by enabling DEBUG logging on `django.contrib.sessions` and
correlating the session ID across requests.

## Why is `has_multifactor` `True` but `active_factors` empty?

This is the **enrolled but not currently authenticated** state. The user has
registered factors (`UserKey` rows exist) but has not yet completed an MFA
challenge in this session. The decorator will redirect them to
`multifactor:authenticate` on the next protected view.

If the user *did* just authenticate and you still see this state, the write
to `session["multifactor"]` didn't take — see the previous question.

## Force-clearing MFA state for a user

To reset a user's MFA session (e.g. for testing the challenge flow without
logging out):

```python
# in a CBV or function view
request.session["multifactor"] = []
request.session.modified = True
```

The next protected view hit will re-challenge.

To kill all of Alice's sessions site-wide:

```python
from django.contrib.sessions.models import Session

for s in Session.objects.all():
    if s.get_decoded().get("_auth_user_id") == str(alice.pk):
        s.delete()
```

She'll be logged out everywhere and need to log in + MFA again.

## Why is the session sticky across recheck even though I set RECHECK_MIN/MAX low?

`RECHECK` only fires when `active_factors()` runs — i.e. when the user hits
a protected view. Idle users keep their session. To force fresh checks on
every request, lower `max_age` on the specific views rather than dropping
`RECHECK_*`.

## See also

- [Session model](../concepts/session-model.md) — the conceptual reference.
- [Common issues](common-issues.md).
