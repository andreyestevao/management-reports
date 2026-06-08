"""APIs JSON para gráficos analíticos do board."""

from __future__ import annotations

import random
from collections import Counter
from datetime import date, timedelta

from burndown_cei_dados import _carregar_historico, _data_fim_iteracao, _parse_data
from cei_graficos_base import (
    contar_por_chave,
    contar_por_status,
    dataset_barra,
    datasets_por_status,
    dias_entre,
    enriquecer_escopo_com_responsaveis,
    envelope_resposta,
    estatisticas_iteration_burndown,
    formatar_label_data,
    listar_todas_iteracoes,
    mapa_responsaveis_kanban,
    media_e_desvio,
    obter_burndown,
    ordenar_iteracoes_por_inicio,
    percentis,
    por_status_do_snapshot,
    resumo_velocidade_iterations,
)
from kanban_cei_dados import COLUNAS_STATUS, buscar_kanban

STATUS_WIP = frozenset({"Em progresso", "Em Impedimento"})
DIAS_SEMANA = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")


def buscar_cfd(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Cumulative Flow Diagram por iteration."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    iteracao = dados["iteracao"]
    inicio = _parse_data(iteracao["inicio"])
    fim = _parse_data(iteracao["fim"])
    hoje = date.today()
    ultimo = min(hoje, fim)

    historico = _carregar_historico()
    bloco = (historico.get("iteracoes") or {}).get(iteracao["id"], {})
    snapshots = bloco.get("snapshots") or []

    dias = dias_entre(inicio, ultimo)
    labels = [formatar_label_data(d) for d in dias]
    series: dict[str, list[int]] = {s: [] for s in COLUNAS_STATUS}

    mapa_snap = {_parse_data(s["data"]): s for s in snapshots}
    ultimo_status: dict[str, int] = {s: 0 for s in COLUNAS_STATUS}

    for dia in dias:
        snap = mapa_snap.get(dia)
        if snap:
            contagem = por_status_do_snapshot(snap)
            for status in COLUNAS_STATUS:
                ultimo_status[status] = contagem.get(status, 0)
        elif dia == ultimo and dados.get("escopo"):
            contagem = contar_por_status(dados["escopo"])
            for status in COLUNAS_STATUS:
                ultimo_status[status] = contagem.get(status, 0)
        for status in COLUNAS_STATUS:
            series[status].append(ultimo_status[status])

    grafico = {
        "tipo": "stackedArea",
        "labels": labels,
        "datasets": datasets_por_status(labels, series),
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=iteracao)


def buscar_cycle_time(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Histograma de cycle time (dias até conclusão na iteration)."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    iteracao = dados["iteracao"]
    inicio = _parse_data(iteracao["inicio"])
    tempos: list[int] = []
    for item in dados.get("escopo") or []:
        if not item.get("concluido") or not item.get("concluidoEm"):
            continue
        fim_item = _parse_data(item["concluidoEm"][:10])
        dias = max(0, (fim_item - inicio).days + 1)
        tempos.append(dias)

    buckets = ["1-3", "4-7", "8-14", "15-21", "22+"]
    contagem = [0, 0, 0, 0, 0]
    for t in tempos:
        if t <= 3:
            contagem[0] += 1
        elif t <= 7:
            contagem[1] += 1
        elif t <= 14:
            contagem[2] += 1
        elif t <= 21:
            contagem[3] += 1
        else:
            contagem[4] += 1

    grafico = {
        "tipo": "bar",
        "labels": buckets,
        "datasets": [dataset_barra("Itens concluídos", buckets, contagem, cor="#0d6efd")],
    }
    media = round(sum(tempos) / len(tempos), 1) if tempos else 0
    return envelope_resposta(
        dados["projeto"],
        grafico,
        iteracao=iteracao,
        metricas=[
            {"rotulo": "Amostras", "valor": str(len(tempos))},
            {"rotulo": "Média (dias)", "valor": str(media)},
        ],
    )


def buscar_throughput(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Throughput (itens concluídos) por iteration encerrada."""
    resumos = resumo_velocidade_iterations(proprietario, numero, 10)
    resumos.reverse()
    labels = [r["titulo"][:28] + ("…" if len(r["titulo"]) > 28 else "") for r in resumos]
    valores = [r["concluido"] for r in resumos]

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("Concluídos", labels, valores, cor="#198754")],
    }
    return envelope_resposta(dados_projeto(proprietario, numero), grafico)


def buscar_monte_carlo(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Projeção Monte Carlo simplificada para a iteration atual."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    iteracao = dados["iteracao"]
    stats = estatisticas_iteration_burndown(dados)
    restante = stats["restante"]
    hoje = date.today()
    fim = _parse_data(iteracao["fim"])
    dias_restantes = max((fim - hoje).days + 1, 1)

    historico_vel = resumo_velocidade_iterations(proprietario, numero, 6)
    throughputs = [r["throughput"] for r in historico_vel if r["throughput"] > 0]
    media, desvio = media_e_desvio(throughputs)
    if media <= 0 and stats["concluido"] > 0:
        inicio = _parse_data(iteracao["inicio"])
        dias_decorridos = max((min(hoje, fim) - inicio).days + 1, 1)
        media = stats["concluido"] / dias_decorridos

    simulacoes = 500
    dias_para_concluir: list[float] = []

    for _ in range(simulacoes):
        rest = restante
        dia = 0
        while rest > 0 and dia < dias_restantes + 60:
            dia += 1
            entrega = max(0.0, random.gauss(media, desvio or media * 0.2))
            rest -= entrega
        dias_para_concluir.append(float(dia))

    p = percentis(dias_para_concluir, [50, 85, 95])
    labels = ["P50", "P85", "P95"]
    valores = [round(p[50], 1), round(p[85], 1), round(p[95], 1)]

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("Dias para concluir", labels, valores, cor="#fd7e14")],
    }
    return envelope_resposta(
        dados["projeto"],
        grafico,
        iteracao=iteracao,
        metricas=[
            {"rotulo": "Restante", "valor": str(restante)},
            {"rotulo": "Dias no sprint", "valor": str(dias_restantes)},
            {"rotulo": "Throughput médio", "valor": f"{media:.2f}/dia"},
        ],
        texto="Simulação com throughput histórico das últimas iterations encerradas.",
    )


def buscar_desvio_due_date(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Scatter: Due Date vs data de conclusão."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    pontos = []
    for item in dados.get("escopo") or []:
        if not item.get("concluido") or not item.get("concluidoEm") or not item.get("dataPrevista"):
            continue
        pontos.append(
            {
                "x": item["dataPrevista"],
                "y": item["concluidoEm"][:10],
                "rotulo": f"#{item.get('numero')}",
            }
        )

    grafico = {
        "tipo": "scatter",
        "datasets": [
            {
                "label": "Conclusão vs Due Date",
                "data": pontos,
                "cor": "#0d6efd",
            }
        ],
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=dados["iteracao"])


def buscar_scope_creep(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Evolução do escopo total ao longo da iteration."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    iteracao = dados["iteracao"]
    inicio = _parse_data(iteracao["inicio"])
    fim = _parse_data(iteracao["fim"])
    hoje = date.today()
    ultimo = min(hoje, fim)

    historico = _carregar_historico()
    bloco = (historico.get("iteracoes") or {}).get(iteracao["id"], {})
    snapshots = bloco.get("snapshots") or []
    mapa = {_parse_data(s["data"]): s.get("total", 0) for s in snapshots}

    dias = dias_entre(inicio, ultimo)
    labels = [formatar_label_data(d) for d in dias]
    escopo_serie: list[int] = []
    ultimo_total = 0
    for dia in dias:
        if dia in mapa:
            ultimo_total = mapa[dia]
        elif dia == ultimo:
            ultimo_total = len(dados.get("escopo") or [])
        escopo_serie.append(ultimo_total)

    inicial = escopo_serie[0] if escopo_serie else 0
    atual = escopo_serie[-1] if escopo_serie else 0
    grafico = {
        "tipo": "line",
        "labels": labels,
        "datasets": [
            {"label": "Escopo total", "data": escopo_serie, "cor": "#6c757d", "preencher": True},
        ],
    }
    return envelope_resposta(
        dados["projeto"],
        grafico,
        iteracao=iteracao,
        metricas=[
            {"rotulo": "Escopo inicial", "valor": str(inicial)},
            {"rotulo": "Escopo atual", "valor": str(atual)},
            {"rotulo": "Crescimento", "valor": f"{atual - inicial:+d}"},
        ],
    )


def buscar_taxa_conclusao(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Percentual concluído por iteration (últimas encerradas + ativa)."""
    iteracoes = ordenar_iteracoes_por_inicio(listar_todas_iteracoes(proprietario, numero))[:12]
    iteracoes.reverse()
    labels: list[str] = []
    valores: list[float] = []

    for it in iteracoes:
        dados = obter_burndown(proprietario, numero, it["id"])
        if dados.get("erro"):
            continue
        stats = estatisticas_iteration_burndown(dados)
        if stats["total"] == 0:
            continue
        labels.append(it.get("title", it["id"])[:26])
        valores.append(stats["progresso"])

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("% concluído", labels, valores, cor="#198754")],
    }
    return envelope_resposta(dados_projeto(proprietario, numero), grafico)


def buscar_carga_responsavel(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Carga aberta por responsável na iteration."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    mapa = mapa_responsaveis_kanban(proprietario, numero)
    escopo = enriquecer_escopo_com_responsaveis(dados.get("escopo") or [], mapa)
    abertos = [i for i in escopo if not i.get("concluido")]
    contagem = contar_por_chave(abertos, "responsaveis", "Sem responsável")

    labels = list(contagem.keys())[:15]
    valores = [contagem[k] for k in labels]

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("Itens abertos", labels, valores, cor="#0d6efd", horizontal=True)],
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=dados["iteracao"])


