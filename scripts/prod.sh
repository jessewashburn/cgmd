#!/usr/bin/env bash
# Thin helpers for the prod box so nobody memorizes container names / ssh flags.
#
#   scripts/prod.sh ps                 # docker ps
#   scripts/prod.sh logs [N]           # web logs (default 50 lines)
#   scripts/prod.sh shell              # Django shell (interactive)
#   scripts/prod.sh manage <args...>   # manage.py <args> (e.g. showmigrations music)
#   scripts/prod.sh migrate            # run migrations manually
#   scripts/prod.sh psql               # psql into the prod DB (interactive)
#   scripts/prod.sh ssh [cmd...]       # raw ssh to the host
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=deploy/config.sh
source "$ROOT/deploy/config.sh"
require ssh

cmd="${1:-help}"; shift || true
case "$cmd" in
  ps)      ssh_prod "docker ps" ;;
  logs)    ssh_prod "docker logs cgmd-web-1 --tail ${1:-50}" ;;
  shell)   ssh_prod_tty "docker exec -it cgmd-web-1 python manage.py shell" ;;
  manage)  ssh_prod_tty "docker exec -it cgmd-web-1 python manage.py $*" ;;
  migrate) ssh_prod "docker exec cgmd-web-1 python manage.py migrate" ;;
  psql)    ssh_prod_tty "docker exec -it cgmd-db-1 psql -U cgmd -d cgmd" ;;
  ssh)     ssh_prod "$@" ;;
  *) echo "usage: prod.sh {ps|logs [N]|shell|manage <args>|migrate|psql|ssh [cmd]}" ;;
esac
