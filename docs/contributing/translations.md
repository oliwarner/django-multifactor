# Contributing translations

All user-facing strings in `django-multifactor` are translatable. The
package ships compiled `.mo` files in the wheel — projects using
`django-multifactor` do **not** need to run `compilemessages`.

If you have translated `django-multifactor` into another language, PRs are
very welcome.

## Locating the catalogs

Translations live at:

```text
multifactor/locale/<language>/LC_MESSAGES/django.po
```

For example, the French catalog (when it exists) would be at
`multifactor/locale/fr/LC_MESSAGES/django.po`.

## Adding a new language

1. **Clone the repo** and install the development dependencies:

   ```bash
   git clone https://github.com/oliwarner/django-multifactor.git
   cd django-multifactor
   poetry install --with dev
   ```

2. **Generate the catalog** for your locale. From the `multifactor/`
   directory:

   ```bash
   cd multifactor
   django-admin makemessages -l fr
   ```

   Substitute your language code for `fr`. The list of valid codes is in
   [Django's documentation](https://docs.djangoproject.com/en/stable/topics/i18n/#term-language-code).

3. **Translate the entries** in `multifactor/locale/fr/LC_MESSAGES/django.po`.
   Each entry looks like:

   ```po
   #: views.py:42
   msgid "Your one-time-password is: %(otp)s"
   msgstr "Votre mot de passe à usage unique est : %(otp)s"
   ```

   - Leave `msgid` exactly as-is — it's the source string.
   - Set `msgstr` to your translation.
   - Preserve formatting placeholders (`%(name)s`, `{}`) exactly.
   - Leave the `#:` comment lines alone — they're source-line references
     that Django uses.

4. **Compile** the catalog so the `.mo` file is built:

   ```bash
   django-admin compilemessages
   ```

5. **Commit** both `django.po` and `django.mo`.

6. **Open a PR.** Title it `i18n: add <Language> translation`. Link any
   open issue (e.g. `#129` tracks the i18n meta-effort).

## Updating an existing translation

If source strings change between releases, you'll see fuzzy or `#~`
entries appear in `django.po` on the next `makemessages -a` run. To
update:

```bash
cd multifactor
django-admin makemessages -a   # update every catalog
# edit any new/changed entries in django.po
django-admin compilemessages
```

Commit the changes.

## Translation guidelines

- **Match Django's conventions.** If you're translating "log in", look at
  how `django/contrib/auth/locale/<your-language>/LC_MESSAGES/django.po`
  phrases it. Consistency matters.
- **Don't over-translate technical terms.** "FIDO2", "TOTP", "QR" usually
  stay as-is even in non-English locales.
- **Preserve placeholders verbatim.** `%(name)s`, `{}`, `%s` — never
  translate or reorder unless your language requires it (use named
  placeholders to reorder safely).
- **Test the output.** Spin up the [bundled testsite](../debugging/testsite.md)
  with `LANGUAGE_CODE = "fr"` and click through the flows.

## Currently bundled languages

| Locale | Status |
| --- | --- |
| `en` | Source (default) |

This list will grow as translations land. See `multifactor/locale/` for the
authoritative state.

## See also

- [i18n guide](../guides/i18n.md) — using translations from a downstream project.
- [Django i18n docs](https://docs.djangoproject.com/en/stable/topics/i18n/translation/).
