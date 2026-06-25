# Extending with custom fallback MFA methods

The fallback OTP system is `django-multifactor`'s extension point for adding
new "soft" factors — SMS, push notification, Signal, Slack DM, paper code,
whatever your environment supports. This page explains the contract and
walks through a real-world worked example (SMS via Twilio) plus a
deliberately-silly stub (carrier pigeon) so you can see the shape of a
minimal transport.

## The contract

A fallback transport is a **callable** with the signature:

```python
def my_transport(user, message: str) -> str | False:
    """Deliver `message` to `user`. Return a truthy label on success,
    or False on failure."""
```

The return value is used in two places:

1. The package collects all non-False returns to build the **"we sent your
   code via …"** message shown to the user.
2. Any transport returning False is silently skipped (no exception is raised
   to the user).

```{important}
Returning a **string** (e.g. `"sms"`) is conventional and shows up in the
"We sent your code via sms and email" line. Returning `True` works too, but
the message becomes "We sent your code via True", which is ugly. Always
return a human-readable label.
```

In addition, each transport is gated by a **predicate**:

```python
predicate = lambda user: user.profile.phone  # truthy if the user can receive
```

The predicate runs first. If it returns falsy, the transport is skipped
without calling the sender. This avoids `AttributeError`s on users who lack
the relevant contact detail.

## How fallback OTPs are dispatched

```{mermaid}
sequenceDiagram
    autonumber
    participant U as User
    participant FAuth as fallback.Auth.get()
    participant Predicate as predicate
    participant Sender as your transport
    participant Msg as messages framework

    U->>FAuth: GET /admin/multifactor/fallback/auth/
    FAuth->>FAuth: generate random OTP, store in session
    FAuth->>FAuth: disabled = DisabledFallback rows for user
    loop each (name, (predicate, sender)) in MULTIFACTOR["FALLBACKS"]
        FAuth->>Predicate: predicate(user)
        alt name in disabled OR predicate falsy
            Note over FAuth: skip
        else predicate truthy
            FAuth->>Sender: sender(user, message)
            Sender-->>FAuth: "sms" or False
            alt return truthy
                FAuth->>FAuth: append label to success list
            else return False
                Note over FAuth: silently skipped
            end
        end
    end
    alt no transport succeeded
        FAuth->>Msg: error("No fallback worked. Contact admin.")
        FAuth-->>U: redirect home
    else at least one
        FAuth->>FAuth: render template with labels joined
        FAuth-->>U: "We sent your code via sms and email"
    end
```

Source: `multifactor/factors/fallback.py:38-62`.

## Worked example: SMS via Twilio

This is the kind of transport most production sites end up writing.

### 1. The sender

```python
# myapp/mfa.py
from django.conf import settings
from twilio.rest import Client


def send_sms(user, message):
    """Deliver an OTP to the user's mobile number."""
    phone = getattr(user.profile, "phone", None)
    if not phone:
        return False

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            to=phone,
            from_=settings.TWILIO_FROM_NUMBER,
            body=message,
        )
        return "sms"  # <-- the label shown to the user
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Twilio SMS failed")
        return False
```

### 2. Wire it into MULTIFACTOR

```python
MULTIFACTOR = {
    "FALLBACKS": {
        "email": (lambda user: user.email, "multifactor.factors.fallback.send_email"),
        "sms": (
            lambda user: getattr(user.profile, "phone", None),
            "myapp.mfa.send_sms",
        ),
    },
}
```

Now when a user clicks "forgot your device?", the OTP is sent to **both**
their email and their phone simultaneously.

### 3. Why fan-out and not selection?

If the package let the user pick a transport, an attacker who had compromised
the user's email could quietly request an OTP and the legitimate user would
never know. With fan-out, the legitimate user's phone rings *at the same
time* — they know an authentication attempt is happening and can react.

This is documented in [fallback risks](../security/fallback-risks.md).

## Worked example: the carrier pigeon

Useful as a minimal template — strip the network calls, keep the shape:

```python
# myapp/mfa.py
from .pigeon_dispatch import find_bird


def send_carrier_pigeon(user, message):
    address = getattr(user, "address", None)
    if not address:
        return False
    bird = find_bird()
    bird.attach(message)
    bird.send(address)
    return (
        "carrier pigeon"  # appears in "We sent your code via carrier pigeon and email"
    )
```

```python
MULTIFACTOR = {
    "FALLBACKS": {
        "email": (lambda u: u.email, "multifactor.factors.fallback.send_email"),
        "pigeon": (lambda u: u.address, "myapp.mfa.send_carrier_pigeon"),
    },
}
```

## Letting users opt out of a transport

The `DisabledFallback` model records per-user opt-outs. If you want to
expose a "don't ever text me" toggle in your account UI, create rows by hand:

```python
from multifactor.models import DisabledFallback

DisabledFallback.objects.get_or_create(user=user, fallback="sms")
```

The dispatch loop checks `name in disabled_fallbacks(request)` and skips
that transport entirely (`factors/fallback.py:36`).

There is no built-in admin UI for these opt-outs at present — see the
[admin integration guide](admin-integration.md) for adding one if needed.

## Disabling fallback entirely

```python
MULTIFACTOR = {
    "FALLBACKS": {},
}
```

Be aware: a user who loses access to all their primary factors can no longer
authenticate. Reset paths become a manual admin task (`UserKey.objects.filter
(user=...).delete()` followed by user re-enrolment).

## Testing your transport

A console-printing transport is provided for development:
`multifactor.factors.fallback.debug_print_console`. Wire it up in your dev
settings:

```python
MULTIFACTOR = {
    "FALLBACKS": {
        "debug-console": (
            lambda u: u,
            "multifactor.factors.fallback.debug_print_console",
        ),
    },
}
```

The OTP is printed to your runserver console — perfect for local testing
without firing real SMS or emails. The bundled `testsite/` uses this
pattern.

## Hardening checklist

- **Rate-limit `/admin/multifactor/fallback/auth/`.** Generating fresh OTPs
  is essentially free for an attacker; sending hundreds of emails is not
  free for *you*. Cap per-IP and per-user.
- **Log every dispatch.** Both successes and failures. A spike in fallback
  use across many users is a phishing-campaign signature.
- **Audit your predicates.** A predicate that returns a phone number copied
  from an attacker-controlled field is a credential-leak vector.
- **Verify the secret stays in the session.** If you're using a non-default
  session backend (e.g. signed cookies), confirm the OTP is not exposed in
  the cookie payload.

## See also

- [Fallback risks](../security/fallback-risks.md) — why fan-out matters.
- [`multifactor.factors.fallback`](../reference/common.md) — the dispatch
  implementation.
