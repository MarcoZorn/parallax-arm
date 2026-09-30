// Profilo trapezoidale sincronizzato (§5), stesso comportamento del firmware, per la simulazione.
// Tutti i giunti seguono lo stesso profilo normalizzato s(t) scalato sulla loro corsa:
// partono e arrivano insieme, e nessuno supera vmax/amax (moltiplicati per il fattore v).
// Integrazione a passi fissi (50 Hz) con legge di arresto discreta: un nuovo move riparte
// dalla posizione e velocità correnti senza scatti (in frenata si usa amax pieno).

export const VMAX = [90, 90, 90, 60]; // °/s, pinza mm/s
export const AMAX = [180, 180, 180, 120]; // °/s², pinza mm/s²
export const DT = 1 / 50;

export class Motion {
  constructor(q) {
    this.q = [...q];
    this.v = [0, 0, 0, 0];
    this.target = [...q];
    this.vl = [0, 0, 0, 0]; // limiti per giunto del profilo corrente
    this.al = [0, 0, 0, 0];
    this.f = 1;
    this.moving = false;
    this.enabled = true;
  }

  move(target, f = 1) {
    this.f = Math.min(1, Math.max(0.01, f));
    this.target = [...target];
    const d = target.map((t, i) => Math.abs(t - this.q[i]));
    // limiti del profilo unitario (corsa 1): il giunto più lento comanda
    let Vs = Infinity, As = Infinity;
    d.forEach((di, i) => {
      if (di > 1e-9) { Vs = Math.min(Vs, VMAX[i] * this.f / di); As = Math.min(As, AMAX[i] * this.f / di); }
    });
    this.vl = d.map((di) => (Vs < Infinity ? di * Vs : 0));
    this.al = d.map((di) => (As < Infinity ? di * As : 0));
    this.moving = true;
  }

  // decelera con amax e tiene la posizione
  stop() {
    this.target = this.q.map((q, i) => {
      const a = AMAX[i] * this.f, v = this.v[i];
      this.vl[i] = Math.abs(v);
      this.al[i] = a;
      return q + (v * Math.abs(v)) / (2 * a);
    });
  }

  // arresto immediato (E-STOP: PWM sganciato)
  halt() {
    this.v = [0, 0, 0, 0];
    this.target = [...this.q];
    this.moving = false;
  }

  step(dt = DT) {
    let busy = false;
    for (let i = 0; i < 4; i++) {
      const e = this.target[i] - this.q[i], ae = Math.abs(e), al = this.al[i];
      let vd = 0;
      if (al > 0 && ae > 0) {
        // massima velocità da cui ci si ferma esattamente in ae con gradini di al·dt
        // (n gradini pieni + resto δ distribuito): discesa lineare, arrivo esatto
        const ad = al * dt * dt;
        const n = Math.floor((Math.sqrt(1 + (8 * ae) / ad) - 1) / 2);
        const vs = n * al * dt + (ae - (ad * n * (n + 1)) / 2) / ((n + 1) * dt);
        vd = Math.sign(e) * Math.min(this.vl[i], vs);
      }
      const v = this.v[i];
      const brake = Math.abs(vd) < Math.abs(v) || vd * v < 0;
      const A = (brake ? Math.max(al, AMAX[i] * this.f) : al) * dt;
      this.v[i] = v + Math.min(A, Math.max(-A, vd - v));
      this.q[i] += this.v[i] * dt;
      if (Math.abs(this.target[i] - this.q[i]) < 1e-9 && Math.abs(this.v[i]) <= A) {
        this.q[i] = this.target[i];
        if (vd === 0) this.v[i] = 0;
      }
      if (this.v[i] !== 0 || this.q[i] !== this.target[i]) busy = true;
    }
    this.moving = busy;
    return busy;
  }
}

// Durata analitica del profilo sincronizzato da fermo (usata dai test)
export function duration(q0, q1, f = 1) {
  let Vs = Infinity, As = Infinity;
  q1.forEach((t, i) => {
    const d = Math.abs(t - q0[i]);
    if (d > 1e-9) { Vs = Math.min(Vs, VMAX[i] * f / d); As = Math.min(As, AMAX[i] * f / d); }
  });
  if (Vs === Infinity) return 0;
  return 1 >= (Vs * Vs) / As ? 1 / Vs + Vs / As : 2 * Math.sqrt(1 / As);
}
