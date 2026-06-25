# Coding standards

The project uses [`black`](https://black.readthedocs.io/) and
[`isort`](https://pycqa.github.io/isort/), enforced by
[`pre-commit`](https://pre-commit.com/). Both are configured in the repo —
you should not need to override anything.

## Formatter settings

From `pyproject.toml`:

```toml
[tool.black]
line-length = 120
```

`isort` is configured via `.pre-commit-config.yaml` with the `black` profile,
so the two never fight.

## Pre-commit hooks

After cloning, install the hooks once:

```bash
pip install pre-commit
pre-commit install
```

From then on every commit runs `black` and `isort` on the staged files. If
either rewrites a file, the commit is aborted — `git add` the formatted
file and re-commit.

To run the hooks across the entire repo (useful before a PR):

```bash
pre-commit run --all-files
```

To refresh the pinned hook versions:

```bash
pre-commit autoupdate
```

## Style beyond formatting

The codebase is small and pragmatic. A few conventions that aren't enforced
by the formatters:

- **Translatable strings.** All user-facing strings — view responses,
  template text, model labels, flash messages, model field help text —
  use `gettext` / `gettext_lazy`. Import them as `_`:

  ```python
  from django.utils.translation import gettext as _
  from django.utils.translation import gettext_lazy as _

  messages.error(request, _("That key was not correct. Please try again."))
  ```

  `gettext_lazy` for module-level constants (settings defaults, model field
  attributes); plain `gettext` for runtime strings inside views.

- **No top-level imports of Django apps.** Anything that touches the DB or
  settings should be imported inside the function/method, not at module
  level, to avoid `AppRegistryNotReady` during app initialisation.

- **Logging.** Each module owns a module-level
  `logger = logging.getLogger(__name__)`. Don't `print()` in production code.

- **Docstrings.** Short, written for someone using the function — not
  describing implementation detail. The `@multifactor_protected` docstring
  in `decorators.py` is a good model.

- **JSON responses from FIDO2 views.** Always `JsonResponse(...)`; never
  hand-build the JSON.

- **Don't catch broad `Exception` without re-raising or logging.** There
  are existing wide `except:` blocks; they all log. New code should follow
  the same pattern.

## Naming

- Models, mixins, classes: `PascalCase`.
- Functions and module names: `snake_case`.
- Settings keys: `SCREAMING_SNAKE_CASE`.
- URL names: `lower_snake_case`.
- Template paths: `lower_snake_case.html`, except FIDO2/TOTP which are
  capitalised for legacy reasons (`templates/multifactor/FIDO2/...`).

## Tests

See [running tests](running-tests.md) for how to add and run them.

- Test file names: `test_*.py` (matching `pyproject.toml`'s pytest config).
- Coverage threshold: **90%** (enforced in CI).
- Tests live in `tests/` mirroring the package layout —
  `tests/factors/test_totp.py` covers `multifactor/factors/totp.py`.

## Where next?

- [Running tests](running-tests.md).
- [Translations](translations.md).
- [Release process](release-process.md).
