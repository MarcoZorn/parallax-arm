// Punto 1: equivalenza planner firmware (motion.cpp, nativo) <-> twin web (motion.js).
// Stessi scenari casuali (seed fisso) su entrambi, traiettorie a 50 Hz confrontate tick per tick.
// Uso: node equiv.mjs [n_per_tipo] [seed]   -> stampa JSON con le metriche, exit 1 se KO.
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { writeFileSync } from 'node:fs';
// EQ_FW / EQ_WEB: binario e modulo alternativi (per misurare le versioni precedenti)
const { Motion, VMAX, AMAX, DT } = await import(process.env.EQ_WEB || '../../web/src/motion.js');
import { duration } from '../../web/src/motion.js';
import { validate, cal } from '../../web/src/robot.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const BIN = process.env.EQ_FW || join(HERE, 'build', 'fw_sim');
const NPT = +(process.argv[2] || 1500);
let seed = +(process.argv[3] || 12345);
const rnd = () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const U = (a, b) => a + (b - a) * rnd();
const r2 = (x) => Math.round(x * 100) / 100; // il browser manda q arrotondati a 0.01 (link.move)

// posa valida casuale, spesso sul bordo (limiti e vincolo th2-phi)
function pose() {
  for (;;) {
    const q = [U(-90, 90), U(20, 160), U(-70, 70), U(0, 59)];
    const b = rnd();
    if (b < 0.15) q[2] = q[1] - 20; else if (b < 0.3) q[2] = q[1] - 150;
    if (rnd() < 0.1) q[0] = rnd() < 0.5 ? -90 : 90;
    if (rnd() < 0.1) q[1] = rnd() < 0.5 ? 20 : 160;
    const qq = q.map(r2);
    if (!validate(qq)) return qq;
  }
}
const near = (q, s) => { for (;;) { const t = q.map((x, j) => r2(x + U(-s, s) * (j === 3 ? 0.5 : 1))); if (!validate(t)) return t; } };
const F = () => r2(rnd() < 0.3 ? 1 : U(0.05, 1)) || 0.05;

// tipi di scenario: eventi {k, c: M|T|H, f, t}
const KINDS = {
  single: () => [{ k: 0, c: 'M', f: F(), t: pose() }],
  retarget: () => [{ k: 0, c: 'M', f: F(), t: pose() }, { k: 1 + Math.floor(U(0, 80)), c: 'M', f: F(), t: pose() }],
  stop: () => [{ k: 0, c: 'M', f: F(), t: pose() }, { k: 1 + Math.floor(U(0, 80)), c: 'T' }],
  stop_move: () => { const k = 1 + Math.floor(U(0, 60)); return [{ k: 0, c: 'M', f: F(), t: pose() }, { k, c: 'T' }, { k: k + 1 + Math.floor(U(0, 30)), c: 'M', f: F(), t: pose() }]; },
  halt: () => [{ k: 0, c: 'M', f: F(), t: pose() }, { k: 1 + Math.floor(U(0, 80)), c: 'H' }, { k: 100, c: 'M', f: F(), t: pose() }],
  // trascinamento del gizmo: target vicini ogni 50 ms (20 comandi/s), spesso lungo il bordo del vincolo
  drag: (q0) => {
    const ev = [];
    let t = q0, k = 0;
    const f = F();
    for (let i = 0; i < 20; i++) { t = near(t, 6); ev.push({ k, c: 'M', f, t }); k += 2 + Math.floor(U(0, 3)); }
    return ev;
  },
};

// tick sufficienti: maggiorante della durata di ogni move (corsa massima da fermo) + 2 s per frenare
const TMAX = (f) => duration([-90, 20, -70, 0], [90, 160, 70, 59], f) + 2;
const ticks = (ev) => Math.ceil(ev.filter((e) => e.c === 'M').reduce((s, e) => s + TMAX(e.f), 0) / DT) + Math.max(...ev.map((e) => e.k)) + 50;

const scen = [];
for (const [kind, gen] of Object.entries(KINDS))
  for (let i = 0; i < NPT; i++) {
    const q0 = pose(), ev = gen(q0);
    scen.push({ kind, q0, ev, N: ticks(ev) });
  }

