/**
 * Tema incorporável — Kanban, Burndown e Gantt CEI.
 * Query: ?tema=escuro&css=/temas/meu.css&cor-primaria=006633&embed=1&sem-rodape=1&fundo=transparente
 * postMessage: { tipo: 'cei-aplicar-tema', tokens: { '--cor-primaria': '#006633' }, corpo: { adicionar: ['ocultar-rodape'] } }
 */
(function () {
  'use strict';

  const PRESETS = {
    cei: null,
    escuro: 'temas/escuro.css',
    claro: 'temas/claro.css',
    transparente: 'temas/transparente.css',
    'cei-ui': 'temas/cei-ui.css',
  };

  /** Parâmetros de URL → variáveis CSS (--cor-primaria, etc.) */
  const PARAM_TOKEN = {
    'cor-primaria': '--cor-primaria',
    'cor-fundo': '--cor-fundo',
    'cor-painel': '--cor-painel',
    'cor-texto': '--cor-texto',
    'cor-texto-suave': '--cor-texto-suave',
    'cor-link': '--cor-link',
    'cor-botao-texto': '--cor-botao-texto',
    'cor-borda': '--cor-borda',
    'cor-input-borda': '--cor-input-borda',
    'raio-borda': '--raio-borda',
    'espacamento': '--espacamento',
    'padding-pagina': '--padding-pagina',
    'fonte-base': '--fonte-base',
    'largura-coluna': '--largura-coluna',
    'cor-coluna-fundo': '--cor-coluna-fundo',
    'cor-positivo': '--cor-positivo',
    'cor-negativo': '--cor-negativo',
    'cor-neutro': '--cor-neutro',
    'cor-info': '--cor-info',
    'cor-grafico-ideal': '--cor-grafico-ideal',
    'cor-grafico-real': '--cor-grafico-real',
    'cor-grafico-real-preenchimento': '--cor-grafico-real-preenchimento',
    'cor-grafico-escopo': '--cor-grafico-escopo',
    'cor-grafico-concluido': '--cor-grafico-concluido',
    'cor-grafico-concluido-preenchimento': '--cor-grafico-concluido-preenchimento',
    'cor-grafico-ideal-burnup': '--cor-grafico-ideal-burnup',
    'cor-gantt-hoje': '--cor-gantt-hoje',
    'cor-gantt-barra-previsto-fundo': '--cor-gantt-barra-previsto-fundo',
    'cor-gantt-barra-real-fundo': '--cor-gantt-barra-real-fundo',
    'cor-gantt-barra-atrasado-fundo': '--cor-gantt-barra-atrasado-fundo',
  };

  function normalizarValor(valor) {
    if (valor == null || valor === '') return null;
    const v = decodeURIComponent(String(valor)).trim();
    if (/^[0-9a-fA-F]{3,8}$/.test(v)) return `#${v}`;
    return v;
  }

  function aplicarTokens(tokens) {
    if (!tokens || typeof tokens !== 'object') return;
    const root = document.documentElement;
    Object.entries(tokens).forEach(([chave, valor]) => {
      if (valor == null || valor === '') return;
      const nome = chave.startsWith('--') ? chave : (PARAM_TOKEN[chave] || `--${chave}`);
      root.style.setProperty(nome, String(valor));
    });
    document.dispatchEvent(new CustomEvent('cei-tema-alterado'));
  }

  function urlCssPermitida(referencia) {
    try {
      const url = new URL(referencia, location.href);
      if (url.protocol !== 'http:' && url.protocol !== 'https:' && url.protocol !== '') return null;
      if (url.origin !== location.origin) return null;
      if (url.pathname.includes('..')) return null;
      return url.pathname + url.search;
    } catch {
      return null;
    }
  }

  function carregarStylesheet(caminho) {
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = caminho;
      link.dataset.ceiTema = '1';
      link.onload = () => resolve(link);
      link.onerror = () => reject(new Error(caminho));
      document.head.appendChild(link);
    });
  }

  function lerToken(nome) {
    const varNome = nome.startsWith('--') ? nome : `--${nome}`;
    return getComputedStyle(document.documentElement).getPropertyValue(varNome).trim();
  }

  function origemPermitida(event, params) {
    if (event.origin === location.origin) return true;
    const lista = (params.get('origem') || '')
      .split(',')
      .map((o) => o.trim())
      .filter(Boolean);
    return lista.includes(event.origin);
  }

  function aplicarOpcoesEmbed(params) {
    const body = document.body;
    const pagina = document.querySelector('.pagina');

    if (params.get('embed') === '1' || params.get('embed') === 'true') {
      pagina?.classList.add('pagina--incorporar');
    }
    if (params.get('sem-rodape') === '1' || params.get('sem-rodape') === 'true') {
      body.classList.add('ocultar-rodape');
    }
    if (params.get('sem-controles') === '1' || params.get('sem-controles') === 'true') {
      body.classList.add('ocultar-controles');
    }

    const fundo = params.get('fundo');
    if (fundo === 'transparente' || fundo === 'transparent') {
      body.classList.add('fundo-transparente');
      aplicarTokens({ '--cor-fundo': 'transparent' });
    }
  }

  function tokensDaUrl(params) {
    const tokens = {};
    Object.entries(PARAM_TOKEN).forEach(([param, varNome]) => {
      const valor = params.get(param);
      const normalizado = normalizarValor(valor);
      if (normalizado != null) tokens[varNome] = normalizado;
    });
    return tokens;
  }

  async function inicializar() {
    const params = new URLSearchParams(location.search);
    aplicarOpcoesEmbed(params);

    const tema = params.get('tema');
    if (tema && PRESETS[tema]) {
      try {
        await carregarStylesheet(PRESETS[tema]);
      } catch {
        console.warn('[cei-tema] Preset não carregado:', tema);
      }
    }

    const css = params.get('css');
    if (css) {
      const caminho = urlCssPermitida(css);
      if (caminho) {
        try {
          await carregarStylesheet(caminho);
        } catch {
          console.warn('[cei-tema] Folha customizada não carregada:', css);
        }
      }
    }

    aplicarTokens(tokensDaUrl(params));

    const classes = params.get('classes');
    if (classes) {
      classes.split(',').forEach((c) => {
        const nome = c.trim();
        if (nome) document.querySelector('.pagina')?.classList.add(nome);
      });
    }

    window.addEventListener('message', (event) => {
      if (!origemPermitida(event, params)) return;
      const data = event.data;
      if (!data || typeof data !== 'object' || data.tipo !== 'cei-aplicar-tema') return;

      if (data.tokens) aplicarTokens(data.tokens);

      const pagina = document.querySelector('.pagina');
      if (data.classes?.adicionar) data.classes.adicionar.forEach((c) => pagina?.classList.add(c));
      if (data.classes?.remover) data.classes.remover.forEach((c) => pagina?.classList.remove(c));

      const body = document.body;
      if (data.corpo?.adicionar) data.corpo.adicionar.forEach((c) => body.classList.add(c));
      if (data.corpo?.remover) data.corpo.remover.forEach((c) => body.classList.remove(c));

      if (data.css) {
        const caminho = urlCssPermitida(data.css);
        if (caminho) carregarStylesheet(caminho).catch(() => {});
      }
    });

    document.dispatchEvent(new CustomEvent('cei-tema-pronto'));
  }

  window.ceiTema = {
    aplicarTokens,
    lerToken,
    presets: PRESETS,
    paramToken: PARAM_TOKEN,
  };

  /** Evita parse de HTML 404 quando a API não existe ou o servidor está desatualizado. */
  async function lerRespostaJson(resposta) {
    const tipo = (resposta.headers.get('content-type') || '').toLowerCase();
    if (!tipo.includes('application/json')) {
      const dica = resposta.status === 404
        ? 'Rota da API não encontrada — reinicie o servidor: python3 servidor-kanban-cei.py'
        : `Resposta inválida (HTTP ${resposta.status}). Abra a página via http://127.0.0.1:8766/, não como arquivo local.`;
      throw new Error(dica);
    }
    return resposta.json();
  }

  window.ceiApi = { lerRespostaJson };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializar);
  } else {
    inicializar();
  }
})();
