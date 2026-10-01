"""Simulazione elettrica BRACCIO: tutti gli scenari, grafici PNG e tabelle per REPORT.md.

    python3 sim/electrical/run_all.py        (~2-3 minuti)
Uscite in sim/electrical/out/: PNG + results.md (tabelle che REPORT.md riporta).
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import model as M
from model import Cfg, Servo, simulate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
CSV_DYN = M.ROOT / "sim" / "dynamics" / "current_profiles.csv"

T_EN = 1.2  # enable dopo il boot (WiFi su)
# posizioni "lontane" compatibili coi limiti di giunto, in gradi servo: base -90, spalla 160 (+70), gomito -70, pinza 0 mm
FAR = [-90.0, 70.0, -70.0, -29.5 * M.GRIP_DEG_MM]
GOFF = [0, 90, 0, 0]  # angolo link = angolo servo + offset (spalla: 0° servo = braccio verticale)

V_SERVO_OK, V_SERVO_KO = 4.3, 4.0   # banda di reset/scatto SG90 ~4.0-4.2 V: sotto 4.0 KO, fino a 4.3 riserva
V3_OK, V3_BOD = 3.0, 2.43           # 3.0 V: minimo per RF/flash; 2.43 V: brownout ESP32 (livello 0)

rows = {}  # nome tabella -> righe


def table(name, header, row):
    rows.setdefault(name, [header]).append(row)


def mavg(x):  # media su 1 ms: il servo non vede le punte da 50 us
    n = int(round(1e-3 / M.DT))
    return np.convolve(x, np.ones(n) / n, mode="valid")


def far_servos(target_fn=lambda j, t: 0.0 if t >= T_EN else None, stagger=0.0, theta0=FAR):
    return [Servo(target=(lambda t, j=j: target_fn(j, t) if t >= T_EN + j * stagger else None),
                  theta0=theta0[j], joint=j, gravity_offset=GOFF[j]) for j in range(4)]


def metrics(r, t0, t1=None):
    t = r["t"]
    m = (t >= t0) & (t <= (t1 if t1 else t[-1]))
    vs = min(mavg(r[f"vs{k}"][m]).min() for k in range(4))
    vs_inst = min(r[f"vs{k}"][m].min() for k in range(4))
    off = r["off_sig"][m]
    v3 = r["v3"][m]
    return dict(vs=vs, vs_inst=vs_inst, vw=mavg(r["vwago"][m]).min(), ipk=r["ibus"][m].max(),
                ibpk=r["ib"][m].max(), v3=v3.min(), off_max=off.max(), off_min=off.min(),
                hi_seen=(v3 - np.maximum(off, 0)).min(), igj=np.abs(r["igj"][m]).max(), trips=r["trips"],
                ripple=np.ptp(r["vwago"][m]))


def verdict(mt):
    ko = mt["trips"] > 0 or mt["vs"] < V_SERVO_KO or mt["v3"] < V3_BOD or mt["hi_seen"] < 1.5 or -mt["off_min"] > 0.8
    res = mt["vs"] < V_SERVO_OK or mt["v3"] < V3_OK or mt["hi_seen"] < 2.0 or -mt["off_min"] > 0.5
    return "KO" if ko else "riserva" if res else "OK"


def fmt_row(label, mt):
    return [label, f"{mt['ipk']:.2f}", f"{mt['vs']:.2f} ({mt['vs_inst']:.2f})", f"{mt['vw']:.2f}", f"{mt['v3']:.2f}",
            f"{mt['off_max']:+.2f}/{mt['off_min']:+.2f}", f"{mt['hi_seen']:.2f}", f"{mt['igj']:.2f}",
            str(mt["trips"]), verdict(mt)]


HDR = ["caso", "I picco caricatore [A]", "V servo min 1ms (istant.) [V]", "V WAGO min [V]", "3V3 min [V]",
       "offset massa max/min [V]", "livello alto visto dal servo min [V]", "I jumper massa max [A]", "trip", "ESITO"]


def plot(r, title, fname, t0=None, extra=None):
    t = r["t"]
    m = t >= (t0 or 0)
    fig, ax = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for k in range(4):
        ax[0].plot(t[m], r[f"vs{k}"][m], lw=0.6, label=f"servo {k}")
    ax[0].plot(t[m], r["vwago"][m], "k", lw=0.8, label="WAGO")
    ax[0].axhline(V_SERVO_KO, color="r", ls="--", lw=0.8)
    ax[0].axhline(V_SERVO_OK, color="orange", ls="--", lw=0.8)
    ax[0].set_ylabel("V servo [V]")
    ax[0].legend(fontsize=7, ncol=5)
    ax[1].plot(t[m], r["ibus"][m], "k", lw=0.6, label="caricatore")
    for k in range(4):
        ax[1].plot(t[m], r[f"is{k}"][m], lw=0.5, label=f"servo {k}")
    ax[1].set_ylabel("I [A]")
    ax[1].legend(fontsize=7, ncol=5)
    ax[2].plot(t[m], r["v3"][m], "b", lw=0.7)
    ax[2].axhline(V3_BOD, color="r", ls="--", lw=0.8)
    ax[2].axhline(V3_OK, color="orange", ls="--", lw=0.8)
    ax[2].set_ylabel("ESP32 3V3 [V]")
    ax[3].plot(t[m], r["off_sig"][m], "m", lw=0.6)
    ax[3].set_ylabel("offset GND servo-ESP [V]")
    ax[3].set_xlabel("t [s]")
    for a in ax:
        a.grid(alpha=0.3)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=110)
    plt.close(fig)


# ---------------- profilo del firmware (trapezio sincronizzato, docs/03 §5) ----------------

def sync_profile(q0, q1, f=1.0):
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    vmax = np.array([90, 90, 90, 60.0]) * f
    amax = np.array([180, 180, 180, 120.0]) * f
    d = np.abs(q1 - q0)

    def T(dj, v, a):
        return 2 * np.sqrt(dj / a) if dj < v * v / a else dj / v + v / a

    Ts = max(T(d[j], vmax[j], amax[j]) for j in range(4))
    j = int(np.argmax([T(d[j], vmax[j], amax[j]) for j in range(4)]))
    v, a = vmax[j], amax[j]
    if d[j] < v * v / a:
        v = np.sqrt(d[j] * a)
    ta = v / a

    def s(t):  # frazione 0..1 del giunto più lento
        t = np.clip(t, 0, Ts)
        if t < ta:
            x = 0.5 * a * t * t
        elif t < Ts - ta:
            x = 0.5 * a * ta * ta + v * (t - ta)
        else:
            x = d[j] - 0.5 * a * (Ts - t) ** 2
        return x / d[j] if d[j] else 1.0
    return Ts, lambda t: q0 + (q1 - q0) * s(t)


def q_to_servo(q):  # unità di giunto -> gradi servo (taratura default)
    return [q[0], q[1] - 90, q[2], (q[3] - 29.5) * M.GRIP_DEG_MM]


def load_dyn_csv():
    """Profili di corrente dall'agente dinamico, se presenti: colonna tempo + 4 correnti [A]."""
    if not CSV_DYN.exists():
        return None
    with open(CSV_DYN) as f:
        rd = list(csv.reader(f))
    head = [h.strip().lower() for h in rd[0]]
    data = np.array([[float(x) for x in r] for r in rd[1:] if r], float)
    ti = next(i for i, h in enumerate(head) if h.startswith("t"))
    ic = [i for i, h in enumerate(head) if i != ti and ("i" in h or "curr" in h) and "id" not in h]
    if len(ic) < 4:
        return None
    t = data[:, ti]
    if t.max() > 100:  # ms
        t = t / 1000
    return t - t[0], data[:, ic[:4]], [rd[0][i] for i in ic[:4]]


