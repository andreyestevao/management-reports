#!/usr/bin/env python3
"""
Gera HTML estático do kanban a partir do GitHub Projects.

Requer: gh autenticado com escopo read:project (ou project).
Saída padrão: kanban-cei-apps.html e kanban-cei-apps-incorporar.html
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

from config_projeto import ler_numero_projeto, ler_proprietario
from kanban_cei_dados import (
    COR_COLUNA,
    agrupar_por_coluna,
    carregar_itens,
    carregar_projeto,
)
import subprocess


def renderizar_cartao(item: dict) -> str:
    """HTML de um cartão do kanban."""
    titulo = html.escape(item["titulo"])
    url = html.escape(item["url"]) if item["url"] else ""
    numero = item["numero"]
    rotulo_numero = f"#{numero}" if numero else "—"

    meta_partes: list[str] = []
    if item["responsaveis"]:
        nomes = ", ".join(html.escape(r) for r in item["responsaveis"])
        meta_partes.append(f'<span class="meta-responsavel">{nomes}</span>')
    if item.get("dataLimiteFormatada"):
        meta_partes.append(
            f'<span class="meta-prazo">📅 {html.escape(item["dataLimiteFormatada"])}</span>'
        )
    if item["iteracao"]:
        meta_partes.append(
            f'<span class="meta-iteracao">{html.escape(item["iteracao"])}</span>'
        )
    if item.get("repositorioCurto"):
        meta_partes.append(f'<span class="meta-repo">{html.escape(item["repositorioCurto"])}</span>')

    titulo_html = (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">{titulo}</a>'
        if url
        else titulo
    )

    meta_html = "".join(f'<div class="cartao-meta-linha">{p}</div>' for p in meta_partes)

    return f"""
    <article class="cartao">
      <header class="cartao-cabecalho">
        <span class="cartao-numero">{html.escape(rotulo_numero)}</span>
      </header>
      <h3 class="cartao-titulo">{titulo_html}</h3>
      {f'<div class="cartao-meta">{meta_html}</div>' if meta_partes else ''}
    </article>
    """


def renderizar_coluna(nome: str, itens: list[dict]) -> str:
    """HTML de uma coluna do kanban."""
    cor = COR_COLUNA.get(nome, "#6c757d")
    cartoes = "".join(renderizar_cartao(i) for i in itens) or '<p class="coluna-vazia">Nenhum item</p>'
    return f"""
    <section class="coluna" style="--cor-coluna: {cor}">
      <header class="coluna-cabecalho">
        <h2>{html.escape(nome)}</h2>
        <span class="coluna-contagem">{len(itens)}</span>
      </header>
      <div class="coluna-cartoes">{cartoes}</div>
    </section>
    """


def folhas_css_kanban() -> str:
    """Links para folhas de estilo externas (personalizáveis via cei-tema.js)."""
    return """
  <link rel="stylesheet" href="cei-tokens.css">
  <link rel="stylesheet" href="cei-compartilhado.css">
  <link rel="stylesheet" href="kanban-cei.css">
  <script src="cei-tema.js"></script>"""


def estilos_css() -> str:
    """CSS inline legado — concatena tokens + compartilhado + kanban (export estático autocontido)."""
    base = Path(__file__).resolve().parent
    partes = ["cei-tokens.css", "cei-compartilhado.css", "kanban-cei.css"]
    return "\n".join((base / nome).read_text(encoding="utf-8") for nome in partes)


def montar_html(
    projeto: dict,
    colunas: dict[str, list[dict]],
    gerado_em: datetime,
    modo_incorporar: bool = False,
) -> str:
    """Monta documento HTML completo."""
    titulo_projeto = html.escape(projeto.get("title", "GitHub Project"))
    url_projeto = html.escape(projeto.get("url", ""))
    total = sum(len(v) for v in colunas.values())
    data_geracao = gerado_em.strftime("%d/%m/%Y %H:%M UTC")

    colunas_html = "".join(renderizar_coluna(n, itens) for n, itens in colunas.items())

    classe_pagina = "pagina pagina--incorporar" if modo_incorporar else "pagina"
    cabecalho = ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{titulo_projeto} — Kanban</title>{folhas_css_kanban()}
</head>
<body>
  <div class="{classe_pagina}" id="pagina-principal">
    {cabecalho}
    <div class="grade-kanban">{colunas_html}</div>
    <footer class="rodape">Gerado por gerar-kanban-cei.py · dados via GitHub Projects API (gh CLI)</footer>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera kanban estático a partir do GitHub Projects")
    parser.add_argument("--proprietario", default=None, help="Owner do project (ou GH_PROJECT_OWNER)")
    parser.add_argument("--projeto", type=int, default=1, help="Número do project (padrão: 1)")
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Diretório de saída dos HTML",
    )
    args = parser.parse_args()

    proprietario = ler_proprietario(args.proprietario)
    numero = ler_numero_projeto(args.projeto)

    try:
        projeto = carregar_projeto(proprietario, numero)
        itens = carregar_itens(proprietario, numero)
    except subprocess.CalledProcessError as erro:
        print(f"Erro ao consultar GitHub: {erro.stderr or erro}", file=sys.stderr)
        print("Verifique: gh auth status (escopo read:project)", file=sys.stderr)
        return 1

    colunas = agrupar_por_coluna(itens)
    agora = datetime.now(timezone.utc)
    dir_saida = args.saida
    dir_saida.mkdir(parents=True, exist_ok=True)

    arquivo_completo = dir_saida / "kanban-cei-apps.html"
    arquivo_incorporar = dir_saida / "kanban-cei-apps-incorporar.html"

    arquivo_completo.write_text(
        montar_html(projeto, colunas, agora, modo_incorporar=False),
        encoding="utf-8",
    )
    arquivo_incorporar.write_text(
        montar_html(projeto, colunas, agora, modo_incorporar=True),
        encoding="utf-8",
    )

    print(f"✓ {arquivo_completo}")
    print(f"✓ {arquivo_incorporar}")
    print(f"  {sum(len(v) for v in colunas.values())} itens em {len(colunas)} colunas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
