// Motor testleri (docs/CONTRACT.md "Motor" bölümü).
// Birim testlerinin verisi sabit ve testin içinde tanımlı. Sondaki uçtan uca test
// gerçek data/players.json ve data/formations.json dosyalarını okur.
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  createMatch,
  protect,
  steal,
  slotScore,
  teamRating,
  result,
} from '../src/engine.js';

const readJson = (rel) => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8'));

const FORMATION = {
  id: '4-3-3',
  slots: ['GK', 'LB', 'CB', 'CB', 'RB', 'CM', 'CM', 'CM', 'LW', 'ST', 'RW'],
};

// Alpha kulübü: 22 oyuncu (her slot pozisyonundan 2 tane) -> iki taraf tam dolar.
// Beta kulübü (aynı lig L1): 22 oyuncu daha. Gamma: sadece 3 ST -> yetersiz havuz.
function makeFixture() {
  const players = [];
  let id = 1;
  const block = (club, league, nation, count) => {
    for (let rep = 0; rep < count; rep++) {
      for (const pos of FORMATION.slots) {
        players.push({
          id: String(id),
          name: `Oyuncu ${id}`,
          pos,
          alt: [],
          rating: 70 + (id % 20),
          club,
          league,
          nation,
          pac: 70, sho: 70, pas: 70, dri: 70, def: 70, phy: 70,
        });
        id++;
      }
    }
  };
  block('Alpha', 'L1', 'Nationa', 2); // id 1..22
  block('Beta', 'L1', 'Nationb', 2);  // id 23..44
  for (let i = 0; i < 3; i++) {
    players.push({
      id: String(id), name: `Forvet ${id}`, pos: 'ST', alt: [], rating: 75,
      club: 'Gamma', league: 'L2', nation: 'Nationa',
      pac: 70, sho: 70, pas: 70, dri: 70, def: 70, phy: 70,
    });
    id++;
  }
  return players;
}

const PLAYERS = makeFixture();
const clone = (x) => JSON.parse(JSON.stringify(x));

function newMatch(overrides = {}) {
  return createMatch({
    players: PLAYERS,
    categories: [{ type: 'club', value: 'Alpha' }],
    formation: FORMATION,
    seed: 1,
    ...overrides,
  });
}

const squadIds = (state, side) => state.sides[side].slots.map((s) => s.player.id);
const unprotected = (state, side) =>
  squadIds(state, side).filter((id) => !state.sides[side].protectedIds.includes(id));
const other = (side) => (side === 'A' ? 'B' : 'A');

// Her iki taraf da ilk protectCount oyuncusunu korur -> phase "steal".
function readyForSteal(overrides = {}) {
  let s = newMatch(overrides);
  s = protect(s, 'A', squadIds(s, 'A').slice(0, s.protectCount));
  s = protect(s, 'B', squadIds(s, 'B').slice(0, s.protectCount));
  return s;
}

describe('createMatch', () => {
  test('havuz yetersizse Error fırlatır', () => {
    assert.throws(
      () => newMatch({ categories: [{ type: 'club', value: 'Gamma' }] }),
      Error,
    );
  });

  test('iki tarafa da formasyonun her slotu için oyuncu dağıtılır (11 slot, slot sırası formasyonla aynı)', () => {
    const s = newMatch();
    for (const side of ['A', 'B']) {
      assert.equal(s.sides[side].slots.length, 11);
      assert.deepEqual(s.sides[side].slots.map((x) => x.pos), FORMATION.slots);
      assert.deepEqual(s.sides[side].protectedIds, []);
    }
  });

  test('aynı oyuncu iki tarafa verilmez', () => {
    const s = newMatch({ categories: [{ type: 'league', value: 'L1' }] });
    const a = squadIds(s, 'A');
    const b = squadIds(s, 'B');
    assert.equal(new Set(a).size, 11);
    assert.equal(new Set(b).size, 11);
    assert.equal(a.filter((id) => b.includes(id)).length, 0);
  });

  test('dağıtılan oyuncu slotunun pozisyonuna (pos veya alt) uyar', () => {
    const s = newMatch({ categories: [{ type: 'league', value: 'L1' }] });
    for (const side of ['A', 'B']) {
      for (const slot of s.sides[side].slots) {
        const ok = slot.player.pos === slot.pos || slot.player.alt.includes(slot.pos);
        assert.ok(ok, `${side} slot ${slot.pos} -> ${slot.player.pos}`);
      }
    }
  });

  test('başlangıç state alanları sözleşmeye uygun', () => {
    const s = newMatch();
    assert.equal(s.phase, 'protect');
    assert.deepEqual(s.stealsLeft, { A: 3, B: 3 });
    assert.equal(s.protectCount, 3);
    assert.ok(Array.isArray(s.log));
  });

  test('aynı seed ve parametreler -> aynı kadrolar (determinizm)', () => {
    assert.deepEqual(newMatch({ seed: 7 }), newMatch({ seed: 7 }));
  });

  test('farklı seed -> farklı dağıtım', () => {
    assert.notDeepEqual(
      squadIds(newMatch({ seed: 1 }), 'A'),
      squadIds(newMatch({ seed: 2 }), 'A'),
    );
  });

  test('girdi nesneleri değiştirilmez', () => {
    const players = clone(PLAYERS);
    const categories = [{ type: 'club', value: 'Alpha' }];
    const formation = clone(FORMATION);
    createMatch({ players, categories, formation, seed: 3 });
    assert.deepEqual(players, PLAYERS);
    assert.deepEqual(categories, [{ type: 'club', value: 'Alpha' }]);
    assert.deepEqual(formation, FORMATION);
  });
});

