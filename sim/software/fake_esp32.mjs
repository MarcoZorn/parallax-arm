// Finto ESP32: stesso protocollo (docs/03) e stesse regole di firmware/src/main.cpp, in Node senza dipendenze.
// HTTP (web app da firmware/data con i .gz, /api/info) + WebSocket /ws con handshake e frame fatti a mano.
// Planner: web/src/motion.js (porting di motion.cpp, equivalenza in equiv.mjs). Float come sul device (Math.fround).
// Uso da solo: node fake_esp32.mjs [porta]  -> http://localhost:porta/ come se fosse braccio.local
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, normalize } from 'node:path';
import { Motion } from '../../web/src/motion.js';

const DATA = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'firmware', 'data');
const NJ = 4, US_MIN = 500, US_MAX = 2500, PAR = [35, 150], TOL = 1e-3, CTRL_MS = 20, STATE_MS = 50, QLEN = 16;
const NAME = ['q1', 'th2', 'phi', 'g'];
const f32 = Math.fround;
const g = (x) => String(+f32(x).toPrecision(6)); // %g
const r2 = (x) => Math.round(f32(x) * 100) / 100;
const calDefault = () => [
  { ref_us: 1500, k: f32(11.11), q_ref: 0, min: -90, max: 90 },
  { ref_us: 1500, k: f32(11.11), q_ref: 90, min: 20, max: 160 },
  { ref_us: 1500, k: f32(11.11), q_ref: 0, min: -70, max: 70 },
  { ref_us: 1500, k: f32(19.89), q_ref: f32(29.5), min: 0, max: 59 },
];
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
export const qToUs = (c, q) => clamp(f32(c.ref_us + c.k * (q - c.q_ref)), US_MIN, US_MAX);
export const usToQ = (c, us) => f32(c.q_ref + (us - c.ref_us) / c.k);

// check_target / check_cal di motion.cpp: null se ok, altrimenti il messaggio d'errore del firmware
export function checkTarget(q, cal) {
  for (let j = 0; j < NJ; j++)
    if (!Number.isFinite(q[j]) || q[j] < cal[j].min - TOL || q[j] > cal[j].max + TOL)
      return `fuori limiti: ${NAME[j]}=${Number.isNaN(q[j]) ? 'nan' : g(q[j])} [${g(cal[j].min)}, ${g(cal[j].max)}]`;
  const e = f32(q[1] - q[2]);
  if (e < PAR[0] - TOL || e > PAR[1] + TOL) return `fuori vincolo: th2-phi=${g(e)}`;
  return null;
}
export function checkCal(cal) {
  for (let j = 0; j < NJ; j++) {
    const c = cal[j];
    const ok = ['ref_us', 'k', 'q_ref', 'min', 'max'].every((f) => Number.isFinite(c[f])) && c.ref_us >= US_MIN && c.ref_us <= US_MAX && Math.abs(c.k) >= 1 && c.min < c.max;
    if (!ok) return `taratura non valida: giunto ${j}`;
  }
  return null;
}

// valori come li legge ArduinoJson: `x | default` dà default se il tipo non è quello chiesto
const num = (x, d) => (typeof x === 'number' ? f32(x) : d);
const int = (x, d) => (Number.isInteger(x) && Math.abs(x) <= 2 ** 31 - 1 ? x : d);

export class Device {
  constructor() {
    this.nvs = {}; // Preferences: sopravvive a reboot()
    this.clients = new Map(); // id -> send(text)
    this.nextId = 1;
    this.rx = []; // log dei messaggi ricevuti (per i test)
    this.boot();
  }

  boot() {
    this.cal = calDefault();
    this.home = [0, 90, 0, 30];
    if (this.nvs.cal && !checkCal(this.nvs.cal)) this.cal = structuredClone(this.nvs.cal);
    if (this.nvs.home && !checkTarget(this.nvs.home, this.cal)) this.home = [...this.nvs.home];
    this.pl = new Motion(this.home);
    this.enabled = false;
    this.known = false;
    this.attached = false; // PWM agganciato
    this.estopReq = false;
    this.q = [];
    this.netMode = 'ap';
  }

  reboot() { this.boot(); }

  // ---- uscita ----
  send(id, o) { const s = JSON.stringify(o); if (id) this.clients.get(id)?.(s); else for (const f of this.clients.values()) f(s); }
  err(id, msg) { this.send(id, { t: 'err', msg }); }
  sendCal(id) {
    this.send(id, { t: 'cal', cal: this.cal.map((c) => ({ ...c })), home: this.home.map(r2) });
  }
  sendState() {
    const p = this.pl;
    this.send(0, { t: 'state', q: p.q.map(r2), target: p.target.map(r2), us: p.q.map((x, j) => r2(qToUs(this.cal[j], x))), moving: p.moving, enabled: this.enabled });
  }

