#!/usr/bin/env bash
# Inicia servidor management-reports (kanban + burndown + burnup + gantt dinâmicos)

set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$DIR/.env"
  set +a
fi
exec python3 "$DIR/servidor-kanban-cei.py" "$@"
