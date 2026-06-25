# Architecture

`django-multifactor` is a small package. Most of the moving parts are direct
Django primitives (views, models, sessions, the messages framework) plus two
external libraries: `pyotp` for TOTP and `fido2` for WebAuthn. This page is the
mental model you need before any of the other pages make sense.

## Component overview

```{mermaid}
flowchart LR
    subgraph YourApp["Your Django app"]
        YourViews["Your views"]
        YourDeco["@multifactor_protected"]
    end

    subgraph Package["multifactor package"]
        direction TB
        Decorators["decorators.py<br/>multifactor_protected"]
        Mixins["mixins.py<br/>RequireMultiAuthMixin<br/>PreferMultiAuthMixin"]
        Common["common.py<br/>has_multifactor()<br/>active_factors()<br/>write_session()<br/>is_bypassed()"]
        Views["views.py<br/>List, Add, Authenticate, Help"]

        subgraph Factors["factors/"]
            FIDO2["fido2.py<br/>Register, Authenticate"]
            TOTP["totp.py<br/>Create, Auth"]
            Fallback["fallback.py<br/>Auth + transports"]
        end

        Models["models.py<br/>UserKey, DisabledFallback"]
        Templates["templates/<br/>multifactor/*.html<br/>brand.html, email.html (overridable)"]
        Settings["app_settings.py<br/>MULTIFACTOR defaults"]
    end

    subgraph Django["Django core"]
        Session[("django.contrib.sessions")]
        DB[("Database<br/>(your DEFAULT)")]
        Messages["django.contrib.messages"]
    end

    YourViews --> YourDeco
    YourDeco --> Decorators
    Decorators --> Common
    Mixins --> Common
    Common --> Models
    Common --> Session
    Common --> Settings

    Views --> Common
    Views --> Factors
    FIDO2 --> Models
    TOTP --> Models
    Fallback --> Messages
    Fallback --> Settings
    Models --> DB
    Views --> Templates

    style YourApp fill:#cfe2ff
    style Package fill:#fff3cd
    style Django fill:#d4edda
```

The user-facing entry point is the **decorator** (or one of the **mixins**). It
inspects the session via `common.py`, looks up the user's `UserKey` rows, and
either:

1. Lets the request through (`baulk()` — i.e. call the wrapped view), or
2. Redirects to `multifactor:authenticate`, where the user picks a factor and
   one of the **factor views** handles the challenge.

On successful verification the factor view calls `common.write_session()`,
which records `(key_type, key_id, timestamp, recheck_expiry)` in the session
and bounces the user back to wherever they were heading.

## Where the state lives

There are three places `django-multifactor` keeps state:

| Location | What's there | Lifecycle |
| --- | --- | --- |
| **Database** | `UserKey` rows (one per registered factor), `DisabledFallback` rows. | Persistent. Survives logout. |
| **Session** | `session["multifactor"]` — a list of `(key_type, key_id, verified_at, recheck_expiry)` tuples for *currently* authenticated factors. Also `session["multifactor-next"]`, `session["fido_state"]`, fallback OTP state. | Tied to the session. Cleared on logout if your `SESSION_ENGINE` clears. |
| **Settings** | Everything in `MULTIFACTOR` (with defaults merged from `app_settings.py`). | Immutable at runtime. |

```{warning}
The session is the source of truth for "is this user currently MFA-verified?".
That means **session security is MFA security** — see
[security best practices](../security/best-practices.md) for cookie hardening.
```

## The two stories: protecting a view vs. registering a factor

Two flows dominate the codebase:

### Story 1 — a user hits a protected view

1. Request comes in for `billing()`.
2. `@multifactor_protected` runs its checks (auth? bypass? user filter? key
   count? max age?).
3. If everything is satisfied, the wrapped view runs.
4. If something fails, the user is bounced to `multifactor:authenticate` with
   `session["multifactor-next"]` set to the original URL.

### Story 2 — a user registers a new factor

1. User visits `/admin/multifactor/` (`views.List`).
2. Picks **Add factor** → `views.Add`.
3. Selects FIDO2 or TOTP. The picker mounts the matching template, which
   talks to either `factors.fido2.Register` or `factors.totp.Create` via
   XHR/POST.
4. On success a new `UserKey` row is created **and** `write_session()` marks
   the factor as currently active in this session.

For a step-by-step view of either story, see [Authentication flow](auth-flow.md).

## What `django-multifactor` does NOT do

- It is **not** a primary authentication system. Users must already be
  authenticated by Django's normal `login()` before any MFA happens.
- It does **not** rate-limit OTP attempts itself. Put a generic rate limiter
  (django-ratelimit, django-axes, your CDN) in front of `multifactor:*` URLs.
- It does **not** notify users of new factor registrations. If you want a
  "your account just had a new security key added" email, hook
  `signals.post_save` on `UserKey`.

## Where next?

- See the full request flow: [Authentication flow](auth-flow.md).
- Understand session state and recheck: [Session model](session-model.md).
- Compare the factor types: [Factors overview](factors-overview.md).
