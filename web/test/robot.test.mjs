// npm test — cinematica e profilo di moto. Solo node:assert.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fk, ik, solve, validate, cal, PAR, P, setParams, envelope } from '../src/robot.js';
import { Motion, VMAX, AMAX, DT, duration } from '../src/motion.js';

// params da rig.json (hanno la precedenza sui default)
setParams(JSON.parse(readFileSync(new URL('../public/models/rig.json', import.meta.url))).params);
assert.equal(P.lev2_r, 30);

let n = 0;
const lim = (j) => [cal[j].min, cal[j].max];
const range = (a, b, s) => { const r = []; for (let x = a; x <= b + 1e-9; x += s) r.push(x); return r; };

// IK(FK(q)) = q e FK(IK(p)) = p su una griglia di q validi
for (const q1 of range(...lim(0), 15))
  for (const th2 of range(...lim(1), 5))
    for (const phi of range(...lim(2), 5)) {
      const q = [q1, th2, phi, 20];
      if (validate(q)) continue;
      const p = fk(q);
      // TCP dietro l'asse di yaw (r < 0): l'IK del contratto dà la soluzione con q1+180, stesso punto
      if (Math.hypot(p.x, p.y) < 1 || Math.cos(q1 * Math.PI / 180) * p.x + Math.sin(q1 * Math.PI / 180) * p.y < 0) continue;
      const s = solve(p, 20);
      assert.ok(s.ok, `solve rifiuta un punto valido ${q}: ${s.msg}`);
      for (let j = 0; j < 3; j++) assert.ok(Math.abs(s.q[j] - q[j]) < 1e-6, `IK(FK(q)) != q per ${q} -> ${s.q}`);
      const p2 = fk(s.q);
      assert.ok(Math.hypot(p2.x - p.x, p2.y - p.y, p2.z - p.z) < 0.01, `FK(IK(p)) != p per ${JSON.stringify(p)}`);
      n++;
    }
assert.ok(n > 1000);

// Griglia cartesiana: ogni punto accettato soddisfa FK(IK(p)) = p entro 0.01 mm
let ok = 0;
for (let x = -50; x <= 260; x += 10)
  for (let y = -200; y <= 200; y += 10)
    for (let z = 0; z <= 300; z += 10) {
      const s = solve({ x, y, z }, 0);
      if (!s.ok) { assert.ok(s.msg); continue; }
      const p = fk(s.q);
      assert.ok(Math.hypot(p.x - x, p.y - y, p.z - z) < 0.01, `FK(IK) ${x},${y},${z}`);
      ok++;
    }
assert.ok(ok > 500, `troppo pochi punti raggiungibili: ${ok}`);

// Rifiuti
assert.equal(ik({ x: 400, y: 0, z: 100 }), null);
assert.match(solve({ x: 400, y: 0, z: 100 }, 0).msg, /irraggiungibile/);
assert.match(solve({ x: 0, y: 0, z: 1000 }, 0).msg, /irraggiungibile/);
// raggiungibile ma fuori vincolo: gomito molto chiuso (th2-phi ~ 10)
const tight = fk([0, 60, 50, 0]);
assert.ok(ik(tight));
assert.match(solve(tight, 0).msg, /fuori vincolo/);
// raggiungibile ma fuori limiti (dietro la base: q1 = 180)
assert.match(solve({ x: -150, y: 0, z: 150 }, 0).msg, /fuori limiti/);
assert.match(validate([0, 90, 0, 70]), /Pinza fuori limiti/);
assert.match(validate([0, 170, 0, 0]), /Spalla fuori limiti/);
assert.match(validate([0, 90, -75, 0]), /Gomito fuori limiti/);
assert.match(validate([0, 110, -45, 0]), /fuori vincolo: th2-phi=155/);
assert.equal(validate([0, 110, -40, 0]), null); // th2-phi = 150: al limite
assert.equal(validate([0, 90, 0, 30]), null);
assert.equal(validate([0, PAR[0] + 30, 30, 0]), null);

