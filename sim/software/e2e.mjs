// Punto 5: protocollo end-to-end. Finto ESP32 (fake_esp32.mjs, regole di main.cpp) e client = web/src/link.js
// importato così com'è (Node ha WebSocket, EventTarget, CustomEvent). Uso: node e2e.mjs, exit 1 se KO.
import assert from 'node:assert/strict';
import { startDevice } from './fake_esp32.mjs';
import { Link } from '../../web/src/link.js';
import { duration } from '../../web/src/motion.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
async function test(name, fn) {
  const t0 = performance.now();
  try { const note = await fn(); results.push({ name, ok: true, ms: Math.round(performance.now() - t0), note }); }
  catch (e) { results.push({ name, ok: false, err: e.message }); }
}

// client: Link + ultimo state, errori, cal, stati di connessione
function client(url) {
  const l = new Link(), c = { l, state: null, errs: [], cals: [], status: [], hello: 0, nState: 0 };
  l.addEventListener('status', (e) => c.status.push(e.detail));
  l.addEventListener('msg', (e) => {
    const m = e.detail;
    if (m.t === 'state') { c.state = m; c.nState++; }
    else if (m.t === 'err') c.errs.push(m.msg);
    else if (m.t === 'cal') c.cals.push(m);
    else if (m.t === 'hello') c.hello++;
  });
  c.stale = setInterval(() => l.checkStale(), 100);
  l.connect(url);
  c.close = () => { clearInterval(c.stale); l.disconnect(); };
  return c;
}
async function until(pred, ms = 3000, what = 'condizione') {
  const t0 = performance.now();
  while (!pred()) { if (performance.now() - t0 > ms) throw new Error(`timeout: ${what}`); await sleep(5); }
}
const lastErr = async (c, n0, re) => { await until(() => c.errs.length > n0, 1000, `err ${re}`); assert.match(c.errs.at(-1), re); };
const near = (a, b, t = 0.011) => a.every((x, j) => Math.abs(x - b[j]) <= t);

const D = await startDevice();
const c = client(D.url);
await until(() => c.state, 2000, 'primo state');

await test('hello e state a 20 Hz', async () => {
  assert.equal(c.hello, 1);
  const n0 = c.nState;
  await sleep(1000);
  const hz = c.nState - n0;
  assert.ok(hz >= 17 && hz <= 22, `${hz} state/s`);
  assert.deepEqual(Object.keys(c.state).sort(), ['enabled', 'moving', 'q', 't', 'target', 'us'].sort());
  return `${hz} state/s`;
});

await test('cal_get: taratura e home di default', async () => {
  const n0 = c.cals.length;
  c.l.calGet();
  await until(() => c.cals.length > n0);
  const m = c.cals.at(-1);
  assert.equal(m.cal.length, 4);
  assert.deepEqual(m.home, [0, 90, 0, 30]);
  assert.deepEqual(m.cal.map((x) => x.q_ref), [0, 90, 0, 29.5]);
});

await test('move prima di enable: rifiutato', async () => {
  const n0 = c.errs.length;
  c.l.move([10, 90, 0, 30], 0.5);
  await lastErr(c, n0, /disabilitato/);
  assert.equal(c.state.enabled, false);
});

await test('enable: PWM agganciato sulla home', async () => {
  c.l.enable();
  await until(() => c.state.enabled);
  assert.ok(D.dev.attached);
  assert.ok(near(c.state.q, [0, 90, 0, 30]));
  assert.ok(near(c.state.us, [1500, 1500, 1500, 1500 + 0.5 * 19.89], 0.02));
});

await test('move valido: arriva nel tempo del profilo', async () => {
  const tgt = [40, 120, 30, 10], t0 = performance.now();
  c.l.move(tgt, 1);
  await until(() => c.state.moving, 500, 'moving');
  await until(() => !c.state.moving, 5000, 'arrivo');
  const T = (performance.now() - t0) / 1000, Te = duration([0, 90, 0, 30], tgt, 1);
  assert.ok(near(c.state.q, tgt), `q ${c.state.q}`);
  assert.ok(Math.abs(T - Te) < 0.25, `durata ${T} attesa ${Te}`);
  return `durata ${T.toFixed(2)} s, profilo ${Te.toFixed(2)} s`;
});

