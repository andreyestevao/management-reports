"""Consulta e normaliza dados do GitHub Project CEI Apps - UFG."""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone

COLUNAS_STATUS = [
    "Backlog do Projeto",
    "Para Fazer",
    "Em progresso",
    "Em Impedimento",
    "Feito",
    "Fechado",
]

COR_COLUNA = {
    "Backlog do Projeto": "#6c757d",
    "Para Fazer": "#0d6efd",
    "Em progresso": "#fd7e14",
    "Em Impedimento": "#dc3545",
    "Feito": "#198754",
    "Fechado": "#495057",
}


def executar_gh(*args: str) -> str:
    """Executa comando gh e retorna stdout."""
    resultado = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return resultado.stdout


def carregar_projeto(proprietario: str, numero: int) -> dict:
    """Obtém metadados do project via gh."""
    saida = executar_gh(
        "project", "view", str(numero),
        "--owner", proprietario,
        "--format", "json",
    )
    return json.loads(saida)


def carregar_itens(proprietario: str, numero: int) -> list[dict]:
    """Lista todos os itens do board."""
    saida = executar_gh(
        "project", "item-list", str(numero),
        "--owner", proprietario,
        "--limit", "500",
        "--format", "json",
    )
    return json.loads(saida).get("items", [])


def formatar_data(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        data = datetime.strptime(valor[:10], "%Y-%m-%d")
        return data.strftime("%d/%m/%Y")
    except ValueError:
        return valor


def _normalizar_responsaveis(assignees) -> list[str]:
    """Extrai logins/nomes legíveis da lista de assignees do gh."""
    nomes: list[str] = []
    for assignee in assignees or []:
        if isinstance(assignee, str):
            texto = assignee.strip()
        elif isinstance(assignee, dict):
            texto = (
                assignee.get("login")
                or assignee.get("name")
                or assignee.get("nameWithOwner")
                or ""
            ).strip()
        else:
            texto = str(assignee).strip()
        if texto:
            nomes.append(texto)
    return nomes


def normalizar_item(bruto: dict) -> dict:
    """Normaliza campos do item para JSON/HTML."""
    conteudo = bruto.get("content") or {}
    assignees = bruto.get("assignees") or []
    iteracao = bruto.get("iteration") or {}
    repositorio = conteudo.get("repository") or ""
    return {
        "numero": conteudo.get("number"),
        "titulo": bruto.get("title") or conteudo.get("title") or "(sem título)",
        "status": bruto.get("status") or "Sem status",
        "url": conteudo.get("url") or "",
        "repositorio": repositorio,
        "repositorioCurto": repositorio.split("/")[-1] if repositorio else "",
        "responsaveis": _normalizar_responsaveis(assignees),
        "dataLimite": bruto.get("due Date") or bruto.get("dueDate"),
        "dataLimiteFormatada": formatar_data(bruto.get("due Date") or bruto.get("dueDate")),
        "iteracao": iteracao.get("title") if isinstance(iteracao, dict) else None,
        "prioridade": bruto.get("priority"),
    }


def agrupar_por_coluna(itens_brutos: list[dict]) -> dict[str, list[dict]]:
    """Agrupa itens normalizados por status na ordem do board."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for bruto in itens_brutos:
        item = normalizar_item(bruto)
        grupos[item["status"]].append(item)

    for status in grupos:
        grupos[status].sort(
            key=lambda i: (i["dataLimite"] or "9999", i["numero"] or 0),
        )

    ordenado: dict[str, list[dict]] = {}
    for coluna in COLUNAS_STATUS:
        if coluna in grupos:
            ordenado[coluna] = grupos[coluna]
    for coluna, lista in grupos.items():
        if coluna not in ordenado:
            ordenado[coluna] = lista
    return ordenado


def buscar_kanban(proprietario: str = "CEI-UFG", numero: int = 1) -> dict:
    """Retorna payload JSON do kanban agrupado por coluna."""
    projeto = carregar_projeto(proprietario, numero)
    itens_brutos = carregar_itens(proprietario, numero)
    colunas = agrupar_por_coluna(itens_brutos)
    total = sum(len(v) for v in colunas.values())

    return {
        "projeto": {
            "titulo": projeto.get("title", "CEI Apps"),
            "url": projeto.get("url", ""),
            "numero": projeto.get("number", numero),
            "proprietario": proprietario,
        },
        "geradoEm": datetime.now(timezone.utc).isoformat(),
        "colunasOrdem": list(colunas.keys()),
        "coresColuna": COR_COLUNA,
        "colunas": colunas,
        "totalItens": total,
    }
