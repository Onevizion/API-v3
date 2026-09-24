# Releasing `onevizion`

Releases are published to PyPI by `.github/workflows/publish.yml` using
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). There is
no PyPI password or API token in this repo, in CI, or on anyone's laptop. The
older `python setup.py sdist bdist_wheel` + `twine upload` procedure no longer
works: `setup.py` was removed when the project moved to uv / PEP 621, and PyPI
stopped accepting password uploads from 2FA-enabled accounts in June 2023.

To cut a release:

1. Bump the version with uv, which updates `pyproject.toml` **and** `uv.lock`,
   then merge both through a PR:

   ```bash
   uv version 1.2.0 --no-sync
   ```

   Editing `pyproject.toml` by hand leaves `uv.lock` stale, and CI's
   `uv sync --locked` fails the PR.
2. Rehearse it: **Actions → Publish → Run workflow**. A manual run always
   uploads to Test PyPI. There is no manual route to PyPI.
3. Tag the merge commit on `master` with the same version and push the tag:

   ```bash
   git tag 1.2.0 && git push origin 1.2.0
   ```

   Tags are bare `N.N.N` with no `v` prefix. The build fails unless the tag
   matches `pyproject.toml` exactly and the tagged commit is on `master`.

The workflow builds with `uv build`, then runs `scripts/smoke-test-dist.sh`:
the wheel and the sdist are installed into clean venvs outside the source tree,
imported, and must report the `pyproject.toml` version; the wheel is also
installed into a bare `python:2.7` container with no dev extras. It uploads only
if that passes. The same script runs on every pull request as the `package`
job, so a broken artifact fails review rather than surfacing at release time.

## One-time setup

Neither of these is code, and a release cannot succeed until the first is done:

- **Register the Trusted Publisher** on PyPI under
  `/manage/project/onevizion/settings/publishing/` — owner `Onevizion`,
  repository `API-v3`, workflow `publish.yml`, environment `release`. Repeat on
  Test PyPI with environment `testpypi`; it is a separate account with a
  separate login.
- **Create the `release` environment** in this repo's settings with a required
  reviewer, and limit its deployment branches to tags. Skipping this lets
  GitHub create the environment unprotected on first use, which leaves a
  release available to every account with push access. Requires repo admin.
