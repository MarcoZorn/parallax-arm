// Punto 3: IK/FK di web/src/robot.js su griglie dense, punti casuali, bordi, asse di yaw, input estremi.
// Quantifica anche cosa si perde senza la soluzione "all'indietro" (q1 ± 180, TCP dietro l'asse di yaw).
// Uso: node ikfk.mjs -> JSON con le metriche, exit 1 se KO.
import { readFileSync } from 'node:fs';
import { fk, ik, solve, validate, setParams, P, PAR, cal } from '../../web/src/robot.js';

setParams(JSON.parse(readFileSync(new URL('../../web/public/models/rig.json', import.meta.url))).params);
const D = Math.PI / 180;
let seed = 4242;
const rnd = () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
const front = (p, g) => { const s = solve(p, g); return s.ok ? s.q : null; }; // IK del contratto (robot.js)
// soluzione all'indietro, solo per misurare: base girata di 180°, r = -hypot - L3
function back({ x, y, z }, g) {
  const a = Math.atan2(y, x) / D, q1 = a > 0 ? a - 180 : a + 180, r = -Math.hypot(x, y) - P.L3, zz = z - P.base_h - P.sh_h - P.tcp_dz;
  const c = (r * r + zz * zz - P.L1 ** 2 - P.L2 ** 2) / (2 * P.L1 * P.L2);
  if (!(Math.abs(c) <= 1)) return null;
  const e = Math.acos(c), th2 = Math.atan2(zz, r) + Math.atan2(P.L2 * Math.sin(e), P.L1 + P.L2 * Math.cos(e));
  const q = [q1, th2 / D, (th2 - e) / D, g];
  return validate(q) ? null : q;
}
const out = { params: { L3: P.L3, tcp_dz: P.tcp_dz } };
let bad = false;

// A. griglia di giunti densa: IK(FK(q)) = q
{
  const r = { pose: 0, dietroAsse: 0, vicinoAsse: 0, frontOk: 0, backOk: 0, maxDq: 0, maxDp: 0, fail: [] };
  for (const q1 of [-90, -60, -30, 0, 30, 60, 90])
    for (let th2 = cal[1].min; th2 <= cal[1].max + 1e-9; th2 += 0.25)
      for (let phi = cal[2].min; phi <= cal[2].max + 1e-9; phi += 0.25) {
        const q = [q1, th2, phi, 20];
        if (validate(q)) continue;
        r.pose++;
        const R = P.L1 * Math.cos(th2 * D) + P.L2 * Math.cos(phi * D) + P.L3;
        if (R < 0) r.dietroAsse++;
        if (Math.abs(R) < 1) { r.vicinoAsse++; continue; } // sull'asse q1 non è definito
        const p = fk(q);
        const f = front(p, 20);
        if (f && f.every((x, j) => Math.abs(x - q[j]) < 1e-6)) {
          r.frontOk++;
          r.maxDq = Math.max(r.maxDq, ...f.map((x, j) => Math.abs(x - q[j])));
          r.maxDp = Math.max(r.maxDp, dist(fk(f), p));
        } else {
          const b = back(p, 20);
          if (R < 0 && b && b.every((x, j) => Math.abs(x - q[j]) < 1e-6)) r.backOk++;
          else if (r.fail.length < 5) r.fail.push({ q, f });
        }
      }
  r.quotaDietro = +(r.dietroAsse / r.pose).toFixed(4);
  out.grigliaGiunti = r;
  // ogni posa valida è ritrovata: dall'IK del contratto, o (TCP dietro l'asse) solo da quella all'indietro
  if (r.fail.length || r.maxDp > 0.01 || r.maxDq > 1e-6) bad = true;
}

// B. volume cartesiano raggiungibile (passo 5 mm) e fetta raggiungibile solo all'indietro (passo 1 mm vicino all'asse)
{
  const r = { punti5mm: 0, maxDp: 0, soloBack1mm: 0 };
  for (let x = -250; x <= 260; x += 5)
    for (let y = -260; y <= 260; y += 5)
      for (let z = -60; z <= 340; z += 5) {
        const p = { x, y, z }, f = front(p, 0);
        if (!f) continue;
        r.punti5mm++;
        r.maxDp = Math.max(r.maxDp, dist(fk(f), p));
      }
  for (let x = -30; x <= 30; x += 1)
    for (let y = -30; y <= 30; y += 1)
      for (let z = -60; z <= 340; z += 1) if (!front({ x, y, z }, 0) && back({ x, y, z }, 0)) r.soloBack1mm++;
  r.volumeCm3 = +((r.punti5mm * 125) / 1000).toFixed(0);
  r.volumePersoCm3 = +(r.soloBack1mm / 1000).toFixed(2);
  r.quotaPersa = +(r.volumePersoCm3 / r.volumeCm3).toFixed(5);
  out.volume = r;
  if (r.maxDp > 0.01) bad = true;
}

