"""Modello elettrico nel tempo: caricatore USB a 2 porte, cavi, WAGO, jumper, condensatore, 4 SG90, ESP32.

Rete risolta a nodi (MNA, Eulero implicito, matrice costante -> LU una volta per topologia).
Riferimento = GND interno del caricatore. Servo e regolatore ESP32 sono generatori di corrente aggiornati a ogni passo.
Tutte le ipotesi numeriche sono qui, commentate; REPORT.md le riassume.
"""
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.linalg import lu_factor, lu_solve

DT = 50e-6  # passo 50 us (verificato contro 20 us in run_all)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("torque", ROOT / "calc" / "torque.py")
torque = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(torque)
KGCM = torque.KGCM

OHM_M = {20: 0.0333, 22: 0.0530, 24: 0.0842, 26: 0.1339, 28: 0.2129, 30: 0.3386}  # rame, ohm/m

# ---- cablaggio: tre casi ----
WIRING = {
    #             cavo B (tagliato)        contatti   jumper 26AWG
    "consigliato": dict(len_b=0.4, awg_b=22, r_ct=0.010, cca=1.0),  # cavo USB-C "3A" accorciato
    "migliore": dict(len_b=0.5, awg_b=24, r_ct=0.010, cca=1.0),
    "nominale": dict(len_b=1.0, awg_b=26, r_ct=0.020, cca=1.0),
    "peggiore": dict(len_b=1.0, awg_b=28, r_ct=0.030, cca=1.6),  # jumper economici in CCA: +60% di resistenza
}


@dataclass
class Cfg:
    wiring: str = "nominale"
    i_lim: float = 3.3        # A, OCP del caricatore "3A" (tipico 3.3-3.6 A); "2A" -> 2.2 A
    v_set: float = 5.10       # V a vuoto
    shared: bool = True       # un solo regolatore per le due porte (caso tipico dei doppi USB economici)
    cap_uF: float = 1000.0    # 0 = senza condensatore
    cap_esr: float = 0.08     # ohm, elettrolitico generico 1000 uF 10 V
    gnd_jumper: bool = True   # massa comune ESP32 -> WAGO GND
    stagger_ms: float = 0.0   # aggancio sfalsato dei servo all'enable
    portb_on_at: float = 0.0  # istante in cui il cavo B viene inserito (hot-plug)
    hiccup: bool = True       # protezione del caricatore: V < 3.0 V per 5 ms -> spento 0.5 s


# ---- SG90 (grandezze riferite all'albero d'uscita) ----
R_M = 6.3        # ohm avvolgimento + ponte H -> stallo 0.73 A a 4.6 V, 0.79 A a 5 V
L_M = 0.4e-3     # H
KE = 0.40        # V/(rad/s): 4.8 V -> ~600 °/s a vuoto (0.1 s/60°)
KT = 0.22        # Nm/A con rendimento ingranaggi ~0.55 -> 1.7 kg*cm in stallo a 4.8 V
J_SERVO = 2.1e-4  # kg m^2 riflessa (costante meccanica ~15 ms)
TF_SERVO = 0.012  # Nm attrito coulombiano interno -> ~55 mA a vuoto in moto
B_SERVO = 2e-4    # Nm/(rad/s)
I_Q = 0.006      # A elettronica a riposo
F_CHOP = 300.0   # Hz PWM interno del driver
E_DB, E_SAT = 1.0, 8.0  # ° banda morta e errore a cui il driver va al 100%
ALPHA_CU = 0.0039

# per giunto: inerzia del link, coppia di gravità di picco (torque.py, payload 30 g), attrito extra
J_LINK = [8e-4, 6e-4, 3e-4, 2e-5]
TG = [0.0, torque.t_shoulder(0.03, False, 2) * KGCM, torque.t_elbow(0.03, False, 4) * KGCM, 0.0]
TF_LINK = [0.45 * KGCM, 0.0, 0.0, 0.0]  # attrito della corona della base (torque.py)
GRIP_DEG_MM = 1.79  # ° servo per mm di apertura


@dataclass
class Servo:
    target: callable          # t -> angolo servo [°] o None (nessun impulso: PWM non agganciato)
    theta0: float = 0.0       # ° posizione iniziale
    wall: tuple = None        # (angolo, verso): ostacolo rigido, verso -1 = blocca sotto l'angolo
    gravity_offset: float = 0.0  # ° fra angolo servo e angolo del link rispetto all'orizzontale
    joint: int = 0
    temp_c: float = 25.0      # temperatura avvolgimento (alza R)
    th: float = field(init=False, default=0.0)
    w: float = field(init=False, default=0.0)
    i: float = field(init=False, default=0.0)
    latched: float = field(init=False, default=None)
    duty: float = field(init=False, default=0.0)

    def __post_init__(self):
        self.th = np.radians(self.theta0)