// ---- firmware (a blocchi: l'output testuale è grande) ----
function runFw(scen) {
let input = '';
for (const s of scen) {
  input += `S ${s.q0.join(' ')} ${s.N}\n`;
  for (const e of s.ev) input += e.c === 'M' ? `M ${e.k} ${e.f} ${e.t.join(' ')}\n` : `${e.c} ${e.k}\n`;
  input += 'E\n';
}
const out = execFileSync(BIN, { input, maxBuffer: 1 << 30 }).toString().split('\n');
let li = 0;
const fw = scen.map((s) => {
  if (out[li++] !== 'S') throw new Error('output firmware non allineato');
  const tr = [], rej = [];
  while (tr.length < s.N) {
    const l = out[li++];
    if (l.startsWith('R ')) { rej.push(l); continue; }
    const a = l.split(' ').map(Number);
    tr.push({ q: a.slice(0, 4), v: a.slice(4, 8), moving: !!a[8] });
  }
  return { tr, rej };
});
return fw;
}

// ---- web (come main.js in simulazione: validate, poi sim.move/stop/halt, step a 50 Hz) ----
const runWeb = (scen) => scen.map((s) => {
  const m = new Motion(s.q0), tr = [], rej = [];
  for (let k = 0; k < s.N; k++) {
    for (const e of s.ev) {
      if (e.k !== k) continue;
      if (e.c === 'M') { if (validate(e.t)) rej.push(k); else { m.enabled = true; m.move(e.t, e.f); } }
      else if (e.c === 'T') m.stop();
      else m.halt();
    }
    m.step(DT);
    tr.push({ q: [...m.q], v: [...m.v], moving: m.moving });
  }
  return { tr, rej };
});

// ---- metriche ----
function analyze(s, tr) {
  const r = { limV: 0, vr: 0, ar: 0, eMin: Infinity, eMax: -Infinity, arrive: -1, stall: false, final: tr.at(-1).q, sync: 0, lim: 0 };
  let prev = s.q0, vprev = [0, 0, 0, 0];
  const fmax = Math.max(...s.ev.filter((e) => e.c === 'M').map((e) => e.f));
  const hk = new Set(s.ev.filter((e) => e.c === 'H').map((e) => e.k)); // estop: arresto istantaneo voluto
  tr.forEach((t, k) => {
    const v = t.q.map((x, j) => (x - prev[j]) / DT);
    for (let j = 0; j < 4; j++) {
      r.vr = Math.max(r.vr, Math.abs(v[j]) / (VMAX[j] * fmax));
      if (!hk.has(k)) r.ar = Math.max(r.ar, Math.abs(v[j] - vprev[j]) / DT / AMAX[j]);
      if (t.q[j] < cal[j].min - 0.011 || t.q[j] > cal[j].max + 0.011) r.lim++;
      r.limV = Math.max(r.limV, cal[j].min - t.q[j], t.q[j] - cal[j].max);
    }
    const e = t.q[1] - t.q[2];
    r.eMin = Math.min(r.eMin, e); r.eMax = Math.max(r.eMax, e);
    if (t.moving) r.arrive = -1; else if (r.arrive < 0) r.arrive = k;
    prev = t.q; vprev = v;
  });
  r.stall = tr.at(-1).moving;
  if (s.kind === 'single') {
    // sincronizzazione: avanzamento normalizzato uguale per tutti i giunti
    const d = s.ev[0].t.map((x, j) => x - s.q0[j]);
    const big = d.map((x) => Math.abs(x) > 0.5);
    for (const t of tr) {
      const pr = t.q.map((x, j) => (x - s.q0[j]) / d[j]).filter((_, j) => big[j]);
      if (pr.length > 1) r.sync = Math.max(r.sync, Math.max(...pr) - Math.min(...pr));
    }
  }
  return r;
}