  // ---- WebSocket (onWs di main.cpp: solo parsing, poi in coda) ----
  connect(sendFn) {
    const id = this.nextId++;
    this.clients.set(id, sendFn);
    sendFn(JSON.stringify({ t: 'hello', fw: '0.1.0', mode: this.netMode }));
    return id;
  }
  disconnect(id) { this.clients.delete(id); }

  receive(id, text) {
    this.rx.push(text);
    let doc;
    try { doc = JSON.parse(text); } catch { return this.err(id, 'json non valido'); }
    const o = doc && typeof doc === 'object' && !Array.isArray(doc) ? doc : {};
    const t = typeof o.t === 'string' ? o.t : '';
    if (t === 'estop') { this.estopReq = true; return; }
    const c = { client: id, t };
    if (t === 'move') {
      if (!Array.isArray(o.q) || o.q.length !== NJ) return this.err(id, 'move: servono 4 valori in q');
      c.q = o.q.map((x) => num(x, NaN));
      c.v = num(o.v, 0.5);
    } else if (t === 'raw') {
      c.j = int(o.j, -1);
      c.v = num(o.us, NaN);
    } else if (t === 'cal_set') {
      if (!Array.isArray(o.cal) || o.cal.length !== NJ) return this.err(id, 'cal_set: servono 4 giunti');
      c.cal = o.cal.map((x) => { const y = x && typeof x === 'object' ? x : {}; return { ref_us: num(y.ref_us, NaN), k: num(y.k, NaN), q_ref: num(y.q_ref, NaN), min: num(y.min, NaN), max: num(y.max, NaN) }; });
    } else if (!['stop', 'enable', 'cal_get', 'cal_save', 'home_set'].includes(t)) return this.err(id, 'comando sconosciuto');
    if (this.q.length >= QLEN) return this.err(id, 'coda comandi piena');
    this.q.push(c);
  }

  // ---- loop() di main.cpp ----
  loop(now) {
    this.tCtl ??= now;
    this.tState ??= now;
    if (this.estopReq) { this.estopReq = false; this.estop(); }
    while (this.q.length) this.handle(this.q.shift());
    if (now - this.tCtl >= CTRL_MS) {
      this.tCtl = now - this.tCtl > 5 * CTRL_MS ? now : this.tCtl + CTRL_MS; // se resta indietro non recupera a raffica
      if (this.enabled) {
        if (!this.clients.size && this.pl.moving && !this.pl.stopping) this.pl.stop(); // watchdog
        this.pl.step(CTRL_MS / 1000, this.cal);
        this.us = this.pl.q.map((x, j) => qToUs(this.cal[j], x)); // writeServos
      }
    }
    if (now - this.tState >= STATE_MS) {
      this.tState = now;
      if (this.clients.size) this.sendState();
    }
  }

  estop() { this.attached = false; this.enabled = false; this.pl.halt(); }

  handle(c) {
    const pl = this.pl;
    let e;
    switch (c.t) {
      case 'move':
        if (!this.enabled) return this.err(c.client, 'disabilitato: manda enable');
        if (!(c.v > 0 && c.v <= 1)) return this.err(c.client, 'v fuori da (0, 1]');
        if ((e = checkTarget(c.q, this.cal))) return this.err(c.client, e);
        pl.move(c.q, c.v);
        break;
      case 'stop':
        if (this.enabled) pl.stop();
        break;
      case 'enable':
        if (this.enabled) return;
        if (!this.known) { this.pl = new Motion(this.home); this.known = true; }
        this.attached = true;
        this.enabled = true;
        break;
      case 'raw':
        if (!this.enabled) return this.err(c.client, 'raw solo con enabled');
        if (c.j < 0 || c.j >= NJ || !Number.isFinite(c.v)) return this.err(c.client, 'raw: giunto o us non validi');
        if (pl.moving) return this.err(c.client, 'raw: braccio in moto');
        pl.q[c.j] = pl.target[c.j] = usToQ(this.cal[c.j], clamp(c.v, US_MIN, US_MAX));
        break;
      case 'cal_get':
        this.sendCal(c.client);
        break;
      case 'cal_set':
        if (pl.moving) return this.err(c.client, 'cal_set: braccio in moto');
        if ((e = checkCal(c.cal))) return this.err(c.client, e);
        for (let j = 0; j < NJ; j++) pl.q[j] = pl.target[j] = usToQ(c.cal[j], qToUs(this.cal[j], pl.q[j]));
        this.cal = c.cal;
        this.sendCal(0);
        break;
      case 'cal_save':
        this.nvs.cal = structuredClone(this.cal);
        break;
      case 'home_set':
        if (pl.moving) return this.err(c.client, 'home_set: braccio in moto');
        if ((e = checkTarget(pl.q, this.cal))) return this.err(c.client, e);
        this.home = [...pl.q];
        this.nvs.home = [...this.home];
        this.sendCal(0);
        break;
    }
  }
}

