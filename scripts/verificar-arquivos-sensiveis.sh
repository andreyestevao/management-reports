#!/usr/bin/env bash
# Bloqueia commit de arquivos sensíveis ou dados locais do board.
# Uso: ./scripts/verificar-arquivos-sensiveis.sh [--staged]

set -euo pipefail

MODO="${1:-all}"
if [[ "$MODO" == "--staged" ]]; then
  ARQUIVOS=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
else
  ARQUIVOS=$(git ls-files 2>/dev/null || true)
fi

if [[ -z "$ARQUIVOS" ]]; then
  exit 0
fi

BLOQUEADOS=(
  '.env'
  '.env.local'
  'dados/burndown-historico.json'
  'kanban-cei-apps.html'
  'kanban-cei-apps-incorporar.html'
)

FALHOU=0

while IFS= read -r arq; do
  [[ -z "$arq" ]] && continue
  base=$(basename "$arq")
  case "$arq" in
    .env|.env.*)
      [[ "$base" == ".env.example" ]] && continue
      echo "BLOQUEADO: $arq (variáveis de ambiente)"
      FALHOU=1
      ;;
    dados/*.json)
      [[ "$arq" == *.example.json ]] && continue
      echo "BLOQUEADO: $arq (snapshot local — use *.example.json)"
      FALHOU=1
      ;;
    *.pem|*.key|*.p12|*.pfx|id_rsa|id_rsa.pub|credentials.json|secrets.json)
      echo "BLOQUEADO: $arq (credencial)"
      FALHOU=1
      ;;
  esac
  for padrao in "${BLOQUEADOS[@]}"; do
    if [[ "$arq" == "$padrao" ]]; then
      echo "BLOQUEADO: $arq"
      FALHOU=1
    fi
  done
done <<< "$ARQUIVOS"

# Padrões de token em conteúdo staged
if [[ "$MODO" == "--staged" ]]; then
  if git diff --cached | grep -qE 'ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'; then
    echo "BLOQUEADO: possível token GitHub no diff"
    FALHOU=1
  fi
fi

if [[ "$FALHOU" -ne 0 ]]; then
  echo ""
  echo "Commit abortado. Remova os arquivos acima do stage ou ajuste .gitignore."
  exit 1
fi

echo "Verificação OK — nenhum arquivo sensível detectado."
