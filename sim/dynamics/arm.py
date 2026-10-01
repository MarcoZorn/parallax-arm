"""Modello dinamico del braccio: MuJoCo (catene chiuse con vincoli `connect`) + servo SG90 + planner del firmware.

Unità interne SI (m, kg, rad). Quote lette da cad/params.scad, masse dai volumi di cad/stl.
Convenzioni come docs/03-protocollo.md: th2, phi assoluti dall'orizzontale, psi = phi + 180 (manovella).
"""
import ctypes
import math
import re
import struct
import subprocess
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
G = 9.81
KGCM = 0.0980665
D2R = math.pi / 180

# ---------------------------------------------------------------- quote e masse


def scad_params(path=ROOT / "cad/params.scad"):
    p = {}
    for m in re.finditer(r"^(\w+)\s*=\s*(-?[\d.]+)\s*;", path.read_text(), re.M):
        p[m.group(1)] = float(m.group(2))
    return p


def stl_volume_cm3(path):
    b = path.read_bytes()
    if b[:5] == b"solid" and b"facet" in b[:300]:
        v = np.array([l.split()[1:] for l in b.decode().splitlines() if l.strip().startswith("vertex")], float)
        t = v.reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", b[80:84])[0]
        a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
        t = a["v"].reshape(-1, 3, 3).astype(float)
    return np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6000


P = scad_params()
MM = 1e-3
L1, L2, L3 = P["L1"] * MM, P["L2"] * MM, P["L3"] * MM
CR, LEV_R, LEV2_R = P["crank_r"] * MM, P["lev_r"] * MM, P["lev2_r"] * MM
SH_H, BASE_H, TCP_DZ = P["sh_h"] * MM, P["base_h"] * MM, P["tcp_dz"] * MM
LIM_E = (20.0, 150.0)  # vettori in params.scad (lim_e, lim_phi): copiati qui
LIM_PHI = (-70.0, 70.0)
LIM_TH2 = (20.0, 160.0)


def part_mass_g(*names, copies=None):
    """Massa stampata: volume STL x PLA 1.24 g/cm3 x 0.6 di riempimento effettivo."""
    tot = 0.0
    for n in names:
        f = next((ROOT / "cad/stl").glob(n + "*.stl"))
        k = 2 if "_x2" in f.name else 1
        tot += k * stl_volume_cm3(f) * 1.24 * 0.6
    return tot


def lead_angles(n):
    """Angoli delle sedi piombi sulla manovella come cad/crank.scad (le centrali prima)."""
    w = P["lead_d"] + 2 * P["clr_pocket"]
    step = 2 * math.degrees(math.asin((w + 2) / 2 / P["cw_elbow_r"]))
    order = {0: [], 2: [-0.5, 0.5], 4: [-1.5, -0.5, 0.5, 1.5], 6: [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]}[n]
    return [k * step for k in order]


# ---------------------------------------------------------------- configurazione

SG90_TS = 1.6  # kg*cm dichiarati @4.8V
DEFAULT = dict(
    payload=0.0,  # kg
    cam=False,
    n_lead_crank=4,
    n_lead_arm=2,
    ts_kgcm=SG90_TS,  # coppia di stallo NETTA in uscita
    tf_int_kgcm=0.15,  # attrito interno riduttore (Coulomb, lato uscita)
    w_nl=math.radians(60) / 0.10,  # 0.1 s/60° a vuoto
    j_motor=2.0e-4,  # inerzia rotore riflessa in uscita (kg m2): costante meccanica ~15 ms
    k_gear=8.0,  # rigidezza ingranaggi+squadretta (N m/rad): 1.1° a coppia di stallo
    c_gear=0.008,
    backlash_deg=1.5,
    deadband_us=5.0,
    e_full_deg=4.0,  # errore oltre la banda morta a cui il driver è al 100%
    i_idle=0.010,
    i_stall=0.75,
    mu_pin=0.3,
    f_axial=2.0,  # N, precarico assiale autobloccanti "a scorrimento"
    mu_crown=0.3,
    m_crown=0.30,  # kg sulla corona
    r_crown=0.050,
    pin_visc=2e-4,  # N m s/rad per perno
    servo_off=False,  # True = PWM sganciato (estop) da t=0
)

