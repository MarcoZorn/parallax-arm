// Scena 3D (digital twin) + cablaggio UI
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import * as R from './robot.js';
import { Motion, DT } from './motion.js';
import { Link } from './link.js';
import './style.css';

const $ = (id) => document.getElementById(id);
const D = Math.PI / 180;
const f1 = (x) => (Number.isFinite(x) ? x.toFixed(1) : '—');
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

// ---------- stato ----------
const S = {
  q: [...R.HOME], // posa mostrata (sim o device)
  target: [...R.HOME], // ultimo target comandato
  us: [0, 0, 0, 0],
  moving: false,
  enabled: true,
  v: 0.5,
  adopt: false, // adotta il target del device al prossimo state
};
const sim = new Motion(R.HOME);
const link = new Link();
const live = () => link.connected;

// ---------- messaggi ----------
let toastT = 0;
function note(text, kind = 'info') {
  const t = $('toast');
  t.textContent = text;
  t.className = `toast show ${kind}`;
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.className = 'toast'), kind === 'err' ? 5000 : 2500);
  if (kind === 'err') log(text, 'err');
}
function log(text, kind = '') {
  const li = document.createElement('li');
  li.className = kind;
  li.textContent = `${new Date().toLocaleTimeString()}  ${text}`;
  $('log').prepend(li);
  while ($('log').children.length > 40) $('log').lastChild.remove();
}

// ---------- comandi ----------
let pend = null, pendT = 0, lastSend = 0;
function flush() {
  pendT = 0;
  if (pend && live()) link.move(pend.q, pend.v);
  pend = null;
  lastSend = performance.now();
}

// valida e comanda un target di giunto; false se rifiutato (il braccio non si muove)
function command(q, v = S.v, quiet = false) {
  const err = R.validate(q);
  if (err) { if (!quiet) note(err, 'err'); return false; }
  if (!S.enabled) { if (!quiet) note('Braccio disabilitato: premi Abilita', 'err'); return false; }
  S.target = [...q];
  if (live()) {
    // max 20 comandi/s verso il device, l'ultimo vince
    pend = { q: [...q], v };
    const wait = 50 - (performance.now() - lastSend);
    if (wait <= 0) flush();
    else if (!pendT) pendT = setTimeout(flush, wait);
  } else sim.move(q, v);
  syncTargetUI();
  return true;
}
function cancelPending() { clearTimeout(pendT); pendT = 0; pend = null; }

function estop() {
  cancelPending();
  seqAbort();
  if (live()) link.estop();
  sim.halt();
  sim.enabled = false;
  S.target = [...S.q];
  S.adopt = true;
  syncTargetUI();
  note('E-STOP: PWM sganciato', 'err');
}
function stop() {
  cancelPending();
  seqAbort();
  if (live()) { link.stop(); S.adopt = true; } else { sim.stop(); S.target = [...sim.target]; syncTargetUI(); }
}
function enable() {
  if (live()) { link.enable(); S.adopt = true; } else { sim.enabled = true; note('Abilitato (simulazione)', 'ok'); }
}

// ---------- scena ----------
const host = $('gl');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x121416);
scene.fog = new THREE.Fog(0x121416, 1400, 3200);
const camera = new THREE.PerspectiveCamera(38, 1, 1, 6000);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.enableDamping = true;
orbit.maxPolarAngle = Math.PI * 0.495;
function homeView() {
  camera.position.set(420, 330, 470);
  orbit.target.set(40, 110, 0);
  orbit.update();
}
homeView();

// Z-up del contratto: si ruota la radice, la matematica resta in Z-up
const root = new THREE.Group();
root.rotation.x = -Math.PI / 2;
scene.add(root);

scene.add(new THREE.HemisphereLight(0xdfe6ee, 0x202326, 0.9));
const sun = new THREE.DirectionalLight(0xffffff, 2.4);
sun.position.set(260, 620, 300);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -420, right: 420, top: 420, bottom: -420, near: 100, far: 1600 });
sun.shadow.bias = -0.0004;
sun.shadow.radius = 4;
scene.add(sun);
const fill = new THREE.DirectionalLight(0x9fb4ff, 0.5);
fill.position.set(-400, 200, -300);
scene.add(fill);

// tavolo, griglie, assi
{
  const table = new THREE.Mesh(
    new THREE.BoxGeometry(640, 520, 18),
    new THREE.MeshStandardMaterial({ color: 0x1d2024, roughness: 0.92, metalness: 0 }),
  );
  table.position.set(80, 0, -9);
  table.receiveShadow = true;
  root.add(table);
  const g1 = new THREE.GridHelper(500, 25, 0x3b4148, 0x2a2e33);
  g1.rotation.x = Math.PI / 2;
  g1.position.set(80, 0, 0.3);
  root.add(g1);
  const g2 = new THREE.GridHelper(3000, 30, 0x24282c, 0x1c1f22);
  g2.rotation.x = Math.PI / 2;
  g2.position.z = -300;
  root.add(g2);
  const axis = (dir, color) => root.add(new THREE.ArrowHelper(new THREE.Vector3(...dir), new THREE.Vector3(0, 0, 0.5), 110, color, 12, 6));
  axis([1, 0, 0], 0xe5484d);
  axis([0, 1, 0], 0x46a758);
  axis([0, 0, 1], 0x3e8ed0);
}