def _esp_current(t):
    """Assorbimento ESP32 (lato 3.3V) con burst WiFi deterministici; t dal boot."""
    if t < 0:
        return 0.0
    if t < 0.25:
        return 0.06
    if t < 0.8:  # calibrazione RF e avvio AP
        return 0.12 + (0.33 if (t % 0.02) < 0.002 else 0.0)
    i = 0.10
    if (t % 0.05) < 0.001:      # broadcast di stato 20 Hz
        i += 0.25
    if (t % 0.1024) < 0.0008:   # beacon AP
        i += 0.25
    return i


class Net:
    """Rete a nodi con topologia fissa; LU ricalcolata solo se cambia (hot-plug, porte)."""

    def __init__(self, cfg: Cfg, n_servo=4):
        self.cfg = cfg
        w = WIRING[cfg.wiring]
        rc = w["r_ct"]
        r_b = w["len_b"] * OHM_M[w["awg_b"]]
        r_a = 1.0 * OHM_M[28]  # cavo dati normale per l'ESP32
        r_jump = 0.20 * OHM_M[26] * w["cca"]
        r_lead = 0.25 * OHM_M[30]  # cavetto proprio dell'SG90
        r_wago = 0.002
        self.r_servo = r_wago + r_jump + 2 * rc + r_lead  # per conduttore
        self.r_jump = r_jump
        names = ["VB", "VP", "WP", "WG", "CI", "EA", "EG"]
        if not cfg.shared:
            names.append("VBA")
        for k in range(n_servo):
            names += [f"SP{k}", f"SG{k}"]
        self.idx = {n: i for i, n in enumerate(names)}
        self.n = len(names)
        self.res = {  # nome -> (a, b, R)
            "int": ("VB", "VP", 0.04),               # resistenza interna/droop del caricatore
            "b+": ("VP", "WP", 2 * rc + r_b + r_wago),  # contatto USB-A + cavo + WAGO
            "b-": ("WG", None, 2 * rc + r_b + r_wago),
            "a+": ("VBA" if not cfg.shared else "VP", "EA", 4 * rc + r_a),  # USB-A + micro-USB
            "a-": ("EG", None, 4 * rc + r_a),
            "gj": ("EG", "WG", 2 * 0.015 + rc + r_jump + r_wago),  # pin DevKit-breadboard, jumper, WAGO
            "esr": ("WP", "CI", cfg.cap_esr),
        }
        for k in range(n_servo):
            self.res[f"s{k}+"] = ("WP", f"SP{k}", self.r_servo)
            self.res[f"s{k}-"] = (f"SG{k}", "WG", self.r_servo)
        self.caps = [("VB", None, 470e-6), ("EA", "EG", 10e-6)]
        if cfg.cap_uF > 0:
            self.caps.append(("CI", "WG", cfg.cap_uF * 1e-6))
        else:
            self.res["esr"] = ("WP", "CI", 1e6)  # nodo CI sospeso, innocuo
            self.caps.append(("CI", "WG", 1e-9))
        if not cfg.shared:
            self.caps.append(("VBA", None, 470e-6))
        self._lu = {}

    def _stamp(self, M, a, b, g):
        ia = self.idx[a] if a else None
        ib = self.idx[b] if b else None
        if ia is not None:
            M[ia, ia] += g
        if ib is not None:
            M[ib, ib] += g
        if ia is not None and ib is not None:
            M[ia, ib] -= g
            M[ib, ia] -= g

    def lu(self, state):
        """state = (porta B collegata, massa comune collegata)."""
        if state not in self._lu:
            M = np.zeros((self.n, self.n))
            for name, (a, b, r) in self.res.items():
                if name in ("b+", "b-") and not state[0]:
                    r = 1e6
                if name == "gj" and not state[1]:
                    r = 1e6
                self._stamp(M, a, b, 1.0 / r)
            for a, b, c in self.caps:
                self._stamp(M, a, b, c / DT)
            self._lu[state] = lu_factor(M)
        return self._lu[state]

    def current(self, v, name, state=(True, True)):
        a, b, r = self.res[name]
        if (name in ("b+", "b-") and not state[0]) or (name == "gj" and not state[1]):
            return 0.0
        va = v[self.idx[a]] if a else 0.0
        vb = v[self.idx[b]] if b else 0.0
        return (va - vb) / r


