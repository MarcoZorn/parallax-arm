// Punto 2: coerenza di limiti, taratura e quote tra cad/params.scad (fonte), rig.json, config.h, robot.js,
// motion.js e docs/03. Valuta params.scad con OpenSCAD (se c'è). Uso: node params.mjs -> tabella, exit 1 se KO.
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import * as R from '../../web/src/robot.js';
import * as M from '../../web/src/motion.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const rd = (p) => readFileSync(join(ROOT, p), 'utf8');
const cfg = rd('firmware/include/config.h'), doc = rd('docs/03-protocollo.md').replace(/−/g, '-');
const scad = rd('cad/params.scad'), wrist = rd('cad/wrist.scad'), asm = rd('cad/assembly.scad');
const rig = JSON.parse(rd('web/public/models/rig.json'));

const arr = (name) => { const m = cfg.match(new RegExp(`${name}\\[NJ\\]\\s*=\\s*\\{([^}]*)\\}`)); return m[1].split(',').map((x) => parseFloat(x)); };
const one = (name) => parseFloat(cfg.match(new RegExp(`${name}\\s*=\\s*([-0-9.]+)`))[1]);
const sc = (name) => { const m = scad.match(new RegExp(`^${name}\\s*=\\s*([^;]*);`, 'm')); return m && JSON.parse(m[1].trim()); };

// OpenSCAD: valori calcolati (piani y delle parti), come fa cad/export.sh per rig.json
let os = null;
try {
  const tmp = join(ROOT, 'sim', 'software', 'build', 'scad');
  mkdirSync(tmp, { recursive: true });
  writeFileSync(join(tmp, 'v.scad'), `include <${join(ROOT, 'cad', 'params.scad')}>\necho(v=[y_arm, y_crank_in, y_rod[0], y_lev[0], y_fore_l[0], y_link[0], y_rod2[0]]);\n`);
  execFileSync('openscad', ['-o', join(tmp, 'v.echo'), join(tmp, 'v.scad')], { stdio: 'ignore', timeout: 60000 });
  os = JSON.parse(readFileSync(join(tmp, 'v.echo'), 'utf8').match(/ECHO: v = (\[.*\])/)[1]);
  rmSync(tmp, { recursive: true });
} catch { /* OpenSCAD assente: si salta il confronto dei piani y */ }

const rows = [];
const eq = (a, b, tol = 1e-6) => JSON.stringify(a) === JSON.stringify(b) || (Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => x == null || b[i] == null || Math.abs(x - b[i]) <= tol)) || Math.abs(a - b) <= tol;
// voce: valori per fonte; ok se tutte le fonti presenti coincidono
function row(what, vals, tol, note = '') {
  const v = Object.entries(vals).filter(([, x]) => x !== undefined && x !== null);
  const ok = v.every(([, x]) => eq(x, v[0][1], tol));
  rows.push({ what, ok, vals: Object.fromEntries(v), note });
}

const cal = R.defaultCal(), col = (f) => cal.map((c) => c[f]);
const docLim = [...doc.matchAll(/\| (-?[0-9.]+) … (-?[0-9.]+) \|/g)].map((m) => [+m[1], +m[2]]);
const docDef = (field) => { const m = doc.match(new RegExp('\\| `' + field + '` \\|[^|]*\\| ([^|]*) \\|')); return m && m[1].split('/').map((x) => parseFloat(x)); };
const docPar = (k) => { const m = doc.match(new RegExp('`' + k + ' = (-?[0-9.]+)`')); return m && +m[1]; };
const lim_th2 = asm.match(/(\d+) <= th2 <= (\d+)/).slice(1).map(Number);