// ---------- robot: parti da rig.json, segnaposto se manca lo STL ----------
const yawG = new THREE.Group();
root.add(yawG);
const pivots = {}; // name -> Group nel frame della parte
const partY = {};
const ROT_X = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const tmpM = new THREE.Matrix4();

function mat(color) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.08 });
}
function mesh(geo, color, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, mat(color));
  m.position.set(x, y, z);
  m.castShadow = m.receiveShadow = true;
  return m;
}
// segnaposto nel frame locale: X lungo il link, Z locale = +Y mondo (spessore), −Y locale ≈ "su"
function placeholder(name, color) {
  const g = new THREE.Group();
  const bar = (x0, x1, w, t, z = 0) => g.add(mesh(new THREE.BoxGeometry(x1 - x0, w, t), color, (x0 + x1) / 2, 0, z));
  const pin = (x, y = 0, r = 4, t = 8) => {
    const c = new THREE.CylinderGeometry(r, r, t, 20);
    c.rotateX(Math.PI / 2);
    g.add(mesh(c, 0x2a2e33, x, y, 0));
  };
  const { L1, L2, L3, tcp_dz, crank_r, lev_r, lev2_r, base_h, sh_h } = R.P;
  switch (name) {
    case 'base': {
      const c = new THREE.CylinderGeometry(70, 72, base_h, 64);
      c.rotateX(Math.PI / 2);
      g.add(mesh(c, color, 0, 0, base_h / 2));
      break;
    }
    case 'turret': {
      g.add(mesh(new THREE.BoxGeometry(70, 70, 6), color, 0, 0, 3));
      for (const s of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(56, 3, sh_h + 10), color, -4, s * 34, (sh_h + 10) / 2));
      const ax = new THREE.CylinderGeometry(3, 3, 72, 16);
      g.add(mesh(ax, 0x2a2e33, 0, 0, sh_h));
      const gp = new THREE.CylinderGeometry(3, 3, 14, 12); // perno fisso G
      g.add(mesh(gp, 0x2a2e33, -lev_r, -3, sh_h));
      break;
    }
    case 'upper_arm': bar(-18, L1, 12, 6); pin(0); pin(L1); break;
    case 'crank': bar(-28, crank_r, 12, 5); pin(0, 0, 6); pin(crank_r); break;
    case 'drive_rod': case 'lev_rod': bar(0, L1, 7, 4); pin(0, 0, 3.5, 6); pin(L1, 0, 3.5, 6); break;
    case 'forearm': bar(-crank_r, L2, 12, 5); pin(0); pin(L2); break;
    case 'lev_rod2': bar(0, L2, 7, 4); pin(0, 0, 3.5, 6); pin(L2, 0, 3.5, 6); break;
    case 'lev_link': {
      const s = new THREE.Shape([new THREE.Vector2(4, 4), new THREE.Vector2(-lev_r - 4, 4), new THREE.Vector2(0, -lev2_r - 4)]);
      const e = new THREE.ExtrudeGeometry(s, { depth: 4, bevelEnabled: false });
      e.translate(0, 0, -2);
      g.add(mesh(e, color));
      break;
    }
    case 'wrist': {
      const top = -lev2_r - 4, bot = -tcp_dz + 6;
      g.add(mesh(new THREE.BoxGeometry(10, bot - top, 8), color, 0, (top + bot) / 2, 0)); // staffa
      g.add(mesh(new THREE.BoxGeometry(L3 - 8, 16, 26), color, (L3 - 8) / 2, -tcp_dz - 8, 0)); // corpo pinza
      g.add(mesh(new THREE.BoxGeometry(8, 6, 72), 0x2a2e33, L3 - 14, -tcp_dz - 3, 0)); // cremagliere
      break;
    }
    case 'jaw_l': case 'jaw_r': {
      const s = name === 'jaw_l' ? 1 : -1;
      g.add(mesh(new THREE.BoxGeometry(26, 22, 4), color, L3, -tcp_dz, s * 2));
      g.add(mesh(new THREE.BoxGeometry(10, 6, 8), 0x2a2e33, L3 - 14, -tcp_dz - 3, s * 4));
      break;
    }
  }
  return g;
}

