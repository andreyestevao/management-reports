# Carga por responsável CEI — incorporação e tema

Itens abertos por pessoa na iteration.

## Página

| Arquivo | Descrição |
|---------|-----------|
| `carga-responsavel-cei-dinamico.html` | Carga por responsável dinâmico via `/api/carga-responsavel` |

URL local: http://127.0.0.1:8766/carga-responsavel-cei-dinamico.html

Iteration específica: `?iteracao=<id>` (compatível com demais parâmetros de tema).

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais |
| `cei-compartilhado.css` | Botões, badges, embed |
| `cei-graficos.css` | Layout compartilhado dos gráficos |
| `cei-grafico-app.js` | App Chart.js + autocomplete |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets prontos |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/carga-responsavel-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente&iteracao=a5dfcb98"
  title="Carga por responsável CEI"
  style="width:100%;min-height:560px;border:0"
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
| `sem-controles` | `1` | Oculta controles |
| `fundo` | `transparente` | Fundo transparente |
| `origem` | `https://portal.exemplo` | Origens no `postMessage` |

## postMessage

```javascript
iframe.contentWindow.postMessage({
  tipo: 'cei-aplicar-tema',
  tokens: { '--cor-fundo': 'transparent' },
  corpo: { adicionar: ['ocultar-rodape'] },
}, 'http://127.0.0.1:8766');
```

O gráfico relê tokens ao evento `cei-tema-alterado`.
