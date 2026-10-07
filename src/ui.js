// Hot-seat arayüzü. Oyun kuralları src/engine.js'te; burada yalnızca gösterim ve olay bağlama var.
import { createMatch, protect, steal, teamRating, result } from './engine.js';

const PROTECT_COUNT = 3;
const STEALS_PER_SIDE = 3;
const SEARCH_LIMIT = 60;

const TYPES = [
  { type: 'club', label: 'Kulüp' },
  { type: 'league', label: 'Lig' },
  { type: 'nation', label: 'Ülke' },
];
const TYPE_LABEL = Object.fromEntries(TYPES.map((t) => [t.type, t.label]));

// Saha üzerinde satır yüksekliği (yüzde) ve satır içi yatay sıra.
const LINE_Y = { ATT: 18, AM: 38, MID: 55, DEF: 72, GK: 90 };
const LINE_OF = {
  GK: 'GK',
  LB: 'DEF', CB: 'DEF', RB: 'DEF', LWB: 'DEF', RWB: 'DEF',
  CDM: 'MID', CM: 'MID', LM: 'MID', RM: 'MID',
  CAM: 'AM',
  LW: 'ATT', RW: 'ATT', ST: 'ATT', CF: 'ATT', LF: 'ATT', RF: 'ATT',
};
const WIDTH_RANK = { LB: 0, LWB: 0, LM: 0, LW: 0, LF: 0, RB: 2, RWB: 2, RM: 2, RW: 2, RF: 2 };

const app = document.getElementById('app');
const restartBtn = document.getElementById('restart');

const data = { players: [], categories: {}, formations: [] };
const ui = {
  view: 'setup', // setup | lineup | protect | steal | done
  type: 'club',
  query: '',
  picked: [], // [{ type, value }]
  formationId: null,
  setupError: '',
  match: null,
  selected: [], // koruma aşamasında seçili id'ler
  target: null, // takas: rakipten alınacak id
  give: null, // takas: karşılığında verilecek id
  message: '',
};

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c]);
}

// Türkçe büyük/küçük harf ve aksan farkını gözetmeden arama için.
function fold(s) {
  return String(s).toLocaleLowerCase('tr').normalize('NFD').replace(/\p{M}/gu, '');
}

function isPicked(type, value) {
  return ui.picked.some((p) => p.type === type && p.value === value);
}

// ---------- Ekran iskeleti ----------

function render() {
  restartBtn.hidden = ui.view === 'setup';
  const views = {
    setup: setupHtml,
    lineup: lineupHtml,
    protect: protectHtml,
    steal: stealHtml,
    done: doneHtml,
  };
  app.innerHTML = views[ui.view]();
  if (ui.view === 'setup') refreshSetup();
}

function go(view) {
  ui.view = view;
  ui.selected = [];
  ui.target = null;
  ui.give = null;
  ui.message = '';
  render();
  window.scrollTo(0, 0);
}

function resetAll() {
  Object.assign(ui, {
    view: 'setup', type: 'club', query: '', picked: [], formationId: null,
    setupError: '', match: null, selected: [], target: null, give: null, message: '',
  });
  render();
  window.scrollTo(0, 0);
}

// ---------- Kurulum ----------

function setupHtml() {
  const tabs = TYPES.map((t) => `
    <button type="button" role="tab" class="tab" aria-selected="${ui.type === t.type}"
      data-action="tab" data-type="${t.type}">${t.label}</button>`).join('');
  return `
  <section class="card" aria-labelledby="h-cat">
    <h2 id="h-cat">1. Kategoriler</h2>
    <p class="hint">Havuz, seçtiğiniz kategorilerden en az birine uyan oyunculardan oluşur. Birden fazla seçebilirsiniz.</p>
    <div class="tabs" role="tablist">${tabs}</div>
    <label class="sr-only" for="q">Ara</label>
    <input id="q" type="search" class="search" placeholder="Kulüp, lig veya ülke ara"
      value="${esc(ui.query)}" autocomplete="off">
    <h3>Seçilenler</h3>
    <div id="chips" class="chips"></div>
    <div id="options"></div>
  </section>
  <section class="card" aria-labelledby="h-form">
    <h2 id="h-form">2. Formasyon</h2>
    <div id="formations" class="formations"></div>
  </section>
  <div class="actions">
    <p id="setup-error" class="error" role="alert"></p>
    <button type="button" id="start" class="btn primary" data-action="start">Maçı başlat</button>
  </div>`;
}