const stl = new STLLoader();
async function buildRobot() {
  let rig = { params: {}, parts: [] };
  try {
    rig = await (await fetch('models/rig.json', { cache: 'no-cache' })).json();
  } catch {
    note('rig.json non trovato: uso i parametri di default', 'err');
    rig.parts = ['base', 'turret', 'upper_arm', 'crank', 'drive_rod', 'lev_rod', 'forearm', 'lev_link', 'lev_rod2', 'wrist', 'jaw_l', 'jaw_r'].map((name) => ({ name }));
  }
  R.setParams(rig.params);
  for (const p of rig.parts) {
    const pv = new THREE.Group();
    pv.name = p.name;
    pivots[p.name] = pv;
    partY[p.name] = +p.y || 0;
    const color = p.color || '#b8bdc2';
    const ph = placeholder(p.name, color);
    pv.add(ph);
    if (p.file) {
      // lo STL sostituisce solo il segnaposto (il polso porta anche le dita come figli)
      stl.loadAsync(`models/${p.file}`).then(
        (geo) => { pv.remove(ph); pv.add(mesh(geo, color)); },
        () => log(`${p.file}: non caricabile, segnaposto`),
      );
    }
  }
  for (const [name, pv] of Object.entries(pivots)) {
    if (name === 'base') root.add(pv);
    else if (name.startsWith('jaw_')) (pivots.wrist || yawG).add(pv);
    else yawG.add(pv);
    if (!['base', 'turret'].includes(name) && !name.startsWith('jaw_')) pv.matrixAutoUpdate = false;
  }
  buildEnvelope();
}

function poseRobot(q) {
  yawG.position.z = R.P.base_h;
  yawG.rotation.z = q[0] * D;
  for (const [name, pv] of Object.entries(pivots)) {
    const ps = R.partPose(name, q, partY[name]);
    if (!ps) continue;
    if ('dz' in ps) { pv.position.z = ps.dz; continue; }
    pv.matrix.copy(ROT_X).premultiply(tmpM.makeRotationY(-ps.a * D)).setPosition(...ps.p);
    pv.matrixWorldNeedsUpdate = true;
  }
}

// ---------- TCP: indicatore, traccia ----------
const tcpDot = new THREE.Mesh(new THREE.SphereGeometry(2.6, 16, 12), new THREE.MeshBasicMaterial({ color: 0xff7a1a }));
tcpDot.renderOrder = 2;
tcpDot.material.depthTest = false;
root.add(tcpDot);
{
  const ax = new THREE.AxesHelper(18);
  ax.material.depthTest = false;
  tcpDot.add(ax);
}
const TRACE_N = 3000;
const traceGeo = new THREE.BufferGeometry();
traceGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(TRACE_N * 3), 3));
traceGeo.setDrawRange(0, 0);
const trace = new THREE.Line(traceGeo, new THREE.LineBasicMaterial({ color: 0xff9a4d, transparent: true, opacity: 0.8 }));
trace.frustumCulled = false;
root.add(trace);
let traceN = 0;
const lastTrace = new THREE.Vector3(1e9, 0, 0);
function pushTrace(p) {
  if (lastTrace.distanceTo(p) < 0.5) return;
  lastTrace.copy(p);
  const a = traceGeo.attributes.position;
  if (traceN >= TRACE_N) { a.array.copyWithin(0, 3); traceN = TRACE_N - 1; }
  a.setXYZ(traceN++, p.x, p.y, p.z);
  a.needsUpdate = true;
  traceGeo.setDrawRange(0, traceN);
}
function clearTrace() { traceN = 0; traceGeo.setDrawRange(0, 0); lastTrace.set(1e9, 0, 0); }

// ---------- inviluppo di lavoro (toggle) ----------
const envG = new THREE.Group();
envG.visible = false;
root.add(envG);
function buildEnvelope() {
  envG.clear();
  const prof = R.envelope(1);
  const pts = prof.map(([r, z]) => new THREE.Vector2(Math.max(0, r), z));
  pts.push(pts[0].clone());
  const [a0, a1] = [R.cal[0].min, R.cal[0].max];
  // Lathe gira attorno a Y: la si porta su Z; angolo lathe φ -> yaw φ−90°
  const lathe = new THREE.LatheGeometry(pts, 96, (a0 + 90) * D, (a1 - a0) * D);
  const m = new THREE.Mesh(lathe, new THREE.MeshBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false }));
  m.rotation.x = Math.PI / 2;
  envG.add(m);
  // profili ai limiti di yaw e a q1 = 0
  for (const a of [a0, 0, a1]) {
    const g = new THREE.BufferGeometry().setFromPoints(prof.map(([r, z]) => new THREE.Vector3(r * Math.cos(a * D), r * Math.sin(a * D), z)));
    envG.add(new THREE.LineLoop(g, new THREE.LineBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: a === 0 ? 0.8 : 0.35 })));
  }
}

