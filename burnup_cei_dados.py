"""Burnup por iteration — reutiliza escopo e snapshots do burndown."""

from __future__ import annotations

from datetime import date, timedelta

from burndown_cei_dados import buscar_burndown


def _montar_grafico_burnup(dados_burndown: dict) -> dict:
    """Converte séries de restante (burndown) em escopo + concluído acumulado (burnup)."""
    grafico_bd = dados_burndown["grafico"]
    labels = grafico_bd["labels"]
    serie_restante = grafico_bd["serieReal"]

    inicio = date.fromisoformat(dados_burndown["iteracao"]["inicio"])
    fim = date.fromisoformat(dados_burndown["iteracao"]["fim"])
    total_escopo = dados_burndown["metricas"]["totalEscopo"]
    total_dias = max(1, (fim - inicio).days + 1)

    mapa_snap = {snap["data"]: snap for snap in dados_burndown.get("snapshots", [])}

    serie_escopo: list[int] = []
    serie_concluido: list[int] = []
    serie_ideal: list[float] = []

    for indice, restante in enumerate(serie_restante):
        dia = inicio + timedelta(days=indice)
        dia_iso = dia.isoformat()
        snap = mapa_snap.get(dia_iso)

        if snap:
            escopo_dia = int(snap.get("total") or total_escopo)
            concluido_dia = int(snap.get("concluido") if snap.get("concluido") is not None else escopo_dia - restante)
        else:
            escopo_dia = total_escopo
            concluido_dia = max(0, escopo_dia - int(restante))

        concluido_dia = min(concluido_dia, escopo_dia)
        serie_escopo.append(escopo_dia)
        serie_concluido.append(concluido_dia)

        if total_dias <= 1:
            serie_ideal.append(float(escopo_dia))
        else:
            dias_decorridos = (dia - inicio).days
            serie_ideal.append(
                round(escopo_dia * dias_decorridos / (total_dias - 1), 2) if escopo_dia else 0.0
            )

    return {
        "labels": labels,
        "serieEscopo": serie_escopo,
        "serieConcluido": serie_concluido,
        "serieIdeal": serie_ideal,
        "periodoCompleto": grafico_bd.get("periodoCompleto", False),
    }


def buscar_burnup(
    proprietario: str = "CEI-UFG",
    numero: int = 1,
    iteracao_id: str | None = None,
) -> dict:
    """Monta payload JSON do burnup para uma iteration (mesmo escopo do burndown)."""
    dados = buscar_burndown(proprietario, numero, iteracao_id)
    if dados.get("erro"):
        return dados

    dados["tipo"] = "burnup"
    dados["grafico"] = _montar_grafico_burnup(dados)
    return dados
