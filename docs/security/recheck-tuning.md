# Tuning RECHECK and max_age

`RECHECK_MIN`, `RECHECK_MAX`, and the per-view `max_age` decorator argument
together control "how long does an MFA verification stay valid?". This page
helps you pick values for your threat model.

## The two knobs

- **`MULTIFACTOR["RECHECK_MIN"]` / `RECHECK_MAX`** — global. Every factor
  verification gets a random expiry uniformly in `[MIN, MAX]`. Default
  3h–6h.
- **`@multifactor_protected(..., max_age=N)`** — per-view. Forces a
  re-challenge if the most recent verification is older than `N` seconds.
  Default `0` (off).

The two are independent. `RECHECK` is the **floor** of MFA freshness across
your whole site; `max_age` is a **ceiling** that lets you require stricter
freshness for individual views.

## How to choose

| Application kind | `RECHECK_MIN` | `RECHECK_MAX` | `max_age` examples |
| --- | --- | --- | --- |
| **Consumer app, low-risk pages** | 8h | 24h | Generally not needed. |
| **B2B SaaS (typical)** | 3h (default) | 6h (default) | 30 min on billing, 10 min on team-admin pages. |
| **Internal admin console** | 1h | 2h | 5 min on destructive actions (delete user, change role). |
| **Banking / vault** | 15 min | 30 min | 60 s on transfer-money; 0 s (always challenge) on add-payee. |
| **Anything `factors=2` required** | normal | normal | 5 min, so the user is comfortable approving multiple verifications in a session. |

## The randomness matters

```{mermaid}
flowchart LR
    subgraph WithoutJitter["Without jitter — synchronised peak"]
        H0[09:00 login peak] --> H1[Every user verifies at ~09:00]
        H1 --> H2[12:00 — every user re-challenged at once]
    end

    subgraph WithJitter["With jitter — spread peak"]
        H3[09:00 login peak] --> H4[Every user verifies at ~09:00]
        H4 --> H5[12:00–15:00 — re-challenges spread across 3 hours]
    end

    style WithoutJitter fill:#fff3cd
    style WithJitter fill:#d4edda
```

Setting `RECHECK_MIN = RECHECK_MAX` removes the jitter. Don't do this in
production — you'll get synchronised re-prompt storms that hammer your
auth path at predictable times.

## Anti-patterns

- **`RECHECK = False` in production.** Means "once verified, verified for
  the session". Combined with long session lifetimes, an MFA verification
  can effectively last for days. Don't.
- **`RECHECK_MIN = 0`.** Means users may be re-challenged within seconds.
  Friction without a clear benefit; you almost certainly want a per-view
  `max_age` instead.
- **Identical `RECHECK_MIN` and `RECHECK_MAX`.** See above; loses the
  jitter benefit.
- **`max_age = 1`.** "Force re-challenge on every page" — annoys users
  enormously. Use it only on truly one-shot actions (large monetary
  transfers, code execution).
- **`max_age = 60` on a busy app.** A user filling out a form for >1 min
  will lose their work when bounced through MFA. Use 5+ minutes unless you
  also implement form-state preservation.

## Interaction with session lifetime

`SESSION_COOKIE_AGE` is Django's session cookie lifetime (default 2 weeks).
A verified MFA session can outlive the recheck window: the session is
still valid, but `active_factors()` filters out the expired entries and
the user is re-challenged.

Make sure your session lifetime is **at least as long** as your `RECHECK_MAX`
— otherwise users will be re-challenged because their session died, which
is fine but confusing.

## A senior-dev decision matrix

When in doubt:

1. **What's the worst thing a hijacked session can do?** That dictates
   `RECHECK_MAX` — set it shorter than how much damage you can absorb.
2. **What action is irreversible in your domain?** Add `max_age` ≤ 5 min on
   the views that perform it.
3. **What's the typical user session?** `RECHECK_MIN` should be longer
   than the median session so genuine users rarely see a mid-session
   re-prompt.
4. **Re-evaluate after rollout.** Measure: how often do real users get
   re-challenged? If it's many times per day per user, dial back.

## See also

- [Threat model](threat-model.md).
- [Session model](../concepts/session-model.md).
- [Settings reference](../reference/settings.md).
