# Release process

Versions are cut by tagging the repository. The `autopublish.yml` GitHub
Actions workflow handles the actual PyPI upload.

## Versioning

The package uses [poetry-dynamic-versioning](https://github.com/mtkennerly/poetry-dynamic-versioning)
configured in `pyproject.toml`:

```toml
[tool.poetry-dynamic-versioning]
enable = true
vcs = "git"
style = "pep440"
```

That means the version in `pyproject.toml` (`0.0.0`) is a placeholder — the
real version is derived from the most recent git tag.

## Cutting a release

1. **Land all PRs** intended for the release on `main`. The CI matrix on
   `main` must be green.

2. **Update the README badge / table** if the supported Python or Django
   matrix has changed. (Skipped if a patch release.)

3. **Tag**:

   ```bash
   git checkout main
   git pull
   git tag v0.9.1
   git push origin v0.9.1
   ```

   Tag names must match `v*.*.*` for the autopublish workflow to fire.

4. **Watch the autopublish workflow** at
   <https://github.com/oliwarner/django-multifactor/actions/workflows/autopublish.yml>.
   It runs `poetry build` (with the dynamic-versioning plugin enabled so
   the version is read from the tag) and pushes to PyPI using the
   `PYPI_TOKEN` repository secret.

5. **Create a GitHub Release** at
   <https://github.com/oliwarner/django-multifactor/releases/new>.
   Tick "Set as the latest release". Use the tag you just pushed. The body
   should call out:
   - New features (with example code if non-obvious).
   - Breaking changes (with migration notes).
   - Bug fixes (with issue references).
   - Dependency floor bumps (Django minimum, Python minimum).

## Versioning policy

`django-multifactor` follows [SemVer](https://semver.org/) loosely:

- **Patch** (`0.9.1` → `0.9.2`) — bug fixes, dependency bumps that don't
  change behaviour, documentation, internal refactors.
- **Minor** (`0.9.x` → `0.10.0`) — backwards-compatible new features, new
  optional settings, new factor types, schema additions that are
  forward-compatible.
- **Major** (`0.x` → `1.0`) — backwards-incompatible changes: removed
  settings, removed factor types, schema changes requiring data
  migration.

The U2F removal in 0.6 and the Python 3.10 floor in 0.9 are examples of
where the project has bumped the minor and bundled a breaking change. As
the package approaches 1.0, expect stricter SemVer discipline.

## After release

1. **Mark the GHSA advisory** (if the release fixed a security issue) as
   public.
2. **Watch the autopublish workflow run to completion** — failures here
   require a manual `poetry publish` from a maintainer's machine. Don't
   delete the tag; instead push a `v0.9.1.post1` tag.
3. **Announce.** The README points to GitHub releases — there is no
   mailing list at present.

## Pre-release tags

For testing release candidates without publishing to PyPI proper:

```bash
git tag v0.10.0a1
git push origin v0.10.0a1
```

The autopublish workflow currently fires on any `v*.*.*` tag. If you don't
want a pre-release to hit PyPI, push the tag without the `v` prefix (the
workflow trigger won't match) and use `poetry build` locally to inspect.

## See also

- [Running tests](running-tests.md) — what must pass before tagging.
- The autopublish workflow source: `.github/workflows/autopublish.yml`.