// ---- server HTTP + WebSocket minimo (RFC 6455, solo ciò che serve) ----
function frame(text) {
  const p = Buffer.from(text);
  const h = p.length < 126 ? Buffer.from([0x81, p.length]) : p.length < 65536 ? Buffer.from([0x81, 126, p.length >> 8, p.length & 255]) : Buffer.concat([Buffer.from([0x81, 127, 0, 0, 0, 0]), Buffer.from([(p.length >>> 24) & 255, (p.length >> 16) & 255, (p.length >> 8) & 255, p.length & 255])]);
  return Buffer.concat([h, p]);
}

export function startDevice({ port = 0, dev = new Device(), host = '127.0.0.1' } = {}) {
  const sockets = new Set();
  let mute = false; // simula un WiFi appeso: il device smette di scrivere ma il TCP resta su
  const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    if (url.pathname === '/api/info') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ fw: '0.1.0', ip: host, mode: dev.netMode })); }
    let p = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
    if (p.endsWith('/')) p += 'index.html';
    const f = join(DATA, p);
    const types = { html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json', stl: 'model/stl', svg: 'image/svg+xml' };
    const type = types[p.split('.').pop()] || 'application/octet-stream';
    if (f.startsWith(DATA) && existsSync(f + '.gz')) { res.writeHead(200, { 'content-type': type, 'content-encoding': 'gzip' }); return res.end(readFileSync(f + '.gz')); }
    if (f.startsWith(DATA) && existsSync(f)) { res.writeHead(200, { 'content-type': type }); return res.end(readFileSync(f)); }
    res.writeHead(404); res.end('404');
  });
  server.on('upgrade', (req, sock) => {
    if (new URL(req.url, 'http://x').pathname !== '/ws') return sock.destroy();
    const acc = createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${acc}\r\n\r\n`);
    sockets.add(sock);
    const id = dev.connect((s) => { if (!mute && !sock.destroyed) sock.write(frame(s)); });
    let buf = Buffer.alloc(0);
    const bye = () => { sockets.delete(sock); dev.disconnect(id); };
    sock.on('close', bye);
    sock.on('error', bye);
    sock.on('data', (d) => {
      buf = Buffer.concat([buf, d]);
      for (;;) {
        if (buf.length < 2) return;
        const fin = buf[0] & 0x80, op = buf[0] & 15, masked = buf[1] & 0x80;
        let len = buf[1] & 127, o = 2;
        if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); o = 4; }
        else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); o = 10; }
        if (buf.length < o + (masked ? 4 : 0) + len) return;
        const mask = masked ? buf.subarray(o, o + 4) : null;
        o += masked ? 4 : 0;
        const pl = Buffer.from(buf.subarray(o, o + len));
        if (mask) for (let i = 0; i < pl.length; i++) pl[i] ^= mask[i & 3];
        buf = buf.subarray(o + len);
        if (op === 8) { sock.end(Buffer.from([0x88, 0])); continue; }
        if (op === 9) { sock.write(Buffer.concat([Buffer.from([0x8a, pl.length]), pl])); continue; }
        if (op === 1 && fin) dev.receive(id, pl.toString()); // come main.cpp: solo frame di testo interi
      }
    });
  });
  const t0 = performance.now();
  const timer = setInterval(() => dev.loop(performance.now() - t0), 1);
  return new Promise((res) => server.listen(port, host, () => res({
    dev,
    port: server.address().port,
    url: `ws://${host}:${server.address().port}/ws`,
    http: `http://${host}:${server.address().port}/`,
    setMute(m) { mute = m; },
    // caduta del device: chiude tutto senza handshake di chiusura
    close() { clearInterval(timer); for (const s of sockets) s.destroy(); return new Promise((r) => server.close(r)); },
  })));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const d = await startDevice({ port: +(process.argv[2] || 8080), host: '0.0.0.0' });
  console.log(`finto ESP32 su http://localhost:${d.port}/ (ws ${d.url})`);
}
