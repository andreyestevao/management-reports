"""Configuração agnóstica do GitHub Project (ambiente ou CLI)."""

from __future__ import annotations

import os


def ler_proprietario(explicito: str | None = None) -> str:
    """Retorna owner/org do project; exige --proprietario ou GH_PROJECT_OWNER."""
    valor = (explicito or os.environ.get("GH_PROJECT_OWNER", "")).strip()
    if not valor:
        raise SystemExit(
            "Defina o owner do GitHub Project: --proprietario ou variável GH_PROJECT_OWNER"
        )
    return valor


def ler_numero_projeto(explicito: int | None = None) -> int:
    """Número do project (GH_PROJECT_NUMBER, padrão 1)."""
    if explicito is not None:
        return explicito
    return int(os.environ.get("GH_PROJECT_NUMBER", "1"))