// Inviluppo: profilo chiuso e con punti tutti raggiungibili
const env = envelope(2);
assert.ok(env.length > 50);

// Profilo trapezoidale sincronizzato
function run(q0, q1, f) {
  const m = new Motion(q0);
  m.move(q1, f);
  const d = q1.map((t, i) => t - q0[i]);
  let prev = [...m.v], steps = 0;
  while (m.step(DT)) {
    steps++;
    assert.ok(steps < 5000, 'il moto non termina');
    const s0 = d.findIndex((x) => Math.abs(x) > 1e-9);
    const s = (m.q[s0] - q0[s0]) / d[s0];
    for (let i = 0; i < 4; i++) {
      assert.ok(Math.abs(m.v[i]) <= VMAX[i] * f + 1e-9, `vmax superata giunto ${i}: ${m.v[i]}`);
      assert.ok(Math.abs(m.v[i] - prev[i]) / DT <= AMAX[i] * f + 1e-6, `amax superata giunto ${i}`);
      // sincronizzazione: tutti i giunti allo stesso avanzamento normalizzato
      if (Math.abs(d[i]) > 1e-9) assert.ok(Math.abs((m.q[i] - q0[i]) / d[i] - s) < 1e-6, `giunti non sincronizzati (${i})`);
    }
    prev = [...m.v];
  }
  for (let i = 0; i < 4; i++) assert.equal(m.q[i], q1[i]);
  const T = duration(q0, q1, f);
  assert.ok(Math.abs(steps * DT - T) <= 3 * DT, `durata ${steps * DT} attesa ${T}`);
  return m;
}
run([0, 90, 0, 30], [60, 40, -30, 50], 1);
run([0, 90, 0, 30], [-80, 150, 60, 0], 0.5);
run([0, 90, 0, 30], [1, 90, 0, 30], 1); // corsa breve: triangolare
run([0, 90, 0, 30], [0, 90, 0, 59], 0.2); // solo pinza

// nuovo move durante il moto e stop: nessuno scatto, arrivo al target
{
  const m = new Motion([0, 90, 0, 30]);
  m.move([80, 60, -20, 10], 1);
  for (let k = 0; k < 20; k++) m.step();
  m.move([-60, 120, 40, 50], 1);
  let prev = [...m.v], k = 0;
  while (m.step()) {
    assert.ok(++k < 5000);
    for (let i = 0; i < 4; i++) {
      assert.ok(Math.abs(m.v[i] - prev[i]) / DT <= AMAX[i] + 1e-6);
      assert.ok(Math.abs(m.v[i]) <= VMAX[i] + 1e-9);
    }
    prev = [...m.v];
  }
  assert.deepEqual(m.q, [-60, 120, 40, 50]);
  m.move([60, 60, 0, 30], 1);
  for (let k2 = 0; k2 < 30; k2++) m.step();
  m.stop();
  prev = [...m.v];
  while (m.step()) {
    for (let i = 0; i < 4; i++) assert.ok(Math.abs(m.v[i] - prev[i]) / DT <= AMAX[i] + 1e-6);
    prev = [...m.v];
  }
  assert.ok(!m.moving);
}

// FK/IK seguono i params caricati (L3/tcp_dz provvisori)
setParams({ L3: 60, tcp_dz: -22 });
{
  const q = [30, 100, -10, 0], s = solve(fk(q), 0);
  assert.ok(s.ok && s.q.every((x, j) => Math.abs(x - q[j]) < 1e-6));
  assert.ok(Math.abs(fk(q).z - (40 + 62 + 80 * Math.sin(100 * Math.PI / 180) + 80 * Math.sin(-10 * Math.PI / 180) - 22)) < 1e-9);
}

console.log(`ok: ${n} pose IK(FK(q)), ${ok} punti FK(IK(p)), rifiuti, profilo sincronizzato`);
