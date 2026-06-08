# Burndown CEI — incorporação e tema

Gráfico de burndown por iteration do GitHub Projects, com métricas de velocidade e escopo de itens.

## Página

| Arquivo | Descrição |
|---------|-----------|
| `burndown-cei-dinamico.html` | Burndown dinâmico via `/api/burndown` |

URL local: http://127.0.0.1:8766/burndown-cei-dinamico.html

Iteration específica: `?iteracao=<id>` (compatível com demais parâmetros de tema).

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais |
| `cei-compartilhado.css` | Botões, badges, embed |
| `burndown-cei.css` | Métricas, autocomplete, gráfico, tabela |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets prontos |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/burndown-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente&iteracao=a5dfcb98"
  title="Burndown CEI"
  style="width:100%;min-height:720px;border:0"
></iframe>
```

## Query string

| Parâmetro | Exemplo | Efeito |
|-----------|---------|--------|
| `iteracao` | `a5dfcb98` | Iteration inicial |
| `tema` | `escuro` | Preset em `temas/` |
| `css` | `/temas/exemplo-portal.css` | Folha custom |
| `embed` | `1` | Layout incorporado |
| `sem-rodape` | `1` | Oculta rodapé |
| `sem-controles` | `1` | Oculta iteration + Atualizar |
| `fundo` | `transparente` | Fundo transparente |
| `cor-grafico-real` | `003366` | Linha “Real” do Chart.js |
| `cor-grafico-ideal` | `6c757d` | Linha “Ideal” |
| `origem` | `https://portal.exemplo` | Origens no `postMessage` |

Exemplo:

```
/burndown-cei-dinamico.html?iteracao=a5dfcb98&tema=escuro&embed=1&sem-rodape=1
```

## Folha CSS customizada

```css
:root {
  --cor-primaria: #003366;
  --cor-grafico-real: #003366;
  --cor-grafico-real-preenchimento: rgba(0, 51, 102, 0.12);
  --cor-grafico-ideal: #adb5bd;
  --cor-positivo: #198754;
  --cor-negativo: #dc3545;
}
.painel-grafico { box-shadow: none; }
```

O gráfico Chart.js relê os tokens ao evento `cei-tema-alterado`.

## postMessage

```javascript
iframe.contentWindow.postMessage({
  tipo: 'cei-aplicar-tema',
  tokens: {
    '--cor-grafico-real': '#4da3ff',
    '--cor-grafico-ideal': '#6c757d',
    '--cor-fundo': 'transparent',
  },
  corpo: { adicionar: ['ocultar-rodape'] },
}, 'http://127.0.0.1:8766');
```

API: `window.ceiTema.lerToken('--cor-grafico-real')`.

## Tokens mais usados no Burndown

| Token | Padrão |
|-------|--------|
| `--cor-grafico-ideal` | `#6c757d` |
| `--cor-grafico-real` | `#003366` |
| `--cor-grafico-real-preenchimento` | `rgba(0, 51, 102, 0.08)` |
| `--cor-positivo` | `#198754` |
| `--cor-negativo` | `#dc3545` |
| `--cor-neutro` | `#fd7e14` |
| `--cor-info` | `#0d6efd` |
| `--cor-badge-ativa-fundo` | `#cfe2ff` |

## Classes para override

`.barra-controles`, `.autocomplete-iteracao`, `.painel-metricas`, `.metrica`, `.painel-velocidade`, `.painel-grafico`, `.grafico-container`, `.lista-escopo`, `.badge-prazo-*`

## Dados

Snapshots diários: `dados/burndown-historico.json`

## Servidor

```bash
git clone https://github.com/andreyestevao/management-reports.git
cd management-reports
python3 servidor-kanban-cei.py
```

API: `GET /api/burndown?iteracao=<id>`, `GET /api/iteracoes?q=&offset=0&limit=10`

## Segurança

`?css=` e CSS via `postMessage` só aceitam URLs da mesma origem do servidor.