// ---------- gizmo IK ----------
const tgt = new THREE.Mesh(new THREE.SphereGeometry(5, 20, 14), new THREE.MeshBasicMaterial({ color: 0xff7a1a, transparent: true, opacity: 0.45, depthTest: false }));
tgt.renderOrder = 3;
root.add(tgt);
const tc = new TransformControls(camera, renderer.domElement);
tc.setSpace('local'); // assi del gizmo = assi Z-up del robot
tc.setSize(0.75);
tc.attach(tgt);
scene.add(tc.getHelper());
let dragging = false, dragBad = false;
tc.addEventListener('dragging-changed', (e) => {
  dragging = e.value;
  orbit.enabled = !e.value;
  if (!e.value) {
    if (dragBad) placeTarget(); // rilasciato in un punto non valido: il gizmo torna al target
    dragBad = false;
    tgt.material.color.set(0xff7a1a);
  }
});
tc.addEventListener('objectChange', () => {
  if (!dragging) return;
  const p = tgt.position;
  const s = R.solve({ x: p.x, y: p.y, z: p.z }, S.target[3]);
  dragBad = !s.ok || !S.enabled;
  tgt.material.color.set(dragBad ? 0xe5484d : 0xff7a1a);
  setIkMsg(s.ok ? (S.enabled ? 'raggiungibile' : 'braccio disabilitato') : s.msg, !dragBad);
  if (!dragBad) command(s.q, S.v, true);
});
function placeTarget() {
  const p = R.fk(S.target);
  tgt.position.set(p.x, p.y, p.z);
}

// ---------- UI: FK ----------
const fkRows = [];
function buildFK() {
  $('fkRows').innerHTML = '';
  R.JOINTS.forEach((J, j) => {
    const row = document.createElement('div');
    row.className = 'jrow';
    row.innerHTML = `
      <label for="fk${j}r">${J.name} <span class="sym">${J.sym}</span></label>
      <output class="ro mono" id="fk${j}o" aria-label="${J.name} attuale">—</output>
      <input type="range" id="fk${j}r" step="0.5" />
      <input type="number" id="fk${j}n" step="0.5" class="num" aria-label="${J.name} target (${J.unit})" />
      <span class="lim mono" id="fk${j}l"></span>`;
    $('fkRows').append(row);
    const r = row.querySelector('input[type=range]'), n = row.querySelector('input[type=number]');
    const onInput = (val) => {
      const q = fkRows.map((x) => +x.n.value);
      q[j] = val;
      r.value = n.value = val;
      fkDraft(q);
    };
    r.addEventListener('input', () => onInput(+r.value));
    n.addEventListener('change', () => onInput(+n.value));
    fkRows.push({ row, r, n, o: row.querySelector('output'), l: row.querySelector('.lim') });
  });
  applyLimits();
}
function applyLimits() {
  fkRows.forEach((x, j) => {
    const c = R.cal[j];
    for (const el of [x.r, x.n]) { el.min = c.min; el.max = c.max; }
    x.l.textContent = `${c.min}…${c.max} ${R.JOINTS[j].unit}`;
  });
  for (const el of [$('gR'), $('gN')]) { el.min = R.cal[3].min; el.max = R.cal[3].max; }
}
// target proposto dagli slider FK: evidenzia in rosso le violazioni, manda solo se valido
function fkDraft(q) {
  const d = q[1] - q[2];
  const bad = d < R.PAR[0] || d > R.PAR[1];
  fkRows[1].row.classList.toggle('bad', bad);
  fkRows[2].row.classList.toggle('bad', bad);
  $('fkPar').classList.toggle('bad', bad);
  $('fkPar').innerHTML = `th2 − phi = <b class="mono">${f1(d)}°</b> <span class="muted">(vincolo ${R.PAR[0]}…${R.PAR[1]})</span>`;
  if (bad) { note(`fuori vincolo: th2-phi=${f1(d)}`, 'err'); return; }
  command(q);
}
function syncTargetUI() {
  const t = S.target;
  fkRows.forEach((x, j) => {
    if (document.activeElement !== x.n) x.n.value = +t[j].toFixed(2);
    x.r.value = t[j];
    x.row.classList.remove('bad');
  });
  const d = t[1] - t[2];
  $('fkPar').classList.remove('bad');
  $('fkPar').innerHTML = `th2 − phi = <b class="mono">${f1(d)}°</b> <span class="muted">(vincolo ${R.PAR[0]}…${R.PAR[1]})</span>`;
  $('gR').value = t[3];
  if (document.activeElement !== $('gN')) $('gN').value = +t[3].toFixed(1);
  const p = R.fk(t);
  for (const [k, id] of [['x', 'ikX'], ['y', 'ikY'], ['z', 'ikZ']]) if (document.activeElement !== $(id)) $(id).value = p[k].toFixed(1);
  if (!dragging) placeTarget();
}

// ---------- UI: IK ----------
function setIkMsg(text, ok) {
  $('ikMsg').textContent = text;
  $('ikMsg').className = `msg ${ok ? 'ok' : 'err'}`;
}
function goXYZ(p) {
  const s = R.solve(p, S.target[3]);
  if (!s.ok) { setIkMsg(s.msg, false); note(s.msg, 'err'); return false; }
  if (command(s.q)) { setIkMsg('raggiungibile', true); return true; }
  return false;
}
$('ikForm').addEventListener('submit', (e) => {
  e.preventDefault();
  goXYZ({ x: +$('ikX').value, y: +$('ikY').value, z: +$('ikZ').value });
});
document.querySelectorAll('[data-jog]').forEach((b) =>
  b.addEventListener('click', () => {
    const [ax, s] = b.dataset.jog.split(',').map(Number);
    const p = R.fk(S.target);
    p['xyz'[ax]] += s * +$('jogStep').value;
    goXYZ(p);
  }),
);