// C. punti casuali (1e5) e bordi: ogni soluzione accettata è valida e torna sul punto
{
  const r = { n: 0, ok: 0, maxDp: 0, invalidiAccettati: 0 };
  for (let i = 0; i < 100000; i++) {
    const p = { x: -260 + 520 * rnd(), y: -260 + 520 * rnd(), z: -60 + 400 * rnd() };
    r.n++;
    const s = solve(p, 30 * rnd());
    if (!s.ok) continue;
    r.ok++;
    if (validate(s.q)) r.invalidiAccettati++;
    r.maxDp = Math.max(r.maxDp, dist(fk(s.q), p));
  }
  // bordo dello sbraccio: punti a distanza max/min dall'asse spalla (c = ±1) e appena fuori
  let edge = 0;
  for (let a = -180; a < 180; a += 0.5)
    for (const k of [1 - 1e-12, 1, 1 + 1e-9]) {
      const L = (P.L1 + P.L2) * k, zz = L * Math.sin(a * D), rr = L * Math.cos(a * D) + P.L3;
      const p = { x: rr, y: 0, z: zz + P.base_h + P.sh_h + P.tcp_dz };
      const s = solve(p, 0);
      if (s.ok) edge++; // e ~ 0 è fuori vincolo: mai accettato
      if (s.q && s.q.some((x) => !Number.isFinite(x))) r.invalidiAccettati++;
    }
  r.bordoAccettati = edge;
  out.casuali = r;
  if (r.invalidiAccettati || r.maxDp > 0.01 || edge) bad = true;
}

// D. condizionamento: |dq/dp| massimo (°/mm) sulla regione valida, e continuità sotto perturbazione 1e-6 mm
{
  let kmax = 0, jump = 0;
  for (let th2 = cal[1].min; th2 <= cal[1].max; th2 += 1)
    for (let phi = cal[2].min; phi <= cal[2].max; phi += 1) {
      const e = th2 - phi;
      if (e < PAR[0] || e > PAR[1]) continue;
      // J (r,z) <- (th2,phi) in mm/rad; norma di J^-1 = 1/sigma_min
      const a = -P.L1 * Math.sin(th2 * D), b = -P.L2 * Math.sin(phi * D), c = P.L1 * Math.cos(th2 * D), d = P.L2 * Math.cos(phi * D);
      const t = a * a + b * b + c * c + d * d, det = Math.abs(a * d - b * c);
      const smin = Math.sqrt((t - Math.sqrt(Math.max(0, t * t - 4 * det * det))) / 2);
      kmax = Math.max(kmax, 1 / smin / D);
      const q = [0, th2, phi, 0], p = fk(q);
      if (Math.abs(p.x) < 1) continue;
      const s1 = solve(p, 0), s2 = solve({ ...p, x: p.x + 1e-6, z: p.z - 1e-6 }, 0);
      if (s1.ok && s2.ok) jump = Math.max(jump, ...s1.q.map((x, j) => Math.abs(x - s2.q[j])));
    }
  out.condizionamento = { gradiPerMmMax: +kmax.toFixed(3), saltoPerPerturbazione1e6: jump };
  if (jump > 1e-3) bad = true;
}

// E. singolarità dell'asse di yaw: il gizmo che passa a 1 mm dall'asse fa saltare q1 (base che gira di colpo)
{
  const r = { saltoQ1Max: 0, dove: null };
  for (const dir of [0, 30, 60, 90]) for (const off of [-1, 1]) {
    let prev = null;
    for (let s = 20; s >= -20; s -= 0.5) {
      const p = { x: s * Math.cos(dir * D) - off * Math.sin(dir * D), y: s * Math.sin(dir * D) + off * Math.cos(dir * D), z: 200 };
      const f = front(p, 0);
      if (f && prev && Math.abs(f[0] - prev[0]) > r.saltoQ1Max) { r.saltoQ1Max = Math.abs(f[0] - prev[0]); r.dove = { dir, off, passoMm: 0.5 }; }
      if (f) prev = f;
    }
  }
  out.asseYaw = r;
}

// F. input estremi: mai eccezioni, mai soluzioni non finite
{
  const vals = [NaN, Infinity, -Infinity, 1e308, -1e308, 0, -0, 1e-320, '12', null, undefined, {}, []];
  let n = 0, thrown = 0, nonFinite = 0;
  for (const x of vals) for (const y of vals) for (const z of vals) {
    n++;
    try {
      const s = solve({ x, y, z }, 0);
      if (s.ok && !s.q.every(Number.isFinite)) nonFinite++;
      const f = fk([x, y, z, 0]);
      void f;
    } catch { thrown++; }
  }
  out.estremi = { casi: n, eccezioni: thrown, soluzioniNonFinite: nonFinite };
  if (thrown || nonFinite) bad = true;
}

console.log(JSON.stringify(out, null, 1));
process.exit(bad ? 1 : 0);
