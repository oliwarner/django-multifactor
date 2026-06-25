# Authentication flow

This page captures the *control flow* of `django-multifactor`. If you're trying
to reason about why a particular user got challenged (or didn't), or if you're
hunting a session bug, start here.

## The big picture

The flowchart below is the one in the project README — it covers every branch
in `decorators.multifactor_protected` plus the factor selection and verification
that follows.

```{mermaid}
flowchart TD
    Start([User attempts to access protected page]) --> Auth{User authenticated?}

    Auth -->|No| AllowAccess[Allow access - no MFA required]
    Auth -->|Yes| Bypass{Bypass enabled?}

    Bypass -->|Yes| AllowAccess
    Bypass -->|No| UserFilter{User matches filter?}

    UserFilter -->|No filter set or<br/>user matches| CheckKeys{User has<br/>MFA keys?}
    UserFilter -->|User doesn't match| AllowAccess

    CheckKeys -->|No keys| CheckRequired{factors > 0?}
    CheckKeys -->|Has keys| CheckActive{Keys authenticated<br/>in session?}

    CheckRequired -->|No| Advertise{advertise=true?}
    CheckRequired -->|Yes| RequireAuth[Redirect to authenticate]

    Advertise -->|Yes| ShowMessage[Show optional MFA message]
    Advertise -->|No| AllowAccess
    ShowMessage --> AllowAccess

    CheckActive -->|No| RequireAuth
    CheckActive -->|Yes| CheckAge{max_age set?}

    CheckAge -->|No| CheckFactorCount
    CheckAge -->|Yes| AgeValid{Auth timestamp<br/>within max_age?}

    AgeValid -->|No| ShowWarning[Show re-auth warning]
    AgeValid -->|Yes| CheckFactorCount{Active factors >=<br/>required factors?}

    ShowWarning --> RequireAuth

    CheckFactorCount -->|No| ShowFactorWarning[Show factor count warning]
    CheckFactorCount -->|Yes| AllowAccess

    ShowFactorWarning --> RequireAuth

    RequireAuth --> AuthPage[MFA Authentication Page]

    AuthPage --> SelectMethod{Select auth method}

    SelectMethod -->|FIDO2| FIDO2Auth[Authenticate with<br/>Security Key/Biometric]
    SelectMethod -->|TOTP| TOTPAuth[Enter TOTP code<br/>from Authenticator]
    SelectMethod -->|Fallback| FallbackAuth[Send OTP via<br/>email/SMS/custom]

    FIDO2Auth --> Verify{Verification<br/>successful?}
    TOTPAuth --> Verify
    FallbackAuth --> Verify

    Verify -->|No| AuthPage
    Verify -->|Yes| WriteSession[Write auth to session<br/>with timestamp]

    WriteSession --> Recheck{RECHECK enabled?}

    Recheck -->|Yes| SetExpiry[Set random expiry<br/>between MIN and MAX]
    Recheck -->|No| SetNever[Set no expiry]

    SetExpiry --> Redirect[Redirect to original page]
    SetNever --> Redirect

    Redirect --> Start

    AllowAccess --> Done([Access granted])

    style Start fill:#e1f5ff
    style Done fill:#d4edda
    style RequireAuth fill:#fff3cd
    style AllowAccess fill:#d4edda
    style AuthPage fill:#cfe2ff
    style WriteSession fill:#cfe2ff
```

Things worth highlighting:

- **Unauthenticated requests pass through** the decorator without ever being
  challenged. That's deliberate — `django-multifactor` lets your existing auth
  stack (`@login_required`, `LoginRequiredMixin`, custom middleware) handle the
  "you are not logged in" case. If you forget `@login_required`, an anonymous
  user can read your "MFA protected" view.
- **`factors=0` is not "MFA off"** — it means "challenge users who already
  have factors; let those without factors through". Combine with `advertise=True`
  to softly encourage adoption.
- **`user_filter=None` matches everyone**. Pass `{"is_staff": True}` to require
  MFA for staff only.

## FIDO2 registration sequence

```{mermaid}
sequenceDiagram
    autonumber
    participant U as User (browser)
    participant W as Your Django view
    participant R as multifactor:fido2_register
    participant F as fido2.server.Fido2Server
    participant DB as Database (UserKey)

    U->>W: GET /admin/multifactor/fido2/new/
    W->>U: HTML page with WebAuthn JavaScript
    U->>R: GET (start registration)
    R->>F: register_begin(user, existing_credentials)
    F-->>R: challenge + state
    R->>R: store state in session["fido_state"]
    R-->>U: JSON registration options
    U->>U: navigator.credentials.create(options)
    Note over U: Browser asks user to<br/>tap key / use Touch ID
    U->>R: POST attestation (credential)
    R->>F: register_complete(state, data)
    F-->>R: AttestedCredentialData
    R->>DB: UserKey.objects.create(key_type=FIDO2, properties=...)
    R->>R: write_session(request, key)
    R-->>U: { status: OK }
```

The full source for this dance lives at `multifactor/factors/fido2.py:52-92`.
A few subtleties:

- The challenge is stored in `session["fido_state"]` — if your session is
  swapped between the GET and POST, registration fails. Sticky-session-or-
  shared-store is a hard requirement.
- The credential ID, type, and **domain** are stored in `UserKey.properties`.
  The domain check is what makes FIDO2 keys non-portable across deployments —
  see [FIDO2 troubleshooting](../debugging/fido2-troubleshooting.md).

## FIDO2 authentication sequence

```{mermaid}
sequenceDiagram
    autonumber
    participant U as User (browser)
    participant A as multifactor:fido2_authenticate
    participant F as fido2.server.Fido2Server
    participant DB as Database (UserKey)

    U->>A: GET (begin auth)
    A->>DB: select enabled FIDO2 keys for user + this domain
    DB-->>A: list of credentials
    A->>F: authenticate_begin(credentials)
    F-->>A: challenge + state
    A->>A: store state in session["fido_state"]
    A-->>U: JSON auth options
    U->>U: navigator.credentials.get(options)
    Note over U: Browser asks user to<br/>tap key / present biometric
    U->>A: POST assertion
    A->>F: authenticate_complete(state, credentials, data)
    F-->>A: matching credential
    A->>DB: lookup UserKey by credential_id
    A->>A: write_session(request, key)
    A-->>U: { status: OK, redirect: ... }
```

## TOTP setup and authentication

```{mermaid}
sequenceDiagram
    autonumber
    participant U as User
    participant C as multifactor:totp_start (Create)
    participant T as pyotp.TOTP
    participant DB as Database

    Note over U,C: ----- Setup -----
    U->>C: GET /admin/multifactor/totp/new/
    C->>T: generate random base32 secret
    T-->>C: secret
    C->>T: provisioning_uri(username, issuer_name)
    T-->>C: otpauth:// URI
    C-->>U: render template with QR code + secret
    U->>U: scan QR with authenticator app
    U->>C: POST { key: secret, answer: 123456 }
    C->>T: TOTP(secret).verify("123456", valid_window=60)
    T-->>C: True
    C->>DB: UserKey.objects.create(key_type=TOTP, properties.secret_key=...)
    C->>C: write_session(request, key)
    C-->>U: redirect to home

    Note over U,C: ----- Authentication -----
    U->>C: POST /admin/multifactor/totp/auth/ { answer: 654321 }
    C->>DB: select enabled TOTP keys for user
    loop each key
        C->>T: TOTP(secret).verify("654321", valid_window=60)
    end
    T-->>C: True (one matches)
    C->>C: write_session(request, matching_key)
    C-->>U: redirect to multifactor-next
```

The `valid_window=60` (one minute either side of "now") is forgiving by TOTP
standards — see [TOTP troubleshooting](../debugging/totp-troubleshooting.md)
if you want to tighten it.

## Fallback OTP fan-out

```{mermaid}
sequenceDiagram
    autonumber
    participant U as User
    participant F as multifactor:fallback_auth
    participant T1 as Transport: email
    participant T2 as Transport: sms
    participant T3 as Transport: signal
    participant DB as DisabledFallback

    U->>F: GET (request OTP)
    F->>F: generate random 8-digit OTP, store in session
    F->>DB: lookup user's DisabledFallback rows
    DB-->>F: ["signal"]   # user opted out of Signal
    par send via every enabled transport
        F->>T1: send_email(user, "Your OTP is …")
        T1-->>F: "email"
    and
        F->>T2: send_sms(user, "Your OTP is …")
        T2-->>F: "sms"
    end
    F-->>U: "We sent your code via email and sms."
    U->>F: POST { otp: 12345678 }
    F->>F: compare to session value
    F->>F: write_session(request, key=None)
    F-->>U: redirect to multifactor-next
```

Two design choices that surprise people on first reading:

- **Fan-out, not selection.** The user does not pick a transport. The package
  sends to **every** enabled transport simultaneously, so a compromised email
  account does not let an attacker quietly intercept the code — the legitimate
  user gets an SMS at the same moment and knows something is wrong.
- **`key=None` on fallback success.** Fallback authentication writes a session
  marker with no `UserKey` row attached, because no specific key was used.
  That means `active_factors()` returns `[None, ...]` for the fallback slot —
  factor-count requirements treat it as a single "soft" factor.

## Where next?

- Where does this state live, and how long? [Session model](session-model.md).
- How are factor types compared? [Factors overview](factors-overview.md).
- Things going wrong? [Common issues](../debugging/common-issues.md).