// ---------- UI: moto, pinza ----------
$('vR').addEventListener('input', () => {
  S.v = +$('vR').value;
  $('vO').textContent = `${Math.round(S.v * 100)}%`;
});
const setG = (g) => command([...S.target.slice(0, 3), clamp(g, R.cal[3].min, R.cal[3].max)]);
$('gR').addEventListener('input', () => setG(+$('gR').value));
$('gN').addEventListener('change', () => setG(+$('gN').value));
$('bOpen').onclick = () => setG(R.cal[3].max);
$('bClose').onclick = () => setG(R.cal[3].min);
$('bHome').onclick = () => command([...R.HOME]);
$('bEnable').onclick = enable;
$('bStop').onclick = stop;
$('bEstop').onclick = estop;
addEventListener('keydown', (e) => {
  const typing = e.target.matches?.('input[type=text], input[type=number], textarea, select');
  if (e.key === 'Escape' || (e.code === 'Space' && !typing)) { e.preventDefault(); estop(); }
});

// tab
const tabs = [...document.querySelectorAll('[role=tab]')];
function selectTab(t) {
  tabs.forEach((x) => {
    const on = x === t;
    x.setAttribute('aria-selected', on);
    x.tabIndex = on ? 0 : -1;
    $(x.getAttribute('aria-controls')).hidden = !on;
  });
  try { localStorage.setItem('braccio.tab', t.id); } catch {}
}
tabs.forEach((t, i) => {
  t.onclick = () => selectTab(t);
  t.onkeydown = (e) => {
    const k = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (!k) return;
    const n = tabs[(i + k + tabs.length) % tabs.length];
    selectTab(n);
    n.focus();
  };
});
try { const id = localStorage.getItem('braccio.tab'); if ($(id)) selectTab($(id)); } catch {}

// toggle vista
$('tEnv').onchange = () => (envG.visible = $('tEnv').checked);
$('tTrace').onchange = () => (trace.visible = $('tTrace').checked);
$('tGizmo').onchange = () => { tc.enabled = tgt.visible = tc.getHelper().visible = $('tGizmo').checked; };
$('bClearTrace').onclick = clearTrace;
$('bView').onclick = homeView;

