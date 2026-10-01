// Cinematica, limiti e frame delle parti. Contratto: docs/03-protocollo.md
// Nessuna dipendenza: usato sia dal browser sia dai test in Node.

// Quote meccaniche di default (copia di cad/params.scad). I params di rig.json hanno la precedenza:
// setParams() li applica e FK/IK/frame usano sempre i valori caricati.
export const P = { base_h: 40, sh_h: 62, L1: 80, L2: 80, L3: 42, tcp_dz: -24, crank_r: 20, lev_r: 20, lev2_r: 30 };
export const setParams = (p) => {
  for (const k in P) if (Number.isFinite(p?.[k])) P[k] = p[k];
};

export const JOINTS = [
  { name: 'Base', sym: 'q1', unit: '°' },
  { name: 'Spalla', sym: 'th2', unit: '°' },
  { name: 'Gomito', sym: 'phi', unit: '°' },
  { name: 'Pinza', sym: 'g', unit: 'mm' },
];

// Vincolo del parallelogramma: PAR[0] <= th2 - phi <= PAR[1]
export const PAR = [20, 150];

// Taratura per giunto (§4). min/max sono i limiti di giunto usati ovunque.
export const defaultCal = () => [
  { ref_us: 1500, k: 11.11, q_ref: 0, min: -90, max: 90 },
  { ref_us: 1500, k: 11.11, q_ref: 90, min: 20, max: 160 },
  { ref_us: 1500, k: 11.11, q_ref: 0, min: -70, max: 70 },
  { ref_us: 1500, k: 19.89, q_ref: 29.5, min: 0, max: 59 },
];
export const cal = defaultCal();
export const CAL_F = ['ref_us', 'k', 'q_ref', 'min', 'max'];
// stessa regola di check_cal del firmware: 4 giunti, campi finiti, ref_us in [500, 2500], |k| >= 1, min < max
export const calValid = (c) =>
  Array.isArray(c) && c.length === 4 &&
  c.every((x) => x && CAL_F.every((f) => Number.isFinite(x[f])) && x.ref_us >= 500 && x.ref_us <= 2500 && Math.abs(x.k) >= 1 && x.min < x.max);
// copia solo i campi noti (il messaggio cal arriva dal device: niente chiavi estranee)
export const setCal = (c) => c.forEach((x, i) => CAL_F.forEach((f) => (cal[i][f] = x[f])));
export const HOME = [0, 90, 0, 30];

const D = Math.PI / 180;
const u = (a) => [Math.cos(a * D), 0, Math.sin(a * D)];
const add = (a, b, s = 1) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s];

// FK: TCP nel mondo (mm)
export function fk(q) {
  const [q1, th2, phi] = q;
  const r = P.L1 * Math.cos(th2 * D) + P.L2 * Math.cos(phi * D) + P.L3;
  return {
    x: r * Math.cos(q1 * D),
    y: r * Math.sin(q1 * D),
    z: P.base_h + P.sh_h + P.L1 * Math.sin(th2 * D) + P.L2 * Math.sin(phi * D) + P.tcp_dz,
  };
}

// IK in forma chiusa, gomito alto. Restituisce [q1, th2, phi] o null se irraggiungibile.
export function ik({ x, y, z }) {
  const q1 = Math.atan2(y, x) / D;
  const r = Math.hypot(x, y) - P.L3;
  const zz = z - P.base_h - P.sh_h - P.tcp_dz;
  const c = (r * r + zz * zz - P.L1 ** 2 - P.L2 ** 2) / (2 * P.L1 * P.L2);
  if (!(Math.abs(c) <= 1)) return null;
  const e = Math.acos(c);
  const th2 = Math.atan2(zz, r) + Math.atan2(P.L2 * Math.sin(e), P.L1 + P.L2 * Math.cos(e));
  return [q1, th2 / D, th2 / D - e / D];
}

const f1 = (v) => (Math.round(v * 10) / 10).toString();