class Buck:
    """Regolatore del caricatore: PI su tensione, uscita = corrente limitata (CC), hiccup su sottotensione."""

    def __init__(self, cfg: Cfg, i_lim):
        self.cfg, self.i_lim = cfg, i_lim
        self.integ = 0.0
        self.low_t = 0.0
        self.off_until = -1.0
        self.ss_start = 0.0  # soft-start
        self.trips = 0

    def step(self, t, v):
        if t < self.off_until:
            self.integ = 0.0
            return 0.0
        vref = self.cfg.v_set * min(1.0, (t - self.ss_start) / 3e-3)
        e = vref - v
        kp, ki = 5.0, 9.4e3  # banda ~1.7 kHz con 470 uF
        i = kp * e + self.integ
        if 0.0 < i < self.i_lim:
            self.integ += ki * e * DT
        i = min(max(i, 0.0), self.i_lim)
        self.integ = min(max(self.integ, 0.0), self.i_lim)
        if self.cfg.hiccup and t - self.ss_start > 0.01 and v < 3.0:
            self.low_t += DT
            if self.low_t > 5e-3:
                self.trips += 1
                self.off_until = t + 0.5
                self.ss_start = self.off_until
                self.low_t = 0.0
        else:
            self.low_t = 0.0
        return i


def simulate(cfg: Cfg, servos, t_end, esp_boot_at=0.0, record_every=1, loads_csv=None):
    """Simula t in [0, t_end]. loads_csv: (t, I[N,4]) correnti imposte al posto del modello SG90."""
    net = Net(cfg, len(servos))
    ix = net.idx
    n = net.n
    v = np.zeros(n)
    buck = Buck(cfg, cfg.i_lim)
    buck_a = Buck(cfg, 2.4) if not cfg.shared else None
    v3 = 0.0
    steps = int(round(t_end / DT))
    rec = {k: [] for k in ["t", "vbus", "vwago", "v3", "ibus", "ib", "ia", "igj", "off_sig", "trip"]}
    rec.update({f"vs{k}": [] for k in range(len(servos))})
    rec.update({f"is{k}": [] for k in range(len(servos))})
    rec.update({f"th{k}": [] for k in range(len(servos))})
    stats = {"e_jump": np.zeros(len(servos)), "e_b": 0.0, "e_gj": 0.0, "i2_servo": np.zeros(len(servos)),
             "i2_b": 0.0, "i2_gj": 0.0}
    cap_names = net.caps
    for k, s in enumerate(servos):
        s.latched = None
        # oscillatori interni indipendenti: frequenza e fase diverse per servo (280-320 Hz)
        s._f, s._ph = F_CHOP * (0.93 + 0.045 * k), 0.27 * k
    for kstep in range(steps):
        t = kstep * DT
        state = (t >= cfg.portb_on_at, cfg.gnd_jumper)
        lu = net.lu(state)
        rhs = np.zeros(n)
        for a, b, c in cap_names:
            g = c / DT
            dv = v[ix[a]] - (v[ix[b]] if b else 0.0)
            rhs[ix[a]] += g * dv
            if b:
                rhs[ix[b]] -= g * dv
        rhs[ix["VB"]] += buck.step(t, v[ix["VB"]])
        if buck_a:
            rhs[ix["VBA"]] += buck_a.step(t, v[ix["VBA"]])
        # ESP32: diodo + AMS1117, corrente di ingresso = corrente 3.3V
        i_esp = _esp_current(t - esp_boot_at)
        vin = v[ix["EA"]] - v[ix["EG"]]
        v3_tgt = min(3.3, max(0.0, vin - (0.25 + 0.4 * i_esp) - (0.95 + 0.35 * i_esp)))
        v3 = v3_tgt if v3_tgt >= v3 else max(v3_tgt, v3 - i_esp * DT / 30e-6)  # 30 uF sul 3.3V
        if v3 < 2.3:
            i_esp = 0.0  # in reset
        rhs[ix["EA"]] -= i_esp
        rhs[ix["EG"]] += i_esp
        # servo
        i_s = np.zeros(len(servos))
        for k, s in enumerate(servos):
            vloc = v[ix[f"SP{k}"]] - v[ix[f"SG{k}"]]
            if loads_csv is not None:
                i_s[k] = np.interp(t, loads_csv[0], loads_csv[1][:, k])
            else:
                i_s[k] = _servo_step(s, t, vloc)
            rhs[ix[f"SP{k}"]] -= i_s[k]
            rhs[ix[f"SG{k}"]] += i_s[k]
        v = lu_solve(lu, rhs)
        ib = net.current(v, "b+", state)
        igj = net.current(v, "gj", state)
        for k in range(len(servos)):
            stats["i2_servo"][k] += i_s[k] ** 2 * DT
        stats["i2_b"] += ib**2 * DT
        stats["i2_gj"] += igj**2 * DT
        if kstep % record_every == 0:
            rec["t"].append(t)
            rec["vbus"].append(v[ix["VP"]])
            rec["vwago"].append(v[ix["WP"]] - v[ix["WG"]])
            rec["v3"].append(v3)
            rec["ibus"].append(net.current(v, "int", state))
            rec["ib"].append(ib)
            rec["ia"].append(net.current(v, "a+", state))
            rec["igj"].append(igj)
            # offset di massa visto dal servo 3 (il più lontano in nessun senso: sono tutti uguali; si prende il max)
            rec["off_sig"].append(max(v[ix[f"SG{k}"]] for k in range(len(servos))) - v[ix["EG"]])
            rec["trip"].append(t < buck.off_until)
            for k, s in enumerate(servos):
                rec[f"vs{k}"].append(v[ix[f"SP{k}"]] - v[ix[f"SG{k}"]])
                rec[f"is{k}"].append(i_s[k])
                rec[f"th{k}"].append(np.degrees(s.th))
    out = {k: np.asarray(x) for k, x in rec.items()}
    out["net"] = net
    out["stats"] = stats
    out["trips"] = buck.trips
    out["t_end"] = t_end
    return out


