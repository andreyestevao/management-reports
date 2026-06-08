# management-reports

Relatórios e visualizações **agnósticos** para qualquer GitHub Project: kanban, burndown, burnup, gantt e 16 gráficos analíticos. Servidor Python local + páginas HTML incorporáveis (iframe) com tema customizável.

Repositório: https://github.com/andreyestevao/management-reports

## Regras do repositório

Este projeto é **independente de organização, stack ou arquitetura interna**. Ao contribuir ou publicar alterações, siga:

### Agnosticismo

| Regra | Descrição |
|-------|-----------|
| **Sem acoplamento organizacional** | Não documente org, produto ou arquitetura específicos. **Proibido** citar nomes reais de organização ou programa em README, exemplos e valores padrão. |
| **Configuração explícita** | O GitHub Project alvo vem de `GH_PROJECT_OWNER` / `GH_PROJECT_NUMBER` ou de `--proprietario` / `--projeto` — nunca hardcode org ou número no código ou na documentação. |
| **Linguagem genérica** | README, readmes das views e textos visíveis ao usuário devem falar em **GitHub Projects**, iterations e board — não em contexto de um cliente ou programa específico. |
| **Temas neutros** | Presets em `temas/` usam nomes genéricos (`escuro`, `claro`, `transparente`, `institucional`). Cores e identidade visual ficam no CSS customizado de quem incorpora o iframe. |

> Nomes históricos de arquivos (`cei-tokens.css`, `*-cei-dinamico.html`, etc.) são legado interno de paths/URLs — **não** devem ser reintroduzidos em documentação nem em valores padrão de configuração.

### Arquivos sensíveis — nunca versionar

| Categoria | Exemplos | Motivo |
|-----------|----------|--------|
| **Ambiente** | `.env`, `.env.local` | Owner do project, parâmetros locais |
| **Credenciais** | `*.pem`, `*.key`, `credentials.json`, tokens | Segurança |
| **Snapshots do board** | `dados/burndown-historico.json`, `dados/*.json` | Dados reais de iterations e métricas |
| **HTML estático gerado** | `kanban-cei-apps.html`, `kanban-cei-apps-incorporar.html` | Contém títulos e links de issues reais |

**Permitido no Git:** apenas templates vazios ou estruturais, como `dados/burndown-historico.example.json` e `.env.example` (sem valores reais).

### Antes de cada commit

```bash
./scripts/verificar-arquivos-sensiveis.sh --staged
```

O script bloqueia `.env`, snapshots em `dados/`, HTML estático do kanban, credenciais e padrões de token GitHub no diff. O `.gitignore` reforça as mesmas regras — **não conte só com ele**; rode a verificação manualmente.

### Autenticação

- Token e sessão ficam **somente** no `gh` CLI local (`gh auth login`, escopo `read:project`).
- O servidor **não** lê nem expõe tokens nas páginas ou respostas da API.
- Não adicione `GITHUB_TOKEN`, PAT ou secrets em arquivos do repositório.

---

## Requisitos

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (`gh`) autenticado com escopo `read:project`

```bash
gh auth login
gh auth refresh -s read:project
```

## Configuração

Defina o project alvo via variáveis de ambiente ou argumentos do servidor:

```bash
cp .env.example .env
# Edite .env: GH_PROJECT_OWNER e GH_PROJECT_NUMBER
```

| Variável | Descrição |
|----------|-----------|
| `GH_PROJECT_OWNER` | Org ou usuário dono do GitHub Project (**obrigatório**) |
| `GH_PROJECT_NUMBER` | Número do project (padrão `1`) |

Equivalente na CLI: `--proprietario` e `--projeto`. O script `iniciar-kanban-dinamico.sh` carrega `.env` automaticamente se existir.

## Início rápido

```bash
git clone https://github.com/andreyestevao/management-reports.git
cd management-reports
cp .env.example .env   # preencha GH_PROJECT_OWNER
cp dados/burndown-historico.example.json dados/burndown-historico.json  # opcional
./iniciar-kanban-dinamico.sh
```

Abra http://127.0.0.1:8766/kanban-cei-dinamico.html

## Estrutura do monorepo

| Pacote / pasta | Conteúdo |
|----------------|----------|
| **Raiz** | `servidor-kanban-cei.py`, módulos Python (`*_dados.py`), assets compartilhados |
| `kanban/`, `burndown/`, `burnup/`, `gantt/` | Documentação e embed de cada view principal |
| `cfd/`, `cycle-time/`, … (16 pastas) | Documentação de cada gráfico analítico |
| `temas/` | Presets CSS (`escuro`, `claro`, `transparente`, `institucional`) |
| `dados/` | Snapshots locais (gitignored — ver `*.example.json`) |
| `scripts/` | Utilitários (`verificar-arquivos-sensiveis.sh`) |

## Views principais

| App | URL |
|-----|-----|
| Kanban | `/kanban-cei-dinamico.html` |
| Burndown | `/burndown-cei-dinamico.html` |
| Burnup | `/burnup-cei-dinamico.html` |
| Gantt | `/gantt-cei-dinamico.html` |

## Gráficos analíticos

16 views em `*-cei-dinamico.html` (CFD, cycle time, throughput, Monte Carlo, etc.). Cada pasta `{app}/readme.md` descreve iframe, query string e tokens de tema.

## API REST

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/kanban` | Board agrupado por coluna |
| `GET /api/burndown?iteracao=` | Burndown da iteration |
| `GET /api/burnup?iteracao=` | Burnup da iteration |
| `GET /api/gantt` | Roadmap / gantt |
| `GET /api/iteracoes?q=&offset=&limit=` | Autocomplete de iterations |
| `GET /api/{grafico}` | Gráficos analíticos |

## Incorporação (iframe)

```html
<iframe
  src="http://127.0.0.1:8766/burnup-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente&iteracao=ID"
  title="Burnup"
  style="width:100%;min-height:720px;border:0"
></iframe>
```

## Scripts utilitários

```bash
./gerar-kanban-cei.sh                    # HTML estático local (gitignored — ver regras acima)
python3 gerar-paginas-graficos-cei.py    # Regenera HTML + readme dos gráficos
./scripts/verificar-arquivos-sensiveis.sh --staged   # Obrigatório antes de commit
```

## Licença

Ajuste conforme a política da sua organização.
