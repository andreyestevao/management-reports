"""Gantt do roadmap CEI — iterations e tarefas (mesmas regras do burndown)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from burndown_cei_dados import (
    QUERY_ISSUES_ITERACAO,
    _carregar_historico,
    _data_fim_iteracao,
    _filtrar_iteracoes,
    _ids_mesma_iteracao,
    _iteracao_esta_arquivada,
    _itens_atuais_da_iteracao,
    _itens_do_historico,
    _mesclar_escopo,
    _mesclar_iteracoes,
    _parse_data,
    _serializar_item_escopo,
    _situacao_iteracao,
    carregar_project_completo,
    executar_graphql,
)


def _extrair_issue_do_project_item(issue: dict, project_numero: int) -> list[tuple[str, dict]]:
    """Retorna pares (iterationId, item bruto) para cada iteration ligada à issue."""
    resultados: list[tuple[str, dict]] = []
    fechado_em = issue.get("closedAt")

    for project_item in issue.get("projectItems", {}).get("nodes", []):
        if project_item.get("project", {}).get("number") != project_numero:
            continue

        status = None
        iteracao_id = None
        data_prevista = None

        for valor in project_item.get("fieldValues", {}).get("nodes", []):
            field = valor.get("field") or {}
            if field.get("name") == "Status" and valor.get("name"):
                status = valor["name"]
            if valor.get("iterationId"):
                iteracao_id = valor["iterationId"]
            if field.get("name") == "Due Date" and valor.get("date"):
                data_prevista = valor["date"][:10]

        if not iteracao_id:
            continue

        item = {
            "id": f"issue-{issue.get('number')}",
            "numero": issue.get("number"),
            "titulo": issue.get("title") or "(sem título)",
            "url": issue.get("url") or "",
            "repositorio": (issue.get("repository") or {}).get("nameWithOwner", ""),
            "status": status or "Sem status",
            "estadoIssue": issue.get("state"),
            "fechadoEm": fechado_em[:10] if fechado_em else None,
            "dataPrevista": data_prevista,
            "iteracaoId": iteracao_id,
        }
        resultados.append((iteracao_id, item))

    return resultados


def _carregar_mapa_issues_por_iteracao(proprietario: str, numero_projeto: int) -> dict[str, list[dict]]:
    """
    Uma varredura org-wide: agrupa issues do project por iterationId.
    Recupera tarefas de iterations arquivadas fora do board ativo.
    """
    consulta = f"org:{proprietario} is:issue"
    cursor: str | None = None
    mapa: dict[str, dict[int | str, dict]] = defaultdict(dict)

    while True:
        resposta = executar_graphql(QUERY_ISSUES_ITERACAO, {"consulta": consulta, "cursor": cursor})
        busca = resposta["data"]["search"]

        for issue in busca["nodes"]:
            for iteracao_id, item in _extrair_issue_do_project_item(issue, numero_projeto):
                chave_item = item.get("numero") or item.get("titulo")
                mapa[iteracao_id][chave_item] = item

        page = busca["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    return {iid: list(itens.values()) for iid, itens in mapa.items()}


def _itens_da_iteracao_no_mapa(mapa: dict[str, list[dict]], iteracao_id: str) -> list[dict]:
    """Busca itens no mapa por ID exato ou prefixo (GitHub usa IDs curtos)."""
    for chave, lista in mapa.items():
        if _ids_mesma_iteracao(chave, iteracao_id):
            return lista
    return []


def _barra_item_gantt(item: dict, inicio_iter: date, fim_iter: date) -> dict:
    """Define intervalo da barra: início da iteration → Due Date ou fim da iteration."""
    inicio_barra = inicio_iter
    if item.get("dataPrevista"):
        fim_planejado = min(_parse_data(item["dataPrevista"]), fim_iter)
    else:
        fim_planejado = fim_iter

    if fim_planejado < inicio_barra:
        fim_planejado = inicio_barra

    fim_real = None
    if item.get("concluido") and item.get("concluidoEm"):
        conclusao = _parse_data(item["concluidoEm"])
        fim_real = max(inicio_barra, min(conclusao, fim_iter))

    return {
        "inicio": inicio_barra.isoformat(),
        "fimPlanejado": fim_planejado.isoformat(),
        "fimReal": fim_real.isoformat() if fim_real else None,
    }


def _coletar_escopo_iteracao(
    iteracao: dict,
    itens_project: list[dict],
    mapa_issues: dict[str, list[dict]],
    historico: dict,
    arquivadas: list[dict],
    hoje: date,
) -> list[dict]:
    """Mescla escopo da iteration (board + issues arquivadas + histórico)."""
    iid = iteracao["id"]
    iteration_arquivada = _iteracao_esta_arquivada(iteracao, arquivadas)

    fontes = [
        _itens_do_historico(historico, iid),
        _itens_da_iteracao_no_mapa(mapa_issues, iid),
        _itens_atuais_da_iteracao(itens_project, iid),
    ]
    if not iteration_arquivada:
        # Board ativo já cobre iterations correntes; mapa complementa removidos
        pass

    escopo_bruto = _mesclar_escopo(*fontes)
    return [_serializar_item_escopo(item, hoje) for item in escopo_bruto]


def buscar_gantt(
    proprietario: str = "CEI-UFG",
    numero: int = 1,
    consulta: str = "",
    situacao_filtro: str | None = None,
) -> dict:
    """
    Monta payload do Gantt: iterations em ordem cronológica de roadmap
    com barras de iteration e de cada tarefa (previsto vs conclusão real).
    """
    dados = carregar_project_completo(proprietario, numero)
    hoje = date.today()
    historico = _carregar_historico()
    arquivadas = dados.get("iteracoesArquivadas", [])
    iteracoes_raw = _mesclar_iteracoes(
        dados["iteracoes"],
        arquivadas,
        dados["itens"],
        historico,
    )
    mapa_issues = _carregar_mapa_issues_por_iteracao(proprietario, numero)

    iteracoes_gantt: list[dict] = []
    datas_extremas: list[date] = []

    for it in iteracoes_raw:
        inicio = _parse_data(it["startDate"])
        fim = _data_fim_iteracao(inicio, it["duration"])
        situacao = _situacao_iteracao(inicio, fim, hoje)

        if situacao_filtro and situacao != situacao_filtro:
            continue

        escopo = _coletar_escopo_iteracao(
            it, dados["itens"], mapa_issues, historico, arquivadas, hoje
        )
        escopo.sort(key=lambda x: (x.get("dataPrevista") or "9999", x.get("numero") or 0))

        itens_barra = []
        for item in escopo:
            barra = _barra_item_gantt(item, inicio, fim)
            itens_barra.append({**item, "barra": barra})
            datas_extremas.append(_parse_data(barra["inicio"]))
            datas_extremas.append(_parse_data(barra["fimPlanejado"]))
            if barra.get("fimReal"):
                datas_extremas.append(_parse_data(barra["fimReal"]))

        datas_extremas.extend([inicio, fim])

        iteracoes_gantt.append(
            {
                "id": it["id"],
                "titulo": it["title"],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "duracaoDias": it["duration"],
                "situacao": situacao,
                "arquivada": _iteracao_esta_arquivada(it, arquivadas),
                "totalItens": len(itens_barra),
                "barra": {
                    "inicio": inicio.isoformat(),
                    "fim": fim.isoformat(),
                },
                "itens": itens_barra,
            }
        )

    iteracoes_gantt.sort(key=lambda x: x["inicio"])

    if consulta:
        meta_filtrada = _filtrar_iteracoes(
            [
                {
                    "id": it["id"],
                    "titulo": it["titulo"],
                    "inicio": it["inicio"],
                    "fim": it["fim"],
                    "situacao": it["situacao"],
                }
                for it in iteracoes_gantt
            ],
            consulta,
        )
        ids_validos = {it["id"] for it in meta_filtrada}
        iteracoes_gantt = [it for it in iteracoes_gantt if it["id"] in ids_validos]

    if datas_extremas:
        periodo_inicio = min(datas_extremas)
        periodo_fim = max(datas_extremas)
    else:
        periodo_inicio = hoje
        periodo_fim = hoje

    margem = 7
    periodo_inicio = periodo_inicio.fromordinal(periodo_inicio.toordinal() - margem)
    periodo_fim = periodo_fim.fromordinal(periodo_fim.toordinal() + margem)

    return {
        "projeto": {
            "titulo": dados["projeto"]["titulo"],
            "url": dados["projeto"]["url"],
            "numero": numero,
            "proprietario": proprietario,
        },
        "geradoEm": datetime.now(timezone.utc).isoformat(),
        "hoje": hoje.isoformat(),
        "periodo": {
            "inicio": periodo_inicio.isoformat(),
            "fim": periodo_fim.isoformat(),
            "totalDias": (periodo_fim - periodo_inicio).days + 1,
        },
        "iteracoes": iteracoes_gantt,
        "resumo": {
            "totalIteracoes": len(iteracoes_gantt),
            "totalItens": sum(it["totalItens"] for it in iteracoes_gantt),
            "ativas": sum(1 for it in iteracoes_gantt if it["situacao"] == "ativa"),
            "encerradas": sum(1 for it in iteracoes_gantt if it["situacao"] == "encerrada"),
            "futuras": sum(1 for it in iteracoes_gantt if it["situacao"] == "futura"),
        },
    }
