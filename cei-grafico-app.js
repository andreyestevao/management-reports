/**
 * App genérico para páginas de gráfico CEI (Chart.js + tema + embed).
 * Configurar via window.CEI_GRAFICO_CONFIG antes de carregar este script.
 */
(function () {
  'use strict';

  const cfg = window.CEI_GRAFICO_CONFIG || {};
  const POR_PAGINA = 10;
  const CORES_PADRAO = ['#003366', '#198754', '#fd7e14', '#dc3545', '#0d6efd', '#6c757d', '#6610f2', '#20c997'];

  const inputIteracao = document.getElementById('busca-iteracao');
  const listaSugestoes = document.getElementById('lista-sugestoes-iteracao');
  const autocompleteEl = document.getElementById('autocomplete-iteracao');
  const barraControles = document.querySelector('.barra-controles');
  const btnAtualizar = document.getElementById('btn-atualizar');
  const statusEl = document.getElementById('status');
  const areaErro = document.getElementById('area-erro');
  const painelMetricas = document.getElementById('metricas');
  const painelTexto = document.getElementById('texto-grafico');
  const canvas = document.getElementById('grafico-principal');
  const containerHeatmap = document.getElementById('container-heatmap');

  let grafico = null;
  let iteracaoSelecionadaId = null;
  let offsetSugestoes = 0;
  let consultaSugestoes = '';
  let indiceAtivo = -1;

  function lerToken(nome, fallback) {
    const valor = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
    return valor || fallback;
  }

  function corDataset(ds, indice) {
    return ds.cor || CORES_PADRAO[indice % CORES_PADRAO.length];
  }

  function montarOpcoesChart(tipo, datasets) {
    const indexAxis = datasets.some((d) => d.horizontal) ? 'y' : 'x';
    const base = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: lerToken('--cor-texto', '#212529') } },
      },
      scales: {},
    };

    if (tipo === 'doughnut' || tipo === 'radar') {
      delete base.scales;
      return base;
    }

    if (tipo === 'scatter') {
      base.scales = {
        x: { type: 'time', time: { unit: 'day' }, ticks: { color: lerToken('--cor-texto-suave', '#6c757d') } },
        y: { type: 'time', time: { unit: 'day' }, ticks: { color: lerToken('--cor-texto-suave', '#6c757d') } },
      };
      return base;
    }

    if (tipo === 'timeline') {
      base.indexAxis = 'y';
      base.scales = {
        x: { type: 'time', position: 'top', ticks: { color: lerToken('--cor-texto-suave', '#6c757d') } },
        y: { ticks: { color: lerToken('--cor-texto', '#212529') } },
      };
      return base;
    }

    base.indexAxis = indexAxis;
    base.scales = {
      x: { ticks: { color: lerToken('--cor-texto-suave', '#6c757d') }, stacked: tipo === 'stackedArea' },
      y: { beginAtZero: true, ticks: { color: lerToken('--cor-texto-suave', '#6c757d') }, stacked: tipo === 'stackedArea' },
    };
    return base;
  }

  function datasetsChartJs(graficoPayload) {
    const tipo = graficoPayload.tipo;
    return (graficoPayload.datasets || []).map((ds, i) => {
      const cor = corDataset(ds, i);
      if (tipo === 'scatter') {
        return {
          label: ds.label,
          data: (ds.data || []).map((p) => ({ x: p.x, y: p.y })),
          backgroundColor: cor,
          pointRadius: 5,
        };
      }
      if (tipo === 'timeline') {
        const labels = graficoPayload.labels || [];
        return {
          label: ds.label,
          data: labels.map((rotulo, idx) => {
            const par = (ds.data || [])[idx];
            if (!par || par.length < 2) return null;
            return { x: [par[0], par[1]], y: rotulo };
          }).filter(Boolean),
          backgroundColor: cor,
          borderColor: cor,
          borderWidth: 1,
          barPercentage: 0.55,
        };
      }
      if (tipo === 'doughnut') {
        return {
          label: ds.label,
          data: ds.data,
          backgroundColor: CORES_PADRAO.slice(0, (ds.data || []).length),
        };
      }
      if (tipo === 'radar') {
        return {
          label: ds.label,
          data: ds.data,
          backgroundColor: cor,
          borderColor: cor.replace('0.6', '1') || cor,
          pointBackgroundColor: cor,
        };
      }
      const preencher = ds.preencher || tipo === 'stackedArea';
      return {
        label: ds.label,
        data: ds.data,
        borderColor: cor,
        backgroundColor: preencher ? cor.replace(')', ', 0.35)').replace('rgb', 'rgba') : 'transparent',
        fill: preencher,
        tension: 0.25,
        stack: ds.empilhado ? 'stack' : undefined,
      };
    });
  }

  function rotuloIteracao(it) {
    return (it && (it.titulo || it.title || it.id)) || '';
  }

  function renderizarHeatmap(graficoPayload) {
    const containerCanvas = canvas ? canvas.parentElement : null;
    if (containerCanvas) {
      containerCanvas.hidden = true;
      containerCanvas.classList.add('grafico-container--oculto');
    }
    if (!containerHeatmap) return;
    containerHeatmap.hidden = false;
    containerHeatmap.innerHTML = '';

    const cols = graficoPayload.labelsColunas || [];
    const linhas = graficoPayload.labelsLinhas || [];
    const valores = graficoPayload.valores || [];

    if (!cols.length) {
      const vazio = document.createElement('p');
      vazio.className = 'painel-texto-grafico';
      vazio.textContent = 'Sem dados para exibir no período.';
      containerHeatmap.appendChild(vazio);
      return;
    }
    let max = 1;
    valores.forEach((row) => row.forEach((v) => { if (v > max) max = v; }));

    const tabela = document.createElement('table');
    tabela.className = 'tabela-heatmap';
    const thead = document.createElement('thead');
    const trHead = document.createElement('tr');
    trHead.appendChild(document.createElement('th'));
    cols.forEach((c) => {
      const th = document.createElement('th');
      th.textContent = c;
      trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = document.createElement('tbody');
    linhas.forEach((linha, i) => {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.textContent = linha;
      tr.appendChild(th);
      (valores[i] || []).forEach((v) => {
        const td = document.createElement('td');
        const intensidade = v / max;
        const fundo = `rgba(0, 51, 102, ${0.12 + intensidade * 0.75})`;
        td.innerHTML = `<span class="celula-heatmap" style="background:${fundo}">${v}</span>`;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tabela.appendChild(tbody);
    containerHeatmap.appendChild(tabela);
  }

  function renderizarGrafico(dados) {
    const g = dados.grafico || {};
    if (g.tipo === 'heatmap') {
      if (grafico) { grafico.destroy(); grafico = null; }
      renderizarHeatmap(g);
      return;
    }

    if (containerHeatmap) containerHeatmap.hidden = true;
    if (canvas) {
      canvas.parentElement.hidden = false;
      canvas.parentElement.classList.remove('grafico-container--oculto');
    }
    if (!canvas || typeof Chart === 'undefined') return;

    const tipoChart = g.tipo === 'stackedArea' ? 'line' : (g.tipo === 'timeline' ? 'bar' : g.tipo);
    const config = {
      type: tipoChart,
      data: {
        labels: g.tipo === 'timeline' ? undefined : (g.labels || []),
        datasets: datasetsChartJs(g),
      },
      options: montarOpcoesChart(g.tipo, g.datasets || []),
    };

    if (grafico) grafico.destroy();
    grafico = new Chart(canvas, config);
  }

  function renderizarMetricas(metricas) {
    if (!painelMetricas) return;
    if (!metricas || !metricas.length) {
      painelMetricas.hidden = true;
      return;
    }
    painelMetricas.hidden = false;
    painelMetricas.innerHTML = metricas.map((m) => (
      `<div class="metrica"><div class="metrica-valor">${m.valor}</div><div class="metrica-rotulo">${m.rotulo}</div></div>`
    )).join('');
    painelMetricas.classList.add('painel-metricas-grafico');
  }

  function mostrarErro(msg) {
    if (!areaErro) return;
    areaErro.hidden = false;
    areaErro.textContent = msg;
  }

  function limparErro() {
    if (areaErro) { areaErro.hidden = true; areaErro.textContent = ''; }
  }

  function urlApi() {
    const params = new URLSearchParams(window.location.search);
    params.delete('embed');
    params.delete('sem-rodape');
    params.delete('sem-controles');
    params.delete('fundo');
    params.delete('tema');
    params.delete('css');
    if (cfg.requerIteracao && iteracaoSelecionadaId) {
      params.set('iteracao', iteracaoSelecionadaId);
    }
    const qs = params.toString();
    return `/api/${cfg.api}${qs ? `?${qs}` : ''}`;
  }

  async function carregarDados() {
    limparErro();
    if (statusEl) statusEl.textContent = 'Consultando GitHub…';
    try {
      const resposta = await fetch(urlApi(), { cache: 'no-store' });
      const dados = await window.ceiApi.lerRespostaJson(resposta);
      if (dados.erro) {
        mostrarErro(dados.erro + (dados.detalhe ? `: ${dados.detalhe}` : ''));
        if (statusEl) statusEl.textContent = 'Erro';
        return;
      }

      if (dados.iteracao && inputIteracao && !iteracaoSelecionadaId) {
        iteracaoSelecionadaId = dados.iteracao.id;
        inputIteracao.value = dados.iteracao.titulo || dados.iteracao.title || '';
      }

      document.title = `${cfg.titulo || 'Gráfico'} — ${dados.projeto?.titulo || 'CEI'}`;
      if (statusEl) {
        const rotulo = dados.iteracao?.titulo || dados.iteracao?.title || '';
        statusEl.textContent = rotulo ? `${rotulo} · ${new Date(dados.geradoEm).toLocaleString('pt-BR')}` : new Date(dados.geradoEm).toLocaleString('pt-BR');
      }

      if (painelTexto) {
        if (dados.texto) {
          painelTexto.hidden = false;
          painelTexto.textContent = dados.texto;
        } else {
          painelTexto.hidden = true;
        }
      }

      renderizarMetricas(dados.metricas);
      renderizarGrafico(dados);
    } catch (err) {
      mostrarErro(err.message || String(err));
      if (statusEl) statusEl.textContent = 'Erro';
    }
  }

  /* Autocomplete iteration (quando requerIteracao) */
  async function buscarSugestoes(reset) {
    if (!listaSugestoes) return;
    if (reset) { offsetSugestoes = 0; listaSugestoes.innerHTML = ''; }
    const q = inputIteracao ? inputIteracao.value.trim() : '';
    consultaSugestoes = q;
    const url = `/api/iteracoes?q=${encodeURIComponent(q)}&offset=${offsetSugestoes}&limit=${POR_PAGINA}`;
    const resposta = await fetch(url);
    const dados = await window.ceiApi.lerRespostaJson(resposta);
    if (q !== consultaSugestoes) return;

    (dados.itens || []).forEach((it) => {
      const li = document.createElement('li');
      li.className = 'item-sugestao';
      li.role = 'option';
      li.dataset.id = it.id;
      li.innerHTML = `<div class="item-sugestao-titulo">${rotuloIteracao(it)}</div><div class="item-sugestao-meta">${it.situacao || ''}</div>`;
      li.addEventListener('mousedown', (e) => {
        e.preventDefault();
        selecionarIteracao(it);
      });
      listaSugestoes.appendChild(li);
    });

    if (dados.temMais) {
      const li = document.createElement('li');
      li.className = 'rodape-lista-sugestoes';
      li.textContent = 'Role para mais…';
      listaSugestoes.appendChild(li);
    }
    listaSugestoes.hidden = !(dados.itens || []).length;
    if (inputIteracao) inputIteracao.setAttribute('aria-expanded', String(!(dados.itens || []).length ? false : true));
  }

  function selecionarIteracao(it) {
    iteracaoSelecionadaId = it.id;
    if (inputIteracao) inputIteracao.value = rotuloIteracao(it);
    if (listaSugestoes) { listaSugestoes.hidden = true; listaSugestoes.innerHTML = ''; }
    const p = new URLSearchParams(window.location.search);
    p.set('iteracao', it.id);
    history.replaceState(null, '', `${window.location.pathname}?${p}`);
    carregarDados();
  }

  function iniciarAutocomplete() {
    if (!cfg.requerIteracao) {
      return;
    }
    if (!inputIteracao) {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    iteracaoSelecionadaId = params.get('iteracao');

    inputIteracao.addEventListener('input', () => { indiceAtivo = -1; buscarSugestoes(true); });
    inputIteracao.addEventListener('focus', () => buscarSugestoes(true));
    inputIteracao.addEventListener('blur', () => setTimeout(() => { if (listaSugestoes) listaSugestoes.hidden = true; }, 150));

    if (listaSugestoes) {
      listaSugestoes.addEventListener('scroll', () => {
        if (listaSugestoes.scrollTop + listaSugestoes.clientHeight >= listaSugestoes.scrollHeight - 8) {
          offsetSugestoes += POR_PAGINA;
          buscarSugestoes(false);
        }
      });
    }
  }

  if (btnAtualizar) btnAtualizar.addEventListener('click', carregarDados);
  document.addEventListener('cei-tema-alterado', () => carregarDados());
  document.addEventListener('cei-tema-pronto', carregarDados);

  iniciarAutocomplete();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', carregarDados);
  } else {
    carregarDados();
  }
})();
