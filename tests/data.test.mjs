// Veri şeması testleri (docs/CONTRACT.md "Veri" bölümü). Gerçek data/*.json dosyalarını okur.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const dataUrl = (file) => new URL(`../data/${file}`, import.meta.url);
const load = async (file) => JSON.parse(await readFile(dataUrl(file), 'utf8'));

// EA FC etiketleri (formasyon slotları ve alt pozisyonlar bu kümeden).
const POS = new Set([
  'GK', 'CB', 'LB', 'RB', 'LWB', 'RWB', 'CDM', 'CM', 'CAM', 'LM', 'RM',
  'LW', 'RW', 'LF', 'RF', 'CF', 'ST', 'LAM', 'RAM',
]);
const ATTRS = ['pac', 'sho', 'pas', 'dri', 'def', 'phy'];
const isInt = (x) => Number.isInteger(x);
const isNonEmptyString = (x) => typeof x === 'string' && x.trim().length > 0;

const players = await load('players.json').catch((e) => e);
const categories = await load('categories.json').catch((e) => e);
const formations = await load('formations.json').catch((e) => e);

describe('players.json', () => {
  test('dizi ve boş değil', () => {
    assert.ok(Array.isArray(players), `okunamadı: ${players.message}`);
    assert.ok(players.length > 0);
  });

  test('her oyuncu şema alanlarına sahip ve doğru tipte', () => {
    for (const p of players) {
      const ctx = `id=${p.id}`;
      assert.ok(isNonEmptyString(p.id), `${ctx}: id string olmalı`);
      assert.ok(isNonEmptyString(p.name), `${ctx}: name dolu olmalı`);
      assert.ok(POS.has(p.pos), `${ctx}: geçersiz pos ${p.pos}`);
      assert.ok(Array.isArray(p.alt), `${ctx}: alt dizi olmalı`);
      for (const a of p.alt) assert.ok(POS.has(a), `${ctx}: geçersiz alt ${a}`);
      assert.ok(isInt(p.rating), `${ctx}: rating tam sayı olmalı`);
      assert.equal(typeof p.club, 'string', `${ctx}: club string olmalı`);
      assert.equal(typeof p.league, 'string', `${ctx}: league string olmalı`);
      assert.ok(isNonEmptyString(p.nation), `${ctx}: nation dolu olmalı`);
      for (const k of ATTRS) assert.ok(isInt(p[k]), `${ctx}: ${k} tam sayı olmalı`);
    }
  });

  test('rating en az 65 (filtre: overall_rating >= 65)', () => {
    for (const p of players) {
      assert.ok(p.rating >= 65, `id=${p.id} rating=${p.rating}`);
    }
  });

  test('id değerleri benzersiz', () => {
    const ids = players.map((p) => p.id);
    assert.equal(new Set(ids).size, ids.length);
  });
});

describe('categories.json', () => {
  const TYPES = ['club', 'league', 'nation'];

  test('club, league, nation anahtarları dizi olarak var', () => {
    assert.ok(!(categories instanceof Error), `okunamadı: ${categories.message}`);
    for (const t of TYPES) assert.ok(Array.isArray(categories[t]), `${t} dizi olmalı`);
  });

  test('her giriş {value: string, count: tam sayı >= 15} ve count gerçek sayıyla eşit', () => {
    for (const t of TYPES) {
      const values = new Set();
      for (const entry of categories[t]) {
        assert.ok(isNonEmptyString(entry.value), `${t}: value string olmalı`);
        assert.ok(isInt(entry.count), `${t}/${entry.value}: count tam sayı olmalı`);
        assert.ok(entry.count >= 15, `${t}/${entry.value}: count ${entry.count} < 15`);
        assert.ok(!values.has(entry.value), `${t}/${entry.value}: tekrarlı giriş`);
        values.add(entry.value);
        const actual = players.filter((p) => p[t] === entry.value).length;
        assert.equal(entry.count, actual, `${t}/${entry.value}: count yanlış`);
      }
    }
  });

  test('en az 15 oyuncusu olan her kulüp/lig/ülke listelenir', () => {
    for (const t of TYPES) {
      const counts = new Map();
      for (const p of players) {
        if (!isNonEmptyString(p[t])) continue;
        counts.set(p[t], (counts.get(p[t]) ?? 0) + 1);
      }
      const listed = new Set(categories[t].map((e) => e.value));
      for (const [value, n] of counts) {
        if (n >= 15) assert.ok(listed.has(value), `${t}/${value} (${n} oyuncu) listede yok`);
      }
    }
  });
});

describe('formations.json', () => {
  test('dizi; her formasyonun id\'si benzersiz ve tam 11 slotu var', () => {
    assert.ok(Array.isArray(formations), `okunamadı: ${formations.message}`);
    const ids = formations.map((f) => f.id);
    assert.equal(new Set(ids).size, ids.length);
    for (const f of formations) {
      assert.ok(isNonEmptyString(f.id));
      assert.equal(f.slots.length, 11, `${f.id}: 11 slot olmalı`);
      for (const s of f.slots) assert.ok(POS.has(s), `${f.id}: geçersiz slot ${s}`);
      assert.equal(f.slots.filter((s) => s === 'GK').length, 1, `${f.id}: tam bir GK olmalı`);
    }
  });

  test('zorunlu formasyonlar mevcut: 4-3-3, 4-4-2, 3-5-2, 4-2-3-1', () => {
    const ids = new Set(formations.map((f) => f.id));
    for (const id of ['4-3-3', '4-4-2', '3-5-2', '4-2-3-1']) {
      assert.ok(ids.has(id), `${id} eksik`);
    }
  });

  test('4-3-3 slotları sözleşmedeki sıralamayla birebir aynı', () => {
    const f = formations.find((x) => x.id === '4-3-3');
    assert.deepEqual(f.slots, ['GK', 'LB', 'CB', 'CB', 'RB', 'CM', 'CM', 'CM', 'LW', 'ST', 'RW']);
  });
});