// Validazione: null se ok, altrimenti il motivo (in italiano)
export function validate(q) {
  for (let j = 0; j < 4; j++) {
    const v = q[j], c = cal[j];
    if (!Number.isFinite(v)) return `${JOINTS[j].name}: valore non valido`;
    if (v < c.min - 1e-6 || v > c.max + 1e-6)
      return `${JOINTS[j].name} fuori limiti: ${JOINTS[j].sym}=${f1(v)} (${c.min}…${c.max} ${JOINTS[j].unit})`;
  }
  const d = q[1] - q[2];
  if (d < PAR[0] - 1e-6 || d > PAR[1] + 1e-6) return `fuori vincolo: th2-phi=${f1(d)} (${PAR[0]}…${PAR[1]})`;
  return null;
}

// IK + validazione. g = apertura pinza da mantenere.
export function solve(p, g) {
  const s = ik(p);
  if (!s) return { ok: false, msg: 'irraggiungibile: fuori dallo sbraccio' };
  const q = [...s, g];
  const msg = validate(q);
  return msg ? { ok: false, q, msg } : { ok: true, q };
}

// Frame delle parti nel frame yaw: P(p, a) = T(p)·Ry(−a)·Rx(−90).
// Ritorna {p, a}; per le dita {dz} (traslazione lungo Z locale del polso); null = identità.
export function partPose(name, q, y = 0) {
  const [, th2, phi, g] = q;
  const psi = phi + 180;
  const O = [0, 0, P.sh_h];
  const E = add(O, u(th2), P.L1);
  const W = add(E, u(phi), P.L2);
  const at = (p, a) => ({ p: [p[0], p[1] + y, p[2]], a });
  switch (name) {
    case 'upper_arm': return at(O, th2);
    case 'crank': return at(O, psi);
    case 'drive_rod': return at(add(O, u(psi), P.crank_r), th2);
    case 'lev_rod': return at(add(O, u(180), P.lev_r), th2);
    case 'forearm': return at(E, phi);
    case 'lev_link': return at(E, 0);
    case 'lev_rod2': return at(add(E, u(90), P.lev2_r), phi);
    case 'wrist': return at(W, 0);
    case 'jaw_l': return { dz: g / 2 };
    case 'jaw_r': return { dz: -g / 2 };
  }
  return null;
}

// Taratura: unità di giunto <-> µs
export const toUs = (j, q, c = cal) => Math.min(2500, Math.max(500, c[j].ref_us + c[j].k * (q - c[j].q_ref)));
export const fromUs = (j, us, c = cal) => c[j].q_ref + (us - c[j].ref_us) / c[j].k;

// Profilo (r, z) del TCP che delimita l'inviluppo: bordo della regione valida (th2, phi)
// mappato dalla FK. Dentro il vincolo la mappa è iniettiva, quindi il bordo va nel bordo.
export function envelope(step = 1) {
  const [a1, b1, a2, b2] = [cal[1].min, cal[1].max, cal[2].min, cal[2].max];
  const clip = (poly, f) => {
    const out = [];
    poly.forEach((A, i) => {
      const B = poly[(i + 1) % poly.length], fa = f(A), fb = f(B);
      if (fa >= 0) out.push(A);
      if (fa * fb < 0) { const t = fa / (fa - fb); out.push([A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1])]); }
    });
    return out;
  };
  let poly = [[a1, a2], [b1, a2], [b1, b2], [a1, b2]];
  poly = clip(poly, ([t, p]) => t - p - PAR[0]);
  poly = clip(poly, ([t, p]) => PAR[1] - (t - p));
  const pts = [];
  poly.forEach((A, i) => {
    const B = poly[(i + 1) % poly.length];
    const n = Math.min(2000, Math.max(1, Math.ceil(Math.hypot(B[0] - A[0], B[1] - A[1]) / step))); // tetto: limiti assurdi dal device non bloccano la UI
    for (let k = 0; k < n; k++) {
      const t = k / n, f = fk([0, A[0] + t * (B[0] - A[0]), A[1] + t * (B[1] - A[1])]);
      pts.push([f.x, f.z]);
    }
  });
  return pts;
}