# ---------------------------------------------------------------- inerzie


def _inertial(items):
    """items: (massa kg, pos m (3,), inerzia propria 3x3 nel frame corpo). -> massa, com, tensore al com."""
    m = sum(i[0] for i in items)
    c = sum(i[0] * np.asarray(i[1]) for i in items) / m
    Itot = np.zeros((3, 3))
    for mi, p, I in items:
        d = np.asarray(p) - c
        Itot += I + mi * (d @ d * np.eye(3) - np.outer(d, d))
    return m, c, Itot


def bar(m, center, a0, length):
    """Barra sottile lungo u(a0) nel piano XZ."""
    u = np.array([math.cos(a0 * D2R), 0, math.sin(a0 * D2R)])
    I = m * length**2 / 12 * (np.eye(3) - np.outer(u, u)) + m * 0.006**2 / 12 * np.eye(3)  # sezione ~6 mm
    return (m, center, I)


def box(m, center, size):
    a, b, c = size
    return (m, center, np.diag([b * b + c * c, a * a + c * c, a * a + b * b]) * m / 12)


def pt(m, pos):
    return (m, pos, np.zeros((3, 3)))


def lp(a0, along, perp=0.0, y=0.0):
    """Punto nel frame del corpo (allineato al mondo nella posa home) da coordinate di link (mm)."""
    u = np.array([math.cos(a0 * D2R), 0, math.sin(a0 * D2R)])
    n = np.array([-math.sin(a0 * D2R), 0, math.cos(a0 * D2R)])
    return (along * u + perp * n + np.array([0, y, 0])) * MM


# ---------------------------------------------------------------- modello MuJoCo
# Posa home (th2 = 90, phi = 0): tutti i corpi con quat identità, giunti a 0.
# Albero: torretta -> {braccio -> {avambraccio -> polso, triangolo -> biella2}, manovella -> biella motrice,
# biella di livellamento 1 (perno G fisso)}. Tre `connect` chiudono i parallelogrammi (B, P1, V).


def bodies(cfg):
    g = 1e-3  # grammi -> kg
    m_arm = part_mass_g("04_", "05_")
    m_crank = part_mass_g("06_", "07_", "08_")
    m_wrist = part_mass_g("15_", "16_", "17_", "18_", "19_") + 9.0  # + SG90 pinza
    b = {}
    # (pivot nel mondo home relativo al genitore, angolo home, elementi d'inerzia)
    b["turret"] = [box((part_mass_g("03_") + 18.0 + 3.0) * g, [-0.002, 0, 0.030], (0.080, 0.085, 0.070))]
    arm = [bar(m_arm * g, lp(90, -1.2, 0, -19.6), 90, 0.125),  # COM dal modello twin
           pt(3.5 * g, lp(90, 80, 0, -10)),  # perno E (M3x40, distanziali, autobloccante)
           pt(3.2 * g, lp(90, -30, 0, -20))]  # viti coperchio coda
    arm += [pt(20 * g, lp(90, -P["cw_shoulder_r"], 0, -20)) for _ in range(cfg["n_lead_arm"])]
    b["upper_arm"] = arm
    cr = [bar(m_crank * g, lp(180, 28.4, 0, 23.6), 180, 0.060),
          pt(2.0 * g, lp(180, P["crank_r"], 0, 15)), pt(3.2 * g, lp(180, 26, 0, 25))]
    cr += [pt(20 * g, lp(180, P["cw_elbow_r"] * math.cos(a * D2R), -P["cw_elbow_r"] * math.sin(a * D2R), 25))
           for a in lead_angles(cfg["n_lead_crank"])]
    b["crank"] = cr
    b["drive_rod"] = [bar(part_mass_g("09_") * g, lp(90, 40, 0, 11), 90, 0.088)]
    b["lev_rod"] = [bar(part_mass_g("10_") * g, lp(90, 40, 0, -1), 90, 0.088)]
    b["forearm"] = [bar((part_mass_g("13_") + 0.3) * g, lp(0, 34.9, 0.4, -4), 0, 0.105),
                    pt(3.0 * g, lp(0, 80, 0, -8)), pt(1.3 * g, lp(0, -20, 0, 6))]  # perni W, B
    b["lev_link"] = [box((part_mass_g("12_") + 2.6) * g, lp(0, -6.3, 10.7, -5), (0.035, 0.004, 0.035))]
    b["lev_rod2"] = [bar(part_mass_g("11_") * g, lp(0, 40, 0, -9), 0, 0.086)]
    w = [box((m_wrist + 1.4) * g, lp(0, 38.3, 7.2, -1.5), (0.070, 0.070, 0.040))]
    if cfg["payload"] > 0:
        w.append(pt(cfg["payload"], [L3, 0, TCP_DZ]))
    if cfg["cam"]:
        w.append(pt((part_mass_g("20_") + 10.0) * g, [0.055, 0, 0.010]))  # culla + ESP32-CAM ~10 g
    b["wrist"] = w
    return b


