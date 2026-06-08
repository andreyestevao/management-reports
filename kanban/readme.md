# Kanban CEI — incorporação e tema

Visualização do board GitHub Projects (colunas e cartões), servida pelo servidor local em `Documentos/CEI/gestao/`.

## Páginas

| Arquivo | Descrição |
|---------|-----------|
| `kanban-cei-dinamico.html` | Kanban ao vivo via `/api/kanban` (refresh 5 min) |
| `kanban-cei-apps.html` | Snapshot estático (`gerar-kanban-cei.py`) |
| `kanban-cei-apps-incorporar.html` | Snapshot estático, layout embed |

URLs locais (servidor na porta **8766**):

- http://127.0.0.1:8766/kanban-cei-dinamico.html
- http://127.0.0.1:8766/kanban-cei-apps-incorporar.html

## Folhas de estilo

| Arquivo | Papel |
|---------|-------|
| `cei-tokens.css` | Tokens globais (`:root`) |
| `cei-compartilhado.css` | Botões, embed, rodapé |
| `kanban-cei.css` | Grade, colunas, cartões |
| `cei-tema.js` | Presets, query string, `postMessage` |
| `temas/*.css` | Presets (`escuro`, `claro`, `transparente`, `cei-ui`) |

## Iframe

```html
<iframe
  src="http://127.0.0.1:8766/kanban-cei-dinamico.html?embed=1&sem-rodape=1&sem-controles=1&fundo=transparente"
  title="Kanban CEI"
  style="width:100%;min-height:420px;border:0"
></iframe>
```

## Query string

| Parâmetro | Exemplo | Efeito |
|-----------|---------|--------|
| `tema` | `escuro`, `claro`, `transparente`, `cei-ui` | Preset em `temas/` |
| `css` | `/temas/exemplo-portal.css` | Folha custom (mesma origem) |
| `embed` | `1` | Padding reduzido |
| `sem-rodape` | `1` | Oculta rodapé |
| `sem-controles` | `1` | Oculta barra “Atualizar agora” |
| `fundo` | `transparente` | Fundo transparente |
| `cor-primaria` | `006633` | Override de token |
| `largura-coluna` | `280px` | Largura das colunas |
| `origem` | `https://portal.exemplo` | Origens permitidas no `postMessage` |

Exemplo:

```
/kanban-cei-dinamico.html?tema=cei-ui&css=/temas/exemplo-portal.css&embed=1&sem-rodape=1
```

## Folha CSS customizada

```css
:root {
  --cor-primaria: #006633;
  --cor-fundo: transparent;
  --largura-coluna: 260px;
  --cor-coluna-fundo: #f0f0f0;
}
.cartao { border-left-width: 4px; }
```

## postMessage

```javascript
iframe.contentWindow.postMessage({
  tipo: 'cei-aplicar-tema',
  tokens: {
    '--cor-primaria': '#003366',
    '--cor-fundo': 'transparent',
    '--largura-coluna': '280px',
  },
  corpo: { adicionar: ['ocultar-rodape', 'ocultar-controles'] },
}, 'http://127.0.0.1:8766');
```

Eventos: `cei-tema-pronto`, `cei-tema-alterado`. API: `window.ceiTema.lerToken('--cor-primaria')`.

## Tokens mais usados no Kanban

| Token | Padrão |
|-------|--------|
| `--cor-primaria` | `#003366` |
| `--cor-fundo` | `#f5f7fa` |
| `--cor-painel` | `#ffffff` |
| `--cor-coluna-fundo` | `#e9ecef` |
| `--largura-coluna` | `300px` |
| `--espacamento` | `12px` |
| `--raio-borda` | `8px` |
| `--cor-link` | `var(--cor-primaria)` |

## Classes para override

`.pagina`, `.grade-kanban`, `.coluna`, `.coluna-cabecalho`, `.coluna-contagem`, `.cartao`, `.cartao-titulo`, `.barra-acoes`, `.rodape`

Colunas usam `--cor-coluna` inline (cor vinda do GitHub Projects).

## Servidor

```bash
cd /home/andrey/Documentos/CEI/gestao
python3 servidor-kanban-cei.py
```

Regenerar estático: `python3 gerar-kanban-cei.py`

## Segurança

`?css=` e CSS via `postMessage` só aceitam URLs da mesma origem do servidor.
