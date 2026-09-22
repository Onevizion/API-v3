# API-v3
Version 3 API for OneVizion

This is a wrapper for simplifying API connection to a OneVizion system.

Install with 

pip install onevizion


The Parameters.json file is not necessary, but we added in, since we use it for our scripts, and it keeps hardcoded logins and things our of a script.

All of our scripts use a Parameters.json file, which includes usernames and passwords along with URLs and other configuration.  This lets us test locally, then copy a script up unedited, to the production server or UAT server, and it will work correctly using parameters for that system.

That file looks like this:
```python
{
	"trackor.onevizion.com": {
		"url":"trackor.onevizion.com",
		"UserName": "jsmith",
		"Password": "xxxxxxxxxxxx"
	},
	"Veracode": {
		"UserName": "jsmith@onevizion.com",
		"Password": "xxxxxxxxx"
	},
	"Folders": {
		"Archiva": "/opt/tomcat/data/repositories/releases",
		"Git": "/Users/jsmith/GitHub/IKAM/ov"
	},
	"SMTP_ESRI": {
		"UserName": "jsmith@onevizion.com",
		"Password": "xxxxxxxxxxxxx",
		"Server": "smtp.office365.com",
		"Port": "587",
		"Security": "STARTTLS",
		"To": "jsmith@onevizion.com"
	},
	"SMTP": {
		"UserName": "jsmith@onevizion.com",
		"Password": "xxxxxxxxxxxx",
		"Server": "smtp.office365.com",
		"Port": "587",
		"Security": "STARTTLS",
		"To": "jsmith@onevizion.com"
	},
	"AWSCredentials": {
		"AccessKey": "AOJBFJQEBFJQEFJEEJBFEJF",
		"SecretAccessKey":"jlknf3kj4nr34rjnwj4nrwj4werwe"
	}
}
```
The idea is that you have a token, like "STMP" , or "trackor.onevizion.com", and it has all the relavent  parameter info.


We tried to add some automatic Logging and Messaging for all API connections.  It is optional, but can cut down on lines of code if you want to use it.
To implement this, we created a Config stucture so you can pass parameters to ALL instances of the classes you create.  This is not elegant, but it cut down on necessary lines of code and made readability much better.

This Config structure is used for Messaging by setting the "Verbosity" item to a number. Vebosity = 0 gives only error messaging, Verbosity = 1 gives a little more information.  The higher the number, the more information, although, at teh time of this writing, 2 is the highest used.
for example:
```python
onevizion.Config["Verbosity"] = 1
```

The Logging part is handled in onevizion.Config["Trace"].  Trace is an OrderedDict.  This can be used however you need to get a list of Messaging that hapened during the script's run.

You can find samples of scripts using this library at [api-samples](https://github.com/Onevizion/api-samples)

## Releasing

Releases are published to PyPI by `.github/workflows/publish.yml` using
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). There is
no PyPI password or API token in this repo, in CI, or on anyone's laptop. The
older `python setup.py sdist bdist_wheel` + `twine upload` procedure no longer
works: `setup.py` was removed when the project moved to uv / PEP 621, and PyPI
stopped accepting password uploads from 2FA-enabled accounts in June 2023.

To cut a release:

1. Bump `version` in `pyproject.toml` on `master` and merge it.
2. Rehearse it: **Actions → Publish → Run workflow**. A manual run always
   uploads to Test PyPI. There is no manual route to PyPI.
3. Tag that commit with the same version and push the tag:

   ```bash
   git tag 1.1.8 && git push origin 1.1.8
   ```

   Tags are bare `N.N.N` with no `v` prefix, and the tag must match
   `pyproject.toml` exactly or the build fails.

The workflow builds with `uv build`, installs both the wheel and the sdist into
clean venvs outside the source tree and imports them, and uploads only if that
passes. The same smoke test runs on every pull request as the `package` job, so
a broken artifact fails review rather than surfacing at release time.

### One-time setup

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