describe('protect', () => {
  test('tam protectCount id değilse Error', () => {
    const s = newMatch();
    assert.throws(() => protect(s, 'A', squadIds(s, 'A').slice(0, 2)), Error);
    assert.throws(() => protect(s, 'A', squadIds(s, 'A').slice(0, 4)), Error);
  });

  test('aynı id iki kez verilirse Error', () => {
    const s = newMatch();
    const [x] = squadIds(s, 'A');
    assert.throws(() => protect(s, 'A', [x, x, x]), Error);
  });

  test('kadroda olmayan id (rakip oyuncusu) verilirse Error', () => {
    const s = newMatch();
    assert.throws(() => protect(s, 'A', squadIds(s, 'B').slice(0, 3)), Error);
  });

  test('geçerli koruma yeni state döndürür, eskisi değişmez', () => {
    const s0 = newMatch();
    const snapshot = clone(s0);
    const ids = squadIds(s0, 'A').slice(0, 3);
    const s1 = protect(s0, 'A', ids);
    assert.notEqual(s1, s0);
    assert.deepEqual(s0, snapshot);
    assert.deepEqual([...s1.sides.A.protectedIds].sort(), [...ids].sort());
  });

  test('yalnızca bir taraf koruyunca phase hâlâ "protect"', () => {
    const s0 = newMatch();
    const s1 = protect(s0, 'A', squadIds(s0, 'A').slice(0, 3));
    assert.equal(s1.phase, 'protect');
  });

  test('iki taraf da koruyunca phase "steal", turn "A"', () => {
    const s0 = newMatch();
    let s = protect(s0, 'A', squadIds(s0, 'A').slice(0, 3));
    s = protect(s, 'B', squadIds(s, 'B').slice(0, 3));
    assert.equal(s.phase, 'steal');
    assert.equal(s.turn, 'A');
  });

  test('steal fazında koruma yapılamaz', () => {
    const s = readyForSteal();
    assert.throws(() => protect(s, 'A', squadIds(s, 'A').slice(0, 3)), Error);
  });
});

