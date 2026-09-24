#!/bin/bash
# Install the built sdist + wheel the way a consumer would, and import them.
#
# Usage: scripts/smoke-test-dist.sh <dist-dir>
#
# Run from the repo root: the expected version is read from ./pyproject.toml,
# and every install must report exactly that version (Python 3.11+ on PATH).
#
# Shared by the `package` job in test.yml and the `smoke-test` job in
# publish.yml so the release gate and the PR gate cannot drift apart.
#
# Every import runs from /tmp, OUTSIDE any source tree. Run from the repo root,
# `import onevizion` resolves to ./onevizion and passes even when the build
# produced a metadata-less UNKNOWN-0.0.0 artifact.
#
# The 2.7 leg installs into a bare python:2.7 container with no dev extras.
# The test matrix's 2.7 leg cannot stand in for it: it installs
# requirements-dev.txt (which carries enum34) and imports from the source tree,
# so a missing RUNTIME dependency is invisible there.

set -eu

dist=$(cd "${1:?usage: $0 <dist-dir>}" && pwd)
expected=$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
echo "expecting onevizion $expected"

check_py3() {
	# $1 = label, $2 = artifact glob
	local venv="/tmp/smoke-$1"
	python -m venv --clear "$venv"
	# shellcheck disable=SC2086  # the glob must expand
	"$venv/bin/pip" install --quiet $2
	(cd /tmp && "$venv/bin/python" - "$1" "$expected" <<'PY'
import importlib.metadata as md
import os
import sys

import onevizion

dist = md.distribution("onevizion")
name, version = dist.metadata["Name"], dist.version
print(sys.argv[1], name, version, "from", os.path.dirname(onevizion.__file__))
assert name.lower() == "onevizion", "wrong distribution name: %r" % name
assert version != "0.0.0", "metadata-less build (UNKNOWN-0.0.0)"
assert version == sys.argv[2], "installed %s, expected %s" % (version, sys.argv[2])
assert "site-packages" in onevizion.__file__, "imported from the source tree, not the install"
PY
	)
}

check_py3 wheel "$dist/*.whl"
check_py3 sdist "$dist/*.tar.gz"

cat > /tmp/py27check.py <<'PY'
from __future__ import print_function
import os
import onevizion, pkg_resources
d = pkg_resources.get_distribution("onevizion")
print("py2.7 onevizion", d.version, "from", onevizion.__file__)
assert d.version != "0.0.0", "metadata-less install (UNKNOWN-0.0.0)"
assert d.version == os.environ["EXPECTED"], "installed %s, expected %s" % (d.version, os.environ["EXPECTED"])
assert "site-packages" in onevizion.__file__, "imported from the source tree"
PY
# The pull is the one step here that depends on Docker Hub, and this script
# gates a required check on master. Retry it rather than fail a merge on a blip.
for attempt in 1 2 3; do
	docker pull --quiet python:2.7 >/dev/null && break
	if [ "$attempt" = 3 ]; then
		echo "docker pull python:2.7 failed 3 times" >&2
		exit 1
	fi
	sleep $((attempt * 10))
done

docker run --rm \
	-e EXPECTED="$expected" \
	-v "$dist:/dist:ro" \
	-v /tmp/py27check.py:/tmp/py27check.py:ro \
	-w /tmp python:2.7 \
	sh -c 'pip install --quiet --disable-pip-version-check /dist/*-py2.py3-none-any.whl && python /tmp/py27check.py'

echo "smoke test OK: wheel + sdist on $(python -V 2>&1), wheel on 2.7"
