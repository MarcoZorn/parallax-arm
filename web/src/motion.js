// Planner del firmware (firmware/src/motion.cpp, §5) portato riga per riga: il twin mostra ciò che fa il device.
// Profilo trapezoidale sincronizzato calcolato online a 50 Hz: da fermo i giunti restano sulla retta e
// arrivano insieme; un nuovo move riparte da posizione e velocità correnti; stop frena ad AMAX pieno.
// Limiti e vincolo th2-phi come bordi morbidi (vedi motion.cpp). Le differenze col firmware sono solo
// di arrotondamento (double qui, float là): verificate da sim/software/equiv.mjs.
import { cal, PAR } from './robot.js';

export const VMAX = [90, 90, 90, 60]; // °/s, pinza mm/s
export const AMAX = [180, 180, 180, 120]; // °/s², pinza mm/s²
export const DT = 1 / 50;

const EPS = 1e-4, TOL = 1e-3, HARD = 0.01, SNAP = 1.2; // come motion.cpp
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
// velocità massima da cui ci si ferma entro d frenando di A*dt a ogni tick, senza superare d nel tick
const vstop = (d, A, dt) => (d <= 0 ? 0 : Math.min(A * dt * (Math.sqrt(0.25 + (2 * d) / (A * dt * dt)) - 0.5), d / dt));

export class Motion {
  constructor(q) {
    this.q = [...q];
    this.v = [0, 0, 0, 0];
    this.target = [...q];
    this.vmax = [0, 0, 0, 0]; // limiti del moto corrente, già scalati per f
    this.amax = [0, 0, 0, 0];
    this.stopping = false;
    this.moving = false;
    this.enabled = true;
  }

  // target già validato; f in (0, 1]
  move(target, f = 1) {
    f = Math.min(1, Math.max(0.01, f));
    this.target = [...target];
    this.vmax = VMAX.map((x) => x * f);
    this.amax = AMAX.map((x) => x * f);
    this.stopping = false;
    this.moving = true;
  }

  // decelera e tiene la posizione (il target diventa la posa di arresto a fine frenata)
  stop() {
    this.stopping = true;
    this.moving = true;
  }

  // arresto immediato (E-STOP: PWM sganciato)
  halt() {
    this.v = [0, 0, 0, 0];
    this.target = [...this.q];
    this.stopping = false;
    this.moving = false;
  }

  // c: taratura con i limiti (default quella della UI; il finto device in sim/ passa la sua)
  step(dt = DT, c = cal) {
    const { q, v, target } = this;
    const d = target.map((t, j) => t - q[j]), v0 = [...v];
    if (this.stopping) {
      // tutte le velocità scalate dello stesso fattore, il giunto più carico frena ad AMAX
      let T = 0;
      for (let j = 0; j < 4; j++) T = Math.max(T, Math.abs(v[j]) / AMAX[j]);
      const s = T > dt ? 1 - dt / T : 0;
      for (let j = 0; j < 4; j++) v[j] *= s;
    } else {
      // limiti per unità di distanza residua, presi dal giunto più lento
      let vs = Infinity, as = Infinity;
      for (let j = 0; j < 4; j++) {
        const ad = Math.abs(d[j]);
        if (ad > EPS) { vs = Math.min(vs, this.vmax[j] / ad); as = Math.min(as, this.amax[j] / ad); }
      }
      for (let j = 0; j < 4; j++) {
        const ad = Math.abs(d[j]);
        let vdes = 0, Aj = AMAX[j];
        if (ad > EPS) {
          Aj = as * ad;
          const vb = Aj * dt * (Math.sqrt(0.25 + (2 * ad) / (Aj * dt * dt)) - 0.5);
          vdes = Math.sign(d[j]) * Math.min(vs * ad, vb);
        }
        // accelera con il limite sincronizzato, frena sempre con AMAX pieno
        const accel = vdes * v[j] >= 0 && Math.abs(vdes) > Math.abs(v[j]);
        const lim = (accel ? Aj : AMAX[j]) * dt;
        const vn = v[j] + clamp(vdes - v[j], -lim, lim);
        // inversione: oltre lo zero è di nuovo accelerazione, col limite sincronizzato
        v[j] = vn * v[j] < 0 ? Math.sign(vn) * Math.min(Math.abs(vn), Aj * dt) : vn;
      }
    }
    // arrivo esatto solo da velocità di fine profilo
    const snap = d.map((dj, j) => {
      const ad = Math.abs(dj), dv = SNAP * AMAX[j] * dt;
      const s = !this.stopping && ((v[j] * dj > 0 && Math.abs(v[j]) * dt >= ad && ad / dt <= dv && Math.abs(v0[j]) - ad / dt <= dv) || (ad <= EPS && v[j] === 0));
      if (s) v[j] = dj / dt;
      return s;
    });
    // bordi morbidi: e = th2 - phi e limiti di giunto
    const e0 = q[1] - q[2], ev = v[1] - v[2];
    const evm = vstop(ev > 0 ? PAR[1] + TOL - e0 : e0 - (PAR[0] - TOL), 2 * AMAX[1], dt);
    if (Math.abs(ev) > evm) {
      const c = (Math.sign(ev) * (Math.abs(ev) - evm)) / 2;
      v[1] -= c; v[2] += c; snap[1] = snap[2] = false;
    }
    for (let j = 0; j < 4; j++) {
      const vm = vstop(v[j] > 0 ? c[j].max + TOL - q[j] : q[j] - (c[j].min - TOL), AMAX[j], dt);
      if (Math.abs(v[j]) > vm) { v[j] = Math.sign(v[j]) * vm; snap[j] = false; }
    }
    const qn = q.map((x, j) => (snap[j] ? target[j] : x + v[j] * dt));
    snap.forEach((s, j) => { if (s) v[j] = 0; });
    // ultima difesa: si blocca solo il moto che peggiora
    for (let j = 0; j < 4; j++)
      if ((qn[j] < c[j].min - HARD && qn[j] < q[j]) || (qn[j] > c[j].max + HARD && qn[j] > q[j])) { qn[j] = q[j]; v[j] = 0; }
    const e1 = qn[1] - qn[2];
    if ((e1 < PAR[0] - HARD && e1 < e0) || (e1 > PAR[1] + HARD && e1 > e0)) { qn[1] = q[1]; qn[2] = q[2]; v[1] = v[2] = 0; }
    this.q = qn;
    if (this.stopping && v.every((x) => x === 0)) this.halt();
    this.moving = this.stopping || this.v.some((x) => x !== 0) || this.q.some((x, j) => x !== this.target[j]);
    return this.moving;
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
