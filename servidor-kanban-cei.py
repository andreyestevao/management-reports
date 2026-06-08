#!/usr/bin/env python3
"""
Servidor management-reports — kanban, burndown e gantt dinâmicos (GitHub Projects).

Endpoints:
  GET /api/kanban
  GET /api/burndown?iteracao=<id>
  GET /api/burnup?iteracao=<id>
  GET /api/gantt?consulta=&situacao=
  GET /api/iteracoes?q=&offset=0&limit=10
  GET /kanban-cei-dinamico.html
  GET /burndown-cei-dinamico.html
  GET /burnup-cei-dinamico.html
  GET /gantt-cei-dinamico.html

Requer gh autenticado (read:project). Token permanece no servidor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from burnup_cei_dados import buscar_burnup
from burndown_cei_dados import buscar_burndown, buscar_iteracoes
from config_projeto import ler_numero_projeto, ler_proprietario
from gantt_cei_dados import buscar_gantt
from graficos_cei_dados import ROTAS_GRAFICOS
from kanban_cei_dados import buscar_kanban

DIR_BASE = Path(__file__).resolve().parent


class ManipuladorBoard(SimpleHTTPRequestHandler):
    """Serve arquivos estáticos e APIs JSON do board."""

    proprietario: str
    numero_projeto: int

    def do_GET(self) -> None:
        caminho = urlparse(self.path).path
        consulta = parse_qs(urlparse(self.path).query)

        if caminho == "/api/kanban":
            self._responder_json(lambda: buscar_kanban(self.proprietario, self.numero_projeto))
            return

        if caminho == "/api/burndown":
            iteracao_id = (consulta.get("iteracao") or [None])[0]
            self._responder_json(
                lambda: buscar_burndown(self.proprietario, self.numero_projeto, iteracao_id)
            )
            return

        if caminho == "/api/burnup":
            iteracao_id = (consulta.get("iteracao") or [None])[0]
            self._responder_json(
                lambda: buscar_burnup(self.proprietario, self.numero_projeto, iteracao_id)
            )
            return

        if caminho == "/api/iteracoes":
            consulta_texto = (consulta.get("q") or [""])[0]
            try:
                offset = int((consulta.get("offset") or ["0"])[0])
            except ValueError:
                offset = 0
            try:
                limit = int((consulta.get("limit") or ["10"])[0])
            except ValueError:
                limit = 10
            self._responder_json(
                lambda: buscar_iteracoes(
                    self.proprietario,
                    self.numero_projeto,
                    consulta_texto,
                    offset,
                    limit,
                )
            )
            return

        if caminho == "/api/gantt":
            consulta_texto = (consulta.get("consulta") or consulta.get("q") or [""])[0]
            situacao = (consulta.get("situacao") or [None])[0]
            self._responder_json(
                lambda: buscar_gantt(
                    self.proprietario,
                    self.numero_projeto,
                    consulta_texto,
                    situacao,
                )
            )
            return

        if caminho.startswith("/api/"):
            rota_grafico = caminho[len("/api/") :]
            if rota_grafico in ROTAS_GRAFICOS:
                iteracao_id = (consulta.get("iteracao") or [None])[0]
                funcao = ROTAS_GRAFICOS[rota_grafico]
                self._responder_json(
                    lambda f=funcao, i=iteracao_id: f(
                        self.proprietario,
                        self.numero_projeto,
                        i,
                    )
                )
                return

        if caminho in ("/", ""):
            self.path = "/kanban-cei-dinamico.html"

        super().do_GET()

    def _responder_json(self, fabrica_payload) -> None:
        try:
            payload = fabrica_payload()
            if payload.get("erro"):
                corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(404)
            else:
                corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        except subprocess.CalledProcessError as erro:
            mensagem = {
                "erro": "Falha ao consultar GitHub via gh CLI",
                "detalhe": (erro.stderr or str(erro)).strip(),
            }
            corpo = json.dumps(mensagem, ensure_ascii=False).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

    def log_message(self, formato: str, *args) -> None:
        sys.stderr.write(
            "%s - [%s] %s\n"
            % (self.address_string(), self.log_date_time_string(), formato % args)
        )


def criar_manipulador(proprietario: str, numero_projeto: int):
    """Factory do handler HTTP com config do project."""

    class Manipulador(ManipuladorBoard):
        def __init__(self, *args, **kwargs):
            self.proprietario = proprietario
            self.numero_projeto = numero_projeto
            super().__init__(*args, directory=str(DIR_BASE), **kwargs)

    return Manipulador


def main() -> int:
    parser = argparse.ArgumentParser(description="Servidor management-reports (kanban, burndown, burnup, gantt e gráficos)")
    parser.add_argument("--porta", type=int, default=8766, help="Porta HTTP (padrão: 8766)")
    parser.add_argument("--proprietario", default=None, help="Owner/org do GitHub Project (ou GH_PROJECT_OWNER)")
    parser.add_argument("--projeto", type=int, default=None, help="Número do project (ou GH_PROJECT_NUMBER, padrão 1)")
    args = parser.parse_args()

    proprietario = ler_proprietario(args.proprietario)
    numero_projeto = ler_numero_projeto(args.projeto)
    handler = criar_manipulador(proprietario, numero_projeto)
    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), handler)
    base = f"http://127.0.0.1:{args.porta}"
    print(f"Kanban:    {base}/kanban-cei-dinamico.html")
    print(f"Burndown:  {base}/burndown-cei-dinamico.html")
    print(f"Burnup:    {base}/burnup-cei-dinamico.html")
    print(f"Gantt:     {base}/gantt-cei-dinamico.html")
    print(f"Gráficos:  {base}/cfd-cei-dinamico.html  (+ 15 views — ver pastas */readme.md)")
    rotas = ", ".join(sorted(ROTAS_GRAFICOS.keys()))
    print(f"API:       {base}/api/kanban | burndown | burnup | gantt | iteracoes | {rotas}")
    print("Ctrl+C para encerrar")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