function optionsHtml() {
  const list = data.categories[ui.type] || [];
  const q = fold(ui.query.trim());
  const matches = [...list]
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value, 'tr'))
    .filter((it) => fold(it.value).includes(q));
  const items = matches.slice(0, SEARCH_LIMIT).map((it) => `
    <button type="button" class="opt" aria-pressed="${isPicked(ui.type, it.value)}"
      data-action="toggle" data-type="${ui.type}" data-value="${esc(it.value)}">
      <span>${esc(it.value)}</span><small>${it.count} oyuncu</small>
    </button>`).join('');
  let note = '';
  if (!matches.length) note = '<p class="hint">Sonuç yok.</p>';
  else if (matches.length > SEARCH_LIMIT) {
    note = `<p class="hint">${matches.length} sonuçtan ilk ${SEARCH_LIMIT} tanesi gösteriliyor. Daraltmak için arayın.</p>`;
  }
  return `<div class="grid options" role="group" aria-label="${TYPE_LABEL[ui.type]} listesi">${items}</div>${note}`;
}

function chipsHtml() {
  if (!ui.picked.length) return '<p class="hint">Henüz kategori seçilmedi.</p>';
  return ui.picked.map((p, i) => `
    <button type="button" class="chip" data-action="unpick" data-index="${i}"
      aria-label="${esc(TYPE_LABEL[p.type])} ${esc(p.value)} kaldır">
      ${esc(TYPE_LABEL[p.type])}: ${esc(p.value)} <span aria-hidden="true">×</span>
    </button>`).join('');
}

function formationsHtml() {
  if (!data.formations.length) return '<p class="hint">Formasyon bulunamadı.</p>';
  return data.formations.map((f) => `
    <button type="button" class="formation" aria-pressed="${f.id === ui.formationId}"
      data-action="formation" data-id="${esc(f.id)}">
      <b>${esc(f.id)}</b><span>${esc(f.slots.join(' '))}</span>
    </button>`).join('');
}

// Yalnızca kurulum alanlarını günceller; arama kutusu odağını kaybetmesin diye tüm ekranı yeniden çizmez.
function refreshSetup() {
  $('#options').innerHTML = optionsHtml();
  $('#chips').innerHTML = chipsHtml();
  $('#formations').innerHTML = formationsHtml();
  $('#setup-error').textContent = ui.setupError;
  $('#start').disabled = !(ui.picked.length && ui.formationId);
}

function startMatch() {
  const formation = data.formations.find((f) => f.id === ui.formationId);
  try {
    ui.match = createMatch({
      players: data.players,
      categories: ui.picked.map((p) => ({ type: p.type, value: p.value })),
      formation,
      protectCount: PROTECT_COUNT,
      stealsPerSide: STEALS_PER_SIDE,
      seed: Math.floor(Math.random() * 2147483646) + 1,
    });
    ui.setupError = '';
    go('lineup');
  } catch (err) {
    ui.setupError = err.message;
    refreshSetup();
  }
}

// ---------- Saha ve kadro gösterimi ----------

// Slotları satırlara böler; her satırda oyuncuları yatayda eşit aralıklı yerleştirir.
function layout(slots) {
  const lines = {};
  slots.forEach((slot, i) => {
    const line = LINE_OF[slot.pos] || 'MID';
    (lines[line] ||= []).push({ slot, i, rank: WIDTH_RANK[slot.pos] ?? 1 });
  });
  const out = [];
  for (const [line, row] of Object.entries(lines)) {
    row.sort((a, b) => a.rank - b.rank || a.i - b.i);
    row.forEach((e, k) => out.push({
      slot: e.slot,
      x: ((k + 1) * 100) / (row.length + 1),
      y: LINE_Y[line],
    }));
  }
  return out;
}