def pin_friction(cfg, f_radial):
    return cfg["mu_pin"] * (f_radial * 1.5e-3 + cfg["f_axial"] * 3e-3)


def build_xml(cfg):
    bd = bodies(cfg)

    def inert(name):
        m, c, I = _inertial(bd[name])
        return (f'<inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{m:.6f}" '
                f'fullinertia="{I[0,0]:.4e} {I[1,1]:.4e} {I[2,2]:.4e} {I[0,1]:.4e} {I[0,2]:.4e} {I[1,2]:.4e}"/>')

    def hinge(name, frad):
        return (f'<joint name="{name}" type="hinge" axis="0 -1 0" damping="{cfg["pin_visc"]}" '
                f'frictionloss="{pin_friction(cfg, frad):.5f}" armature="1e-7"/>')

    crown = cfg["mu_crown"] * cfg["m_crown"] * G * cfg["r_crown"]
    # carichi radiali sui perni (N), stima prudente con la forza nelle bielle a th2-phi piccolo
    xml = f"""
<mujoco model="braccio">
  <option timestep="{cfg.get('dt', 2.5e-4)}" gravity="0 0 -{G}" integrator="Euler">
    <flag contact="disable"/>
  </option>
  <worldbody>
    <body name="turret" pos="0 0 {BASE_H}">
      <joint name="q1" type="hinge" axis="0 0 1" damping="1e-4" frictionloss="{crown:.5f}"/>
      {inert('turret')}
      <body name="upper_arm" pos="0 0 {SH_H}">
        {hinge('s', 2.5)}
        {inert('upper_arm')}
        <body name="forearm" pos="0 0 {L1}">
          {hinge('f', 2.0)}
          {inert('forearm')}
          <body name="wrist" pos="{L2} 0 0">
            {hinge('w', 1.5)}
            {inert('wrist')}
          </body>
        </body>
        <body name="lev_link" pos="0 0 {L1}">
          {hinge('l', 2.0)}
          {inert('lev_link')}
          <body name="lev_rod2" pos="0 0 {LEV2_R}">
            {hinge('r2', 2.0)}
            {inert('lev_rod2')}
          </body>
        </body>
      </body>
      <body name="crank" pos="0 0 {SH_H}">
        {hinge('c', 2.5)}
        {inert('crank')}
        <body name="drive_rod" pos="{-CR} 0 0">
          {hinge('d', 3.0)}
          {inert('drive_rod')}
        </body>
      </body>
      <body name="lev_rod" pos="{-LEV_R} 0 {SH_H}">
        {hinge('lr', 3.0)}
        {inert('lev_rod')}
      </body>
    </body>
  </worldbody>
  <equality>
    <connect body1="drive_rod" body2="forearm" anchor="0 0 {L1}" solref="0.0005 1" solimp="0.99 0.999 0.001"/>
    <connect body1="lev_rod" body2="lev_link" anchor="0 0 {L1}" solref="0.0005 1" solimp="0.99 0.999 0.001"/>
    <connect body1="lev_rod2" body2="wrist" anchor="{L2} 0 0" solref="0.0005 1" solimp="0.99 0.999 0.001"/>
  </equality>
</mujoco>"""
    return xml


