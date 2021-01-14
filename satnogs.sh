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

DOCKER_CMD="docker"
COMPOSE_CMD="docker-compose"
COMPOSE_FILE="docker-compose.yml"
SERVICE_WEB="web"
VOLUMES="satnogs-network_db satnogs-network_media satnogs-network_redis satnogs-network_static"
SHELL_CMD="/bin/bash"
REFRESH_CMD="./contrib/refresh-requirements.sh"
TOX_CMD="tox"
MANAGE_CMD="django-admin"
NPM_CMD="npm"

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]... [COMMAND]...
SatNOGS Development and Maintenance script.

COMMANDS:
  DOCKER_COMPOSE_COMMANDS [ARGS]
                        Run any Docker Compose command.
                         See 'docker-compose --help' for details.
                         'up' command will also attempt to initialize
                         the installation and will always run in the
                         background.
  shell SERVICE         Open a shell to a running service.
  clean                 Bring down all services and remove volumes.
  flush                 Remove all data from database only.
  tox [ARGS]            Run 'tox' test automation tool.
  refresh               Refresh requirements files.
  update                Update frontend dependencies.

OPTIONS:
  --help                Print usage
EOF
	exit 1
}

parse_args() {
	arg="$1"
	case $arg in
		build|config|create|down|events|exec|images|kill|logs|pause|port|ps|pull|push|restart|rm|run|scale|start|stop|top|unpause|up)
			if [ "$arg" = "up" ]; then
				prepare
				shift
				"$COMPOSE_CMD" "$arg" -d "$@"
				initialize
			else
				"$COMPOSE_CMD" "$@"
			fi
			return
			;;
		shell)
			shift
			if [ -z "$1" ]; then
				echo "ERROR: No service name specified!" >&2
				usage
				exit 1
			fi
			"$COMPOSE_CMD" exec "$1" "$SHELL_CMD"
			return
			;;
		clean)
			"$COMPOSE_CMD" down
			"$DOCKER_CMD" volume rm "$VOLUMES"
			return
			;;
		flush)
			"$COMPOSE_CMD" exec "$SERVICE_WEB" "$MANAGE_CMD" flush
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
			"$NPM_CMD" update
			./node_modules/.bin/gulp
			return
			;;
		*)
			usage
			exit 1
			;;
	esac
}

prepare() {
	"$NPM_CMD" install
	./node_modules/.bin/gulp
}

initialize() {
	echo "Collecting static assets, compressing and migrating..."
	while ! "$COMPOSE_CMD" exec "$SERVICE_WEB" ps -p 1 -o args= | grep -q "runserver"; do
		sleep 5
	done
	if ! "$COMPOSE_CMD" exec "$SERVICE_WEB" "$MANAGE_CMD" dumpdata --no-color --format yaml users.user | grep -q "is_superuser: true"; then
		"$COMPOSE_CMD" exec "$SERVICE_WEB" djangoctl.sh initialize
	fi
}

main() {
	if [ ! -f "$COMPOSE_FILE" ]; then
		echo "ERROR: No Docker Compose file found! Please run from top directory." >&2
		exit 1
	fi
	parse_args "$@"
}

main "$@"