const agg = {};
const worst = {};
const problems = [];
for (let c0 = 0; c0 < scen.length; c0 += 250) {
const part = scen.slice(c0, c0 + 250), fw = runFw(part), web = runWeb(part);
part.forEach((s, i) => {
  const a = analyze(s, fw[i].tr), b = analyze(s, web[i].tr);
  let dq = 0;
  fw[i].tr.forEach((t, k) => { for (let j = 0; j < 4; j++) dq = Math.max(dq, Math.abs(t.q[j] - web[i].tr[k].q[j])); });
  const dfin = Math.max(...a.final.map((x, j) => Math.abs(x - b.final[j])));
  const g = (agg[s.kind] ??= { n: 0, dqMax: 0, dqMean: 0, dFinalMax: 0, dArriveMax: 0, rejDiff: 0,
    fw: { vr: 0, ar: 0, nAcc: 0, eMin: Infinity, eMax: -Infinity, stall: 0, lim: 0, limV: 0, sync: 0 },
    web: { vr: 0, ar: 0, nAcc: 0, eMin: Infinity, eMax: -Infinity, stall: 0, lim: 0, limV: 0, sync: 0 } });
  g.n++;
  g.dqMax = Math.max(g.dqMax, dq);
  g.dqMean += dq / NPT;
  g.dFinalMax = Math.max(g.dFinalMax, dfin);
  if (a.arrive >= 0 && b.arrive >= 0) g.dArriveMax = Math.max(g.dArriveMax, Math.abs(a.arrive - b.arrive));
  if (fw[i].rej.length !== web[i].rej.length) g.rejDiff++;
  for (const [x, G] of [[a, g.fw], [b, g.web]]) {
    G.vr = Math.max(G.vr, x.vr); G.ar = Math.max(G.ar, x.ar); G.sync = Math.max(G.sync, x.sync);
    G.eMin = Math.min(G.eMin, x.eMin); G.eMax = Math.max(G.eMax, x.eMax); G.stall += x.stall; G.lim += x.lim > 0; G.limV = Math.max(G.limV, x.limV); G.nAcc += x.ar > 1.3;
  }
  for (const [lab, x, rj] of [['fw', a, fw[i].rej], ['web', b, web[i].rej]]) {
    const why = [x.stall && 'fermo a metà', x.ar > 1.2 && `acc ${x.ar.toFixed(2)}x amax`, (x.eMin < 20 - 2e-3 || x.eMax > 150 + 2e-3) && 'vincolo violato', x.lim && 'limiti violati'].filter(Boolean);
    if (why.length && problems.filter((p) => p.lato === lab && p.kind === s.kind).length < 3) problems.push({ lato: lab, kind: s.kind, why, rej: rj, q0: s.q0, ev: s.ev, N: s.N });
  }
  if (!worst[s.kind] || dq > worst[s.kind].dq) worst[s.kind] = { dq, q0: s.q0, ev: s.ev };
});
}
const R = (x) => (Number.isFinite(x) ? +x.toFixed(4) : x);
// (arrotondamento in uscita: replacer di JSON.stringify)
const res = { scenari: scen.length, tick: scen.reduce((s, x) => s + x.N, 0), agg, peggiori: Object.fromEntries(Object.entries(worst).map(([k, w]) => [k, { dq: R(w.dq), q0: w.q0, ev: w.ev }])) };
writeFileSync(join(HERE, 'build', 'problemi.json'), JSON.stringify(problems, null, 1));
console.log(JSON.stringify(res, (k, v) => (typeof v === 'number' ? R(v) : v), 1));
// riepilogo leggibile su stderr
console.error(`${res.scenari} scenari, ${res.tick} tick a 50 Hz`);
console.error('tipo        dq max(°)  dfin(°)  darr(tick)  | fw: acc/amax  n>1.3  th2-phi min..max  fermi | web: idem');
for (const [k, g] of Object.entries(agg)) console.error(`${k.padEnd(10)}  ${R(g.dqMax).toString().padStart(8)}  ${R(g.dFinalMax).toString().padStart(7)}  ${String(g.dArriveMax).padStart(10)}  | ${R(g.fw.ar)}  ${g.fw.nAcc}  ${R(g.fw.eMin)}..${R(g.fw.eMax)}  ${g.fw.stall} | ${R(g.web.ar)}  ${g.web.nAcc}  ${R(g.web.eMin)}..${R(g.web.eMax)}  ${g.web.stall}`);
// criteri: firmware e twin sempre nel vincolo, mai fermi a metà, stesso arrivo; scarto di traiettoria piccolo
const bad = Object.values(agg).some((g) => g.fw.eMin < 20 - 2e-3 || g.fw.eMax > 150 + 2e-3 || g.web.eMin < 20 - 2e-3 || g.web.eMax > 150 + 2e-3 || g.fw.stall || g.web.stall || g.dFinalMax > 0.01 || g.dqMax > 0.5);
process.exit(bad ? 1 : 0);