class Arm:
    """Modello MuJoCo + accesso alle coordinate di giunto del protocollo."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.m = mujoco.MjModel.from_xml_string(build_xml(cfg))
        self.d = mujoco.MjData(self.m)
        self.adr = {n: self.m.joint(n).qposadr[0] for n in ["q1", "s", "f", "w", "l", "r2", "c", "d", "lr"]}
        self.dof = {n: self.m.joint(n).dofadr[0] for n in self.adr}

    def set_pose(self, q1, th2, phi):
        """Posa consistente con i parallelogrammi (gradi)."""
        s = th2 - 90
        val = dict(q1=q1, s=s, f=phi - s, w=-phi, l=-s, r2=phi, c=phi, d=s - phi, lr=s)
        self.d.qpos[:] = 0
        self.d.qvel[:] = 0
        for k, v in val.items():
            self.d.qpos[self.adr[k]] = v * D2R
        mujoco.mj_forward(self.m, self.d)

    def joints(self):
        """(q1, th2, phi_avambraccio, phi_manovella) in gradi, e velocità (°/s)."""
        q, v, a = self.d.qpos, self.d.qvel, self.adr
        dv = self.dof
        pos = np.array([q[a["q1"]], q[a["s"]] + math.pi / 2, q[a["s"]] + q[a["f"]], q[a["c"]]]) / D2R
        vel = np.array([v[dv["q1"]], v[dv["s"]], v[dv["s"]] + v[dv["f"]], v[dv["c"]]]) / D2R
        return pos, vel

    def servo_state(self):
        """Angolo/velocità dell'albero dei 3 servo (base, spalla, gomito) in rad, rad/s."""
        q, v = self.d.qpos, self.d.qvel
        a, dv = self.adr, self.dof
        return (np.array([q[a["q1"]], q[a["s"]] + math.pi / 2, q[a["c"]]]),
                np.array([v[dv["q1"]], v[dv["s"]], v[dv["c"]]]))

    def apply(self, tau):
        self.d.qfrc_applied[:] = 0
        for k, t in zip(["q1", "s", "c"], tau):
            self.d.qfrc_applied[self.dof[k]] = t

    def step(self):
        mujoco.mj_step(self.m, self.d)

    def violation(self):
        """Errore massimo dei vincoli connect (mm)."""
        return float(np.abs(self.d.efc_pos[self.d.efc_type == mujoco.mjtConstraint.mjCNSTR_EQUALITY]).max(initial=0)) / MM


def fk(q1, th2, phi):
    """TCP nel mondo (mm) da gradi."""
    r = L1 * math.cos(th2 * D2R) + L2 * math.cos(phi * D2R) + L3
    z = BASE_H + SH_H + L1 * math.sin(th2 * D2R) + L2 * math.sin(phi * D2R) + TCP_DZ
    return np.array([r * math.cos(q1 * D2R), r * math.sin(q1 * D2R), z]) / MM


def static_torques(cfg, th2, phi, dq=1e-5):
    """Coppie gravitazionali ai servo (N m) per lavoro virtuale: -dV/dq sull'energia potenziale MuJoCo."""
    arm = Arm(cfg)

    def V(t, p):
        arm.set_pose(0, t, p)
        return -sum(arm.m.body_mass[i] * arm.d.xipos[i] @ arm.m.opt.gravity for i in range(arm.m.nbody))

    ts = (V(th2 + dq / D2R, phi) - V(th2 - dq / D2R, phi)) / (2 * dq)
    te = (V(th2, phi + dq / D2R) - V(th2, phi - dq / D2R)) / (2 * dq)
    return ts, te  # coppia che il servo deve FORNIRE = +dV/dq


# ---------------------------------------------------------------- servo SG90


