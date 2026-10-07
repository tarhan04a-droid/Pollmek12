// Rastgele Seçimli Maç motoru. Saf fonksiyonlar: DOM yok, state değiştirilmez, hata = Error.
// Sözleşme: docs/CONTRACT.md

const SIDES = ["A", "B"];
const CATEGORY_TYPES = ["club", "league", "nation"];
const ALT_PENALTY = 10;

function fail(message) {
  throw new Error(message);
}

function assertSide(side) {
  if (side !== "A" && side !== "B") {
    fail(`Geçersiz taraf: ${String(side)} (A veya B olmalı)`);
  }
}

function assertState(state) {
  if (!state || typeof state !== "object" || !state.sides || !state.phase) {
    fail("Geçersiz state: createMatch ile oluşturulmuş bir state gerekli");
  }
}

function other(side) {
  return side === "A" ? "B" : "A";
}

// Seed'li PRNG (mulberry32). Aynı seed -> aynı dizi.
function makeRng(seed) {
  let a = Number(seed) >>> 0;
  return function rng() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pickRandom(rng, list) {
  return list[Math.floor(rng() * list.length)];
}

function matchesCategory(player, category) {
  if (category.type === "club") return player.club === category.value;
  if (category.type === "league") return player.league === category.value;
  if (category.type === "nation") return player.nation === category.value;
  return false;
}

function hasProtected(log, side) {
  return log.some((entry) => entry.type === "protect" && entry.side === side);
}

// Önce tam pozisyon eşleşmesi aranır, yoksa alt pozisyon. İki taraf da aynı havuzdan
// tekrarsız çekilir, bu yüzden aynı oyuncu iki tarafa verilmez.
function dealSides(pool, slotPositions, rng) {
  const used = new Set();
  const dealt = {};
  for (const side of SIDES) {
    dealt[side] = slotPositions.map((pos) => {
      const free = pool.filter((p) => !used.has(p.id));
      let candidates = free.filter((p) => p.pos === pos);
      if (candidates.length === 0) {
        candidates = free.filter((p) => Array.isArray(p.alt) && p.alt.includes(pos));
      }
      if (candidates.length === 0) {
        fail(`Havuz yetersiz: ${side} tarafının "${pos}" slotu için uygun oyuncu kalmadı`);
      }
      const player = pickRandom(rng, candidates);
      used.add(player.id);
      return { pos, player };
    });
  }
  return dealt;
}

export function createMatch({
  players,
  categories,
  formation,
  protectCount = 3,
  stealsPerSide = 3,
  seed = 1,
} = {}) {
  if (!Array.isArray(players) || players.length === 0) {
    fail("Oyuncu listesi boş");
  }
  if (!Array.isArray(categories) || categories.length === 0) {
    fail("En az bir kategori seçilmeli");
  }
  for (const category of categories) {
    if (!category || !CATEGORY_TYPES.includes(category.type) || typeof category.value !== "string") {
      fail(`Geçersiz kategori: ${JSON.stringify(category)} (type club|league|nation, value metin olmalı)`);
    }
  }
  if (!formation || !Array.isArray(formation.slots) || formation.slots.length === 0) {
    fail("Geçersiz formasyon: slots dolu bir dizi olmalı");
  }
  if (formation.slots.some((slot) => typeof slot !== "string" || slot === "")) {
    fail("Geçersiz formasyon: her slot bir pozisyon metni olmalı");
  }
  if (!Number.isInteger(protectCount) || protectCount < 0 || protectCount > formation.slots.length) {
    fail(`Geçersiz protectCount: ${protectCount} (0..${formation.slots.length} tam sayı olmalı)`);
  }
  if (!Number.isInteger(stealsPerSide) || stealsPerSide < 0) {
    fail(`Geçersiz stealsPerSide: ${stealsPerSide} (0 veya büyük tam sayı olmalı)`);
  }

  const seen = new Set();
  const pool = [];
  for (const player of players) {
    if (seen.has(player.id)) continue;
    if (categories.some((category) => matchesCategory(player, category))) {
      seen.add(player.id);
      pool.push(player);
    }
  }
  if (pool.length === 0) {
    fail("Seçilen kategorilerde oyuncu yok");
  }

  const rng = makeRng(seed);
  const dealt = dealSides(pool, formation.slots, rng);

  return {
    phase: "protect",
    sides: {
      A: { slots: dealt.A, protectedIds: [] },
      B: { slots: dealt.B, protectedIds: [] },
    },
    turn: "A",
    stealsLeft: { A: stealsPerSide, B: stealsPerSide },
    protectCount,
    log: [],
  };
}

export function protect(state, side, playerIds) {
  assertState(state);
  assertSide(side);
  if (state.phase !== "protect") {
    fail(`Koruma aşamasında değil (faz: ${state.phase})`);
  }
  if (hasProtected(state.log, side)) {
    fail(`${side} tarafı zaten koruma yaptı`);
  }
  if (!Array.isArray(playerIds)) {
    fail("playerIds bir dizi olmalı");
  }
  if (playerIds.length !== state.protectCount) {
    fail(`Tam ${state.protectCount} oyuncu korunmalı (verilen: ${playerIds.length})`);
  }
  if (new Set(playerIds).size !== playerIds.length) {
    fail("Aynı oyuncu birden fazla kez korunamaz");
  }
  const roster = new Set(state.sides[side].slots.map((slot) => slot.player.id));
  for (const id of playerIds) {
    if (!roster.has(id)) {
      fail(`${id} ${side} tarafının kadrosunda değil`);
    }
  }

  const log = [...state.log, { type: "protect", side, playerIds: [...playerIds] }];
  const bothProtected = SIDES.every((s) => hasProtected(log, s));

  return {
    ...state,
    phase: bothProtected ? (state.stealsLeft.A + state.stealsLeft.B === 0 ? "done" : "steal") : state.phase,
    turn: bothProtected ? "A" : state.turn,
    sides: {
      ...state.sides,
      [side]: { slots: state.sides[side].slots, protectedIds: [...playerIds] },
    },
    log,
  };
}

export function steal(state, side, targetId, giveId) {
  assertState(state);
  assertSide(side);
  if (state.phase !== "steal") {
    fail(`Takas aşamasında değil (faz: ${state.phase})`);
  }
  if (state.turn !== side) {
    fail(`Sıra ${state.turn} tarafında, ${side} takas yapamaz`);
  }
  if (state.stealsLeft[side] <= 0) {
    fail(`${side} tarafının takas hakkı kalmadı`);
  }

  const foe = other(side);
  const me = state.sides[side];
  const rival = state.sides[foe];

  const targetIndex = rival.slots.findIndex((slot) => slot.player.id === targetId);
  if (targetIndex < 0) {
    fail(`${targetId} rakip kadrosunda değil`);
  }
  if (rival.protectedIds.includes(targetId)) {
    fail(`${targetId} korumalı, alınamaz`);
  }

  const giveIndex = me.slots.findIndex((slot) => slot.player.id === giveId);
  if (giveIndex < 0) {
    fail(`${giveId} kendi kadrosunda değil`);
  }
  if (me.protectedIds.includes(giveId)) {
    fail(`${giveId} korumalı, verilemez`);
  }

  const targetPlayer = rival.slots[targetIndex].player;
  const givePlayer = me.slots[giveIndex].player;

  // Oyuncular birbirinin slotuna geçer; slot pozisyon etiketi yerinde kalır.
  const mySlots = me.slots.map((slot, i) =>
    i === giveIndex ? { pos: slot.pos, player: targetPlayer } : slot
  );
  const rivalSlots = rival.slots.map((slot, i) =>
    i === targetIndex ? { pos: slot.pos, player: givePlayer } : slot
  );

  const stealsLeft = { ...state.stealsLeft, [side]: state.stealsLeft[side] - 1 };
  const done = stealsLeft.A === 0 && stealsLeft.B === 0;

  return {
    ...state,
    phase: done ? "done" : "steal",
    turn: foe,
    stealsLeft,
    sides: {
      ...state.sides,
      [side]: { slots: mySlots, protectedIds: [...me.protectedIds, targetId] },
      [foe]: { slots: rivalSlots, protectedIds: [...rival.protectedIds] },
    },
    log: [...state.log, { type: "steal", side, targetId, giveId }],
  };
}

export function slotScore(slotPos, player) {
  if (player.pos === slotPos) return player.rating;
  if (Array.isArray(player.alt) && player.alt.includes(slotPos)) return player.rating;
  return Math.max(0, player.rating - ALT_PENALTY);
}

export function teamRating(state, side) {
  assertState(state);
  assertSide(side);
  const slots = state.sides[side].slots;
  const total = slots.reduce((sum, slot) => sum + slotScore(slot.pos, slot.player), 0);
  return Math.round(total / slots.length);
}

export function result(state) {
  assertState(state);
  if (state.phase !== "done") {
    fail(`Sonuç için maç bitmiş olmalı (faz: ${state.phase})`);
  }
  const A = teamRating(state, "A");
  const B = teamRating(state, "B");
  const winner = A > B ? "A" : B > A ? "B" : "draw";
  return { A, B, winner };
}
