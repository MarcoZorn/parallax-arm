// WebSocket verso l'ESP32 + messaggi del protocollo (§6).
// Eventi: 'status' (detail: {state: off|connecting|on|retry, delay}), 'msg' (detail: messaggio JSON).

const r2 = (x) => Math.round(x * 100) / 100;

export class Link extends EventTarget {
  ws = null;
  url = '';
  want = false;
  delay = 500;
  timer = 0;
  last = 0;

  get connected() { return this.ws?.readyState === WebSocket.OPEN; }

  connect(url) {
    this.url = url;
    this.want = true;
    this.delay = 500;
    this.#open();
  }

  disconnect() {
    this.want = false;
    clearTimeout(this.timer);
    this.ws?.close();
    this.ws = null;
    this.#status('off');
  }

  #status(state, delay) { this.dispatchEvent(new CustomEvent('status', { detail: { state, delay } })); }

  #open() {
    clearTimeout(this.timer);
    if (this.ws) { this.ws.onclose = null; this.ws.close(); }
    let ws;
    try { ws = new WebSocket(this.url); } catch { return this.#retry(); }
    this.ws = ws;
    this.#status('connecting');
    ws.onopen = () => { this.delay = 500; this.last = performance.now(); this.#status('on'); };
    ws.onmessage = (e) => {
      this.last = performance.now();
      let m;
      try { m = JSON.parse(e.data); } catch { return; }
      if (m && typeof m.t === 'string') this.dispatchEvent(new CustomEvent('msg', { detail: m }));
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.want ? this.#retry() : this.#status('off');
    };
  }

  // riconnessione con backoff esponenziale (0.5 s … 8 s)
  #retry() {
    this.#status('retry', this.delay);
    this.timer = setTimeout(() => this.#open(), this.delay);
    this.delay = Math.min(this.delay * 2, 8000);
  }

  // il device manda state a 20 Hz: 2 s di silenzio = link morto (WiFi caduto senza close)
  checkStale() {
    if (this.connected && performance.now() - this.last > 2000) this.ws.close();
  }

  send(o) {
    if (!this.connected) return false;
    this.ws.send(JSON.stringify(o));
    return true;
  }

  move(q, v) { return this.send({ t: 'move', q: q.map(r2), v: r2(v) }); }
  stop() { return this.send({ t: 'stop' }); }
  estop() { return this.send({ t: 'estop' }); }
  enable() { return this.send({ t: 'enable' }); }
  raw(j, us) { return this.send({ t: 'raw', j, us: Math.round(us) }); }
  calGet() { return this.send({ t: 'cal_get' }); }
  calSet(cal) { return this.send({ t: 'cal_set', cal }); }
  calSave() { return this.send({ t: 'cal_save' }); }
  homeSet() { return this.send({ t: 'home_set' }); }
}
