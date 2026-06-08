# Gantt CEI — incorporação e tema

Roadmap cronológico por iterations: barras de iteration, previsto (Due Date), conclusão real e atraso.

## Página

| Arquivo | Descrição |
|---------|-----------|
| `gantt-cei-dinamico.html` | Gantt dinâmico via `/api/gantt` |

URL local: http://127.0.0.1:8766/gantt-cei-dinamico.html

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais |
| `cei-compartilhado.css` | Botões, badges, embed |
| `gantt-cei.css` | Timeline, barras, legenda |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets prontos |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/gantt-cei-dinamico.html?embed=1&sem-rodape=1&fundo=transparente"
  title="Gantt CEI"
  style="width:100%;min-height:600px;border:0"
></iframe>
```

## Query string

| Parâmetro | Exemplo | Efeito |
|-----------|---------|--------|
| `tema` | `escuro` | Preset em `temas/` |
| `css` | `/temas/exemplo-portal.css` | Folha custom |
| `embed` | `1` | Layout incorporado |
| `sem-rodape` | `1` | Oculta rodapé |
| `sem-controles` | `1` | Oculta filtros, legenda e resumo |
| `fundo` | `transparente` | Fundo transparente |
| `cor-gantt-hoje` | `fd7e14` | Linha “Hoje” |
| `cor-gantt-barra-previsto-fundo` | `rgba(13,110,253,0.5)` | Barra prevista |
| `cor-gantt-barra-real-fundo` | `rgba(25,135,84,0.7)` | Conclusão real |
| `origem` | `https://portal.exemplo` | Origens no `postMessage` |

Exemplo:

```
/gantt-cei-dinamico.html?tema=transparente&embed=1&sem-rodape=1&cor-gantt-hoje=ff6600
```

## Folha CSS customizada

```css
:root {
  --cor-gantt-cabecalho-fundo: #f8f9fa;
  --cor-gantt-barra-previsto-fundo: rgba(0, 102, 51, 0.5);
  --cor-gantt-barra-real-fundo: rgba(0, 102, 51, 0.85);
  --cor-gantt-barra-atrasado-fundo: rgba(220, 53, 69, 0.5);
  --cor-gantt-hoje: #ff6600;
  --cor-fundo: transparent;
}
.gantt-scroll { max-height: 70vh; }
```

## postMessage

```javascript
iframe.contentWindow.postMessage({
  tipo: 'cei-aplicar-tema',
  tokens: {
    '--cor-gantt-hoje': '#ff6600',
    '--cor-gantt-barra-previsto-fundo': 'rgba(13, 110, 253, 0.4)',
    '--cor-fundo': 'transparent',
  },
  corpo: { adicionar: ['ocultar-rodape', 'ocultar-controles'] },
}, 'http://127.0.0.1:8766');
```

API: `window.ceiTema.lerToken('--cor-gantt-hoje')`.

## Tokens mais usados no Gantt

| Token | Padrão |
|-------|--------|
| `--cor-gantt-cabecalho-fundo` | `#f8f9fa` |
| `--cor-gantt-linha-iteracao-fundo` | `#eef3f8` |
| `--cor-gantt-timeline-iteracao-fundo` | `#f8fbff` |
| `--cor-gantt-barra-iteracao-fundo` | `rgba(0, 51, 102, 0.15)` |
| `--cor-gantt-barra-previsto-fundo` | `rgba(13, 110, 253, 0.45)` |
| `--cor-gantt-barra-real-fundo` | `rgba(25, 135, 84, 0.7)` |
| `--cor-gantt-barra-atrasado-fundo` | `rgba(220, 53, 69, 0.45)` |
| `--cor-gantt-hoje` | `#fd7e14` |

## Classes para override

`.gantt-container`, `.gantt-grid`, `.gantt-etiqueta`, `.gantt-etiqueta-iteracao`, `.gantt-timeline`, `.gantt-barra`, `.gantt-barra-previsto`, `.gantt-barra-real`, `.gantt-barra-atrasado`, `.gantt-linha-hoje`, `.legenda-gantt`, `.painel-resumo`

## Legenda

| Amostra | Significado |
|---------|-------------|
| Iteration | Período da sprint/iteration |
| Previsto | Início da iteration → Due Date |
| Conclusão real | Data de fechamento da issue |
| Atrasado | Conclusão após Due Date |

## Servidor

```bash
cd /home/andrey/Documentos/CEI/gestao
python3 servidor-kanban-cei.py
```

API: `GET /api/gantt`

## Segurança

`?css=` e CSS via `postMessage` só aceitam URLs da mesma origem do servidor.
