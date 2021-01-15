#!/bin/sh -e
#
# Development and maintenance script
#
# Copyright (C) 2021 Libre Space Foundation <https://libre.space/>
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

COMPOSE_CMD="docker-compose"
COMPOSE_FILE="docker-compose.yml"
SERVICE_WEB="web"
SHELL_CMD="/bin/bash"
REFRESH_CMD="./contrib/refresh-requirements.sh"
TOX_CMD="tox"
MANAGE_CMD="django-admin"
NPM_CMD="npm"

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]... [COMMAND]...
SatNOGS Development and Maintenance script.

DOCKER COMMANDS:
  DOCKER_COMPOSE_COMMANDS [ARGS]
                        Run any Docker Compose command.
                         See 'docker-compose --help' for details.
                         'up' command will also attempt to initialize
                         the installation and will always run in the
                         background.
  shell SERVICE         Open a shell to a running service.
  clean                 Bring down all services and remove volumes.
  django-admin          Execute 'django-admin'. See 'django-admin help'
                         for available subcommands.

VIRTUALENV COMMANDS:
  develop               Run application in development mode and
                         initialize, if needed.
  develop_celery        Run Celery in development mode and initialize,
                         if needed.
  remove                Remove virtualenv.

DEVELOPMENT AND MAINTENANCE COMMANDS:
  tox [ARGS]            Run 'tox' test automation tool.
  refresh               Refresh requirements files.
  update                Update frontend dependencies.

OPTIONS:
  --help                Print usage
EOF
	exit 1
}

yesno() {
	while true; do
		echo "$1"
		read -r yesno
		case $yesno in
			Y|y|YES|Yes|yes)
				return 0
				;;
			N|n|NO|No|no)
				return 1
				;;
			*)
				echo "Please answer yes or no."
				;;
		esac
	done
}

frontend_deps() {
	if [ "$1" = "install" ] || [ "$1" = "update" ]; then
		"$NPM_CMD" "$1"
	fi
	./node_modules/.bin/gulp
}

wait_prepare() {
	echo "Collecting static assets, compressing and migrating..."
	while ! "$COMPOSE_CMD" exec "$SERVICE_WEB" ps -p 1 -o args= | grep -q "runserver"; do
		sleep 5
	done
}

docker_initialize() {
	if ! "$COMPOSE_CMD" exec "$SERVICE_WEB" "$MANAGE_CMD" dumpdata --no-color --format yaml users.user | grep -q "is_superuser: true"; then
		"$COMPOSE_CMD" exec "$SERVICE_WEB" djangoctl.sh initialize
	fi
}

virtualenv_initialize() {
	. .virtualenv/bin/activate
	if ! "$MANAGE_CMD" dumpdata --no-color --format yaml users.user | grep -q "is_superuser: true"; then
		./bin/djangoctl.sh initialize
	fi
	deactivate
}

virtualenv_install() {
	virtualenv .virtualenv
	.virtualenv/bin/pip install \
			    --no-cache-dir \
			    --no-deps \
			    --force-reinstall \
			    -e "."
	.virtualenv/bin/pip install \
			    --no-cache-dir \
			    --no-deps \
			    -r "./requirements-dev.txt"
}

parse_args() {
	arg="$1"
	case $arg in
		build|config|create|down|events|exec|images|kill|logs|pause|port|ps|pull|push|restart|rm|run|scale|start|stop|top|unpause|up)
			if [ "$arg" = "up" ]; then
				frontend_deps install
				shift
				"$COMPOSE_CMD" "$arg" -d "$@"
				wait_prepare
				docker_initialize
			else
				"$COMPOSE_CMD" "$@"
			fi
			echo "Services start-up completed."
			return
			;;
		shell)
			shift
			if [ -z "$1" ]; then
				echo "ERROR: No service name specified!" >&2
				usage
				exit 1
			fi
			if ! "$COMPOSE_CMD" exec "$1" "$SHELL_CMD"; then
				echo "Please make sure that the services are up!" >&2
				exit 1
			fi
			return
			;;
		clean)
			yesno "This action will delete all installation data! Are you sure? [Yes/No]"
			"$COMPOSE_CMD" down -v
			return
			;;
		django-admin)
			if ! "$COMPOSE_CMD" exec "$SERVICE_WEB" "$MANAGE_CMD" django-admin; then
				echo "Please make sure that the services are up!" >&2
				exit 1
			fi
			return
			;;
		tox)
			"$TOX_CMD" "$@"
			return
			;;
		refresh)
			"$REFRESH_CMD"
			return
			;;
		update)
			frontend_deps update
			return
			;;
		develop|develop_celery)
			if [ ! -d .virtualenv ]; then
				frontend_deps install
				virtualenv_install
				virtualenv_initialize
			fi
			. .virtualenv/bin/activate
			./bin/djangoctl.sh "$arg" .
			return
			;;
		remove)
			yesno "This action will delete all installation data! Are you sure? [Yes/No]"
			rm -rf ".virtualenv" "db.sqlite3" "media" "staticfiles"
			return
			;;
		*)
			usage
			exit 1
			;;
	esac
}

main() {
	if [ ! -f "$COMPOSE_FILE" ]; then
		echo "ERROR: No Docker Compose file found! Please run from top directory." >&2
		exit 1
	fi
	parse_args "$@"
}

main "$@"
