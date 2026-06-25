# Running tests

The project uses `pytest` driven by `tox` over a matrix of Python and Django
versions. CI on GitHub Actions runs the full matrix on every push and pull
request, and gates on a 90% coverage threshold.

## Running the full matrix

```bash
pip install tox
tox
```

This runs every environment listed in `tox.ini` that your system can build.
The current matrix (also reflected in `.github/workflows/main.yml`):

| Python | Django 5.2 | Django 6.0 | Django 6.1 |
| --- | --- | --- | --- |
| 3.10 | ✅ | n/a | n/a |
| 3.11 | ✅ | n/a | n/a |
| 3.12 | ✅ | ✅ | ✅ |
| 3.13 | ✅ | ✅ | ✅ |
| 3.14 | ✅ | ✅ | ✅ |
| 3.15 | ✅ | ✅ | ✅ |

Django 6.0+ requires Python 3.12+, hence the n/a cells.

## Running a single environment

```bash
tox -e py313-django52
```

…runs against Python 3.13 + Django 5.2 only. Useful while debugging — much
faster than the full matrix.

## Running pytest directly (faster iteration)

```bash
poetry run pytest tests/
```

Skips tox's environment setup. Uses whatever Python/Django your virtualenv
has. Faster, but doesn't catch matrix-specific breakage.

To run a single test file:

```bash
poetry run pytest tests/test_decorators.py
```

A single test:

```bash
poetry run pytest tests/test_decorators.py::test_multifactor_protected_anonymous_passes_through
```

## Coverage

Coverage is enforced at **90%**. To see the report locally:

```bash
poetry run coverage run -m pytest tests/
poetry run coverage report --fail-under=90
poetry run coverage html
open htmlcov/index.html
```

Or via tox:

```bash
tox
# .coverage* files left in repo root; combine and view:
coverage combine
coverage html --skip-covered --skip-empty
open htmlcov/index.html
```

If your PR drops coverage below 90, CI will fail and you'll need to add
tests.

## Tests structure

```text
tests/
├── test___init__.py
├── test_admin.py
├── test_app_settings.py
├── test_common.py
├── test_decorators.py
├── test_mixins.py
├── test_models.py
├── test_urls.py
├── test_views.py
└── factors/
    ├── test_fido2.py
    ├── test_totp.py
    └── test_fallback.py
```

The `factors/test_fido2.py` mocks `Fido2Server` — there's no way to
exercise the WebAuthn dance from pytest. For end-to-end coverage of FIDO2,
use the testsite manually.

## Adding a test

- File name must match `test_*.py`, `*_tests.py`, or `tests.py`
  (`tool.pytest.ini_options` in `pyproject.toml`).
- Function name must start with `test_`.
- `pytest-django` is not currently a dependency — tests bootstrap Django
  via `DJANGO_SETTINGS_MODULE=testsite.testsite.settings`. The
  `tox.ini` `setenv` block handles this for you in tox runs.

```python
# tests/test_my_change.py
from multifactor.common import has_multifactor


def test_has_multifactor_no_keys(rf, db):
    # use rf (RequestFactory) and db (transactional db) from your conftest
    ...
```

Each test should set up its own state and clean up after itself —
`@pytest.mark.django_db` (if available) or test cases that inherit from
`django.test.TestCase` both work.

## CI behaviour

`.github/workflows/main.yml`:

- Runs on every push to `main` and every PR targeting `main`.
- Cancels in-progress runs on new pushes (`concurrency` block).
- Each matrix cell uploads its `.coverage*` artifacts.
- A separate `coverage` job downloads all artifacts, combines them, and
  enforces the 90% threshold.
- On failure, the combined HTML coverage report is uploaded as an artifact
  for inspection.

`.github/workflows/docs.yml`:

- Builds the Sphinx docs on every PR that touches `docs/` or the workflow
  itself.
- On push to `main`, also fires a webhook to trigger a Read the Docs build.

## See also

- [Development setup](development-setup.md).
- [Release process](release-process.md).