def buscar_wip_pessoa(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """WIP (Em progresso / Impedimento) por responsável."""
    kanban = buscar_kanban(proprietario, numero)
    if kanban.get("erro"):
        return kanban

    titulo_iteracao: str | None = None
    if iteracao_id:
        dados = obter_burndown(proprietario, numero, iteracao_id)
        if not dados.get("erro"):
            titulo_iteracao = dados["iteracao"].get("titulo")

    itens_wip: list[dict] = []
    for status, lista in (kanban.get("colunas") or {}).items():
        if status not in STATUS_WIP:
            continue
        for item in lista:
            if titulo_iteracao and item.get("iteracao") != titulo_iteracao:
                continue
            itens_wip.append(item)

    contagem = contar_por_chave(itens_wip, "responsaveis", "Sem responsável")
    labels = list(contagem.keys())[:15]
    valores = [contagem[k] for k in labels]

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("WIP", labels, valores, cor="#fd7e14", horizontal=True)],
    }
    return envelope_resposta(kanban["projeto"], grafico)


def buscar_mapa_repositorio(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Distribuição por repositório no escopo da iteration."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    contagem = contar_por_chave(dados.get("escopo") or [], "repositorio", "Sem repositório")
    labels = []
    valores = []
    for repo, qtd in sorted(contagem.items(), key=lambda x: -x[1])[:12]:
        curto = repo.split("/")[-1] if "/" in repo else repo
        labels.append(curto)
        valores.append(qtd)

    grafico = {
        "tipo": "doughnut",
        "labels": labels,
        "datasets": [{"label": "Itens", "data": valores}],
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=dados["iteracao"])


def buscar_release_timeline(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Timeline de iterations (duração e janela temporal)."""
    iteracoes = ordenar_iteracoes_por_inicio(listar_todas_iteracoes(proprietario, numero))[:10]
    iteracoes.reverse()

    labels: list[str] = []
    barras: list[list[str]] = []
    for it in iteracoes:
        if not it.get("startDate"):
            continue
        inicio = _parse_data(it["startDate"])
        fim = _data_fim_iteracao(inicio, it.get("duration") or 0)
        titulo = it.get("title") or it["id"]
        labels.append(titulo[:32] + ("…" if len(titulo) > 32 else ""))
        barras.append([inicio.isoformat(), fim.isoformat()])

    grafico = {
        "tipo": "timeline",
        "labels": labels,
        "datasets": [{"label": "Iteration", "data": barras, "cor": "rgba(0, 51, 102, 0.55)"}],
    }
    return envelope_resposta(dados_projeto(proprietario, numero), grafico)


def buscar_aging_wip(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Idade dos itens não concluídos na iteration."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    inicio = _parse_data(dados["iteracao"]["inicio"])
    hoje = date.today()
    itens_idade: list[tuple[str, int]] = []

    for item in dados.get("escopo") or []:
        if item.get("concluido"):
            continue
        idade = max(0, (hoje - inicio).days + 1)
        rotulo = f"#{item.get('numero')} { (item.get('titulo') or '')[:24]}"
        itens_idade.append((rotulo, idade))

    itens_idade.sort(key=lambda x: -x[1])
    itens_idade = itens_idade[:20]
    labels = [i[0] for i in itens_idade]
    valores = [i[1] for i in itens_idade]

    grafico = {
        "tipo": "bar",
        "labels": labels,
        "datasets": [dataset_barra("Dias em aberto", labels, valores, cor="#dc3545", horizontal=True)],
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=dados["iteracao"])


def buscar_status_portfolio(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Distribuição de status de todo o board."""
    kanban = buscar_kanban(proprietario, numero)
    if kanban.get("erro"):
        return kanban

    contagem: Counter[str] = Counter()
    for status, lista in (kanban.get("colunas") or {}).items():
        contagem[status] += len(lista)

    labels = list(contagem.keys())
    valores = [contagem[k] for k in labels]

    grafico = {
        "tipo": "doughnut",
        "labels": labels,
        "datasets": [{"label": "Itens", "data": valores}],
    }
    total = sum(valores)
    return envelope_resposta(
        kanban["projeto"],
        grafico,
        metricas=[{"rotulo": "Total no board", "valor": str(total)}],
    )


def buscar_heatmap_atividade(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Heatmap de conclusões por dia da semana (últimos 90 dias)."""
    from burndown_cei_dados import _data_conclusao, _item_concluido
    from gantt_cei_dados import _carregar_mapa_issues_por_iteracao

    hoje = date.today()
    inicio_janela = hoje - timedelta(days=90)
    matriz: dict[int, Counter[tuple[int, int]]] = {i: Counter() for i in range(7)}

    mapa_issues = _carregar_mapa_issues_por_iteracao(proprietario, numero)
    numeros_vistos: set[int | str] = set()
    total_eventos = 0

    for lista in mapa_issues.values():
        for item in lista:
            chave = item.get("numero") or item.get("id")
            if chave in numeros_vistos:
                continue
            if not _item_concluido(item):
                continue
            conclusao = _data_conclusao(item, hoje)
            if not conclusao or conclusao < inicio_janela:
                continue
            numeros_vistos.add(chave)
            total_eventos += 1
            ano, semana, _ = conclusao.isocalendar()
            matriz[conclusao.weekday()][(ano, semana)] += 1

    semanas_ordenadas = sorted({chave for contador in matriz.values() for chave in contador.keys()})[-12:]
    labels_semanas = [f"Sem {s:02d}/{a}" for a, s in semanas_ordenadas]
    linhas = list(DIAS_SEMANA)
    valores = [
        [matriz[i].get(chave, 0) for chave in semanas_ordenadas]
        for i in range(7)
    ]

    grafico = {
        "tipo": "heatmap",
        "labelsColunas": labels_semanas,
        "labelsLinhas": linhas,
        "valores": valores,
    }
    metricas = [{"rotulo": "Conclusões (90 dias)", "valor": str(total_eventos)}]
    texto = None
    if total_eventos == 0:
        texto = "Nenhuma conclusão registrada nos últimos 90 dias."

    return envelope_resposta(
        dados_projeto(proprietario, numero),
        grafico,
        metricas=metricas,
        texto=texto,
    )


def buscar_iteration_health(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Score de saúde da iteration (métricas + radar)."""
    dados = obter_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    iteracao = dados["iteracao"]
    stats = estatisticas_iteration_burndown(dados)
    velocidade = dados.get("velocidade") or {}
    indice_ritmo = velocidade.get("indiceRitmo") or 0
    no_prazo = dados.get("entregasNoPrazo") or {}
    pct_prazo = no_prazo.get("percentual") or 0

    hoje = date.today()
    inicio = _parse_data(iteracao["inicio"])
    fim = _parse_data(iteracao["fim"])
    dias_totais = max((fim - inicio).days + 1, 1)
    dias_decorridos = max((min(hoje, fim) - inicio).days + 1, 1)
    pct_tempo = min(100, round(100 * dias_decorridos / dias_totais, 1))

    historico = _carregar_historico()
    bloco = (historico.get("iteracoes") or {}).get(iteracao["id"], {})
    snaps = bloco.get("snapshots") or []
    escopo_inicial = snaps[0].get("total", stats["total"]) if snaps else stats["total"]
    estabilidade = 100
    if escopo_inicial and stats["total"]:
        crescimento = max(0, stats["total"] - escopo_inicial)
        estabilidade = max(0, round(100 - 100 * crescimento / escopo_inicial, 1))

    score_progresso = stats["progresso"]
    score_ritmo = min(100, max(0, round(float(indice_ritmo) * 100, 1))) if indice_ritmo else 50
    score_prazo = float(pct_prazo)
    score_escopo = estabilidade
    wip_aberto = stats["restante"]
    score_wip = max(0, min(100, round(100 - wip_aberto * 3, 1)))

    metricas = [
        {"rotulo": "Progresso", "valor": f"{score_progresso}%"},
        {"rotulo": "Tempo decorrido", "valor": f"{pct_tempo}%"},
        {"rotulo": "Índice de ritmo", "valor": f"{indice_ritmo or '—'}"},
        {"rotulo": "No prazo", "valor": f"{pct_prazo}%"},
        {"rotulo": "Estabilidade escopo", "valor": f"{estabilidade}%"},
        {"rotulo": "Itens restantes", "valor": str(wip_aberto)},
    ]

    grafico = {
        "tipo": "radar",
        "labels": ["Progresso", "Ritmo", "Prazo", "Escopo", "WIP"],
        "datasets": [
            {
                "label": "Saúde",
                "data": [score_progresso, score_ritmo, score_prazo, score_escopo, score_wip],
                "cor": "rgba(0, 51, 102, 0.6)",
            }
        ],
    }
    return envelope_resposta(dados["projeto"], grafico, iteracao=iteracao, metricas=metricas)


def buscar_comparativo_iterations(proprietario: str, numero: int, iteracao_id: str | None = None) -> dict:
    """Comparativo de restante normalizado por dia entre iterations."""
    iteracoes = ordenar_iteracoes_por_inicio(listar_todas_iteracoes(proprietario, numero))[:6]
    iteracoes.reverse()

    if iteracao_id:
        alvo = next((it for it in iteracoes if it["id"] == iteracao_id), None)
        if alvo and alvo not in iteracoes:
            iteracoes.append(alvo)

    max_dias = 1
    series_dados: list[tuple[str, list[int | None]]] = []

    for it in iteracoes:
        dados = obter_burndown(proprietario, numero, it["id"])
        if dados.get("erro"):
            continue
        inicio = _parse_data(dados["iteracao"]["inicio"])
        fim = _parse_data(dados["iteracao"]["fim"])
        duracao = max((fim - inicio).days + 1, 1)
        max_dias = max(max_dias, duracao)

        historico = _carregar_historico()
        bloco = (historico.get("iteracoes") or {}).get(it["id"], {})
        snaps = bloco.get("snapshots") or []
        mapa = {_parse_data(s["data"]): s.get("restante", 0) for s in snaps}

        serie: list[int | None] = []
        for offset in range(duracao):
            dia = inicio + timedelta(days=offset)
            if dia in mapa:
                serie.append(mapa[dia])
            elif offset == duracao - 1:
                stats = estatisticas_iteration_burndown(dados)
                serie.append(stats["restante"])
            else:
                serie.append(None)
        titulo = (it.get("title") or it["id"])[:24]
        series_dados.append((titulo, serie))

    labels = [f"D{i + 1}" for i in range(max_dias)]
    datasets = []
    cores = ["#003366", "#198754", "#fd7e14", "#dc3545", "#0d6efd", "#6c757d"]
    for idx, (titulo, serie) in enumerate(series_dados):
        dados_pad = serie + [None] * (max_dias - len(serie))
        datasets.append(
            {
                "label": titulo,
                "data": dados_pad[:max_dias],
                "cor": cores[idx % len(cores)],
            }
        )

    grafico = {"tipo": "line", "labels": labels, "datasets": datasets}
    return envelope_resposta(dados_projeto(proprietario, numero), grafico)


def dados_projeto(proprietario: str, numero: int) -> dict:
    """Metadados mínimos do project."""
    kanban = buscar_kanban(proprietario, numero)
    return kanban.get("projeto") or {"titulo": f"Project {numero}"}


ROTAS_GRAFICOS: dict[str, callable] = {
    "cfd": buscar_cfd,
    "cycle-time": buscar_cycle_time,
    "throughput": buscar_throughput,
    "monte-carlo": buscar_monte_carlo,
    "desvio-due-date": buscar_desvio_due_date,
    "scope-creep": buscar_scope_creep,
    "taxa-conclusao": buscar_taxa_conclusao,
    "carga-responsavel": buscar_carga_responsavel,
    "wip-pessoa": buscar_wip_pessoa,
    "mapa-repositorio": buscar_mapa_repositorio,
    "release-timeline": buscar_release_timeline,
    "aging-wip": buscar_aging_wip,
    "status-portfolio": buscar_status_portfolio,
    "heatmap-atividade": buscar_heatmap_atividade,
    "iteration-health": buscar_iteration_health,
    "comparativo-iterations": buscar_comparativo_iterations,
}