def _servo_step(s: Servo, t, vloc):
    # impulso a 50 Hz: il servo aggiorna il riferimento a ogni frame (canali LEDC sullo stesso timer: fronti allineati)
    frame = int(t / 0.02)
    if getattr(s, "_frame", None) != frame:
        s._frame = frame
        tgt = s.target(frame * 0.02)
        s.latched = tgt
    # driver: duty proporzionale all'errore, chopping a 300 Hz
    if s.latched is None or vloc < 3.0:  # niente impulsi, o elettronica sotto la soglia di funzionamento
        sgn = 0.0
    else:
        err = s.latched - np.degrees(s.th)
        x = t * s._f + s._ph
        per = int(x)
        if getattr(s, "_per", None) != per:
            s._per = per
            s.duty = float(np.clip((abs(err) - E_DB) / (E_SAT - E_DB), 0.0, 1.0))
            s._dir = np.sign(err)
        sgn = s._dir if (x - per) < s.duty else 0.0
    r = R_M * (1 + ALPHA_CU * (s.temp_c - 25))
    vm = sgn * vloc
    s.i = (s.i + DT / L_M * (vm - KE * s.w)) / (1 + DT * r / L_M)  # Eulero implicito
    if s.latched is None:  # servo mai comandato: il braccio controbilanciato resta dove è (attrito ingranaggi)
        s.w = 0.0
        return (I_Q if vloc > 2.5 else 0.0) + sgn * s.i
    # meccanica
    j = s.joint
    ang_link = np.radians(np.degrees(s.th) + s.gravity_offset)
    tau = KT * s.i - TG[j] * np.cos(ang_link) - B_SERVO * s.w
    tf = TF_SERVO + TF_LINK[j]
    if abs(s.w) > 1e-3:
        tau -= np.sign(s.w) * tf
    elif abs(tau) <= tf:
        tau, s.w = 0.0, 0.0
    else:
        tau -= np.sign(tau) * tf
    if s.wall is not None:
        a, d = s.wall
        pen = np.radians(a) - s.th
        if (d < 0 and s.th < np.radians(a)) or (d > 0 and s.th > np.radians(a)):
            tau += 50.0 * pen - 0.5 * s.w  # ostacolo rigido (molla + smorzatore)
    s.w += tau / (J_SERVO + J_LINK[j]) * DT
    s.th += s.w * DT
    return (I_Q if vloc > 2.5 else 0.0) + sgn * s.i


# ---- termico ----

def sg90_thermal(i_of_T, t_end=600.0, t_amb=25.0, dt=0.05):
    """Due costanti di tempo: avvolgimento -> carcassa motore -> ambiente.
    i_of_T(T) -> potenza dissipata [W] in funzione della temperatura dell'avvolgimento."""
    rth_w, cth_w = 18.0, 0.45     # K/W, J/K: tau ~8 s
    rth_c, cth_c = 38.0, 7.0      # K/W, J/K: tau ~270 s (servo intero chiuso nel guscio)
    tw = tc = t_amb
    ts, tws, tcs, ps = [], [], [], []
    for k in range(int(t_end / dt)):
        p = i_of_T(tw)
        tw += dt / cth_w * (p - (tw - tc) / rth_w)
        tc += dt / cth_c * ((tw - tc) / rth_w - (tc - t_amb) / rth_c)
        ts.append(k * dt), tws.append(tw), tcs.append(tc), ps.append(p)
    return np.array(ts), np.array(tws), np.array(tcs), np.array(ps)


def wire_dT(i_rms, ohm_m, d_out=1.3e-3, h=12.0):
    """Sovratemperatura a regime di un filo isolato in aria calma."""
    return i_rms**2 * ohm_m / (h * np.pi * d_out)
