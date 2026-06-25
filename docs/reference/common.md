# multifactor.common

Utility functions used internally by the decorator, mixins, and factor views.
You can import any of these from `multifactor.common`; they form the
package's de-facto public helper API. Source: `multifactor/common.py`.

## has_multifactor

```text
has_multifactor(request: HttpRequest) -> bool
```

`True` if `request.user` has at least one `UserKey` with `enabled=True`.

Cheap — runs `UserKey.objects.filter(...).exists()`. Use in templates or
views to gate "you should add a factor" prompts.

## active_factors

```text
active_factors(request: HttpRequest) -> list[tuple]
```

Returns the list of currently-active factors in
`request.session["multifactor"]`, filtering out any whose `recheck_expiry`
has passed. Each tuple is `(key_type, key_id, verified_at, recheck_expiry)`.

Side-effect: writes the filtered list back to the session so expired
entries don't accumulate.

```python
from multifactor.common import active_factors

if not active_factors(request):
    # user is logged in but has no verified factors right now
    ...
```

## disabled_fallbacks

```text
disabled_fallbacks(request: HttpRequest) -> QuerySet[str]
```

Flat values list of `DisabledFallback.fallback` for the current user. Used
by `factors.fallback.Auth` to skip transports the user has opted out of.

## next_check

```text
next_check() -> float
```

Returns a Unix timestamp `now + randint(RECHECK_MIN, RECHECK_MAX)`. Called
by `write_session()` to set each factor's `recheck_expiry`.

## render

```text
render(request, template_name, context, **kwargs) -> HttpResponse
```

A thin wrapper around `django.shortcuts.render` with the context spread
into a fresh dict. Used by the views; you're unlikely to need it directly.

## method_url

```text
method_url(method: str) -> str
```

Maps a factor name to its auth URL name:

```python
method_url("FIDO2")  # -> "multifactor:fido2_auth"
method_url("TOTP")  # -> "multifactor:totp_auth"
```

## write_session

```text
write_session(request: HttpRequest, key: UserKey | None) -> None
```

Records a successful factor verification in the session. Prepends a new
tuple `(key_type, key_id, now, next_check_or_False)` to
`request.session["multifactor"]`, removing any prior entry for the same
key (so duplicates don't accumulate).

If `key` is `None` (the fallback case), the tuple is `(None, None, now,
next_check)`.

If `key` is a real `UserKey`, also updates `key.last_used` and saves.

```python
from multifactor.common import write_session

# after your own custom factor verification logic
write_session(request, key=my_userkey)
```

## login

```text
login(request: HttpRequest) -> HttpResponse
```

Post-verification redirect. Order of precedence:

1. If `MULTIFACTOR["SHOW_LOGIN_MESSAGE"]` is truthy, flashes `LOGIN_MESSAGE`
   formatted with the URL of `multifactor:home`.
2. If `session["multifactor-next"]` is set, redirects there (and pops it).
3. If `MULTIFACTOR["LOGIN_CALLBACK"]` is set, calls
   `import_string(callback)(request, username=session["base_username"])`
   and returns the result.
4. Otherwise redirects to `settings.LOGIN_URL`.

## is_bypassed

```text
is_bypassed(request: HttpRequest) -> bool
```

Returns the result of `import_string(MULTIFACTOR["BYPASS"])(request)`,
or `False` if `BYPASS` is unset. See [conditional bypass](../guides/conditional-bypass.md).

## See also

- [Session model](../concepts/session-model.md) — how these are used.
- [Authentication flow](../concepts/auth-flow.md) — the call-graph.