await test('move fuori vincolo / fuori limiti / v non valido / q corto: rifiutati, il braccio resta fermo', async () => {
  const q0 = [...c.state.q];
  for (const [m, re] of [
    [{ t: 'move', q: [0, 30, 18, 30], v: 1 }, /fuori vincolo: th2-phi=12/],
    [{ t: 'move', q: [95, 90, 0, 30], v: 1 }, /fuori limiti: q1=95/],
    [{ t: 'move', q: [0, 90, 0, 30], v: 0 }, /v fuori/],
    [{ t: 'move', q: [0, 90, 0, 30], v: 2 }, /v fuori/],
    [{ t: 'move', q: [0, 90, 0], v: 1 }, /servono 4 valori/],
    [{ t: 'move', q: [0, '90', 0, 30], v: 1 }, /fuori limiti: th2=nan/],
    [{ t: 'move', q: [0, 90, 0, 1e400], v: 1 }, /fuori limiti: g/],
  ]) {
    const n0 = c.errs.length;
    c.l.send(m);
    await lastErr(c, n0, re);
  }
  await sleep(100);
  assert.ok(near(c.state.q, q0) && !c.state.moving);
});

await test('target sul bordo arrotondato a 0.01 (th2-phi = 20.00, in float 19.999998): accettato', async () => {
  const n0 = c.errs.length;
  c.l.move([0, 40.01, 20.01, 30], 1); // rifiutato dal firmware prima della tolleranza
  await until(() => c.state.moving, 500);
  await until(() => !c.state.moving, 5000);
  assert.equal(c.errs.length, n0);
  assert.ok(near(c.state.q, [0, 40.01, 20.01, 30]));
});

await test('stop a metà moto: decelera e tiene la posizione', async () => {
  c.l.move([-60, 60, -20, 50], 1);
  await sleep(500);
  c.l.stop();
  await until(() => !c.state.moving, 3000);
  const q = c.state.q;
  assert.ok(q[0] < 0 && q[0] > -60, `q1 ${q[0]}`);
  assert.ok(near(c.state.target, q), 'target = posa di arresto');
  await sleep(300);
  assert.ok(near(c.state.q, q), 'fermo');
});

await test('raw: rifiutato in moto, poi impulso diretto e posa coerente', async () => {
  c.l.move([0, 90, 0, 30], 1);
  await until(() => c.state.moving, 500);
  let n0 = c.errs.length;
  c.l.raw(1, 1600);
  await lastErr(c, n0, /braccio in moto/);
  await until(() => !c.state.moving, 5000);
  c.l.raw(1, 1600);
  await until(() => Math.abs(c.state.us[1] - 1600) < 0.02, 1000, 'us 1600');
  assert.ok(Math.abs(c.state.q[1] - (90 + 100 / 11.11)) < 0.01);
  n0 = c.errs.length;
  c.l.send({ t: 'raw', j: 7, us: 1500 });
  await lastErr(c, n0, /giunto o us non validi/);
  n0 = c.errs.length;
  c.l.send({ t: 'raw', j: 1.5, us: 1500 });
  await lastErr(c, n0, /giunto o us non validi/);
  c.l.raw(1, 99999); // clamp a 2500
  await until(() => Math.abs(c.state.us[1] - 2500) < 0.02, 1000, 'clamp 2500');
  c.l.raw(1, 1500);
  await until(() => Math.abs(c.state.q[1] - 90) < 0.01, 1000);
});