function pitchHtml(side) {
  const chips = layout(ui.match.sides[side].slots).map(({ slot, x, y }) => `
    <div class="slot" style="left:${x}%;top:${y}%">
      <b>${esc(slot.player.name)}</b>
      <span>${esc(slot.pos)} · ${slot.player.rating}</span>
    </div>`).join('');
  return `<div class="pitch" role="img" aria-label="Oyuncu ${side} dizilişi">${chips}</div>`;
}

function teamCard(side) {
  return `
  <section class="card">
    <header class="team-head">
      <h2>Oyuncu ${side}</h2>
      <span class="rating">Takım gücü ${teamRating(ui.match, side)}</span>
    </header>
    ${pitchHtml(side)}
  </section>`;
}

// ---------- Kadro ekranları ----------

function lineupHtml() {
  return `
  <p class="banner">Kadrolar dağıtıldı. Önce koruma aşaması, sonra takas turları.</p>
  ${teamCard('A')}
  ${teamCard('B')}
  <div class="actions">
    <button type="button" class="btn primary" data-action="to-protect">Koruma aşamasına geç</button>
  </div>`;
}

function playerBtn(p, { action, pressed = false, disabled = false, tag = '' }) {
  return `
  <button type="button" class="player" aria-pressed="${pressed}" data-action="${action}"
    data-id="${esc(p.id)}" ${disabled ? 'disabled' : ''}>
    <b>${esc(p.name)}</b>
    <span>${esc(p.pos)} · ${p.rating}</span>
    ${tag ? `<em>${esc(tag)}</em>` : ''}
  </button>`;
}

// Koruma sırası: ilk taraf A, A koruyunca B. Taraf, kendi korumalı listesinin boşluğuna göre belirlenir.
function currentProtectSide() {
  return ui.match.sides.A.protectedIds.length ? 'B' : 'A';
}

function protectHtml() {
  const side = currentProtectSide();
  const squad = ui.match.sides[side].slots.map((s) => s.player);
  const ready = ui.selected.length === PROTECT_COUNT;
  return `
  <p class="banner">Sıra: <b>Oyuncu ${side}</b>. Korumaya alınacak ${PROTECT_COUNT} oyuncuyu seçin.</p>
  <section class="card">
    <h2>Oyuncu ${side} kadrosu</h2>
    <p class="hint">${ui.selected.length}/${PROTECT_COUNT} seçildi. Korumalı oyuncular takas turlarında rakip tarafından alınamaz.</p>
    <div class="grid">${squad.map((p) => playerBtn(p, {
      action: 'protect-pick',
      pressed: ui.selected.includes(p.id),
    })).join('')}</div>
  </section>
  <p class="error" role="alert">${esc(ui.message)}</p>
  <div class="actions">
    <button type="button" class="btn primary" data-action="confirm-protect" ${ready ? '' : 'disabled'}>Korumayı onayla</button>
  </div>`;
}

function stealHtml() {
  const m = ui.match;
  const turn = m.turn;
  const other = turn === 'A' ? 'B' : 'A';
  const rivalProtected = new Set(m.sides[other].protectedIds);
  const rivalPlayers = m.sides[other].slots.map((s) => s.player);
  const ownPlayers = m.sides[turn].slots.map((s) => s.player);
  const ready = ui.target && ui.give;
  return `
  <p class="banner">Sıra: <b>Oyuncu ${turn}</b> · Kalan takas hakkı: ${m.stealsLeft[turn]}</p>
  <p class="hint">Takım gücü: A ${teamRating(m, 'A')} · B ${teamRating(m, 'B')}</p>
  <section class="card">
    <h2>1. Rakipten al (Oyuncu ${other})</h2>
    <p class="hint">Korumalı oyuncular seçilemez.</p>
    <div class="grid">${rivalPlayers.map((p) => playerBtn(p, {
      action: 'steal-target',
      pressed: ui.target === p.id,
      disabled: rivalProtected.has(p.id),
      tag: rivalProtected.has(p.id) ? 'korumalı' : '',
    })).join('')}</div>
  </section>
  <section class="card">
    <h2>2. Karşılığında ver (Oyuncu ${turn})</h2>
    <div class="grid">${ownPlayers.map((p) => playerBtn(p, {
      action: 'steal-give',
      pressed: ui.give === p.id,
    })).join('')}</div>
  </section>
  <p class="error" role="alert">${esc(ui.message)}</p>
  <div class="actions">
    <button type="button" class="btn primary" data-action="confirm-steal" ${ready ? '' : 'disabled'}>Takası onayla</button>
  </div>`;
}