# ================================ SCENARI ================================

def s1_boot_enable():
    print("S1 boot + enable")
    res = {}
    for w in ["consigliato", "migliore", "nominale", "peggiore"]:
        for st in [0.0, 0.2]:
            r = simulate(Cfg(wiring=w, stagger_ms=st * 1e3), far_servos(stagger=st), T_EN + 1.4)
            mt = metrics(r, T_EN - 0.05)
            res[(w, st)] = (r, mt)
            table("S1", HDR, fmt_row(f"{w}, {'tutti insieme' if st == 0 else 'sfalsato 200 ms'}", mt))
    plot(res[("peggiore", 0.0)][0], "S1 enable, tutti insieme, cablaggio peggiore", "s1_enable_insieme.png", T_EN - 0.1)
    plot(res[("peggiore", 0.2)][0], "S1 enable sfalsato 200 ms, cablaggio peggiore", "s1_enable_sfalsato.png", T_EN - 0.1)
    # boot: transitorio di accensione completo
    plot(res[("nominale", 0.0)][0], "S1 boot completo (cablaggio nominale)", "s1_boot.png")

    # sweep dello sfalsamento
    for w in ["nominale", "peggiore"]:
        for st in [0, 0.1, 0.15, 0.2, 0.25, 0.3]:
            r = simulate(Cfg(wiring=w), far_servos(stagger=st), T_EN + 1.6)
            mt = metrics(r, T_EN - 0.05)
            tsettle = T_EN + 3 * st + 0.3
            table("S1_stagger", ["cablaggio", "sfalsamento [ms]", "I picco [A]", "V servo min [V]", "3V3 min [V]",
                                 "enable completo dopo [ms]"],
                  [w, f"{st * 1e3:.0f}", f"{mt['ipk']:.2f}", f"{mt['vs']:.2f}", f"{mt['v3']:.2f}",
                   f"{(tsettle - T_EN) * 1e3:.0f}"])

    # hot-plug del cavo B (e-stop hardware rilasciato) con caricatore già acceso
    for w, c, sh in [("nominale", 470, True), ("nominale", 1000, True), ("nominale", 2200, True),
                     ("peggiore", 1000, True), ("nominale", 1000, False)]:
        r = simulate(Cfg(wiring=w, cap_uF=c, portb_on_at=0.8, shared=sh), far_servos(lambda j, t: None), 1.0)
        mt = metrics(r, 0.79)
        table("S1_hotplug", ["cablaggio", "C [uF]", "regolatore", "I spunto picco [A]", "3V3 min [V]", "ESITO"],
              [w, str(c), "condiviso" if sh else "separato", f"{mt['ibpk']:.1f}", f"{mt['v3']:.2f}",
               "KO" if mt["v3"] < V3_BOD or mt["trips"] else "riserva" if mt["v3"] < V3_OK else "OK"])
        if w == "nominale" and c == 1000 and sh:
            plot(r, "S1b hot-plug del cavo B (e-stop hardware riarmato), nominale", "s1_hotplug.png", 0.78)
    return res


