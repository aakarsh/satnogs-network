#!/bin/sh -e
#
# SatNOGS Django control script
#
# Copyright (C) 2018-2019 Libre Space Foundation <https://libre.space/>
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

MANAGE_CMD="django-admin"
WSGI_SERVER="gunicorn"
DJANGO_APP="network"
CELERY_VAR_RUN="/var/run/celery"

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]... [COMMAND]...
SatNOGS Django control script.

COMMANDS:
  prepare               Collect static files, compress templates and
                         apply migrations
  initialize            Load initial fixtures
  run                   Run WSGI HTTP server
  run_celery [worker|beat]
                        Run Celery worker or beat
  develop [SOURCE_DIR]  Run application in development mode, optionally
                         installing SOURCE_DIR in editable mode
  develop_celery [SOURCE_DIR]
                        Run Celery, optionally installing SOURCE_DIR
                         in editable mode

OPTIONS:
  --help                Print usage
EOF
	exit 1
}

prepare() {
	"$MANAGE_CMD" collectstatic --noinput --clear
	"$MANAGE_CMD" compress --force
	"$MANAGE_CMD" migrate --noinput
}

install_editable() {
	pip install \
	    --no-cache-dir \
	    --no-deps \
	    -r "${1}/requirements-dev.txt"
	pip install \
	    --no-cache-dir \
	    --no-deps \
	    --force-reinstall \
	    -e "${1}"
}

run() {
	prepare
	exec "$WSGI_SERVER" "$DJANGO_APP".wsgi
}

run_celery() {
	case "$1" in
		worker|beat)
			exec celery -A "$DJANGO_APP" "$1" -l INFO --workdir "$CELERY_VAR_RUN"
			;;
		*)
			usage
			exit 1
			;;
	esac
}

develop() {
	if [ -d "$1" ]; then
		install_editable "$1"
	fi
	prepare
	exec "$MANAGE_CMD" runserver 0.0.0.0:8000
}

develop_celery() {
	if [ -d "$1" ]; then
		install_editable "$1"
	fi
	exec celery -A "$DJANGO_APP" worker -B -l INFO
}

initialize() {
	"$MANAGE_CMD" initialize
}

parse_args() {
	while [ $# -gt 0 ]; do
		arg="$1"
		case $arg in
			prepare|run|initialize)
				command="$arg"
				break
				;;
			develop|develop_celery|run_celery)
				shift
				subargs="$1"
				command="$arg"
				break
				;;
			*)
				usage
				exit 1
				;;
		esac
		shift
	done
}

main() {
	parse_args "$@"
	if [ -z "$command" ]; then
		usage
		exit 1
	fi
	if [ -x "manage.py" ]; then
		MANAGE_CMD="./manage.py"
	fi
	"$command" "$subargs"
}

main "$@"
