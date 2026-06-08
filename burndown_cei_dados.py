"""Burndown por iteration do GitHub Projects."""

from __future__ import annotations

import json
import subprocess
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DIR_DADOS = Path(__file__).resolve().parent / "dados"
ARQUIVO_HISTORICO = DIR_DADOS / "burndown-historico.json"

STATUS_CONCLUIDO = frozenset({"Feito", "Fechado"})
_TTL_CACHE_ITERACOES_SEG = 300
_cache_iteracoes: dict[tuple[str, int], tuple[datetime, list[dict]]] = {}
_cache_itens_iteracao_arquivada: dict[tuple[str, int, str], tuple[datetime, list[dict]]] = {}

QUERY_ITENS = """
query($owner: ID!, $numero: Int!, $cursor: String) {
  node(id: $owner) {
    ... on Organization {
      projectV2(number: $numero) {
        title
        url
        fields(first: 30) {
          nodes {
            ... on ProjectV2IterationField {
              name
              configuration {
                iterations {
                  id
                  title
                  startDate
                  duration
                }
                completedIterations {
                  id
                  title
                  startDate
                  duration
                }
              }
            }
          }
        }
        items(first: 100, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            content {
              ... on Issue {
                number
                title
                state
                closedAt
                url
                repository { nameWithOwner }
              }
            }
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field { ... on ProjectV2SingleSelectField { name } }
                }
                ... on ProjectV2ItemFieldIterationValue {
                  iterationId
                  title
                  startDate
                  duration
                }
                ... on ProjectV2ItemFieldDateValue {
                  date
                  field { ... on ProjectV2FieldCommon { name } }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

QUERY_ISSUES_ITERACAO = """
query($consulta: String!, $cursor: String) {
  search(query: $consulta, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on Issue {
        number
        title
        state
        closedAt
        url
        repository { nameWithOwner }
        projectItems(first: 5) {
          nodes {
            project { number }
            fieldValues(first: 20) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field { ... on ProjectV2SingleSelectField { name } }
                }
                ... on ProjectV2ItemFieldIterationValue {
                  iterationId
                  title
                  startDate
                  duration
                }
                ... on ProjectV2ItemFieldDateValue {
                  date
                  field { ... on ProjectV2FieldCommon { name } }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def executar_graphql(query: str, variables: dict) -> dict:
    """Executa consulta GraphQL via gh api."""
    payload = json.dumps({"query": query, "variables": variables})
    resultado = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=payload,
        check=True,
        capture_output=True,
        text=True,
    )
    dados = json.loads(resultado.stdout)
    if dados.get("errors"):
        raise subprocess.CalledProcessError(1, "graphql", json.dumps(dados["errors"]))
    return dados


def obter_id_organizacao(login: str) -> str:
    """Resolve login da org para node ID GraphQL."""
    query = "query($login: String!) { organization(login: $login) { id } }"
    resultado = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"login={login}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(resultado.stdout)["data"]["organization"]["id"]


def _extrair_iteracoes_do_project(fields_nodes: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa iterations ativas e arquivadas (completedIterations) do campo Iteration."""
    for field in fields_nodes:
        configuracao = field.get("configuration")
        if not configuracao:
            continue
        ativas = configuracao.get("iterations") or []
        arquivadas = configuracao.get("completedIterations") or []
        return ativas, arquivadas
    return [], []


def carregar_project_completo(proprietario: str, numero: int) -> dict:
    """Carrega project, iterations e todos os itens via GraphQL paginado."""
    owner_id = obter_id_organizacao(proprietario)
    variables: dict[str, Any] = {"owner": owner_id, "numero": numero, "cursor": None}
    itens: list[dict] = []
    project_meta: dict | None = None
    iterations: list[dict] = []
    iterations_arquivadas: list[dict] = []

    while True:
        resposta = executar_graphql(QUERY_ITENS, variables)
        project = resposta["data"]["node"]["projectV2"]
        if project_meta is None:
            project_meta = {"titulo": project["title"], "url": project["url"], "numero": numero}
            iterations, iterations_arquivadas = _extrair_iteracoes_do_project(project["fields"]["nodes"])

        for node in project["items"]["nodes"]:
            itens.append(_normalizar_no_graphql(node))

        page = project["items"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        variables["cursor"] = page["endCursor"]

    return {
        "projeto": project_meta,
        "iteracoes": iterations,
        "iteracoesArquivadas": iterations_arquivadas,
        "itens": itens,
    }


def _extrair_data_prevista(field_values: list[dict]) -> str | None:
    """Lê Due Date do item no GitHub Project."""
    for valor in field_values:
        field = valor.get("field") or {}
        if field.get("name") == "Due Date" and valor.get("date"):
            return valor["date"][:10]
    return None


def _normalizar_no_graphql(node: dict) -> dict:
    """Extrai status, iteration, due date e dados da issue de um nó GraphQL."""
    status = None
    iteracao_id = None
    iteracao_titulo = None
    iteracao_inicio = None
    iteracao_duracao = None
    field_nodes = node.get("fieldValues", {}).get("nodes", [])

    for valor in field_nodes:
        field = valor.get("field") or {}
        if field.get("name") == "Status" and valor.get("name"):
            status = valor["name"]
        if valor.get("iterationId"):
            iteracao_id = valor["iterationId"]
            iteracao_titulo = valor.get("title")
            iteracao_inicio = valor.get("startDate")
            iteracao_duracao = valor.get("duration")

    data_prevista = _extrair_data_prevista(field_nodes)
    conteudo = node.get("content") or {}
    fechado_em = conteudo.get("closedAt")
    return {
        "id": node.get("id"),
        "numero": conteudo.get("number"),
        "titulo": conteudo.get("title") or "(sem título)",
        "url": conteudo.get("url") or "",
        "repositorio": (conteudo.get("repository") or {}).get("nameWithOwner", ""),
        "status": status or "Sem status",
        "estadoIssue": conteudo.get("state"),
        "fechadoEm": fechado_em[:10] if fechado_em else None,
        "dataPrevista": data_prevista,
        "iteracaoId": iteracao_id,
        "iteracaoTitulo": iteracao_titulo,
        "iteracaoInicio": iteracao_inicio,
        "iteracaoDuracao": iteracao_duracao,
    }


def _parse_data(valor: str) -> date:
    return datetime.strptime(valor[:10], "%Y-%m-%d").date()


def _data_fim_iteracao(inicio: date, duracao: int) -> date:
    return inicio + timedelta(days=duracao - 1)


def _situacao_iteracao(inicio: date, fim: date, hoje: date) -> str:
    if hoje < inicio:
        return "futura"
    if hoje > fim:
        return "encerrada"
    return "ativa"


def _ids_mesma_iteracao(identificador_a: str | None, identificador_b: str | None) -> bool:
    """Compara IDs de iteration (completos ou prefixo curto do GitHub)."""
    if not identificador_a or not identificador_b:
        return False
    if identificador_a == identificador_b:
        return True
    prefixo = min(len(identificador_a), len(identificador_b), 8)
    return identificador_a[:prefixo] == identificador_b[:prefixo]


def _mesclar_iteracoes(
    config: list[dict],
    arquivadas: list[dict],
    itens: list[dict],
    historico: dict,
) -> list[dict]:
    """Une iterations ativas, arquivadas, dos itens e do histórico."""
    mapa: dict[str, dict] = {}

    arquivada_ids = {it["id"] for it in arquivadas}

    for it in config + arquivadas:
        mapa[it["id"]] = {
            "id": it["id"],
            "title": it["title"],
            "startDate": it["startDate"],
            "duration": it["duration"],
            "arquivada": it["id"] in arquivada_ids,
        }

    for item in itens:
        iid = item.get("iteracaoId")
        if not iid:
            continue
        chave = next((k for k in mapa if _ids_mesma_iteracao(k, iid)), iid)
        if chave not in mapa and item.get("iteracaoInicio") and item.get("iteracaoDuracao"):
            mapa[chave] = {
                "id": iid,
                "title": item.get("iteracaoTitulo") or iid,
                "startDate": item["iteracaoInicio"],
                "duration": item["iteracaoDuracao"],
                "arquivada": False,
            }

    for iid, bloco in historico.get("iteracoes", {}).items():
        chave = next((k for k in mapa if _ids_mesma_iteracao(k, iid)), iid)
        if chave in mapa:
            continue
        inicio = bloco.get("inicio")
        duracao = bloco.get("duracaoDias")
        if inicio and duracao:
            mapa[chave] = {
                "id": iid,
                "title": bloco.get("titulo") or iid,
                "startDate": inicio,
                "duration": duracao,
                "arquivada": bloco.get("arquivada", True),
            }

    ordenadas = sorted(mapa.values(), key=lambda it: it["startDate"], reverse=True)
    return ordenadas


def _montar_iteracoes_disponiveis(iteracoes: list[dict], hoje: date) -> list[dict]:
    """Lista iterations para UI: encerradas (recente→antiga), ativa, futuras (próxima→distante)."""
    encerradas: list[dict] = []
    ativas: list[dict] = []
    futuras: list[dict] = []

    for it in iteracoes:
        inicio = _parse_data(it["startDate"])
        fim = _data_fim_iteracao(inicio, it["duration"])
        situacao = _situacao_iteracao(inicio, fim, hoje)
        entrada = {
            "id": it["id"],
            "titulo": it["title"],
            "inicio": it["startDate"],
            "fim": fim.isoformat(),
            "duracaoDias": it["duration"],
            "situacao": situacao,
            "arquivada": it.get("arquivada", situacao == "encerrada"),
        }
        if situacao == "encerrada":
            encerradas.append(entrada)
        elif situacao == "ativa":
            ativas.append(entrada)
        else:
            futuras.append(entrada)

    encerradas.sort(key=lambda x: x["inicio"], reverse=True)
    ativas.sort(key=lambda x: x["inicio"])
    futuras.sort(key=lambda x: x["inicio"])
    return encerradas + ativas + futuras


def _atualizar_cache_iteracoes(proprietario: str, numero: int, lista: list[dict]) -> None:
    """Guarda lista ordenada de iterations para autocomplete (TTL curto)."""
    expira = datetime.now(timezone.utc) + timedelta(seconds=_TTL_CACHE_ITERACOES_SEG)
    _cache_iteracoes[(proprietario, numero)] = (expira, lista)


def _listar_iteracoes_disponiveis(proprietario: str, numero: int) -> list[dict]:
    """Retorna iterations ordenadas, com cache em memória para paginação rápida."""
    chave = (proprietario, numero)
    agora = datetime.now(timezone.utc)
    if chave in _cache_iteracoes:
        expira, lista = _cache_iteracoes[chave]
        if agora < expira:
            return lista

    dados = carregar_project_completo(proprietario, numero)
    historico = _carregar_historico()
    iteracoes = _mesclar_iteracoes(
        dados["iteracoes"],
        dados.get("iteracoesArquivadas", []),
        dados["itens"],
        historico,
    )
    lista = _montar_iteracoes_disponiveis(iteracoes, date.today())
    _atualizar_cache_iteracoes(proprietario, numero, lista)
    return lista


def _normalizar_texto_busca(texto: str) -> str:
    """Lowercase sem acentos para comparação tolerante na busca."""
    texto = (texto or "").strip().lower()
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acentos if unicodedata.category(c) != "Mn")


def _filtrar_iteracoes(lista: list[dict], consulta: str) -> list[dict]:
    """Filtra por título, datas ou situação (case-insensitive, sem acento)."""
    termo = _normalizar_texto_busca(consulta)
    tokens = [t for t in termo.split() if t]
    if not tokens:
        return lista

    def corresponde(item: dict) -> bool:
        campos = (
            item.get("titulo") or "",
            item.get("inicio") or "",
            item.get("fim") or "",
            item.get("situacao") or "",
        )
        haystack = _normalizar_texto_busca(" ".join(str(valor) for valor in campos))
        return all(token in haystack for token in tokens)

    return [item for item in lista if corresponde(item)]


def buscar_iteracoes(
    proprietario: str,
    numero: int = 1,
    consulta: str = "",
    offset: int = 0,
    limit: int = 10,
) -> dict:
    """Lista iterations paginadas para autocomplete (10 por página por padrão)."""
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    lista = _listar_iteracoes_disponiveis(proprietario, numero)
    filtrada = _filtrar_iteracoes(lista, consulta)
    total = len(filtrada)
    pagina = filtrada[offset : offset + limit]

    return {
        "consulta": consulta,
        "offset": offset,
        "limit": limit,
        "total": total,
        "temMais": offset + limit < total,
        "itens": pagina,
    }


def _iteracao_por_id(iteracoes: list[dict], iteracao_id: str | None) -> dict | None:
    if not iteracao_id:
        return None
    for it in iteracoes:
        if _ids_mesma_iteracao(it["id"], iteracao_id):
            return it
    return None


def _iteracao_padrao(iteracoes: list[dict], hoje: date) -> dict | None:
    """Prefere iteration ativa; senão a encerrada mais recente."""
    for it in iteracoes:
        inicio = _parse_data(it["startDate"])
        fim = _data_fim_iteracao(inicio, it["duration"])
        if inicio <= hoje <= fim:
            return it
    for it in iteracoes:
        inicio = _parse_data(it["startDate"])
        if inicio <= hoje:
            return it
    return iteracoes[0] if iteracoes else None


def _item_concluido(item: dict) -> bool:
    if item["status"] in STATUS_CONCLUIDO:
        return True
    return item.get("estadoIssue") == "CLOSED"


def _data_conclusao(item: dict, hoje: date) -> date | None:
    if not _item_concluido(item):
        return None
    if item.get("fechadoEm"):
        return _parse_data(item["fechadoEm"])
    return hoje


def _itens_atuais_da_iteracao(itens: list[dict], iteracao_id: str) -> list[dict]:
    return [i for i in itens if _ids_mesma_iteracao(i.get("iteracaoId"), iteracao_id)]


def _normalizar_issue_com_iteracao(issue: dict, project_numero: int, iteracao_id: str) -> dict | None:
    """Extrai item do board a partir de Issue.projectItems quando a iteration está arquivada."""
    for project_item in issue.get("projectItems", {}).get("nodes", []):
        if project_item.get("project", {}).get("number") != project_numero:
            continue

        status = None
        iteracao_encontrada = False
        iteracao_titulo = None
        iteracao_inicio = None
        iteracao_duracao = None
        data_prevista = None
        field_nodes = project_item.get("fieldValues", {}).get("nodes", [])

        for valor in field_nodes:
            field = valor.get("field") or {}
            if field.get("name") == "Status" and valor.get("name"):
                status = valor["name"]
            if valor.get("iterationId"):
                if _ids_mesma_iteracao(valor["iterationId"], iteracao_id):
                    iteracao_encontrada = True
                    iteracao_titulo = valor.get("title")
                    iteracao_inicio = valor.get("startDate")
                    iteracao_duracao = valor.get("duration")

        data_prevista = _extrair_data_prevista(field_nodes)

        if not iteracao_encontrada:
            continue

        fechado_em = issue.get("closedAt")
        repositorio = (issue.get("repository") or {}).get("nameWithOwner", "")
        return {
            "id": f"issue-{issue.get('number')}",
            "numero": issue.get("number"),
            "titulo": issue.get("title") or "(sem título)",
            "url": issue.get("url") or "",
            "repositorio": repositorio,
            "status": status or "Sem status",
            "estadoIssue": issue.get("state"),
            "fechadoEm": fechado_em[:10] if fechado_em else None,
            "dataPrevista": data_prevista,
            "iteracaoId": iteracao_id,
            "iteracaoTitulo": iteracao_titulo,
            "iteracaoInicio": iteracao_inicio,
            "iteracaoDuracao": iteracao_duracao,
            "_origem": "issue-arquivada",
        }
    return None


def _buscar_itens_iteracao_arquivada(
    proprietario: str,
    numero_projeto: int,
    iteracao_id: str,
) -> list[dict]:
    """
    Recupera issues vinculadas ao project com iteration arquivada.
    O GitHub mantém o vínculo em Issue.projectItems mesmo após arquivar a iteration
    ou remover o item da visão ativa do board.
    """
    chave_cache = (proprietario, numero_projeto, iteracao_id[:8])
    agora = datetime.now(timezone.utc)
    if chave_cache in _cache_itens_iteracao_arquivada:
        expira, lista = _cache_itens_iteracao_arquivada[chave_cache]
        if agora < expira:
            return lista

    consulta = f"org:{proprietario} is:issue"
    cursor: str | None = None
    mapa: dict[int | str, dict] = {}

    while True:
        variables = {"consulta": consulta, "cursor": cursor}
        resposta = executar_graphql(QUERY_ISSUES_ITERACAO, variables)
        busca = resposta["data"]["search"]

        for issue in busca["nodes"]:
            item = _normalizar_issue_com_iteracao(issue, numero_projeto, iteracao_id)
            if not item:
                continue
            chave = item.get("numero") or item.get("titulo")
            mapa[chave] = item

        page = busca["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    lista = list(mapa.values())
    expira = agora + timedelta(seconds=_TTL_CACHE_ITERACOES_SEG)
    _cache_itens_iteracao_arquivada[chave_cache] = (expira, lista)
    return lista


def _iteracao_esta_arquivada(iteracao: dict, arquivadas: list[dict]) -> bool:
    if iteracao.get("arquivada"):
        return True
    return any(_ids_mesma_iteracao(it["id"], iteracao["id"]) for it in arquivadas)


def _itens_do_historico(historico: dict, iteracao_id: str) -> list[dict]:
    """Recupera escopo persistido: snapshots acumulados + escopo consolidado."""
    bloco = historico.get("iteracoes", {}).get(iteracao_id)
    if not bloco:
        for chave, valor in historico.get("iteracoes", {}).items():
            if _ids_mesma_iteracao(chave, iteracao_id):
                bloco = valor
                break
    if not bloco:
        return []

    mapa: dict[int | str, dict] = {}
    for snap in bloco.get("snapshots", []):
        for item in snap.get("itens", []):
            chave = item.get("numero") or item.get("id") or item.get("titulo")
            mapa[chave] = {**item, "_origem": "historico"}

    for item in bloco.get("escopoConsolidado", []):
        chave = item.get("numero") or item.get("id") or item.get("titulo")
        mapa[chave] = {**item, "_origem": "historico"}

    return list(mapa.values())


def _mesclar_escopo(*fontes: list[dict]) -> list[dict]:
    """Combina escopos de várias fontes; entradas posteriores prevalecem."""
    mapa: dict[int | str, dict] = {}

    for fonte in fontes:
        for item in fonte:
            chave = item.get("numero") or item.get("id") or item.get("titulo")
            if chave in mapa:
                mapa[chave] = {**mapa[chave], **item}
            else:
                mapa[chave] = dict(item)

    return list(mapa.values())


def _persistir_escopo_consolidado(
    historico: dict,
    iteracao: dict,
    inicio: date,
    fim: date,
    escopo_serializado: list[dict],
    arquivada: bool,
) -> None:
    """Persiste escopo completo de iterations encerradas/arquivadas para burndown futuro."""
    if not arquivada:
        return

    iid = iteracao["id"]
    bloco = historico.setdefault("iteracoes", {}).setdefault(iid, {"snapshots": []})
    bloco["titulo"] = iteracao["title"]
    bloco["inicio"] = inicio.isoformat()
    bloco["fim"] = fim.isoformat()
    bloco["duracaoDias"] = iteracao["duration"]
    bloco["arquivada"] = True

    mapa = {
        item.get("numero") or item.get("titulo"): item
        for item in bloco.get("escopoConsolidado", [])
    }
    for item in escopo_serializado:
        chave = item.get("numero") or item.get("titulo")
        mapa[chave] = item
    bloco["escopoConsolidado"] = list(mapa.values())


def _classificar_prazo_item(item: dict, hoje: date) -> tuple[str | None, int | None]:
    """Compara conclusão real com Due Date; retorna situação e desvio em dias."""
    prevista_txt = item.get("dataPrevista")
    if not prevista_txt:
        return None, None

    prevista = _parse_data(prevista_txt)
    if item.get("concluido") and item.get("concluidoEm"):
        conclusao = _parse_data(item["concluidoEm"])
        desvio = (conclusao - prevista).days
        if desvio < 0:
            return "adiantado", desvio
        if desvio == 0:
            return "no_prazo", 0
        return "atrasado", desvio

    if hoje > prevista:
        return "pendente_atrasado", (hoje - prevista).days
    return "pendente", None


def _calcular_velocidade(
    escopo: list[dict],
    inicio: date,
    fim: date,
    hoje: date,
    situacao: str,
    total: int,
    concluido: int,
    restante: int,
) -> dict:
    """
    Calcula velocidade do time: ritmo de entrega vs planejado da iteration
    e aderência às datas previstas (Due Date).
    """
    dia_referencia = fim if situacao in ("encerrada", "futura") else min(hoje, fim)
    if situacao == "futura":
        dia_referencia = inicio

    total_dias = max(1, (fim - inicio).days + 1)
    dias_decorridos = max(1, (dia_referencia - inicio).days + 1)
    dias_restantes = max(0, (fim - dia_referencia).days)

    planejada = round(total / total_dias, 3) if total else 0.0
    real = round(concluido / dias_decorridos, 3) if concluido else 0.0
    necessaria = round(restante / dias_restantes, 3) if dias_restantes > 0 and restante > 0 else 0.0
    indice_ritmo = round(100 * real / planejada, 1) if planejada else 0.0

    progresso_real = concluido / total if total else 0.0
    progresso_esperado = dias_decorridos / total_dias
    indice_progresso = round(100 * progresso_real / progresso_esperado, 1) if progresso_esperado else 0.0

    if indice_ritmo >= 105:
        rotulo_ritmo = "Acima do planejado"
    elif indice_ritmo >= 85:
        rotulo_ritmo = "No ritmo"
    else:
        rotulo_ritmo = "Abaixo do planejado"

    com_prevista = [i for i in escopo if i.get("dataPrevista")]
    concluidos_com_prevista = [i for i in com_prevista if i.get("concluido") and i.get("concluidoEm")]
    desvios = [i["desvioDias"] for i in concluidos_com_prevista if i.get("desvioDias") is not None]

    adiantados = sum(1 for i in concluidos_com_prevista if i.get("situacaoPrazo") == "adiantado")
    no_prazo = sum(1 for i in concluidos_com_prevista if i.get("situacaoPrazo") == "no_prazo")
    atrasados = sum(1 for i in concluidos_com_prevista if i.get("situacaoPrazo") == "atrasado")
    pendentes_atrasados = sum(1 for i in com_prevista if i.get("situacaoPrazo") == "pendente_atrasado")

    entregues_no_prazo = adiantados + no_prazo
    pct_no_prazo = (
        round(100 * entregues_no_prazo / len(concluidos_com_prevista), 1)
        if concluidos_com_prevista
        else None
    )
    desvio_medio = round(sum(desvios) / len(desvios), 1) if desvios else None

    if desvio_medio is not None:
        if desvio_medio <= -1:
            rotulo_prazo = "Entregas antecipadas"
        elif desvio_medio <= 1:
            rotulo_prazo = "Entregas no prazo"
        else:
            rotulo_prazo = "Entregas atrasadas"
    elif pendentes_atrasados:
        rotulo_prazo = "Itens pendentes em atraso"
    elif com_prevista and not concluidos_com_prevista:
        rotulo_prazo = "Aguardando primeiras entregas"
    else:
        rotulo_prazo = "Sem Due Date no escopo"

    return {
        "itensPorDiaPlanejado": planejada,
        "itensPorDiaReal": real,
        "itensPorDiaNecessario": necessaria,
        "indiceRitmoPercentual": indice_ritmo,
        "indiceProgressoPercentual": indice_progresso,
        "rotuloRitmo": rotulo_ritmo,
        "diasDecorridos": dias_decorridos,
        "diasRestantes": dias_restantes,
        "totalDiasIteration": total_dias,
        "comDataPrevista": len(com_prevista),
        "concluidosComDataPrevista": len(concluidos_com_prevista),
        "entreguesNoPrazo": entregues_no_prazo,
        "entreguesAtrasados": atrasados,
        "entreguesAdiantados": adiantados,
        "pendentesAtrasados": pendentes_atrasados,
        "percentualNoPrazo": pct_no_prazo,
        "desvioMedioDias": desvio_medio,
        "rotuloPrazo": rotulo_prazo,
    }


def _serializar_item_escopo(item: dict, hoje: date) -> dict:
    concluido = _item_concluido(item)
    conclusao = _data_conclusao(item, hoje)
    concluido_em = conclusao.isoformat() if concluido and conclusao else item.get("concluidoEm")
    data_prevista = item.get("dataPrevista")

    base = {
        "numero": item.get("numero"),
        "titulo": item.get("titulo") or "(sem título)",
        "status": item.get("status") or "Sem status",
        "url": item.get("url") or "",
        "repositorio": item.get("repositorio") or "",
        "concluido": concluido,
        "concluidoEm": concluido_em,
        "dataPrevista": data_prevista,
    }

    situacao_prazo, desvio = _classificar_prazo_item(
        {"concluido": concluido, "concluidoEm": concluido_em, "dataPrevista": data_prevista},
        hoje,
    )
    base["situacaoPrazo"] = situacao_prazo
    base["desvioDias"] = desvio
    return base


def _carregar_historico() -> dict:
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO_HISTORICO.exists():
        return {"versoes": 1, "iteracoes": {}}
    return json.loads(ARQUIVO_HISTORICO.read_text(encoding="utf-8"))


def _salvar_historico(historico: dict) -> None:
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_HISTORICO.write_text(
        json.dumps(historico, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _registrar_snapshot(
    historico: dict,
    iteracao: dict,
    inicio: date,
    fim: date,
    escopo_serializado: list[dict],
    hoje: date,
) -> None:
    """Persiste snapshot diário apenas para iteration ativa."""
    if not (inicio <= hoje <= fim):
        return

    iid = iteracao["id"]
    restante = sum(1 for i in escopo_serializado if not i["concluido"])
    concluido = sum(1 for i in escopo_serializado if i["concluido"])
    total = len(escopo_serializado)
    hoje_iso = hoje.isoformat()

    bloco = historico.setdefault("iteracoes", {}).setdefault(
        iid,
        {"titulo": iteracao["title"], "snapshots": []},
    )
    bloco["titulo"] = iteracao["title"]
    bloco["inicio"] = inicio.isoformat()
    bloco["fim"] = fim.isoformat()
    bloco["duracaoDias"] = iteracao["duration"]

    por_status: dict[str, int] = {}
    for item in escopo_serializado:
        status = item.get("status") or "Sem status"
        por_status[status] = por_status.get(status, 0) + 1

    entrada = {
        "data": hoje_iso,
        "restante": restante,
        "concluido": concluido,
        "total": total,
        "itens": escopo_serializado,
        "porStatus": por_status,
    }

    snapshots: list[dict] = bloco["snapshots"]
    if snapshots and snapshots[-1]["data"] == hoje_iso:
        snapshots[-1] = entrada
    else:
        snapshots.append(entrada)


def _serie_a_partir_snapshots(snapshots: list[dict], inicio: date, fim: date) -> dict[date, int]:
    mapa: dict[date, int] = {}
    for snap in snapshots:
        d = _parse_data(snap["data"])
        if inicio <= d <= fim:
            mapa[d] = snap["restante"]
    return mapa


def _total_escopo(escopo: list[dict], snapshots: list[dict]) -> int:
    totais_snapshot = [s.get("total", 0) for s in snapshots if s.get("total")]
    max_snap = max(totais_snapshot) if totais_snapshot else 0
    return max(len(escopo), max_snap)


def _restante_no_dia(escopo: list[dict], dia: date, hoje: date) -> int:
    return sum(
        1
        for item in escopo
        if not (_data_conclusao(item, hoje) and _data_conclusao(item, hoje) <= dia)
    )


def buscar_burndown(
    proprietario: str,
    numero: int = 1,
    iteracao_id: str | None = None,
) -> dict:
    """Monta payload JSON do burndown para uma iteration (ativa, futura ou encerrada)."""
    dados = carregar_project_completo(proprietario, numero)
    hoje = date.today()
    historico = _carregar_historico()
    iteracoes = _mesclar_iteracoes(
        dados["iteracoes"],
        dados.get("iteracoesArquivadas", []),
        dados["itens"],
        historico,
    )
    itens = dados["itens"]
    arquivadas = dados.get("iteracoesArquivadas", [])

    iteracao = _iteracao_por_id(iteracoes, iteracao_id) if iteracao_id else _iteracao_padrao(iteracoes, hoje)
    if not iteracao:
        return {"erro": "Nenhuma iteration encontrada no project"}

    iid = iteracao["id"]
    inicio = _parse_data(iteracao["startDate"])
    fim = _data_fim_iteracao(inicio, iteracao["duration"])
    situacao = _situacao_iteracao(inicio, fim, hoje)
    iteration_arquivada = _iteracao_esta_arquivada(iteracao, arquivadas) or situacao == "encerrada"

    if situacao == "futura":
        ultimo_dia = inicio
    elif situacao == "encerrada":
        ultimo_dia = fim
    else:
        ultimo_dia = min(hoje, fim)

    itens_historico = _itens_do_historico(historico, iid)
    itens_arquivados: list[dict] = []
    if iteration_arquivada:
        itens_arquivados = _buscar_itens_iteracao_arquivada(proprietario, numero, iid)

    escopo_bruto = _mesclar_escopo(
        itens_historico,
        itens_arquivados,
        _itens_atuais_da_iteracao(itens, iid),
    )
    escopo_serializado = [_serializar_item_escopo(i, hoje) for i in escopo_bruto]

    _registrar_snapshot(historico, iteracao, inicio, fim, escopo_serializado, hoje)
    _persistir_escopo_consolidado(
        historico, iteracao, inicio, fim, escopo_serializado, iteration_arquivada
    )
    _salvar_historico(historico)

    snapshots = historico.get("iteracoes", {}).get(iid, {}).get("snapshots", [])
    mapa_snap = _serie_a_partir_snapshots(snapshots, inicio, fim)
    total = _total_escopo(escopo_bruto, snapshots)

    concluidos = [i for i in escopo_serializado if i["concluido"]]
    restantes = [i for i in escopo_serializado if not i["concluido"]]
    velocidade = _calcular_velocidade(
        escopo_serializado, inicio, fim, hoje, situacao, total, len(concluidos), len(restantes)
    )

    dias: list[date] = []
    cursor = inicio
    while cursor <= ultimo_dia:
        dias.append(cursor)
        cursor += timedelta(days=1)

    total_dias = (fim - inicio).days + 1
    labels: list[str] = []
    serie_ideal: list[float] = []
    serie_real: list[int] = []

    for indice, dia in enumerate(dias):
        labels.append(dia.strftime("%d/%m"))
        if total_dias <= 1:
            serie_ideal.append(float(total))
        else:
            dias_decorridos = (dia - inicio).days
            serie_ideal.append(round(total * (1 - dias_decorridos / (total_dias - 1)), 2))

        if dia in mapa_snap:
            serie_real.append(mapa_snap[dia])
        else:
            serie_real.append(_restante_no_dia(escopo_bruto, dia, hoje))

    rotulo_situacao = {"ativa": "iteration ativa", "encerrada": "iteration encerrada", "futura": "iteration futura"}
    iteracoes_disponiveis = _montar_iteracoes_disponiveis(iteracoes, hoje)
    _atualizar_cache_iteracoes(proprietario, numero, iteracoes_disponiveis)

    return {
        "projeto": {
            "titulo": dados["projeto"]["titulo"],
            "url": dados["projeto"]["url"],
            "numero": numero,
            "proprietario": proprietario,
        },
        "geradoEm": datetime.now(timezone.utc).isoformat(),
        "iteracao": {
            "id": iid,
            "titulo": iteracao["title"],
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "duracaoDias": iteracao["duration"],
            "situacao": situacao,
            "ativa": situacao == "ativa",
            "arquivada": iteration_arquivada,
        },
        "iteracoesDisponiveis": iteracoes_disponiveis,
        "metricas": {
            "totalEscopo": total,
            "concluido": len(concluidos),
            "restante": len(restantes),
            "progressoPercentual": round(100 * len(concluidos) / total, 1) if total else 0,
        },
        "velocidade": velocidade,
        "grafico": {
            "labels": labels,
            "serieIdeal": serie_ideal,
            "serieReal": serie_real,
            "periodoCompleto": situacao == "encerrada",
        },
        "snapshots": snapshots,
        "itensEscopo": sorted(
            escopo_serializado,
            key=lambda x: (not x["concluido"], x.get("numero") or 0),
        ),
        "rotuloSituacao": rotulo_situacao[situacao],
    }
