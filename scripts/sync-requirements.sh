#!/bin/bash
# Validate requirements-dev.txt consistency with pyproject.toml
#
# NOTE: requirements-dev.txt CANNOT be auto-generated because it contains
# conditional dependencies for Python 2.7-3.13 support. This script only
# validates that package names are consistent.

set -e

echo "Checking package name consistency..."

# Extract package names from pyproject.toml
pyproject_packages=$(grep -A 20 '\[project.optional-dependencies\]' pyproject.toml | \
  grep -E '^\s+"[a-z0-9-]+(>=|<|==)' | \
  sed -E 's/^\s+"([a-z0-9-]+).*/\1/' | \
  sort -u)

# Extract package names from requirements-dev.txt
reqdev_packages=$(grep -v '^#' requirements-dev.txt | \
  grep -v '^$' | \
  sed -E 's/^([a-z0-9-]+).*/\1/' | \
  grep -v '^requests$' | \
  sort -u)

echo "Packages in pyproject.toml:"
echo "$pyproject_packages"
echo ""
echo "Packages in requirements-dev.txt:"
echo "$reqdev_packages"
echo ""

# Check if all pyproject packages are in requirements-dev
missing=""
for pkg in $pyproject_packages; do
  if ! echo "$reqdev_packages" | grep -q "^${pkg}$"; then
    missing="${missing}${pkg} "
  fi
done

if [ -n "$missing" ]; then
  echo "ERROR: Missing packages in requirements-dev.txt: $missing"
  echo ""
  echo "You must manually add these with appropriate Python version constraints."
  exit 1
fi

echo "All package names are consistent"