class Servo:
    """SG90 analogico: anello P interno con banda morta sul potenziometro d'uscita, motore DC a PWM
    (curva coppia-velocità lineare, aperto nella banda morta), inerzia del rotore, gioco e
    cedevolezza del riduttore, attrito Coulomb interno. Stato del motore riportato all'uscita."""

    def __init__(self, cfg, k_us_per_deg=11.11):
        self.ts = cfg["ts_kgcm"] * KGCM
        self.tf = cfg["tf_int_kgcm"] * KGCM
        self.tem = self.ts + self.tf  # coppia elettromagnetica di stallo: in uscita restano ts
        self.w_nl = cfg["w_nl"]
        self.w0 = cfg["w_nl"] / (1 - self.tf / self.tem)  # a vuoto (solo attrito) gira a w_nl
        self.J, self.K, self.C = cfg["j_motor"], cfg["k_gear"], cfg["c_gear"]
        self.bl = cfg["backlash_deg"] * D2R / 2
        self.db = cfg["deadband_us"] / k_us_per_deg * D2R
        self.ef = cfg["e_full_deg"] * D2R
        self.i0, self.ist = cfg["i_idle"], cfg["i_stall"]
        self.on = not cfg["servo_off"]
        self.th = self.w = 0.0
        self.u = self.t_em = self.tau = 0.0

    def reset(self, th, preload=0.0):
        """Albero motore allineato all'uscita; preload (N m) carica già il gioco dal lato giusto."""
        self.th = th + (math.copysign(self.bl, preload) + preload / self.K if preload else 0.0)
        self.w = 0.0

    def step(self, dt, cmd, th_o, w_o):
        if self.on:
            e = cmd - th_o
            self.u = 0.0 if abs(e) <= self.db else max(-1.0, min(1.0, (e - math.copysign(self.db, e)) / self.ef))
        else:
            self.u = 0.0
        # PWM: acceso per |u| del tempo a tensione piena, aperto (niente freno) per il resto
        self.t_em = abs(self.u) * self.tem * (math.copysign(1, self.u) - self.w / self.w0) if self.u else 0.0
        dlt = self.th - th_o
        dz = dlt - max(-self.bl, min(self.bl, dlt))
        self.tau = self.K * dz + self.C * (self.w - w_o) if dz else 0.0
        net = self.t_em - self.tau
        if self.w == 0.0 and abs(net) <= self.tf:
            pass  # aderenza
        else:
            s = math.copysign(1, self.w) if self.w else math.copysign(1, net)
            w1 = self.w + dt * (net - self.tf * s) / self.J
            self.w = 0.0 if w1 * self.w < 0 else w1  # l'attrito ferma, non inverte
        self.th += self.w * dt
        return self.tau

    def current(self):
        return self.i0 + (self.ist - self.i0) * abs(self.t_em) / self.tem if self.on else 0.0

    def t_avail(self, w_o):
        """Coppia d'uscita disponibile a quella velocità, nel verso del moto (N m)."""
        return max(0.0, self.ts * (1 - abs(w_o) / self.w_nl))


# ---------------------------------------------------------------- planner del firmware (ctypes)


_LIBS = {}


def planner_lib(vmax=None, amax=None):
    """Compila firmware/src/motion.cpp così com'è. Con vmax/amax (liste da 4) usa una COPIA di config.h
    con quei limiti (solo in build/, il firmware non si tocca): serve per i what-if del planner."""
    tag = "" if vmax is None else "_" + "_".join(f"{x:g}" for x in vmax + amax)
    if tag in _LIBS:
        return _LIBS[tag]
    so = HERE / f"build/libmotion{tag}.so"
    inc = ROOT / "firmware/include"
    src = [ROOT / "firmware/src/motion.cpp", HERE / "planner_shim.cpp", inc / "config.h"]
    if tag:
        inc = HERE / f"build/cfg{tag}"
        inc.mkdir(parents=True, exist_ok=True)
        txt = (ROOT / "firmware/include/config.h").read_text()
        txt = re.sub(r"VMAX\[NJ\] = \{[^}]*\}", "VMAX[NJ] = {" + ", ".join(map(str, vmax)) + "}", txt)
        txt = re.sub(r"AMAX\[NJ\] = \{[^}]*\}", "AMAX[NJ] = {" + ", ".join(map(str, amax)) + "}", txt)
        (inc / "config.h").write_text(txt)
    if not so.exists() or any(s.stat().st_mtime > so.stat().st_mtime for s in src):
        so.parent.mkdir(exist_ok=True)
        subprocess.run(["g++", "-O2", "-shared", "-fPIC", f"-I{inc}", f"-I{ROOT}/firmware/src",
                        *map(str, src[:2]), "-o", str(so)], check=True)
    lib = ctypes.CDLL(str(so))
    F4 = ctypes.c_float * 4
    lib.pl_init.argtypes = [F4]
    lib.pl_move.argtypes = [F4, ctypes.c_float]
    lib.pl_step.argtypes = [ctypes.c_float]
    lib.pl_get.argtypes = [F4, F4]
    lib.pl_us.argtypes = [ctypes.c_int, ctypes.c_float]
    lib.pl_us.restype = ctypes.c_float
    lib.pl_check.argtypes = [F4]
    lib.F4 = F4
    _LIBS[tag] = lib
    return lib