def s2_motion():
    print("S2 moto sincronizzato aggressivo")
    qa, qb = [-90, 40, -50, 0], [90, 150, 60, 59]  # th2-phi = 90: dentro il vincolo
    t0 = 0.5

    def make(f):
        T1, p1 = sync_profile(qa, qb, f)
        T2, p2 = sync_profile(qb, qa, f)

        def tgt(j, t):
            if t < t0:
                return q_to_servo(qa)[j]
            if t < t0 + T1:
                return q_to_servo(p1(t - t0))[j]
            return q_to_servo(p2(t - t0 - T1))[j]
        return tgt, T1 + T2
    th0 = q_to_servo(qa)
    dyn = load_dyn_csv()
    out = {}
    for label, cfg, f in [("consigliato", Cfg(wiring="consigliato"), 1.0), ("nominale", Cfg(), 1.0),
                          ("nominale, v=0.5", Cfg(), 0.5),
                          ("peggiore", Cfg(wiring="peggiore"), 1.0), ("peggiore, 2A", Cfg(wiring="peggiore", i_lim=2.2), 1.0),
                          ("nominale, senza C", Cfg(cap_uF=0), 1.0),
                          ("nominale, senza massa comune", Cfg(gnd_jumper=False), 1.0),
                          ("peggiore, senza massa comune", Cfg(wiring="peggiore", gnd_jumper=False), 1.0)]:
        tgt, T = make(f)
        sv = [Servo(target=lambda t, j=j, tgt=tgt: tgt(j, t), theta0=th0[j], joint=j, gravity_offset=GOFF[j])
              for j in range(4)]
        r = simulate(cfg, sv, t0 + T + 0.3, esp_boot_at=-2.0)
        mt = metrics(r, t0)
        out[label] = (r, mt)
        table("S2", HDR, fmt_row(label, mt))
        irms = [np.sqrt(np.mean(r[f"is{k}"][r["t"] > t0] ** 2)) for k in range(4)]
        table("S2_corr", ["caso", "I media caricatore [A]", "I rms per servo [A]", "I picco per servo [A]"],
              [label, f"{np.mean(r['ibus'][r['t'] > t0]):.2f}", " / ".join(f"{x:.2f}" for x in irms),
               " / ".join(f"{r[f'is{k}'].max():.2f}" for k in range(4))])
    if dyn is not None:  # correnti medie (senza chopping) dal modello dinamico: carico imposto
        t, I, names = dyn
        for w in ["nominale", "peggiore"]:
            r = simulate(Cfg(wiring=w), [Servo(target=lambda t: None) for _ in range(4)], t[-1],
                         esp_boot_at=-2.0, loads_csv=(t, I))
            mt = metrics(r, 0.05)
            out[f"csv {w}"] = (r, mt)
            table("S2", HDR, fmt_row(f"{w}, profili sim/dynamics/current_profiles.csv", mt))
        plot(r, "S2 con profili di corrente da sim/dynamics (cablaggio peggiore)", "s2_moto_csv.png")
    plot(out["peggiore"][0], "S2 moto sincronizzato v=1, cablaggio peggiore", "s2_moto.png", t0 - 0.1)
    plot(out["nominale, senza C"][0], "S6 moto senza condensatore (nominale)", "s6_senza_C.png", t0 - 0.1)
    plot(out["peggiore, senza massa comune"][0], "S7 massa comune scollegata (peggiore)", "s7_senza_massa.png", t0 - 0.1)
    return out


