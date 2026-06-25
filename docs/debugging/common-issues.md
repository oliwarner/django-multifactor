# Common issues

A triage table for the failures that come up most often when integrating
`django-multifactor`. If a symptom isn't listed here, check the specific
troubleshooting pages for [FIDO2](fido2-troubleshooting.md), [TOTP](totp-troubleshooting.md),
or [sessions](session-debugging.md).

## "I get a 404 on /admin/multifactor/"

The URL include is missing or in the wrong place.

```python
# urls.py
urlpatterns = [
    path("admin/multifactor/", include("multifactor.urls")),  # <-- required
    path("admin/", admin.site.urls),
]
```

Confirm with `python manage.py show_urls | grep multifactor` (requires
[`django-extensions`](https://django-extensions.readthedocs.io/), which the
testsite ships with).

## "I get a 500 on first visit"

Usually a missing migration:

```bash
python manage.py migrate
```

Or `django.contrib.messages` not in `INSTALLED_APPS`. The package flashes
warnings through the messages framework — without it the middleware
explodes.

## "WebAuthn pops up but registration fails silently"

99% of the time this is `FIDO_SERVER_ID` not matching the page's domain.
See [FIDO2 troubleshooting](fido2-troubleshooting.md).

## "TOTP says 'Could not validate key, please try again' for the right code"

- **Clock drift** on either the server or the user's device. The TOTP
  algorithm depends on synchronised clocks (within a few seconds).
- **Wrong secret** — the user scanned an old QR, or has two accounts and
  scanned the wrong one.
- **Window too tight** — the package ships with `valid_window=60` (very
  generous). If you've subclassed to tighten it, loosen it again until you
  isolate the cause.

Full triage: [TOTP troubleshooting](totp-troubleshooting.md).

## "The user logs in, gets MFA, goes to the next page, gets challenged again"

Session lost between the challenge and the next page. Possible causes:

- Two server processes with different `SECRET_KEY` (rotating deployment,
  multi-region without shared sessions).
- Sticky-session affinity not configured at the load balancer.
- Session backend = `signed_cookies` and the cookie size exceeds the
  browser's 4 KB cap (FIDO2 state is large).
- The user is rejecting cookies.

See [session debugging](session-debugging.md) for inspecting in-flight.

## "Users see the login message every page load"

`MULTIFACTOR["SHOW_LOGIN_MESSAGE"]` is `True` (the default) but the message
is being rendered on every page because your base template doesn't *consume*
messages. Make sure your template iterates `messages` and renders them in
a way that consumes the queryset, e.g.:

```django
{% if messages %}
  <ul class="messages">
    {% for message in messages %}<li>{{ message }}</li>{% endfor %}
  </ul>
{% endif %}
```

The Django messages framework auto-clears messages once iterated.

## "Advertise banner won't go away"

`advertise=True` records `request.session["multifactor-advertised"] = True`
to prevent re-showing. If it keeps coming back, your session isn't
persisting writes (see above).

## "FIDO2 registration works in Chrome, fails in Safari"

Safari has historically been stricter about `FIDO_SERVER_ID` formatting and
user-verification requirements. Check the browser console for the actual
WebAuthn error. Safari errors are sometimes only visible there.

## "I disabled a key in admin but the user still gets through"

`active_factors()` reads the session's `multifactor` list. Disabling a key
in the admin doesn't purge existing session entries. Either:

1. Wait for the session entry to expire (`RECHECK_MAX`).
2. Force a logout — `from django.contrib.sessions.models import Session`
   then `Session.objects.filter(...).delete()` for that user.

The next protected-view hit will re-evaluate `has_multifactor` and bounce
the user through the challenge again.

## "I bumped Django and admin URLs broke"

`django.urls.include` semantics haven't changed, but `app_name` requires a
matching `namespace` on some configurations. The package sets `app_name =
"multifactor"` — your `include()` should use the bare string:

```python
path("admin/multifactor/", include("multifactor.urls"))  # correct
```

…and not the `(module, "namespace")` tuple form, which collides with the
package's own namespace declaration.

## "The fallback OTP arrives in email but the form rejects it"

Watch for whitespace — Outlook in particular has a habit of inserting
non-breaking spaces around codes. The default form strips whitespace
(`request.POST["otp"].strip()`); a custom template that doesn't strip will
break.

## When the dump-everything approach is faster

For a fast "what does the session look like *right now*?" check, see
[session debugging](session-debugging.md) — it walks through dropping a
breakpoint into `decorators.py` and inspecting state mid-request.

## Where next?

- FIDO2-specific failures: [FIDO2 troubleshooting](fido2-troubleshooting.md).
- TOTP-specific failures: [TOTP troubleshooting](totp-troubleshooting.md).
- Session state: [Session debugging](session-debugging.md).
- Logging configuration: [Logging](logging.md).