await test('cal_set: impulso invariato, posa riletta; rifiuti (k=0, min>max, in moto, campi null)', async () => {
  const us0 = [...c.state.us];
  const cal = c.cals.at(-1).cal.map((x) => ({ ...x }));
  cal[0].k = -12; cal[0].ref_us = 1490;
  let n0 = c.cals.length;
  c.l.calSet(cal);
  await until(() => c.cals.length > n0);
  await sleep(120);
  assert.ok(near(c.state.us, us0, 0.02), `us ${c.state.us} vs ${us0}`);
  assert.ok(Math.abs(c.state.q[0] - (0 + (1500 - 1490) / -12)) < 0.01, `q1 riletto ${c.state.q[0]}`);
  for (const bad of [
    cal.map((x, j) => (j === 2 ? { ...x, k: 0 } : x)),
    cal.map((x, j) => (j === 1 ? { ...x, min: 100, max: 50 } : x)),
    cal.map((x, j) => (j === 3 ? null : x)),
    cal.map((x, j) => (j === 0 ? { ...x, ref_us: 3000 } : x)),
  ]) {
    n0 = c.errs.length;
    c.l.calSet(bad);
    await lastErr(c, n0, /taratura non valida/);
  }
  n0 = c.errs.length;
  c.l.calSet(cal.slice(0, 3));
  await lastErr(c, n0, /servono 4 giunti/);
  c.l.move([30, 90, 0, 30], 0.3);
  await until(() => c.state.moving, 500);
  n0 = c.errs.length;
  c.l.calSet(cal);
  await lastErr(c, n0, /in moto/);
  await until(() => !c.state.moving, 5000);
});

await test('cal_save e home_set: sopravvivono al reboot', async () => {
  c.l.calSave();
  const n0 = c.cals.length;
  c.l.homeSet();
  await until(() => c.cals.length > n0);
  const home = c.cals.at(-1).home;
  assert.ok(near(home, c.state.q), `home ${home}`);
  await sleep(50);
  D.dev.reboot();
  await until(() => !c.state.enabled, 500);
  const n1 = c.cals.length;
  c.l.calGet();
  await until(() => c.cals.length > n1);
  assert.equal(c.cals.at(-1).cal[0].k, -12);
  assert.ok(near(c.cals.at(-1).home, home));
  c.l.enable();
  await until(() => c.state.enabled);
  assert.ok(near(c.state.q, home), 'enable dopo reboot: posa = home salvata');
});

await test('estop in moto: PWM sganciato subito; comandi durante estop rifiutati', async () => {
  c.l.move([-40, 120, 40, 40], 1);
  await sleep(300);
  c.l.estop();
  await until(() => !c.state.enabled, 200, 'enabled=false');
  assert.equal(D.dev.attached, false);
  const q = [...c.state.q];
  await sleep(200);
  assert.ok(near(c.state.q, q) && !c.state.moving, 'congelato');
  for (const [send, re] of [[() => c.l.move([0, 90, 0, 30], 1), /disabilitato/], [() => c.l.raw(0, 1500), /raw solo con enabled/]]) {
    const n0 = c.errs.length;
    send();
    await lastErr(c, n0, re);
  }
  c.l.stop(); // ignorato
  await sleep(100);
  assert.equal(c.state.enabled, false);
  c.l.enable(); // riaggancia sulla posa congelata, senza salti
  await until(() => c.state.enabled);
  assert.ok(near(c.state.q, q));
});

await test('estop nello stesso pacchetto dopo enable+move (gara coda/estop di main.cpp)', async () => {
  c.l.estop();
  await until(() => !c.state.enabled);
  // tre messaggi arrivati insieme: onWs accoda enable e move, estop alza solo il flag;
  // loop() esegue prima l'estop, poi svuota la coda -> riabilita e muove
  D.dev.receive(0, '{"t":"enable"}');
  D.dev.receive(0, '{"t":"move","q":[20,90,0,30],"v":1}');
  D.dev.receive(0, '{"t":"estop"}');
  await sleep(150);
  const bug = D.dev.enabled;
  if (bug) { c.l.estop(); await until(() => !c.state.enabled); }
  return bug ? 'BUG riprodotto: dopo estop il braccio resta abilitato e in moto (main.cpp, vedi REPORT)' : 'ok';
});

