// Punto 4 (web) + 5: la web app compilata (firmware/data) in Chrome headless, servita dal finto ESP32.
// Il device manda messaggi malformati: la UI non deve lanciare eccezioni né mandare comandi;
// poi i pulsanti (Abilita, Home, Esc) devono produrre i comandi giusti. CDP via WebSocket di Node.
// Uso: node ui_fuzz.mjs (serve `npm run build` fatto). Senza Chrome: SALTATO, exit 0.
import { spawn, execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startDevice } from './fake_esp32.mjs';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chrome = ['google-chrome-stable', 'chromium', 'chromium-browser', 'google-chrome'].find((c) => { try { execFileSync('which', [c], { stdio: 'ignore' }); return true; } catch { return false; } });
if (!chrome) { console.log('SALTATO: Chrome/Chromium non trovato'); process.exit(0); }

// Chrome mette il suo socket in TMPDIR: con un percorso lungo (> ~100 caratteri) non parte, si ripiega su /tmp
const TMP = tmpdir().length > 60 ? '/tmp' : tmpdir();
const prof = mkdtempSync(join(TMP, 'braccio-chrome-'));
const proc = spawn(chrome, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${prof}`, '--no-first-run', '--no-default-browser-check',
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=1280,900', 'about:blank'], { stdio: 'ignore', env: { ...process.env, TMPDIR: TMP } });
const cleanup = () => { try { proc.kill('SIGKILL'); } catch {} try { rmSync(prof, { recursive: true, force: true }); } catch {} };
process.on('exit', cleanup);

async function until(pred, ms, what) {
  const t0 = performance.now();
  for (;;) { const v = await pred(); if (v) return v; if (performance.now() - t0 > ms) throw new Error(`timeout: ${what}`); await sleep(20); }
}

const port = await until(() => existsSync(join(prof, 'DevToolsActivePort')) && readFileSync(join(prof, 'DevToolsActivePort'), 'utf8').split('\n')[0], 30000, 'avvio Chrome');
const page = await until(async () => (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page'), 5000, 'pagina');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let nid = 0;
const pending = new Map(), exceptions = [], consoleErr = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id) { pending.get(m.id)?.(m); pending.delete(m.id); }
  else if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') consoleErr.push(m.params.args.map((a) => a.value ?? a.description).join(' '));
};
const cdp = (method, params = {}) => new Promise((r) => { const id = ++nid; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => (await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const text = (id) => ev(`document.getElementById(${JSON.stringify(id)})?.textContent`);
const click = (id) => ev(`document.getElementById(${JSON.stringify(id)}).click()`);
await cdp('Runtime.enable');

const results = [];
const check = (name, ok, note = '') => results.push({ name, ok: !!ok, note });

const D = await startDevice();
const sent = () => D.dev.rx.map((s) => { try { return JSON.parse(s); } catch { return { raw: s }; } });
const toUi = (s) => { for (const f of D.dev.clients.values()) f(typeof s === 'string' ? s : JSON.stringify(s)); };

await cdp('Page.navigate', { url: D.http });
await until(() => D.dev.clients.size > 0, 15000, 'la pagina si connette da sola (servita dal device)');
await until(() => D.dev.rx.length > 0, 3000, 'cal_get');
await until(async () => (await text('nState')) === 'connesso', 3000, 'stato connesso');
check('pagina servita dal device: si connette a ws://host/ws e chiede cal_get', sent().map((m) => m.t).join() === 'cal_get', sent().map((m) => m.t).join());
check('nessuna eccezione al caricamento (WebGL software)', exceptions.length === 0, exceptions.join(' | '));
await sleep(300);
check('modo LIVE con state a 20 Hz', (await text('fMode')) === 'LIVE · ESP32');

// ---- messaggi malformati dal device ----
const okCal = (over = {}) => [0, 1, 2, 3].map((j) => ({ ref_us: 1500, k: 11.11, q_ref: [0, 90, 0, 29.5][j], min: [-90, 20, -70, 0][j], max: [90, 160, 70, 59][j], ...over }));
const evil = [
  'non json', '{"t":', 'null', '42', '[]', '"state"', '{"t":5}', '{"t":null}', '{"t":"state"}', '{"t":"state","q":"abc"}', '{"t":"state","q":[1,2,3]}',
  '{"t":"state","q":[1,2,3,"4"]}', '{"t":"state","q":[1,null,3,4]}', '{"t":"state","q":[1e308,-1e308,0,0],"us":[1,2],"moving":"si","enabled":1,"target":"x"}',
  '{"t":"cal"}', '{"t":"cal","cal":"x"}', '{"t":"cal","cal":[null,null,null,null]}', '{"t":"cal","cal":[1,2,3,4]}', '{"t":"cal","cal":[{},{},{},{}]}',
  JSON.stringify({ t: 'cal', cal: okCal({ k: 0.5 }) }), JSON.stringify({ t: 'cal', cal: okCal({ ref_us: 9000 }) }),
  '{"t":"cal","cal":[' + Array(4).fill('{"__proto__":{"polluted":1},"ref_us":1500,"k":11.11,"q_ref":0,"min":-1e12,"max":1e12}').join(',') + '],"home":[0,90,0,30,5]}',
  '{"t":"err"}', '{"t":"err","msg":{"a":1}}', '{"t":"err","msg":"<img src=x onerror=window.__xss=1>"}',
  '{"t":"hello","fw":"<b id=xss2>x</b>","mode":"__proto__"}', '{"t":"hello","fw":null,"mode":"constructor"}', '{"t":"sconosciuto"}',
  JSON.stringify({ t: 'err', msg: 'x'.repeat(1 << 20) }), '['.repeat(200000) + ']'.repeat(200000),
];
const rx0 = D.dev.rx.length;
for (const m of evil) { toUi(m); await sleep(15); }
await sleep(400);
check('nessuna eccezione con ' + evil.length + ' messaggi malformati', exceptions.length === 0, exceptions.slice(0, 3).join(' | '));
check('nessun comando inviato in risposta', D.dev.rx.length === rx0, D.dev.rx.slice(rx0).join(' '));
check('niente XSS da err/hello', !(await ev('window.__xss === 1 || !!document.getElementById("xss2")')));
check('niente prototype pollution', !(await ev('({}).polluted === 1')));
// limiti assurdi ma "validi" applicati dalla UI: la pagina resta reattiva (inviluppo con tetto di punti)
check('UI reattiva dopo i messaggi', (await ev('1 + 1')) === 2);

// il device si riprende: taratura vera e state validi aggiornano la UI
D.dev.sendCal(0);
D.dev.pl.q = [10, 100, 20, 30]; // il prossimo state del device porta questa posa
D.dev.pl.target = [10, 100, 20, 30];
// l'HUD si aggiorna nel ciclo di rendering: con WebGL software e i modelli reali un fotogramma può superare i 300 ms
const hudOk = async () => (await ev('document.getElementById("fk0o").textContent')) === '10.0';
for (let t = 0; t < 5000 && !(await hudOk()); t += 100) await sleep(100);
{ const hud = await ev('document.getElementById("fk0o").textContent'); check('state valido dopo i malformati: HUD aggiornato', hud === '10.0', 'HUD=' + hud); }

// ---- comandi dalla UI ----
await sleep(200); // gli state veri del device riprendono il controllo
let n = D.dev.rx.length;
await click('bEnable');
await until(() => D.dev.enabled, 2000, 'enable');
check('Abilita -> {"t":"enable"}', sent().slice(n).some((m) => m.t === 'enable'));
await until(async () => (await text('fEn')) === 'ABILITATO', 2000, 'UI abilitata');
await ev('document.getElementById("vR").value = 0.8; document.getElementById("vR").dispatchEvent(new Event("input"))');
n = D.dev.rx.length;
await ev('document.getElementById("fk0n").value = 33.337; document.getElementById("fk0n").dispatchEvent(new Event("change"))');
await until(() => sent().slice(n).some((m) => m.t === 'move'), 2000, 'move da slider');
const mv = sent().slice(n).find((m) => m.t === 'move');
check('slider FK -> move con q arrotondati a 0.01 e v del cursore', mv.q[0] === 33.34 && mv.v === 0.8, JSON.stringify(mv));
await until(() => D.dev.pl.moving, 1000, 'device in moto');
n = D.dev.rx.length;
await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await until(() => !D.dev.enabled, 1000, 'estop');
check('Esc -> estop, PWM sganciato', sent().slice(n).some((m) => m.t === 'estop') && !D.dev.attached);
await sleep(300);
n = D.dev.rx.length;
await click('bHome');
await sleep(300);
check('Home durante estop: nessun move inviato', !sent().slice(n).some((m) => m.t === 'move'), sent().slice(n).map((m) => m.t).join());
n = D.dev.rx.length;
await ev('document.getElementById("fk1n").value = 30; document.getElementById("fk2n").value = 18; document.getElementById("fk2n").dispatchEvent(new Event("change"))');
await sleep(200);
check('target fuori vincolo dagli slider: nessun move inviato', !sent().slice(n).some((m) => m.t === 'move'));

// ---- caduta e ritorno del device ----
const p0 = D.port, dev = D.dev;
await D.close();
await until(async () => (await text('fMode')) === 'SIMULAZIONE', 3000, 'torna in simulazione');
const D2 = await startDevice({ port: p0, dev });
await until(async () => (await text('nState')) === 'connesso', 10000, 'riconnessione');
check('caduta del device: simulazione, poi riconnessione automatica', true);
check('nessuna eccezione in tutto il test', exceptions.length === 0, exceptions.slice(0, 3).join(' | '));
check('nessun console.error', consoleErr.length === 0, consoleErr.slice(0, 3).join(' | '));
await D2.close();
ws.close();

for (const r of results) console.log(`${r.ok ? 'OK ' : 'KO '} ${r.name}${r.note && !r.ok ? ` — ${r.note.slice(0, 300)}` : ''}`);
const ko = results.filter((r) => !r.ok).length;
console.log(`\n${results.length} controlli, ${ko} falliti`);
cleanup();
process.exit(ko ? 1 : 0);
