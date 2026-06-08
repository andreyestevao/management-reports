# management-reports

Monorepo de relatórios e visualizações para GitHub Projects (CEI Apps - UFG): kanban, burndown, burnup, gantt e 16 gráficos analíticos. Servidor Python local + páginas HTML incorporáveis (iframe) com tema customizável.

Repositório: https://github.com/andreyestevao/management-reports

## Requisitos

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (`gh`) autenticado com escopo `read:project`

```bash
gh auth login
gh auth refresh -s read:project
```

## Início rápido

```bash
git clone https://github.com/andreyestevao/management-reports.git
cd management-reports
cp dados/burndown-historico.example.json dados/burndown-historico.json  # opcional
./iniciar-kanban-dinamico.sh
# ou: python3 servidor-kanban-cei.py
```

Abra http://127.0.0.1:8766/kanban-cei-dinamico.html

Parâmetros do servidor: `--porta`, `--proprietario` (padrão `CEI-UFG`), `--projeto` (padrão `1`).

## Estrutura do monorepo

| Pacote / pasta | Conteúdo |
|----------------|----------|
| **Raiz** | `servidor-kanban-cei.py`, módulos Python (`*_cei_dados.py`), assets compartilhados (`cei-tokens.css`, `cei-tema.js`, …) |
| `kanban/`, `burndown/`, `burnup/`, `gantt/` | Documentação e embed de cada view principal |
| `cfd/`, `cycle-time/`, … (16 pastas) | Documentação de cada gráfico analítico |
| `temas/` | Presets CSS (`escuro`, `claro`, `transparente`, `cei-ui`) |
| `dados/` | Snapshots locais (`burndown-historico.json`, gitignored — ver `.example`) |

## Views principais

| App | URL |
|-----|-----|
| Kanban | `/kanban-cei-dinamico.html` |
| Burndown | `/burndown-cei-dinamico.html` |
| Burnup | `/burnup-cei-dinamico.html` |
| Gantt | `/gantt-cei-dinamico.html` |

## Gráficos analíticos

`/cfd-cei-dinamico.html`, `/cycle-time-cei-dinamico.html`, `/throughput-cei-dinamico.html`, `/monte-carlo-cei-dinamico.html`, `/desvio-due-date-cei-dinamico.html`, `/scope-creep-cei-dinamico.html`, `/taxa-conclusao-cei-dinamico.html`, `/carga-responsavel-cei-dinamico.html`, `/wip-pessoa-cei-dinamico.html`, `/mapa-repositorio-cei-dinamico.html`, `/release-timeline-cei-dinamico.html`, `/aging-wip-cei-dinamico.html`, `/status-portfolio-cei-dinamico.html`, `/heatmap-atividade-cei-dinamico.html`, `/iteration-health-cei-dinamico.html`, `/comparativo-iterations-cei-dinamico.html`

Cada pasta `{app}/readme.md` descreve iframe, query string e tokens de tema.

## API REST

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/kanban` | Board agrupado por coluna |
| `GET /api/burndown?iteracao=` | Burndown da iteration |
| `GET /api/burnup?iteracao=` | Burnup da iteration |
| `GET /api/gantt` | Roadmap / gantt |
| `GET /api/iteracoes?q=&offset=&limit=` | Autocomplete de iterations |
| `GET /api/{grafico}` | Gráficos (`cfd`, `cycle-time`, …) |

## Incorporação (iframe)

```html
<iframe
  src="http://127.0.0.1:8766/burnup-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente&iteracao=ID"
  title="Burnup CEI"
  style="width:100%;min-height:720px;border:0"
></iframe>
```

## Scripts utilitários

```bash
./gerar-kanban-cei.sh              # HTML estático do kanban
python3 gerar-paginas-graficos-cei.py   # Regenera HTML + readme dos gráficos
```

## Dados locais

Na primeira execução, copie o exemplo se quiser iniciar vazio:

```bash
cp dados/burndown-historico.example.json dados/burndown-historico.json
```

O servidor atualiza snapshots automaticamente para iterations ativas.

## Licença

Uso interno / CEI-UFG. Ajuste conforme política da organização.