function doneHtml() {
  const r = result(ui.match);
  const title = r.winner === 'draw' ? 'Berabere' : `Kazanan: Oyuncu ${r.winner}`;
  return `
  <section class="card result">
    <h2>${title}</h2>
    <p class="score">A ${r.A} · B ${r.B}</p>
    <div class="actions">
      <button type="button" class="btn primary" data-action="restart">Yeni maç</button>
    </div>
  </section>
  ${teamCard('A')}
  ${teamCard('B')}`;
}

// ---------- Olaylar ----------

app.addEventListener('input', (e) => {
  if (e.target.id !== 'q') return;
  ui.query = e.target.value;
  $('#options').innerHTML = optionsHtml();
});

app.addEventListener('click', (e) => {
  const el = e.target.closest('[data-action]');
  if (!el || el.disabled) return;
  handle(el.dataset.action, el);
});

restartBtn.addEventListener('click', () => {
  if (confirm('Maç sıfırlansın mı?')) resetAll();
});

function handle(action, el) {
  switch (action) {
    case 'tab':
      ui.type = el.dataset.type;
      render();
      break;
    case 'toggle': {
      const type = el.dataset.type;
      const value = el.dataset.value;
      const idx = ui.picked.findIndex((p) => p.type === type && p.value === value);
      if (idx >= 0) ui.picked.splice(idx, 1);
      else ui.picked.push({ type, value });
      ui.setupError = '';
      refreshSetup();
      break;
    }
    case 'unpick':
      ui.picked.splice(Number(el.dataset.index), 1);
      refreshSetup();
      break;
    case 'formation':
      ui.formationId = el.dataset.id;
      refreshSetup();
      break;
    case 'start':
      startMatch();
      break;
    case 'to-protect':
      go('protect');
      break;
    case 'protect-pick': {
      const id = el.dataset.id;
      if (ui.selected.includes(id)) {
        ui.selected = ui.selected.filter((x) => x !== id);
        ui.message = '';
      } else if (ui.selected.length < PROTECT_COUNT) {
        ui.selected = [...ui.selected, id];
        ui.message = '';
      } else {
        ui.message = `En fazla ${PROTECT_COUNT} oyuncu korunabilir.`;
      }
      render();
      break;
    }
    case 'confirm-protect':
      try {
        ui.match = protect(ui.match, currentProtectSide(), ui.selected);
        go(ui.match.phase === 'steal' ? 'steal' : 'protect');
      } catch (err) {
        ui.message = err.message;
        render();
      }
      break;
    case 'steal-target':
      ui.target = ui.target === el.dataset.id ? null : el.dataset.id;
      ui.message = '';
      render();
      break;
    case 'steal-give':
      ui.give = ui.give === el.dataset.id ? null : el.dataset.id;
      ui.message = '';
      render();
      break;
    case 'confirm-steal':
      try {
        ui.match = steal(ui.match, ui.match.turn, ui.target, ui.give);
        go(ui.match.phase === 'done' ? 'done' : 'steal');
      } catch (err) {
        ui.message = err.message;
        render();
      }
      break;
    case 'restart':
      resetAll();
      break;
  }
}

// ---------- Başlangıç ----------

async function loadJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} yüklenemedi (${res.status})`);
  return res.json();
}

async function init() {
  try {
    const [players, categories, formations] = await Promise.all([
      loadJson('data/players.json'),
      loadJson('data/categories.json'),
      loadJson('data/formations.json'),
    ]);
    Object.assign(data, { players, categories, formations });
    render();
  } catch (err) {
    app.innerHTML = `
      <section class="card">
        <p class="error" role="alert">Veriler yüklenemedi: ${esc(err.message)}.
        Sayfayı bir HTTP sunucusu üzerinden açın (örn. <code>python3 -m http.server</code>).</p>
      </section>`;
  }
}

init();
