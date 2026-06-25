# Reporting a security issue

If you believe you have found a security vulnerability in `django-multifactor`,
**please do not open a public GitHub issue.**

## Preferred channel

GitHub Security Advisories — private, deduplicated, and the maintainers are
notified directly:

<https://github.com/oliwarner/django-multifactor/security/advisories/new>

## What to include

- A short description of the vulnerability.
- The version (or commit SHA) you tested against.
- Reproduction steps — code, settings, request payload, expected vs actual.
- An assessment of impact (what an attacker could do).
- Suggested fix, if you have one.

A CVSS score is welcome but not required.

## What to expect

- Acknowledgement within a few business days.
- A privately-shared draft fix where appropriate.
- A coordinated disclosure date that gives users a reasonable window to
  upgrade after a CVE is published.

`django-multifactor` is a community-maintained project; we have no formal
SLA. Maintainers triage as time allows.

## Things that are **not** vulnerabilities

These are out of scope as security issues. They may still be valid feature
requests — open a regular GitHub issue instead.

- "TOTP secrets are in the database." Required by RFC 6238. See the
  [TOTP guide](../guides/totp.md) for at-rest encryption strategies.
- "Email fallback can be intercepted." Email is intentionally a weak
  transport; that's why the system fans out — see
  [fallback risks](fallback-risks.md).
- "No built-in rate-limiting." Documented as a deployment responsibility
  in [best practices](best-practices.md).
- "FIDO2 keys are domain-bound." Required by the WebAuthn spec.

## Defensive disclosure to other users

Once a CVE is published, the maintainers will:

- Issue a patched release.
- Publish a GHSA advisory describing impact, affected versions, fix versions,
  and mitigations.
- Note the fix in the next release's notes.

Subscribe to repository releases (GitHub → Watch → Releases) to be notified.
