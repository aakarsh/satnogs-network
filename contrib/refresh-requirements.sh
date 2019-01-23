#!/bin/sh -e
#
# Script to refresh requirements.txt file
#
# Copyright (C) 2019 Libre Space Foundation <https://libre.space/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

EXCLUDE_REGEXP="^\(pkg-resources\|satnogs-network\)"
VIRTUALENV_DIR=$(mktemp -d)
PIP_COMMAND="$VIRTUALENV_DIR/bin/pip"

# Create virtualenv
virtualenv "$VIRTUALENV_DIR"

# Install package with dependencies
"$PIP_COMMAND" install --no-cache-dir --force-reinstall .

# Create requirements file from installed dependencies
cat << EOF > requirements.txt
# This is a generated file; DO NOT EDIT!
#
# Please edit 'setup.cfg' to add top-level dependencies and use
# './contrib/refresh-requirements.sh to regenerate this file

EOF
"$PIP_COMMAND" freeze | grep -v "$EXCLUDE_REGEXP" >> requirements.txt

# Install development package with dependencies
"$PIP_COMMAND" install --no-cache-dir .[dev]

# Create development requirements file from installed dependencies
cat << EOF > requirements-dev.txt
# This is a generated file; DO NOT EDIT!
#
# Please edit 'setup.cfg' to add top-level extra dependencies and use
# './contrib/refresh-requirements.sh to regenerate this file
-r requirements.txt

EOF

_tmp_requirements_dev=$(mktemp)
"$PIP_COMMAND" freeze | grep -v "$EXCLUDE_REGEXP" | sort > "$_tmp_requirements_dev"
sort < requirements.txt | comm -13 - "$_tmp_requirements_dev" >> requirements-dev.txt
rm -f "$_tmp_requirements_dev"

# Verify dependency compatibility
"$PIP_COMMAND" check

# Cleanup
rm -rf "$VIRTUALENV_DIR"
