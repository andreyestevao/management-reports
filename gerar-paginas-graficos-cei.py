#!/usr/bin/env python3
"""Gera HTML e readme.md para cada gráfico analítico."""

from __future__ import annotations

from pathlib import Path

DIR_BASE = Path(__file__).resolve().parent

GRAFICOS = [
    {"id": "cfd", "nome": "CFD", "titulo": "Cumulative Flow Diagram", "descricao": "Fluxo acumulado por status ao longo da iteration.", "requer_iteracao": True},
    {"id": "cycle-time", "nome": "Cycle Time", "titulo": "Cycle Time", "descricao": "Histograma de dias até conclusão na iteration.", "requer_iteracao": True},
    {"id": "throughput", "nome": "Throughput", "titulo": "Throughput por iteration", "descricao": "Itens concluídos nas últimas iterations encerradas.", "requer_iteracao": False},
    {"id": "monte-carlo", "nome": "Monte Carlo", "titulo": "Projeção Monte Carlo", "descricao": "Simulação de prazo com throughput histórico.", "requer_iteracao": True},
    {"id": "desvio-due-date", "nome": "Desvio Due Date", "titulo": "Desvio Due Date", "descricao": "Scatter Due Date vs data de conclusão.", "requer_iteracao": True},
    {"id": "scope-creep", "nome": "Scope Creep", "titulo": "Scope Creep", "descricao": "Evolução do escopo total na iteration.", "requer_iteracao": True},
    {"id": "taxa-conclusao", "nome": "Taxa de conclusão", "titulo": "Taxa de conclusão", "descricao": "Percentual entregue por iteration.", "requer_iteracao": False},
    {"id": "carga-responsavel", "nome": "Carga por responsável", "titulo": "Carga por responsável", "descricao": "Itens abertos por pessoa na iteration.", "requer_iteracao": True},
    {"id": "wip-pessoa", "nome": "WIP por pessoa", "titulo": "WIP por pessoa", "descricao": "Work in progress por responsável.", "requer_iteracao": True},
    {"id": "mapa-repositorio", "nome": "Mapa por repositório", "titulo": "Mapa por repositório", "descricao": "Distribuição do escopo por repo.", "requer_iteracao": True},
    {"id": "release-timeline", "nome": "Release timeline", "titulo": "Release timeline", "descricao": "Janelas temporais das iterations.", "requer_iteracao": False},
    {"id": "aging-wip", "nome": "Aging WIP", "titulo": "Aging WIP", "descricao": "Idade dos itens não concluídos.", "requer_iteracao": True},
    {"id": "status-portfolio", "nome": "Status portfolio", "titulo": "Status portfolio", "descricao": "Distribuição de status de todo o board.", "requer_iteracao": False},
    {"id": "heatmap-atividade", "nome": "Heatmap atividade", "titulo": "Heatmap de atividade", "descricao": "Conclusões por dia da semana (90 dias).", "requer_iteracao": False},
    {"id": "iteration-health", "nome": "Iteration health", "titulo": "Saúde da iteration", "descricao": "Radar e métricas de saúde da iteration.", "requer_iteracao": True},
    {"id": "comparativo-iterations", "nome": "Comparativo iterations", "titulo": "Comparativo de iterations", "descricao": "Restante normalizado por dia entre iterations.", "requer_iteracao": False},
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Management Reports — {nome}</title>
  <link rel="stylesheet" href="cei-tokens.css">
  <link rel="stylesheet" href="cei-compartilhado.css">
  <link rel="stylesheet" href="cei-graficos.css">
  <script src="cei-tema.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
</head>
<body>
  <div class="pagina pagina--incorporar" id="pagina-principal">
    <div class="barra-controles">
      {controles_iteracao}
      <button type="button" class="botao-atualizar" id="btn-atualizar">Atualizar</button>
      <span class="status-carregamento" id="status">Consultando GitHub…</span>
    </div>

    <div id="area-erro" class="mensagem-erro" hidden></div>
    <div class="painel-metricas" id="metricas" hidden></div>
    <p id="texto-grafico" class="painel-texto-grafico" hidden></p>

    <section class="painel-grafico-generico">
      <h2 class="titulo-painel">{titulo}</h2>
      <div class="grafico-container"><canvas id="grafico-principal"></canvas></div>
      <div id="container-heatmap" hidden></div>
    </section>

    <footer class="rodape">{nome} dinâmico · API /api/{id}</footer>
  </div>

  <script>
    window.CEI_GRAFICO_CONFIG = {{
      api: '{id}',
      titulo: '{titulo_js}',
      requerIteracao: {requer_iteracao_js}
    }};
  </script>
  <script src="cei-grafico-app.js"></script>
</body>
</html>
"""

CONTROLES_ITERACAO = """
      <label for="busca-iteracao">Iteration</label>
      <div class="autocomplete-iteracao" id="autocomplete-iteracao">
        <input type="text" id="busca-iteracao" autocomplete="off" spellcheck="false"
          placeholder="Pesquisar iteration…" aria-autocomplete="list"
          aria-controls="lista-sugestoes-iteracao" aria-expanded="false" />
        <ul id="lista-sugestoes-iteracao" class="lista-sugestoes" role="listbox" hidden></ul>
      </div>"""

README_TEMPLATE = """# {nome} — incorporação e tema

{descricao}

## Página

| Arquivo | Descrição |
|---------|-----------|
| `{id}-cei-dinamico.html` | {nome} dinâmico via `/api/{id}` |

URL local: http://127.0.0.1:8766/{id}-cei-dinamico.html

{iteracao_doc}

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais |
| `cei-compartilhado.css` | Botões, badges, embed |
| `cei-graficos.css` | Layout compartilhado dos gráficos |
| `cei-grafico-app.js` | App Chart.js + autocomplete |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets prontos |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/{id}-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente{iteracao_exemplo}"
  title="{nome}"
  style="width:100%;min-height:560px;border:0"
></iframe>
```

## Query string

| Parâmetro | Exemplo | Efeito |
|-----------|---------|--------|
{iteracao_param}| `tema` | `escuro` | Preset em `temas/` |
| `css` | `/temas/exemplo-portal.css` | Folha custom |
| `embed` | `1` | Layout incorporado |
| `sem-rodape` | `1` | Oculta rodapé |
| `sem-controles` | `1` | Oculta controles |
| `fundo` | `transparente` | Fundo transparente |
| `origem` | `https://portal.exemplo` | Origens no `postMessage` |

## postMessage

```javascript
iframe.contentWindow.postMessage({{
  tipo: 'cei-aplicar-tema',
  tokens: {{ '--cor-fundo': 'transparent' }},
  corpo: {{ adicionar: ['ocultar-rodape'] }},
}}, 'http://127.0.0.1:8766');
```

O gráfico relê tokens ao evento `cei-tema-alterado`.
"""


def gerar() -> None:
    for g in GRAFICOS:
        gid = g["id"]
        controles = CONTROLES_ITERACAO if g["requer_iteracao"] else ""
        html = HTML_TEMPLATE.format(
            id=gid,
            nome=g["nome"],
            titulo=g["titulo"],
            titulo_js=g["titulo"].replace("'", "\\'"),
            controles_iteracao=controles,
            requer_iteracao_js="true" if g["requer_iteracao"] else "false",
        )
        (DIR_BASE / f"{gid}-cei-dinamico.html").write_text(html, encoding="utf-8")

        pasta = DIR_BASE / gid
        pasta.mkdir(exist_ok=True)
        iteracao_doc = (
            "Iteration específica: `?iteracao=<id>` (compatível com demais parâmetros de tema)."
            if g["requer_iteracao"]
            else "Visão agregada do board (sem iteration obrigatória)."
        )
        iteracao_exemplo = "&iteracao=a5dfcb98" if g["requer_iteracao"] else ""
        iteracao_param = "| `iteracao` | `a5dfcb98` | Iteration inicial |\n" if g["requer_iteracao"] else ""
        readme = README_TEMPLATE.format(
            id=gid,
            nome=g["nome"],
            descricao=g["descricao"],
            iteracao_doc=iteracao_doc,
            iteracao_exemplo=iteracao_exemplo,
            iteracao_param=iteracao_param,
        )
        (pasta / "readme.md").write_text(readme, encoding="utf-8")
        print(f"Gerado: {gid}-cei-dinamico.html + {gid}/readme.md")


if __name__ == "__main__":
    gerar()