PWM_BITS, PWM_PERIOD = 16, 20000.0
CAL_K = [11.11, 11.11, 11.11, 19.89]
CAL_QREF = [0, 90, 0, 29.5]


def pwm_quantize(us):
    """Come main.cpp: duty = lroundf(us * 2^16 / 20000), poi il servo vede duty * 20000 / 2^16."""
    return round(us * (1 << PWM_BITS) / PWM_PERIOD) * PWM_PERIOD / (1 << PWM_BITS)


def us_to_servo_deg(j, us):
    """Angolo d'albero comandato (°). Per la pinza: gradi del pignone (11.11 µs/°)."""
    return CAL_QREF[j] + (us - 1500) / CAL_K[j] if j < 3 else (us - 1500) / 11.11


# ---------------------------------------------------------------- simulazione completa

GRIP_DEG_PER_MM = 19.89 / 11.11  # 1.79 °/mm (pignone r = 16 mm)


class Gripper:
    """Pinza come 1 gdl: pignone r=16 mm, 2 cremagliere su code di rondine, oggetto rigido tra le dita."""

    def __init__(self, cfg):
        self.sv = Servo(cfg)
        # ponytail: inerzia d'uscita gonfiata 10x (vera ~3e-6) per la stabilità dell'integrazione esplicita;
        # la dinamica la fa comunque il rotore riflesso (2e-4)
        self.J, self.tf, self.r = 3e-5, 0.010, 0.016
        self.th = self.w = 0.0
        self.obj = None  # larghezza oggetto (mm) se c'è un oggetto tra le dita

    def g_mm(self):
        return 29.5 + self.th / D2R / GRIP_DEG_PER_MM

    def step(self, dt, cmd):
        tau = self.sv.step(dt, cmd, self.th, self.w)
        f = 20.0 * (self.obj - self.g_mm()) if self.obj and self.g_mm() < self.obj else 0.0  # 20 N/mm per dito
        net = tau + 2 * f * self.r
        if self.w == 0.0 and abs(net) <= self.tf:
            pass
        else:
            s = math.copysign(1, self.w) if self.w else math.copysign(1, net)
            w1 = self.w + dt * (net - self.tf * s) / self.J
            self.w = 0.0 if w1 * self.w < 0 else w1
        self.th += self.w * dt
        return f