describe('steal', () => {
  test('phase "protect" iken steal Error', () => {
    const s = newMatch();
    const target = squadIds(s, 'B')[0];
    const give = squadIds(s, 'A')[0];
    assert.throws(() => steal(s, 'A', target, give), Error);
  });

  test('sıra bu tarafta değilse Error (A bitmeden B çalamaz)', () => {
    const s = readyForSteal();
    const target = unprotected(s, 'A')[0];
    const give = unprotected(s, 'B')[0];
    assert.throws(() => steal(s, 'B', target, give), Error);
  });

  test('korumalı rakip oyuncusu alınamaz', () => {
    const s = readyForSteal();
    const protectedTarget = s.sides.B.protectedIds[0];
    const give = unprotected(s, 'A')[0];
    assert.throws(() => steal(s, 'A', protectedTarget, give), Error);
  });

  test('hedef rakip kadrosunda değilse Error (kendi oyuncusu)', () => {
    const s = readyForSteal();
    const ownPlayer = unprotected(s, 'A')[0];
    const give = unprotected(s, 'A')[1];
    assert.throws(() => steal(s, 'A', ownPlayer, give), Error);
  });

  test('giveId kendi kadroda değilse Error', () => {
    const s = readyForSteal();
    const target = unprotected(s, 'B')[0];
    const notMine = squadIds(s, 'B')[0];
    assert.throws(() => steal(s, 'A', target, notMine), Error);
  });

  test('giveId kendi korumalı oyuncusuysa Error (korumalı oyuncu verilemez)', () => {
    const s = readyForSteal();
    const target = unprotected(s, 'B')[0];
    const protectedGive = s.sides.A.protectedIds[0];
    assert.throws(() => steal(s, 'A', target, protectedGive), Error);
  });

  test('korumasız giveId ile takas başarılı: sıra değişir, stealsLeft azalır, alınan oyuncu korumalı olur', () => {
    const s0 = readyForSteal();
    const target = unprotected(s0, 'B')[0];
    const give = unprotected(s0, 'A')[0];
    assert.ok(!s0.sides.A.protectedIds.includes(give));

    const s1 = steal(s0, 'A', target, give);

    assert.equal(s1.turn, 'B');
    assert.equal(s1.stealsLeft.A, s0.stealsLeft.A - 1);
    assert.ok(s1.sides.A.protectedIds.includes(target));
    assert.ok(squadIds(s1, 'B').includes(give));
  });

  test('geçerli takas: iki oyuncu birbirinin slotuna geçer, slot pozisyonları değişmez', () => {
    const s0 = readyForSteal();
    const target = unprotected(s0, 'B')[0];
    const give = unprotected(s0, 'A')[0];
    const iA = s0.sides.A.slots.findIndex((x) => x.player.id === give);
    const iB = s0.sides.B.slots.findIndex((x) => x.player.id === target);
    const snapshot = clone(s0);

    const s1 = steal(s0, 'A', target, give);

    assert.deepEqual(s0, snapshot, 'girdi state değişmemeli');
    assert.equal(s1.sides.A.slots[iA].player.id, target);
    assert.equal(s1.sides.B.slots[iB].player.id, give);
    assert.equal(s1.sides.A.slots[iA].pos, s0.sides.A.slots[iA].pos);
    assert.equal(s1.sides.B.slots[iB].pos, s0.sides.B.slots[iB].pos);
  });

  test('takas sonrası sıra değişir ve stealsLeft azalır', () => {
    const s0 = readyForSteal();
    const s1 = steal(s0, 'A', unprotected(s0, 'B')[0], unprotected(s0, 'A')[0]);
    assert.equal(s1.turn, 'B');
    assert.equal(s1.stealsLeft.A, s0.stealsLeft.A - 1);
    assert.equal(s1.stealsLeft.B, s0.stealsLeft.B);
    assert.equal(s1.phase, 'steal');
  });

  test('alınan oyuncu alan tarafta korumalı olur', () => {
    const s0 = readyForSteal();
    const target = unprotected(s0, 'B')[0];
    const s1 = steal(s0, 'A', target, unprotected(s0, 'A')[0]);
    assert.ok(s1.sides.A.protectedIds.includes(target));
  });

  test('alınan oyuncu geri çalınamaz (rakip sırası gelince bile)', () => {
    const s0 = readyForSteal();
    const target = unprotected(s0, 'B')[0];
    const s1 = steal(s0, 'A', target, unprotected(s0, 'A')[0]);
    // Sıra B'de; B, A'dan aldığı oyuncuyu geri almaya çalışır.
    assert.throws(() => steal(s1, 'B', target, unprotected(s1, 'B')[0]), Error);
  });

  test('6 takas (A,B,A,B,A,B) sonunda phase "done"; ara adımlarda "steal"', () => {
    let s = readyForSteal();
    const order = ['A', 'B', 'A', 'B', 'A', 'B'];
    order.forEach((side, k) => {
      assert.equal(s.turn, side, `adım ${k} sırası ${side} olmalı`);
      const opp = other(side);
      s = steal(s, side, unprotected(s, opp)[0], unprotected(s, side)[0]);
      if (k < order.length - 1) assert.equal(s.phase, 'steal', `adım ${k} sonrası`);
    });
    assert.equal(s.phase, 'done');
    assert.deepEqual(s.stealsLeft, { A: 0, B: 0 });
  });

  test('phase "done" iken steal Error', () => {
    let s = readyForSteal();
    for (const side of ['A', 'B', 'A', 'B', 'A', 'B']) {
      s = steal(s, side, unprotected(s, other(side))[0], unprotected(s, side)[0]);
    }
    assert.throws(() => steal(s, 'A', unprotected(s, 'B')[0], unprotected(s, 'A')[0]), Error);
  });
});

describe('slotScore', () => {
  const p = { pos: 'ST', alt: ['LW'], rating: 80 };

  test('pozisyon eşleşirse rating', () => {
    assert.equal(slotScore('ST', p), 80);
  });

  test('alt pozisyonda ise rating', () => {
    assert.equal(slotScore('LW', p), 80);
  });

  test('uymayan slotta rating - 10', () => {
    assert.equal(slotScore('CB', p), 70);
  });

  test('ceza sıfırın altına inmez', () => {
    assert.equal(slotScore('CB', { pos: 'GK', alt: [], rating: 5 }), 0);
  });
});