// ---------- UI: waypoint e sequenze ----------
const STORE = 'braccio.waypoints.v1';
let WP = { waypoints: [], sequence: [] };
try { WP = { ...WP, ...JSON.parse(localStorage.getItem(STORE)) }; } catch {}
const save = () => { try { localStorage.setItem(STORE, JSON.stringify(WP)); } catch {} };
const uid = () => Math.random().toString(36).slice(2, 9);
const wpById = (id) => WP.waypoints.find((w) => w.id === id);
const move = (arr, i, d) => { const j = i + d; if (j < 0 || j >= arr.length) return; [arr[i], arr[j]] = [arr[j], arr[i]]; };
function iconBtn(label, text, fn) {
  const b = document.createElement('button');
  b.className = 'btn sm';
  b.type = 'button';
  b.textContent = text;
  b.setAttribute('aria-label', label);
  b.title = label;
  b.onclick = fn;
  return b;
}
function renderWP() {
  const ol = $('wpList');
  ol.innerHTML = '';
  if (!WP.waypoints.length) ol.innerHTML = '<li class="empty">Nessun waypoint. Porta il braccio in posa e premi «Salva posa».</li>';
  WP.waypoints.forEach((w, i) => {
    const li = document.createElement('li');
    const p = R.fk(w.q);
    li.innerHTML = `<span class="nm"></span><span class="mono muted xs">${f1(p.x)} ${f1(p.y)} ${f1(p.z)} · g ${f1(w.q[3])}</span>`;
    li.querySelector('.nm').textContent = w.name;
    const a = document.createElement('span');
    a.className = 'acts';
    a.append(
      iconBtn(`Vai a ${w.name}`, 'Vai', () => command(w.q)),
      iconBtn('Sposta su', '↑', () => { move(WP.waypoints, i, -1); commitWP(); }),
      iconBtn('Sposta giù', '↓', () => { move(WP.waypoints, i, 1); commitWP(); }),
      iconBtn(`Rinomina ${w.name}`, 'Rin.', () => {
        const n = prompt('Nuovo nome', w.name);
        if (n?.trim()) { w.name = n.trim().slice(0, 40); commitWP(); }
      }),
      iconBtn(`Elimina ${w.name}`, '✕', () => {
        if (!confirm(`Eliminare «${w.name}»?`)) return;
        WP.waypoints.splice(i, 1);
        WP.sequence = WP.sequence.filter((s) => s.wp !== w.id);
        commitWP();
      }),
    );
    li.append(a);
    ol.append(li);
  });
  renderSeq();
}
function renderSeq() {
  const ol = $('seqList');
  ol.innerHTML = '';
  if (!WP.sequence.length) ol.innerHTML = '<li class="empty">Sequenza vuota: aggiungi passi con «+ Passo».</li>';
  WP.sequence.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = 'step';
    li.id = `step${i}`;
    li.innerHTML = `
      <select aria-label="Waypoint del passo ${i + 1}">${WP.waypoints.map((w) => `<option value="${w.id}"></option>`).join('')}</select>
      <label class="xs">v <input type="number" class="num sm" min="0.05" max="1" step="0.05" value="${s.v}" aria-label="Velocità passo ${i + 1}" /></label>
      <label class="xs">pausa <input type="number" class="num sm" min="0" max="60" step="0.1" value="${s.pause}" aria-label="Pausa passo ${i + 1} in secondi" />s</label>`;
    const sel = li.querySelector('select');
    [...sel.options].forEach((o, k) => (o.textContent = WP.waypoints[k].name));
    sel.value = s.wp;
    sel.onchange = () => { s.wp = sel.value; save(); };
    const [iv, ip] = li.querySelectorAll('input');
    iv.onchange = () => { s.v = clamp(+iv.value || 0.5, 0.05, 1); iv.value = s.v; save(); };
    ip.onchange = () => { s.pause = clamp(+ip.value || 0, 0, 60); ip.value = s.pause; save(); };
    const a = document.createElement('span');
    a.className = 'acts';
    a.append(
      iconBtn('Passo su', '↑', () => { move(WP.sequence, i, -1); commitWP(); }),
      iconBtn('Passo giù', '↓', () => { move(WP.sequence, i, 1); commitWP(); }),
      iconBtn(`Rimuovi passo ${i + 1}`, '✕', () => { WP.sequence.splice(i, 1); commitWP(); }),
    );
    li.append(a);
    ol.append(li);
  });
}
function commitWP() { save(); renderWP(); }
$('wpForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const name = $('wpName').value.trim() || `P${WP.waypoints.length + 1}`;
  WP.waypoints.push({ id: uid(), name, q: S.target.map((x) => +x.toFixed(2)) });
  $('wpName').value = '';
  commitWP();
});
$('bSeqAdd').onclick = () => {
  if (!WP.waypoints.length) return note('Prima salva almeno un waypoint', 'err');
  WP.sequence.push({ wp: WP.waypoints[WP.waypoints.length - 1].id, v: S.v, pause: 0.5 });
  commitWP();
};

let run = null;
const sleep = (ms, tok) => new Promise((res) => {
  const t0 = performance.now();
  const id = setInterval(() => { if (tok.stop || performance.now() - t0 >= ms) { clearInterval(id); res(); } }, 30);
});
async function arrive(tok) {
  await sleep(150, tok); // lascia arrivare il primo state dal device
  while (!tok.stop && (S.moving || S.q.some((x, j) => Math.abs(x - S.target[j]) > 0.3))) {
    if (!S.enabled) { tok.stop = true; break; }
    await sleep(40, tok);
  }
}
async function play() {
  if (run || !WP.sequence.length) return;
  const tok = (run = { stop: false });
  $('bPlay').disabled = true;
  do {
    for (let i = 0; i < WP.sequence.length && !tok.stop; i++) {
      document.querySelectorAll('#seqList .step').forEach((el, k) => el.classList.toggle('cur', k === i));
      const s = WP.sequence[i], w = wpById(s.wp);
      if (!w) continue;
      if (!command(w.q, s.v)) { tok.stop = true; break; }
      await arrive(tok);
      await sleep(s.pause * 1000, tok);
    }
  } while ($('seqLoop').checked && !tok.stop);
  document.querySelectorAll('#seqList .step').forEach((el) => el.classList.remove('cur'));
  $('bPlay').disabled = false;
  run = null;
}
function seqAbort() { if (run) run.stop = true; }
$('bPlay').onclick = play;
$('bSeqStop').onclick = () => { seqAbort(); stop(); };
$('bExport').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(WP, null, 2)], { type: 'application/json' }));
  a.download = 'braccio-waypoint.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
};
$('fImport').onchange = async (e) => {
  const f = e.target.files[0];
  e.target.value = '';
  if (!f) return;
  try {
    const d = JSON.parse(await f.text());
    const okQ = (q) => Array.isArray(q) && q.length === 4 && q.every(Number.isFinite);
    if (!Array.isArray(d.waypoints) || !d.waypoints.every((w) => w.id && typeof w.name === 'string' && okQ(w.q))) throw new Error('waypoint non validi');
    WP = { waypoints: d.waypoints, sequence: (d.sequence || []).filter((s) => d.waypoints.some((w) => w.id === s.wp)).map((s) => ({ wp: s.wp, v: clamp(+s.v || 0.5, 0.05, 1), pause: clamp(+s.pause || 0, 0, 60) })) };
    commitWP();
    note(`Importati ${WP.waypoints.length} waypoint`, 'ok');
  } catch (err) {
    note(`Import fallito: ${err.message}`, 'err');
  }
};

