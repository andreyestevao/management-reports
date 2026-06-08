#!/usr/bin/env bash
# Gera HTML estático do kanban (GitHub Projects)
# Uso: ./gerar-kanban-cei.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/gerar-kanban-cei.py" --saida "$DIR" "$@"
