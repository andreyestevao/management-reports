# Burnup CEI — incorporação e tema

Gráfico de burnup por iteration: escopo total, conclusão acumulada e linha ideal de entrega. Compartilha dados e snapshots com o burndown.

## Página

| Arquivo | Descrição |
|---------|-----------|
| `burnup-cei-dinamico.html` | Burnup dinâmico via `/api/burnup` |

URL local: http://127.0.0.1:8766/burnup-cei-dinamico.html

Iteration específica: `?iteracao=<id>` (compatível com demais parâmetros de tema).

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais |
| `cei-compartilhado.css` | Botões, badges, embed |
| `burnup-cei.css` | Estende `burndown-cei.css` |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets prontos |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/burnup-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente&iteracao=a5dfcb98"
  title="Burnup CEI"
  style="width:100%;min-height:720px;border:0"
></iframe>
```

## Gráfico

| Série | Significado |
|-------|-------------|
| **Escopo** | Total de itens no escopo da iteration (pode subir se o escopo crescer) |
| **Concluído** | Itens entregues acumulados ao longo dos dias |
| **Ideal** | Ritmo linear de entrega até o fim da iteration |

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
| `cor-grafico-concluido` | `198754` | Linha “Concluído” |
| `cor-grafico-escopo` | `6c757d` | Linha “Escopo” |
| `cor-grafico-ideal-burnup` | `003366` | Linha “Ideal” |
| `origem` | `https://portal.exemplo` | Origens no `postMessage` |

Exemplo:

```
/burnup-cei-dinamico.html?iteracao=a5dfcb98&tema=escuro&embed=1&sem-rodape=1
```

## Folha CSS customizada

```css
:root {
  --cor-grafico-escopo: #adb5bd;
  --cor-grafico-concluido: #198754;
  --cor-grafico-concluido-preenchimento: rgba(25, 135, 84, 0.15);
  --cor-grafico-ideal-burnup: rgba(0, 51, 102, 0.55);
}
.painel-grafico-burnup { box-shadow: none; }
```

O gráfico Chart.js relê os tokens ao evento `cei-tema-alterado`.

## postMessage

```javascript
iframe.contentWindow.postMessage({
  tipo: 'cei-aplicar-tema',
  tokens: {
    '--cor-grafico-concluido': '#198754',
    '--cor-grafico-escopo': '#6c757d',
    '--cor-fundo': 'transparent',
  },
  corpo: { adicionar: ['ocultar-rodape'] },
}, 'http://127.0.0.1:8766');
```

## Tokens mais usados no Burnup

| Token | Padrão |
|-------|--------|
| `--cor-grafico-escopo` | `#6c757d` |
| `--cor-grafico-concluido` | `#198754` |
| `--cor-grafico-concluido-preenchimento` | `rgba(25, 135, 84, 0.12)` |
| `--cor-grafico-ideal-burnup` | `rgba(0, 51, 102, 0.45)` |
| `--cor-positivo` | `#198754` |
| `--cor-primaria` | `#003366` |

## Classes para override

`.barra-controles`, `.painel-metricas`, `.painel-velocidade`, `.painel-grafico-burnup`, `.grafico-container`, `.lista-escopo`

## Dados

Mesmo histórico do burndown: `dados/burndown-historico.json` (snapshots diários alimentam escopo e concluído).

## Servidor

```bash
git clone https://github.com/andreyestevao/management-reports.git
cd management-reports
python3 servidor-kanban-cei.py
```

API: `GET /api/burnup?iteracao=<id>`, `GET /api/iteracoes?q=&offset=0&limit=10`

## Segurança

`?css=` e CSS via `postMessage` só aceitam URLs da mesma origem do servidor.