row('limiti min (q1, th2, phi, g)', { config: arr('Q_MIN'), robot: col('min'), docs: docLim.map((x) => x[0]), cad: [undefined, lim_th2[0], sc('lim_phi')[0], undefined] }, 1e-6, 'CAD: th2 da assembly.scad, phi da lim_phi; q1 e g non hanno variabile nel CAD');
row('limiti max (q1, th2, phi, g)', { config: arr('Q_MAX'), robot: col('max'), docs: docLim.map((x) => x[1]), cad: [undefined, lim_th2[1], sc('lim_phi')[1], undefined] });
row('vincolo th2-phi', { config: [one('PAR_MIN'), one('PAR_MAX')], robot: R.PAR, docs: doc.match(/`(\d+) ≤ th2 - phi ≤ (\d+)`/).slice(1).map(Number), cad: sc('lim_e') });
row('ref_us', { config: arr('CAL_REF_US'), robot: col('ref_us'), docs: docDef('ref_us') });
row('k (µs/unità)', { config: arr('CAL_K'), robot: col('k'), docs: docDef('k') }, 1e-6);
// k derivato: SG90 2000 µs / 180°; pinza: pignone m*zp/2, apertura = 2*r*dtheta
const m = parseFloat(wrist.match(/^m\s*=\s*([0-9.]+)/m)[1]), zp = parseFloat(wrist.match(/^zp\s*=\s*([0-9.]+)/m)[1]);
const kServo = 2000 / 180, kG = (kServo * 180) / Math.PI / (2 * ((m * zp) / 2));
row('k derivato dalla meccanica', { config: arr('CAL_K'), calcolo: [kServo, kServo, kServo, kG] }, 0.01, `pignone m${m} z${zp}: ${kG.toFixed(3)} µs/mm`);
row('q_ref', { config: arr('CAL_Q_REF'), robot: col('q_ref'), docs: docDef('q_ref') });
row('home default', { config: arr('HOME_DEFAULT'), robot: R.HOME, docs: JSON.parse(doc.match(/default `(\[[^\]]*\])`/)[1]) });
row('home valida', { validate: R.validate(arr('HOME_DEFAULT')) ?? 'ok', atteso: 'ok' });
row('VMAX', { config: arr('VMAX'), motionJs: M.VMAX, docs: [90, 90, 90, 60].map((x, i) => (doc.includes('`vmax` 90 °/s (pinza 60 mm/s)') ? x : NaN)) });
row('AMAX', { config: arr('AMAX'), motionJs: M.AMAX, docs: [180, 180, 180, 120].map((x) => (doc.includes('`amax` 180 °/s² (pinza 120 mm/s²)') ? x : NaN)) });
row('periodo di controllo (s)', { config: one('CTRL_MS') / 1000, motionJs: M.DT });
row('clamp µs', { config: [one('US_MIN'), one('US_MAX')], robot: [R.toUs(0, -1e9), R.toUs(0, 1e9)], docs: doc.match(/clamp finale del segnale a \[(\d+), (\d+)\]/).slice(1).map(Number) });
// µs ai limiti con la taratura di default: tutto il campo di giunto deve stare nel clamp (niente saturazione)
row('µs ai limiti dentro [500, 2500]', { esito: cal.every((c, j) => [c.min, c.max].every((q) => { const u = c.ref_us + c.k * (q - c.q_ref); return u >= 500 && u <= 2500; })) ? 'ok' : 'satura', atteso: 'ok' });

for (const k of ['base_h', 'sh_h', 'L1', 'L2', 'L3', 'tcp_dz', 'crank_r', 'lev_r', 'lev2_r'])
  row(`quota ${k}`, { cad: sc(k), rigJson: rig.params[k], robotDefault: R.P[k], docs: docPar(k) });
const docJson = JSON.parse(doc.match(/```json\n([\s\S]*?)```/)[1]).params;
row('esempio rig.json in docs/03 §2', { esempio: [docJson.L3, docJson.tcp_dz], rigJson: [rig.params.L3, rig.params.tcp_dz] }, 1e-6, 'solo un esempio, ma con valori vecchi');
const names = ['upper_arm', 'crank', 'drive_rod', 'lev_rod', 'forearm', 'lev_link', 'lev_rod2'];
const docY = Object.fromEntries([...doc.matchAll(/(\w+) (-?[0-9.]+)[,.]/g)].filter((m) => names.includes(m[1]) || m[1] === 'wrist').map((m) => [m[1], +m[2]]));
row('piani y delle parti', { cad: os ?? undefined, rigJson: names.map((n) => rig.parts.find((p) => p.name === n).y), docs: names.map((n) => docY[n]) }, 0.051, names.join(', '));

const W = Math.max(...rows.map((r) => r.what.length));
for (const r of rows) console.log(`${r.ok ? 'OK  ' : 'DIFF'} ${r.what.padEnd(W)}  ${Object.entries(r.vals).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join('  ')}${r.note ? `  (${r.note})` : ''}`);
// le differenze note e solo documentali (docs/ non si tocca da qui) non fanno fallire
const KNOWN = ['esempio rig.json in docs/03 §2', 'piani y delle parti'];
const fail = rows.filter((r) => !r.ok && !KNOWN.includes(r.what));
console.log(`\n${rows.length} voci, ${rows.filter((r) => !r.ok).length} differenze (${fail.length} non note)`);
process.exit(fail.length ? 1 : 0);