await test('messaggi malformati verso il device: err, nessun crash, stato invariato', async () => {
  c.l.enable();
  await until(() => c.state.enabled);
  const q0 = [...c.state.q];
  const raw = ['{"t":', 'null', '[1,2]', '"move"', '{"t":5}', '{"t":"MOVE"}', '{}', '{"t":"move","q":"0,90,0,30"}', '{"t":"move","q":{"0":1}}',
    '{"t":"cal_set","cal":"x"}', '{"t":"raw"}', JSON.stringify({ t: 'move', q: q0, v: '1' }), '{"t":"move","q":[0,90,0,30],"v":-0}',
    '{"t":"move","q":[1e999,90,0,30]}', '{"t":"move","q":[0,90,0,30],"v":1e-50}', 'x'.repeat(5000), '{"t":"' + 'a'.repeat(3000) + '"}'];
  let nErr = 0;
  for (const s of raw) { const n0 = c.errs.length; c.l.ws.send(s); await sleep(25); nErr += c.errs.length > n0; }
  await sleep(100);
  // v stringa -> 0.5 come ArduinoJson (accettato in silenzio): qui verso la posa attuale, nessun moto
  assert.ok(near(c.state.q, q0), 'posa invariata');
  return `${raw.length} messaggi, ${nErr} risposte err`;
});

await test('watchdog: il client cade durante un moto -> stop', async () => {
  const c2 = client(D.url);
  await until(() => c2.state, 1000);
  c.close();
  c2.l.move([80, 140, 50, 0], 0.4);
  await until(() => c2.state.moving, 500);
  await sleep(200);
  c2.close(); // nessun client connesso
  await until(() => !D.dev.pl.moving, 3000, 'fermo');
  const q = D.dev.pl.q;
  assert.ok(q[0] < 79, `fermato prima del target (q1 ${q[0].toFixed(1)})`);
});

await test('caduta del server: riconnessione con backoff e ripresa dello stato', async () => {
  const c3 = client(D.url);
  await until(() => c3.state, 1000);
  const port = D.port, dev = D.dev;
  await D.close();
  await until(() => c3.status.some((s) => s.state === 'retry'), 1000, 'retry');
  await sleep(1600);
  const delays = c3.status.filter((s) => s.state === 'retry').map((s) => s.delay);
  const D2 = await startDevice({ port, dev });
  const n0 = c3.hello;
  await until(() => c3.hello > n0, 10000, 'riconnesso');
  await until(() => c3.l.connected && c3.state, 1000);
  c3.close();
  await D2.close();
  assert.deepEqual(delays.slice(0, 3), [500, 1000, 2000]);
  return `backoff ${delays.join(', ')} ms`;
});

await test('link appeso (device muto, TCP aperto): chiuso dopo 2 s e riaperto', async () => {
  const D3 = await startDevice();
  const c4 = client(D3.url);
  await until(() => c4.state, 1000);
  D3.setMute(true);
  const t0 = performance.now();
  await until(() => c4.status.some((s) => s.state === 'retry'), 4000, 'chiusura per silenzio');
  const dt = performance.now() - t0;
  D3.setMute(false);
  const n0 = c4.hello;
  await until(() => c4.hello > n0, 3000, 'riaperto');
  c4.close();
  await D3.close();
  assert.ok(dt > 1900 && dt < 2700, `${dt} ms`);
  return `chiuso dopo ${Math.round(dt)} ms`;
});

for (const r of results) console.log(`${r.ok ? 'OK ' : 'KO '} ${r.name}${r.ms != null ? ` (${r.ms} ms)` : ''}${r.note ? ` — ${r.note}` : ''}${r.err ? ` — ${r.err}` : ''}`);
const ko = results.filter((r) => !r.ok).length;
console.log(`\n${results.length} test, ${ko} falliti`);
process.exit(ko ? 1 : 0);
