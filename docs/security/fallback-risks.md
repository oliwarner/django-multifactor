# Fallback risks

The fallback OTP is the "user lost their phone" escape hatch. By design it
is **weaker** than your primary factors — it relies on out-of-band transports
(email, SMS, …) that are themselves attackable. This page explains the
trade-offs and the mitigations baked into `django-multifactor`.

## Why fallback exists at all

If you allow MFA enrolment, you must allow recovery. Otherwise a single
lost device leads to:

- Locked-out users.
- Support tickets that require manual admin intervention to clear.
- Pressure to give admins shortcuts ("disable MFA for this user") that
  themselves become attack surface.

Better to ship a deliberate, well-understood fallback than to wait for
your support team to invent one ad hoc.

## The risks, by transport

### Email fallback (default)

- **Email account compromise** — if the attacker controls the user's
  mailbox, they receive the OTP.
- **Unverified email** — if your User model lets users change email
  without verification, an attacker with the password can rewrite the
  recipient.
- **Email-in-transit interception** — modern mail is mostly TLS, but
  forwarders and corporate gateways may not be. Treat email as
  *plaintext* for threat-modelling purposes.

### SMS fallback (common addition)

- **SIM swap** — attackers persuade the user's mobile carrier to issue a
  new SIM bound to the user's number. Receiver of the OTP becomes the
  attacker.
- **SS7 / signalling attacks** — feasible for sophisticated adversaries.
- **Stolen phone (locked)** — modern phones display SMS previews on the
  lock screen by default.
- **Cost / deliverability** — a sufficiently aggressive attacker can run
  up your SMS bill or knock out delivery by triggering many fallback
  flows.

### "Custom" fallbacks (push, Signal, Slack, …)

- **As secure as the underlying channel.** A Slack DM relies on Slack
  authentication; a push notification relies on the device's lock screen.
- **Dependency** — if your push provider is down, users cannot recover.

## The fan-out mitigation

`django-multifactor` defends against the worst case of fallback compromise
with a deliberately-unusual design: when fallback is triggered, the OTP is
sent to **every** enabled transport simultaneously. The user does **not**
pick a transport.

```{mermaid}
flowchart LR
    F((Fallback<br/>requested)) --> E[Email]
    F --> S[SMS]
    F --> P[Push]
    F --> X[Other]
    style F fill:#fff3cd
```

Why this matters: if an attacker has hijacked the user's email and silently
requests an OTP, the legitimate user's **phone still pings** at the same
moment. They notice. They act. The attack is no longer silent.

Compare to a "pick your fallback" UX, where the attacker would request the
email-only path and the user would have no signal that anything is wrong.

Source: `multifactor/factors/fallback.py:38-67`.

## What this means for you

- **Configure at least two transports** if you can. The fan-out only works
  when there is somewhere else for the alert to land.
- **Don't let users opt out of every transport.** Cap the opt-outs in your
  UI; require at least one channel remain active.
- **Surface a "we sent your code via …" message** to the user (the default
  template does). It tells them what to expect — a missing channel is itself
  a clue.

## Mitigations to layer on top

| Mitigation | Cost / benefit |
| --- | --- |
| **Rate-limit `multifactor:fallback_auth`** | Cheap. Prevents OTP-flood denial-of-service against your SMS bill and the user's inbox. |
| **Send a "fallback was used" notification** through a separate channel | Moderate effort. Hook `factors.fallback.Auth.post` post-success to push a notification via your usual user-notification pipeline. |
| **Require fallback OTP + a primary factor for high-risk views** | `@multifactor_protected(factors=2)` — fallback counts as one factor; the user needs another verified factor to reach 2. Forces a fallback user to have at least one primary factor remaining. |
| **Email verification on profile changes** | Stops the "attacker rewrites email and recovers" path. |
| **Restrict fallback to specific user groups** | Custom fallback predicate: `lambda user: user.profile.fallback_allowed`. Lets you turn it off for the most sensitive accounts. |

## Concrete example — escalate-and-notify

```python
# myapp/mfa.py
def send_email(user, message):
    # Original email transport
    ...


def notify_signal(user, message):
    # NOT a fallback transport — a side-channel alert.
    requests.post(
        "https://signal-cli.internal/send",
        json={
            "to": user.profile.signal_number,
            "body": "A fallback OTP was just requested on your account.",
        },
    )


def send_email_and_alert(user, message):
    result = send_email(user, message)
    notify_signal(user, "fallback OTP requested")
    return result
```

The user gets the OTP via email; they *also* get a heads-up via Signal that
the OTP was issued. If they didn't request it, they call security.

## See also

- [Threat model](threat-model.md).
- [Custom fallback guide](../guides/custom-fallback.md).