def simulate(cfg, start, moves=(), hold=1.0, estop_at=None, rec_dt=1e-3, stop_on=None, t_max=None, offset=(0, 0, 0),
             limits=None):
    """start: [q1, th2, phi, g]; moves: lista di (target[4], v, dwell_s, obj_mm|None).
    Ogni tick a 50 Hz: planner.step del firmware -> q_to_us -> quantizzazione LEDC -> comando ai servo.
    Ritorna un dict di array registrati a rec_dt."""
    lib = planner_lib(*limits) if limits else planner_lib()
    cfg = dict(cfg)
    arm_ = Arm(cfg)
    arm_.set_pose(*(np.array(start[:3]) + offset))  # offset: posa reale diversa dal comando (avvicinamento)
    dt = arm_.m.opt.timestep
    sv = [Servo(cfg) for _ in range(3)]
    grip = Gripper(cfg)
    grip.th = (start[3] - 29.5) * GRIP_DEG_PER_MM * D2R
    grip.sv.reset(grip.th)
    ts, te = static_torques(cfg, start[1] + offset[1], start[2] + offset[2])
    th_s, _ = arm_.servo_state()
    for k, pre in enumerate([0.0, ts, te]):
        sv[k].reset(th_s[k], pre)
    lib.pl_init(lib.F4(*start))
    qp, vp = lib.F4(), lib.F4()
    cmd = np.zeros(4)

    def update_cmd():
        lib.pl_get(qp, vp)
        for j in range(4):
            cmd[j] = us_to_servo_deg(j, pwm_quantize(lib.pl_us(j, qp[j]))) * D2R

    update_cmd()
    queue = list(moves)
    seg, t_dwell_end, tick = -1, hold if not moves else 0.3, 0.02
    n_tick = int(round(0.02 / dt))
    rec = {k: [] for k in ["t", "plan", "q", "vel", "u", "tau", "i", "tcp", "g", "seg", "viol", "fgrip"]}
    t, i = 0.0, 0
    arrived = True
    if estop_at == 0:
        for s in sv + [grip.sv]:
            s.on = False
    while True:
        if i % n_tick == 0:  # tick di controllo a 50 Hz
            moving = lib.pl_moving()
            if not moving and arrived is False:
                arrived, t_dwell_end = True, t + queue[0][2]
                queue.pop(0)
            if arrived and t >= t_dwell_end:
                if queue:
                    tgt, v, _, obj = queue[0]
                    assert lib.pl_check(lib.F4(*tgt)), tgt
                    lib.pl_move(lib.F4(*tgt), v)
                    grip.obj = obj
                    seg += 1
                    arrived = False
                elif t_max is None or t >= t_max:
                    break
            lib.pl_step(0.02)
            update_cmd()
        if estop_at is not None and estop_at > 0 and t >= estop_at and sv[0].on:
            for s in sv + [grip.sv]:
                s.on = False
        th, w = arm_.servo_state()
        tau = [sv[k].step(dt, cmd[k], th[k], w[k]) for k in range(3)]
        fg = grip.step(dt, cmd[3])
        arm_.apply(tau)
        arm_.step()
        t += dt
        i += 1
        if i % int(round(rec_dt / dt)) == 0:
            q, v = arm_.joints()
            lib.pl_get(qp, vp)
            rec["t"].append(t)
            rec["plan"].append(list(qp))
            rec["q"].append(q)
            rec["vel"].append(v)
            rec["u"].append([s.u for s in sv] + [grip.sv.u])
            rec["tau"].append(tau + [grip.sv.tau])
            rec["i"].append([s.current() for s in sv] + [grip.sv.current()])
            rec["tcp"].append(fk(q[0], q[1], q[2]))
            rec["g"].append(grip.g_mm())
            rec["seg"].append(seg)
            rec["viol"].append(arm_.violation())
            rec["fgrip"].append(fg)
            if stop_on and stop_on(q, rec["tcp"][-1], t):
                break
        if t_max is not None and t >= t_max and not queue and arrived:
            break
    out = {k: np.array(v) for k, v in rec.items()}
    out["servos"] = sv
    out["grip"] = grip
    return out


def selfcheck():
    """Controlli minimi: servo a vuoto e in stallo, equilibrio statico MuJoCo = lavoro virtuale, vincoli chiusi."""
    sv = Servo(DEFAULT)
    for _ in range(8000):  # 2 s a vuoto, comando lontano
        sv.step(2.5e-4, 100.0, sv.th, sv.w)  # uscita solidale al motore
    assert abs(sv.w / math.radians(600) - 1) < 0.02, sv.w
    sv = Servo(DEFAULT)
    sv.th = sv.bl + DEFAULT["ts_kgcm"] * KGCM / sv.K  # albero bloccato, gioco già recuperato
    assert abs(sv.step(2.5e-4, 1.0, 0.0, 0.0) / (DEFAULT["ts_kgcm"] * KGCM) - 1) < 0.01
    cfg = dict(DEFAULT, payload=0.05)
    r = simulate(cfg, [0, 45, 10, 30], t_max=2.0)
    ts, te = static_torques(cfg, *r["q"][-1, 1:3])
    tau = r["tau"][-200:].mean(0)
    fr = pin_friction(cfg, 3.0) * 4  # tolleranza: attrito dei perni
    assert abs(tau[1] - ts) < fr and abs(tau[2] - te) < fr, (tau, ts, te)
    assert r["viol"].max() < 0.05 and abs(r["q"][-1, 2] - r["q"][-1, 3]) < 0.1  # avambraccio = manovella
    print(f"selfcheck ok: spalla {tau[1] / KGCM:.3f} vs {ts / KGCM:.3f}, gomito {tau[2] / KGCM:.3f} vs {te / KGCM:.3f} kg*cm")


if __name__ == "__main__":
    selfcheck()
