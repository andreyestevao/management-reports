"""Utilitários compartilhados para gráficos do management-reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, pstdev

from burndown_cei_dados import (
    _carregar_historico,
    _data_fim_iteracao,
    _parse_data,
    buscar_burndown,
    buscar_iteracoes,
)
from kanban_cei_dados import COLUNAS_STATUS, COR_COLUNA, buscar_kanban

STATUS_WIP = frozenset({"Em progresso", "Em Impedimento"})
DIAS_SEMANA = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")


def envelope_resposta(
    projeto: dict,
    grafico: dict,
    *,
    iteracao: dict | None = None,
    metricas: list[dict] | None = None,
    texto: str | None = None,
) -> dict:
    """Monta payload JSON padrão para páginas de gráfico."""
    payload: dict = {
        "projeto": projeto,
        "geradoEm": datetime.now().astimezone().isoformat(timespec="seconds"),
        "grafico": grafico,
    }
    if iteracao is not None:
        payload["iteracao"] = iteracao
    if metricas:
        payload["metricas"] = metricas
    if texto:
        payload["texto"] = texto
    return payload


def obter_burndown(proprietario: str, numero: int, iteracao_id: str | None) -> dict:
    """Consulta burndown e propaga erro como dict."""
    dados = buscar_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados
    return dados


def listar_todas_iteracoes(proprietario: str, numero: int) -> list[dict]:
    """Carrega todas as iterations disponíveis (paginado)."""
    itens: list[dict] = []
    offset = 0
    while True:
        pagina = buscar_iteracoes(proprietario, numero, "", offset, 50)
        itens.extend(pagina.get("itens") or [])
        if not pagina.get("temMais"):
            break
        offset += pagina.get("limit") or 50
    return itens


def ordenar_iteracoes_por_inicio(iteracoes: list[dict], reverso: bool = True) -> list[dict]:
    """Ordena iterations por data de início."""
    def chave(it: dict) -> date:
        try:
            return _parse_data(it["startDate"]) if it.get("startDate") else date.min
        except ValueError:
            return date.min

    return sorted(iteracoes, key=chave, reverse=reverso)


def mapa_responsaveis_kanban(proprietario: str, numero: int) -> dict[int, list[str]]:
    """Mapeia número da issue → lista de responsáveis do kanban."""
    dados = buscar_kanban(proprietario, numero)
    if dados.get("erro"):
        return {}
    mapa: dict[int, list[str]] = {}
    for lista in (dados.get("colunas") or {}).values():
        for item in lista:
            numero_issue = item.get("numero")
            if numero_issue:
                mapa[numero_issue] = item.get("responsaveis") or []
    return mapa


def enriquecer_escopo_com_responsaveis(
    escopo: list[dict],
    mapa: dict[int, list[str]],
) -> list[dict]:
    """Anexa responsáveis do kanban aos itens de escopo."""
    enriquecidos: list[dict] = []
    for item in escopo:
        copia = dict(item)
        numero = copia.get("numero")
        if numero and numero in mapa:
            copia["responsaveis"] = mapa[numero]
        else:
            copia["responsaveis"] = copia.get("responsaveis") or []
        enriquecidos.append(copia)
    return enriquecidos


def contar_por_status(itens: list[dict]) -> dict[str, int]:
    """Conta itens agrupados por status."""
    contagem: Counter[str] = Counter()
    for item in itens:
        contagem[item.get("status") or "Sem status"] += 1
    return dict(contagem)


def _rotulo_contagem(valor) -> str:
    """Converte valor de agrupamento (str ou dict assignee) em rótulo legível."""
    if isinstance(valor, str):
        return valor.strip() or "Sem valor"
    if isinstance(valor, dict):
        return (
            valor.get("login")
            or valor.get("name")
            or valor.get("nameWithOwner")
            or "Sem valor"
        )
    return str(valor)


def contar_por_chave(itens: list[dict], chave: str, padrao: str = "Sem valor") -> dict[str, int]:
    """Conta itens agrupados por campo arbitrário."""
    contagem: Counter[str] = Counter()
    for item in itens:
        valor = item.get(chave) or padrao
        if isinstance(valor, list):
            if not valor:
                contagem[padrao] += 1
            else:
                for v in valor:
                    contagem[_rotulo_contagem(v)] += 1
        else:
            contagem[_rotulo_contagem(valor)] += 1
    return dict(contagem)


def formatar_label_data(valor: date) -> str:
    """Formata data para eixo do gráfico."""
    return valor.strftime("%d/%m")


def dias_entre(inicio: date, fim: date) -> list[date]:
    """Lista inclusive de dias entre duas datas."""
    dias: list[date] = []
    atual = inicio
    while atual <= fim:
        dias.append(atual)
        atual += timedelta(days=1)
    return dias


def por_status_do_snapshot(snap: dict) -> dict[str, int]:
    """Obtém contagem por status de um snapshot (compatível com histórico antigo)."""
    if snap.get("porStatus"):
        return dict(snap["porStatus"])
    return contar_por_status(snap.get("itens") or [])


def dataset_barra(
    rotulo: str,
    labels: list[str],
    valores: list[float | int],
    *,
    cor: str | None = None,
    horizontal: bool = False,
) -> dict:
    """Monta dataset padrão para gráfico de barras."""
    ds: dict = {"label": rotulo, "data": valores}
    if cor:
        ds["cor"] = cor
    if horizontal:
        ds["horizontal"] = True
    return ds


def datasets_por_status(
    labels: list[str],
    series: dict[str, list[int]],
    ordem: list[str] | None = None,
) -> list[dict]:
    """Converte séries por status em datasets Chart.js."""
    ordem_final = ordem or COLUNAS_STATUS
    vistos = set(ordem_final)
    for status in series:
        if status not in vistos:
            ordem_final = [*ordem_final, status]
            vistos.add(status)

    datasets: list[dict] = []
    for status in ordem_final:
        if status not in series:
            continue
        datasets.append(
            {
                "label": status,
                "data": series[status],
                "cor": COR_COLUNA.get(status, "#6c757d"),
                "empilhado": True,
            }
        )
    return datasets


def estatisticas_iteration_burndown(dados: dict) -> dict:
    """Extrai métricas resumidas de um payload burndown."""
    escopo = dados.get("escopo") or []
    total = len(escopo)
    concluido = sum(1 for i in escopo if i.get("concluido"))
    restante = total - concluido
    progresso = round(100 * concluido / total, 1) if total else 0.0
    return {
        "total": total,
        "concluido": concluido,
        "restante": restante,
        "progresso": progresso,
    }


def resumo_velocidade_iterations(
    proprietario: str,
    numero: int,
    limite: int = 8,
) -> list[dict]:
    """Calcula throughput médio (itens/dia) das últimas iterations encerradas."""
    iteracoes = ordenar_iteracoes_por_inicio(listar_todas_iteracoes(proprietario, numero))
    hoje = date.today()
    resumos: list[dict] = []

    for it in iteracoes:
        if not it.get("startDate"):
            continue
        inicio = _parse_data(it["startDate"])
        fim = _data_fim_iteracao(inicio, it.get("duration") or 0)
        if fim >= hoje:
            continue
        dados = buscar_burndown(proprietario, numero, it["id"])
        if dados.get("erro"):
            continue
        stats = estatisticas_iteration_burndown(dados)
        duracao = max((fim - inicio).days + 1, 1)
        resumos.append(
            {
                "id": it["id"],
                "titulo": it.get("title") or it["id"],
                "concluido": stats["concluido"],
                "total": stats["total"],
                "duracaoDias": duracao,
                "throughput": round(stats["concluido"] / duracao, 2),
            }
        )
        if len(resumos) >= limite:
            break
    return resumos


def percentis(valores: list[float], percentis_alvo: list[int]) -> dict[int, float]:
    """Percentis simples (sem numpy)."""
    if not valores:
        return {p: 0.0 for p in percentis_alvo}
    ordenados = sorted(valores)
    resultado: dict[int, float] = {}
    for p in percentis_alvo:
        if len(ordenados) == 1:
            resultado[p] = ordenados[0]
            continue
        idx = min(len(ordenados) - 1, max(0, int(round(p / 100 * (len(ordenados) - 1)))))
        resultado[p] = ordenados[idx]
    return resultado


def media_e_desvio(valores: list[float]) -> tuple[float, float]:
    """Média e desvio padrão populacional."""
    if not valores:
        return 0.0, 0.0
    if len(valores) == 1:
        return valores[0], 0.0
    return mean(valores), pstdev(valores)