// ---------- UI: taratura ----------
let calEdit = R.defaultCal();
const CAL_F = ['ref_us', 'k', 'q_ref', 'min', 'max'];
function renderCal() {
  $('calRows').innerHTML = '';
  calEdit.forEach((c, j) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<th scope="row">${R.JOINTS[j].sym}</th>` + CAL_F.map((f) => `<td><input type="number" class="num sm" step="any" value="${c[f]}" aria-label="${R.JOINTS[j].name} ${f}" data-f="${f}" /></td>`).join('');
    tr.querySelectorAll('input').forEach((i) => (i.onchange = () => { if (Number.isFinite(+i.value) && i.value !== '') c[i.dataset.f] = +i.value; else i.value = c[i.dataset.f]; }));
    $('calRows').append(tr);
  });
}
$('calJ').innerHTML = R.JOINTS.map((J, j) => `<option value="${j}">J${j} ${J.name}</option>`).join('');
const calJ = () => +$('calJ').value;
function sendRaw(us) {
  us = clamp(Math.round(us), 500, 2500);
  $('rawUs').value = us;
  if (!S.enabled) return note('raw: braccio disabilitato', 'err');
  const j = calJ();
  if (live()) link.raw(j, us);
  else {
    // simulazione: impulso diretto, niente profilo né vincoli (come il device)
    sim.halt();
    sim.q[j] = R.fromUs(j, us);
    sim.target = [...sim.q];
    S.target = [...sim.q];
    syncTargetUI();
  }
}
$('bRaw').onclick = () => sendRaw(+$('rawUs').value);
document.querySelectorAll('[data-us]').forEach((b) => (b.onclick = () => sendRaw(+$('rawUs').value + +b.dataset.us)));
$('calJ').onchange = () => ($('rawUs').value = Math.round(S.us[calJ()]));
$('bRef').onclick = () => { calEdit[calJ()].ref_us = +$('rawUs').value; renderCal(); };
$('bK').onclick = () => {
  const c = calEdit[calJ()], q2 = +$('kAng').value;
  if ($('kAng').value === '' || Math.abs(q2 - c.q_ref) < 1e-6) return note('k: serve un 2° punto diverso da q_ref', 'err');
  c.k = +((+$('rawUs').value - c.ref_us) / (q2 - c.q_ref)).toFixed(3);
  renderCal();
};
function calValid(c) {
  return c.length === 4 && c.every((x) => CAL_F.every((f) => Number.isFinite(x[f])) && x.k !== 0 && x.min < x.max);
}
function applyCal(cal, home) {
  if (!calValid(cal)) return note('Taratura non valida', 'err');
  R.setCal(cal);
  if (home) R.HOME.splice(0, 4, ...home);
  calEdit = cal.map((x) => ({ ...x }));
  renderCal();
  applyLimits();
  buildEnvelope();
  $('calDev').textContent = `${cal.map((x, j) => `${R.JOINTS[j].sym.padEnd(4)} ref ${x.ref_us}  k ${x.k}  q_ref ${x.q_ref}  [${x.min} … ${x.max}]`).join('\n')}\nhome [${R.HOME.join(', ')}]${live() ? '' : '\n(simulazione: taratura locale)'}`;
}
$('bCalGet').onclick = () => (live() ? link.calGet() : applyCal(R.cal));
$('bCalSet').onclick = () => {
  if (!calValid(calEdit)) return note('Taratura non valida (k ≠ 0, min < max)', 'err');
  live() ? link.calSet(calEdit) : applyCal(calEdit);
};
$('bCalSave').onclick = () => (live() ? (link.calSave(), note('cal_save inviato', 'ok')) : note('Simulazione: nessun device su cui salvare', 'err'));
$('bHomeSet').onclick = () => {
  if (live()) { link.homeSet(); link.calGet(); } else { R.HOME.splice(0, 4, ...S.q.map((x) => +x.toFixed(2))); applyCal(R.cal); }
  note('Home impostata sulla posa corrente', 'ok');
};

// ---------- connessione ----------
const fromDevice = !import.meta.env.DEV && location.protocol.startsWith('http');
if (fromDevice) {
  $('wsUrl').value = `ws://${location.host}/ws`;
  $('wsUrl').readOnly = true;
}
$('netForm').addEventListener('submit', (e) => {
  e.preventDefault();
  if (link.want) link.disconnect();
  else link.connect($('wsUrl').value.trim());
});
const STATE_TXT = { off: 'disconnesso', connecting: 'connessione…', on: 'connesso', retry: 'riconnessione' };
link.addEventListener('status', (e) => {
  const { state, delay } = e.detail;
  $('nState').textContent = state === 'retry' ? `riconnessione tra ${(delay / 1000).toFixed(1)} s` : STATE_TXT[state];
  $('nState').className = state === 'on' ? 'ok' : state === 'off' ? '' : 'warn';
  $('bConn').textContent = link.want ? 'Disconnetti' : 'Connetti';
  if (state === 'on') {
    log(`connesso a ${link.url}`);
    S.adopt = true;
    link.calGet();
  } else if (gotState) {
    // si torna in simulazione dall'ultima posa nota
    gotState = false;
    sim.halt();
    sim.q = [...S.q];
    sim.target = [...S.q];
    sim.enabled = S.enabled;
    S.target = [...S.q];
    syncTargetUI();
    seqAbort();
    log('link perso: simulazione', 'err');
  }
});
let gotState = false;
link.addEventListener('msg', (e) => {
  const m = e.detail;
  const arr4 = (a) => Array.isArray(a) && a.length === 4 && a.every(Number.isFinite);
  switch (m.t) {
    case 'state':
      if (!arr4(m.q)) return;
      gotState = true;
      S.q = [...m.q];
      if (arr4(m.us)) S.us = [...m.us];
      S.moving = !!m.moving;
      S.enabled = !!m.enabled;
      if (S.adopt && !S.moving && arr4(m.target)) { S.target = [...m.target]; S.adopt = false; syncTargetUI(); }
      break;
    case 'cal':
      if (Array.isArray(m.cal)) applyCal(m.cal, arr4(m.home) ? m.home : null);
      break;
    case 'err':
      note(`device: ${m.msg}`, 'err');
      break;
    case 'hello':
      $('nFw').textContent = m.fw ?? '—';
      $('nMode').textContent = { sta: 'rete di casa (STA)', ap: 'access point BRACCIO' }[m.mode] ?? m.mode ?? '—';
      log(`hello fw ${m.fw} (${m.mode})`);
      break;
  }
});
setInterval(() => link.checkStale(), 500);

// ---------- HUD ----------
const hq = R.JOINTS.map((J, j) => {
  const tr = document.createElement('tr');
  tr.innerHTML = `<th>${J.sym}</th><td class="mono"></td><td class="mono muted"></td>`;
  $('hQ').append(tr);
  return tr.querySelectorAll('td');
});
function hud() {
  const p = R.fk(S.q);
  $('hX').textContent = f1(p.x);
  $('hY').textContent = f1(p.y);
  $('hZ').textContent = f1(p.z);
  hq.forEach(([a, b], j) => {
    a.textContent = `${f1(S.q[j])} ${R.JOINTS[j].unit}`;
    b.textContent = `${Math.round(S.us[j])} µs`;
    fkRows[j].o.textContent = f1(S.q[j]);
  });
  const d = S.q[1] - S.q[2];
  $('hPar').textContent = `th2−phi ${f1(d)}°`;
  $('hPar').classList.toggle('bad', d < R.PAR[0] || d > R.PAR[1]);
  const L = live();
  $('fMode').textContent = L ? 'LIVE · ESP32' : 'SIMULAZIONE';
  $('fMode').className = `flag ${L ? 'live' : 'sim'}`;
  $('fEn').textContent = S.enabled ? 'ABILITATO' : 'DISABILITATO';
  $('fEn').className = `flag ${S.enabled ? 'on' : 'off'}`;
  $('fMov').textContent = S.moving ? 'IN MOTO' : 'FERMO';
  $('fMov').className = `flag ${S.moving ? 'mov' : ''}`;
  $('hSrc').textContent = L ? 'device (comandato)' : 'simulazione';
  $('hNote').hidden = !L;
  $('calUs').textContent = Math.round(S.us[calJ()]);
}

// ---------- loop ----------
function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host);

let acc = 0, tPrev = performance.now(), tHud = 0;
const tcpV = new THREE.Vector3();
function frame(t) {
  const dt = Math.min(0.1, (t - tPrev) / 1000);
  tPrev = t;
  if (!live()) {
    // simulazione a 50 Hz fissi come il firmware
    for (acc += dt; acc >= DT; acc -= DT) sim.step(DT);
    S.q = [...sim.q];
    S.moving = sim.moving;
    S.enabled = sim.enabled;
    S.us = S.q.map((x, j) => R.toUs(j, x));
  }
  poseRobot(S.q);
  const p = R.fk(S.q);
  tcpV.set(p.x, p.y, p.z);
  tcpDot.position.copy(tcpV);
  if (S.moving) pushTrace(tcpV);
  if (t - tHud > 80) { hud(); tHud = t; }
  orbit.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

// ---------- avvio ----------
buildFK();
renderCal();
renderWP();
$('vR').dispatchEvent(new Event('input'));
applyCal(R.cal);
$('calDev').textContent = '— non letta —';
await buildRobot();
applyLimits();
syncTargetUI();
$('rawUs').value = Math.round(R.toUs(0, S.q[0]));
if (fromDevice) link.connect($('wsUrl').value);
requestAnimationFrame(frame);