def s3_gripper():
    print("S3 pinza in stallo")
    contact = (25 - 29.5) * M.GRIP_DEG_MM  # oggetto da 25 mm
    out = {}
    for label, tg in [("comando 0 mm (45° oltre il contatto)", -29.5 * M.GRIP_DEG_MM),
                      ("comando 3° oltre il contatto", contact - 3.0),
                      ("comando 2° oltre il contatto", contact - 2.0)]:
        sv = [Servo(target=lambda t, j=j: 0.0 if j < 3 else None, theta0=0.0, joint=j, gravity_offset=GOFF[j])
              for j in range(4)]
        sv[3] = Servo(target=lambda t, tg=tg: tg if t > 0.2 else 0.0, theta0=0.0, joint=3, wall=(contact, -1))
        r = simulate(Cfg(wiring="peggiore"), sv, 1.5, esp_boot_at=-2.0)
        m = r["t"] > 0.8
        i_avg = np.mean(r["is3"][m])
        v_avg = np.mean(r["vs3"][m])
        duty = sv[3].duty
        # potenza nel servo vs temperatura: duty * V^2 / R(T) (chopping a 300 Hz, L/R << periodo)
        def p_of_T(T, d=duty, v=v_avg):
            return d * v * v / (M.R_M * (1 + M.ALPHA_CU * (T - 25))) + M.I_Q * v
        ts, tw, tc, p = M.sg90_thermal(p_of_T, t_end=900)
        def t_reach(x):
            k = np.argmax(tw >= x)
            return f"{ts[k]:.0f}" if tw[k] >= x else "mai"
        f_jaw = M.KT * duty * v_avg / M.R_M / (2 * 0.016)
        out[label] = (ts, tw, tc, p)
        table("S3", ["caso", "duty driver", "I media [A]", "P iniziale [W]", "forza/dito [N]", "T avvolg. 60 s [°C]",
                     "T avvolg. regime [°C]", "t a 80 °C [s]", "t a 120 °C [s]", "ESITO"],
              [label, f"{duty:.2f}", f"{i_avg:.2f}", f"{p[0]:.2f}", f"{f_jaw:.1f}", f"{np.interp(60, ts, tw):.0f}",
               f"{tw[-1]:.0f}", t_reach(80), t_reach(120),
               "KO" if np.interp(60, ts, tw) > 100 or tw[-1] > 120 else "riserva" if tw[-1] > 70 else "OK"])
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, (ts, tw, tc, p) in out.items():
        ax.plot(ts, tw, label=f"avvolgimento, {label}")
        ax.plot(ts, tc, ls="--", lw=0.8, label=f"carcassa, {label}")
    ax.axhline(80, color="orange", ls=":", lw=1)
    ax.axhline(120, color="r", ls=":", lw=1)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("T [°C]")
    ax.set_title("S3 SG90 pinza in stallo: temperatura (25 °C ambiente)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "s3_pinza_termico.png", dpi=110)
    plt.close(fig)


def s4_all_stall():
    print("S4 tutti in stallo / S5 caricatore 2A")
    res = {}
    for label, cfg in [("3A, nominale", Cfg()), ("3A, peggiore", Cfg(wiring="peggiore")),
                       ("3A, migliore", Cfg(wiring="migliore")), ("3A, consigliato", Cfg(wiring="consigliato")),
                       ("2A, nominale", Cfg(i_lim=2.2, v_set=5.05)), ("2A, peggiore", Cfg(wiring="peggiore", i_lim=2.2, v_set=5.05)),
                       ("3A, peggiore, regolatori separati", Cfg(wiring="peggiore", shared=False))]:
        walls = [(5.0, 1), (5.0, 1), (5.0, 1), (5.0, 1)]  # ostacolo a +5°, comando +45°
        sv = [Servo(target=lambda t: 45.0 if t > 0.3 else 0.0, theta0=0.0, joint=j, gravity_offset=GOFF[j],
                    wall=walls[j]) for j in range(4)]
        r = simulate(cfg, sv, 2.0, esp_boot_at=-2.0)
        mt = metrics(r, 0.3)
        res[label] = (r, mt)
        table("S4", HDR, fmt_row(label, mt))
        m = r["t"] > 1.0
        net = r["net"]
        i_s = np.mean([np.mean(r[f"is{k}"][m]) for k in range(4)])
        ib = np.mean(r["ib"][m])
        igj = np.mean(np.abs(r["igj"][m]))
        w = M.WIRING[cfg.wiring]
        ohm_b = M.OHM_M[w["awg_b"]]
        table("S4_cavi", ["caso", "I per servo [A]", "caduta jumper+contatti+cavetto servo, A/R [V]",
                          "P per jumper 26AWG [mW]", "P per contatto [mW]", "dT jumper [K]",
                          "I cavo B [A]", "caduta cavo B A/R [V]", "P cavo B [W]", "dT cavo B [K]",
                          "I massa via ESP32 [A]"],
                      [label, f"{i_s:.2f}", f"{2 * i_s * net.r_servo:.2f}", f"{i_s ** 2 * net.r_jump * 1e3:.0f}",
                       f"{i_s ** 2 * w['r_ct'] * 1e3:.0f}", f"{M.wire_dT(i_s, M.OHM_M[26] * w['cca']):.1f}",
                       f"{ib:.2f}", f"{2 * ib * (w['len_b'] * ohm_b + 2 * w['r_ct']):.2f}",
                       f"{2 * ib ** 2 * w['len_b'] * ohm_b:.2f}", f"{M.wire_dT(ib, ohm_b, d_out=3e-3):.0f}",
                       f"{igj:.2f}"])
    plot(res["3A, peggiore"][0], "S4 tutti in stallo, 3A, cablaggio peggiore", "s4_stallo_3A.png")
    plot(res["2A, nominale"][0], "S5 tutti in stallo, caricatore 2A (nominale)", "s5_stallo_2A.png")

    # S5: enable e moto col 2A
    for st in [0.0, 0.2]:
        for w in ["nominale", "peggiore"]:
            r = simulate(Cfg(wiring=w, i_lim=2.2, v_set=5.05), far_servos(stagger=st), T_EN + 1.4)
            mt = metrics(r, T_EN - 0.05)
            table("S5", HDR, fmt_row(f"2A, {w}, enable {'tutti insieme' if st == 0 else 'sfalsato 200 ms'}", mt))


def s6_cap_sweep():
    print("S6 scelta condensatore")
    for c in [0, 100, 470, 1000, 2200, 4700]:
        r = simulate(Cfg(wiring="peggiore", cap_uF=c), far_servos(), T_EN + 0.6)
        mt = metrics(r, T_EN - 0.02)
        m = (r["t"] > T_EN) & (r["t"] < T_EN + 0.3)
        table("S6", ["C [uF]", "V servo min 1ms [V]", "V servo min istant. [V]", "ripple WAGO pk-pk [V]",
                     "I picco caricatore [A]", "3V3 min [V]"],
              [str(c), f"{mt['vs']:.2f}", f"{mt['vs_inst']:.2f}", f"{np.ptp(r['vwago'][m]):.2f}",
               f"{mt['ipk']:.2f}", f"{mt['v3']:.2f}"])


def check_dt():
    """Convergenza: S1 peggiore a 50 us contro 20 us."""
    out = []
    for dt in [50e-6, 20e-6]:
        M.DT = dt
        r = simulate(Cfg(wiring="peggiore"), far_servos(), T_EN + 0.5, record_every=1)
        out.append(metrics(r, T_EN - 0.05))
    M.DT = 50e-6
    for d, m in zip([50, 20], out):
        table("dt", ["passo", "I picco [A]", "V servo min [V]", "3V3 min [V]"],
              [f"{d} us", f"{m['ipk']:.3f}", f"{m['vs']:.3f}", f"{m['v3']:.3f}"])
    assert abs(out[0]["vs"] - out[1]["vs"]) < 0.03, "passo troppo grande"


def write_md():
    with open(OUT / "results.md", "w") as f:
        for name, rr in rows.items():
            f.write(f"### {name}\n\n| " + " | ".join(rr[0]) + " |\n|" + "---|" * len(rr[0]) + "\n")
            for r in rr[1:]:
                f.write("| " + " | ".join(r) + " |\n")
            f.write("\n")


if __name__ == "__main__":
    check_dt()
    s1_boot_enable()
    s2_motion()
    s3_gripper()
    s4_all_stall()
    s6_cap_sweep()
    write_md()
    print((OUT / "results.md").read_text())
