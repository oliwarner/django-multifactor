# Development setup

Setting up a local environment for hacking on `django-multifactor` itself.
If you just want to *use* the package, see [Installation](../getting-started/installation.md)
instead.

## Prerequisites

- Python 3.10 – 3.15. Use [pyenv](https://github.com/pyenv/pyenv) if you
  need to juggle multiple versions.
- [Poetry](https://python-poetry.org/) (the project's package manager).
- Git.
- A FIDO2-capable browser (any current Chrome/Firefox/Safari/Edge).

## Clone and install

```bash
git clone https://github.com/oliwarner/django-multifactor.git
cd django-multifactor
poetry install --with dev
```

`poetry install --with dev` brings in `pytest` and `pytest-cov` from the
`dev` group. The runtime deps (`Django`, `pyotp`, `fido2`, `cryptography`)
come from the main `[tool.poetry.dependencies]` block.

## Install pre-commit hooks

The repository uses `black` and `isort` via [pre-commit](https://pre-commit.com/):

```bash
pip install pre-commit
pre-commit install
```

Every commit now runs the formatters before being written. To run them
manually across the whole tree:

```bash
pre-commit run --all-files
```

To update the pinned hook versions:

```bash
pre-commit autoupdate
```

## Running the testsite

The bundled `testsite/` is the easiest way to exercise the package
interactively. See [the testsite guide](../debugging/testsite.md) for the
full walkthrough.

## Running the tests

```bash
poetry run pytest tests/
```

For the full matrix (which is what CI runs):

```bash
pip install tox
tox
```

Details: [running tests](running-tests.md).

## Recommended editor settings

- **black** is the formatter — line length 120 (set in `pyproject.toml`).
- **isort** is configured to be black-compatible.
- VS Code: install the Python and Pylance extensions; set
  `python.formatting.provider` to `black`.
- PyCharm: enable "Reformat on save" with black; configure isort to run
  alongside.

## Working on the WebAuthn JavaScript

The FIDO2 templates contain JavaScript that drives `navigator.credentials.*`.
The JS itself isn't built — it's plain ES2017 embedded in templates. Edit
in place, then reload the browser. Watch the **Console** for errors.

For the package logo / branding assets, see the `design/` directory in the
repo root (Figma source files, esbuild config, etc.).

## Adding a new dependency

Use Poetry:

```bash
poetry add some-package         # runtime
poetry add --group dev some-pkg # dev-only
```

Both `pyproject.toml` and `poetry.lock` will be updated — commit both.

## Where next?

- [Running tests](running-tests.md) — the test matrix.
- [Coding standards](coding-standards.md) — the formatting expectations.
- [Translations](translations.md) — how to add a language.
- [Release process](release-process.md) — how versions get cut.