describe('teamRating', () => {
  test('tam sayı döner ve 11 slotun slotScore ortalamasının yuvarlanmışıdır', () => {
    const s = newMatch();
    for (const side of ['A', 'B']) {
      const r = teamRating(s, side);
      const sum = s.sides[side].slots.reduce((acc, x) => acc + slotScore(x.pos, x.player), 0);
      assert.ok(Number.isInteger(r));
      assert.equal(r, Math.round(sum / 11));
    }
  });

  test('uymayan oyuncu slot cezasını yansıtır', () => {
    const s = clone(newMatch());
    // Kalecinin yerine 80 rating forvet: GK slotunda skor 70.
    s.sides.A.slots[0].player = { id: 'X', name: 'X', pos: 'ST', alt: [], rating: 80 };
    const expectedSum = s.sides.A.slots.reduce((acc, x) => acc + slotScore(x.pos, x.player), 0);
    assert.equal(slotScore('GK', s.sides.A.slots[0].player), 70);
    assert.equal(teamRating(s, 'A'), Math.round(expectedSum / 11));
  });
});

describe('result', () => {
  function finished() {
    let s = readyForSteal();
    for (const side of ['A', 'B', 'A', 'B', 'A', 'B']) {
      s = steal(s, side, unprotected(s, other(side))[0], unprotected(s, side)[0]);
    }
    return s;
  }

  test('phase "done" değilken Error', () => {
    assert.throws(() => result(newMatch()), Error);
    assert.throws(() => result(readyForSteal()), Error);
  });

  test('done state için takım puanları ve kazanan döner', () => {
    const s = finished();
    const r = result(s);
    assert.equal(r.A, teamRating(s, 'A'));
    assert.equal(r.B, teamRating(s, 'B'));
    const expected = r.A > r.B ? 'A' : r.B > r.A ? 'B' : 'draw';
    assert.equal(r.winner, expected);
  });

  test('eşit puanda winner "draw"', () => {
    const s = clone(finished());
    s.sides.B.slots = s.sides.A.slots.map((x) => ({ pos: x.pos, player: { ...x.player } }));
    const r = result(s);
    assert.equal(r.A, r.B);
    assert.equal(r.winner, 'draw');
  });
});

describe('determinizm (tam maç)', () => {
  test('aynı seed + aynı hamleler -> birebir aynı sonuç', () => {
    const play = () => {
      let s = newMatch({ seed: 42 });
      s = protect(s, 'A', squadIds(s, 'A').slice(0, 3));
      s = protect(s, 'B', squadIds(s, 'B').slice(0, 3));
      for (const side of ['A', 'B', 'A', 'B', 'A', 'B']) {
        s = steal(s, side, unprotected(s, other(side))[0], unprotected(s, side)[0]);
      }
      return { state: s, result: result(s) };
    };
    assert.deepEqual(play(), play());
  });
});

describe('uçtan uca (gerçek veri)', () => {
  test('Real Madrid + FC Barcelona + Manchester City, 4-3-3, seed sabit: 3+3 koruma, 6 takas, done, result', () => {
    const players = readJson('../data/players.json');
    const formations = readJson('../data/formations.json');
    const formation = formations.find((f) => f.id === '4-3-3');
    assert.ok(formation, '4-3-3 formasyonu data/formations.json içinde olmalı');

    const categories = [
      { type: 'club', value: 'Real Madrid' },
      { type: 'club', value: 'FC Barcelona' },
      { type: 'club', value: 'Manchester City' },
    ];
    let s = createMatch({ players, categories, formation, seed: 2026 });
    assert.equal(s.phase, 'protect');

    // Her iki taraf kadrosundan ilk 3 oyuncuyu korur.
    s = protect(s, 'A', squadIds(s, 'A').slice(0, 3));
    s = protect(s, 'B', squadIds(s, 'B').slice(0, 3));
    assert.equal(s.phase, 'steal');
    assert.equal(s.turn, 'A');
    assert.equal(s.sides.A.protectedIds.length, 3);
    assert.equal(s.sides.B.protectedIds.length, 3);

    // 6 takas: A,B,A,B,A,B. Her turda rakipten korumasız, kendinden korumasız oyuncu.
    for (const side of ['A', 'B', 'A', 'B', 'A', 'B']) {
      const opp = other(side);
      const target = unprotected(s, opp)[0];
      const give = unprotected(s, side)[0];
      assert.ok(target && give, `${side} için takas adayı yok`);
      assert.ok(!s.sides[opp].protectedIds.includes(target));
      assert.ok(!s.sides[side].protectedIds.includes(give));
      s = steal(s, side, target, give);
    }

    assert.equal(s.phase, 'done');
    assert.deepEqual(s.stealsLeft, { A: 0, B: 0 });

    const r = result(s);
    assert.deepEqual(Object.keys(r).sort(), ['A', 'B', 'winner']);
    assert.equal(r.A, teamRating(s, 'A'));
    assert.equal(r.B, teamRating(s, 'B'));
    assert.ok(['A', 'B', 'draw'].includes(r.winner));
  });
});
