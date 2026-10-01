"""Rigenera tutta la simulazione dinamica: tabelle (results.md, results.json), grafici (fig/), current_profiles.csv.
Uso (dalla radice del progetto):
  python3 -m venv sim/.venv && sim/.venv/bin/pip install mujoco numpy scipy matplotlib
  sim/.venv/bin/python sim/dynamics/run_all.py
"""
import json
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arm  # noqa: E402
from arm import DEFAULT, KGCM, simulate, static_torques  # noqa: E402

OUT = Path(__file__).resolve().parent
FIG = OUT / "fig"
FIG.mkdir(exist_ok=True)
NAMES = ["base", "spalla", "gomito", "pinza"]
md = []  # righe di results.md
res = {}

REACH = [0, 20, 0, 30]  # braccio quasi orizzontale avanti, avambraccio orizzontale: caso peggiore
HOME = [0, 90, 0, 30]
BACK = [0, 160, 10, 30]  # braccio tutto indietro: coppia della spalla invertita
LOADS = [("0 g", 0.0, False), ("30 g", 0.03, False), ("50 g", 0.05, False),
         ("30 g + CAM", 0.03, True), ("50 g + CAM", 0.05, True)]
OBJ = 25.0  # mm, oggetto preso dalla pinza
# Pick & place tra pose estreme (q1, th2, phi, g, oggetto tra le dita)
SEQ = [([-90, 20, 0, 40], None),  # sopra il pezzo, sbraccio massimo a sinistra
       ([-90, 20, 0, 22], OBJ),  # chiude sul pezzo (comando 3 mm sotto la larghezza)
       ([90, 160, 10, 22], OBJ),  # giro completo: base 180°, spalla 140°
       ([0, 60, -70, 22], OBJ),  # deposito basso davanti
       ([0, 60, -70, 40], None),  # apre
       (HOME, None)]
SEQ_NAMES = ["home->sbraccio", "chiude", "giro+indietro", "giù davanti", "apre", "->home"]


def table(head, rows):
    md.append("| " + " | ".join(head) + " |")
    md.append("|" + "---|" * len(head))
    for r in rows:
        md.append("| " + " | ".join(str(x) for x in r) + " |")
    md.append("")


def servo_angles(r):
    """Angoli d'albero dei servo braccio (q1, th2, phi manovella) e del planner."""
    return r["q"][:, [0, 1, 3]], r["plan"][:, :3]


# ------------------------------------------------------------------ 1. tenuta statica


def static_hold(cfg, pose, t=2.0):
    out = []
    for off in (+2.0, -2.0):  # avvicinamento da sopra e da sotto (2° oltre il comando)
        r = simulate(cfg, pose, t_max=t, offset=(0, off, off))
        q, _ = servo_angles(r)
        last = r["t"] > t - 0.5
        err = q[last].mean(0) - np.array(pose[:3])
        tcp = np.linalg.norm(r["tcp"][last].mean(0) - arm.fk(*pose[:3]))
        out.append((err, np.abs(r["u"][last]).mean(0), r["i"][last].mean(0), tcp, np.ptp(q[last], 0)))
    return out


def scenario1():
    md.append("## 1. Tenuta statica\n")
    md.append("Errore a regime (comando − albero) dopo 2 s, avvicinamento da +2° e da −2°. "
              "T = coppia gravitazionale per lavoro virtuale. Duty = uscita del driver (1 = saturo).\n")
    rows, res["static"] = [], []
    for pname, pose in [("REACH th2=20 phi=0", REACH), ("BACK th2=160 phi=10", BACK), ("HOME", HOME)]:
        for lname, pl, cam in LOADS:
            if pose is not REACH and lname not in ("0 g", "50 g + CAM"):
                continue
            cfg = dict(DEFAULT, payload=pl, cam=cam)
            ts, te = static_torques(cfg, pose[1], pose[2])
            a, b = static_hold(cfg, pose)
            es = sorted([a[0][1], b[0][1]])
            ee = sorted([a[0][2], b[0][2]])
            d = dict(pose=pname, load=lname, Ts=ts / KGCM, Te=te / KGCM, err_s=es, err_e=ee,
                     duty_s=max(a[1][1], b[1][1]), duty_e=max(a[1][2], b[1][2]),
                     tcp=max(a[3], b[3]), i=max(a[2][1] + a[2][2], b[2][1] + b[2][2]),
                     ripple=float(max(a[4].max(), b[4].max())))
            res["static"].append(d)
            sf = lambda t: f"{cfg['ts_kgcm'] / abs(t):.1f}" if abs(t) > 1e-3 else "∞"
            rows.append([pname, lname, f"{ts / KGCM:+.2f} (SF {sf(ts / KGCM)})", f"{te / KGCM:+.2f} (SF {sf(te / KGCM)})",
                         f"{es[0]:+.2f} … {es[1]:+.2f}", f"{ee[0]:+.2f} … {ee[1]:+.2f}",
                         f"{d['duty_s']:.2f} / {d['duty_e']:.2f}", f"{d['tcp']:.1f}", f"{d['i'] * 1000:.0f}",
                         f"{d['ripple']:.2f}"])
    table(["posa", "carico", "T spalla kg·cm", "T gomito kg·cm", "err spalla °", "err gomito °",
           "duty sp/gom", "err TCP mm", "I sp+gom mA", "oscill. °"], rows)

    # pose estreme del vincolo: gioco dei perni nel parallelogramma di comando (analitico, non nel modello MuJoCo)
    md.append("Gioco dei perni (clr_pivot 0.3 mm diametrale → 0.15 mm radiale, 2 perni in serie per biella): "
              "rotazione libera dell'avambraccio = 0.3 mm / (crank_r·sin(th2−phi)), del polso = 0.3/(lev_r·sin th2) + "
              "0.3/(lev2_r·cos phi). Sotto carico è un offset ripetibile, a carico nullo è gioco vero.\n")
    rows = []
    for e in (20, 45, 90, 150):
        dphi = math.degrees(0.3 / (20 * math.sin(math.radians(e))))
        rows.append([f"{e}°", f"±{dphi / 2:.2f}°", f"±{math.radians(dphi / 2) * 80:.2f}"])
    table(["th2−phi", "gioco avambraccio", "TCP mm (L2)"], rows)


# ------------------------------------------------------------------ 2. pick & place


def seq_metrics(r):
    """Per ogni segmento e servo: errore d'inseguimento max, sovraelongazione, assestamento, errore finale."""
    q, p = servo_angles(r)
    t, seg = r["t"], r["seg"]
    out = []
    for k in range(len(SEQ)):
        idx = np.where(seg == k)[0]
        if len(idx) == 0:
            continue
        tgt = np.array(SEQ[k][0][:3], float)
        arr = idx[np.all(np.abs(r["plan"][idx] - np.array(SEQ[k][0], float)) < 1e-4, axis=1)]  # pinza compresa
        i_arr = arr[0] if len(arr) else idx[-1]
        mov, dwell = idx[idx <= i_arr], idx[idx > i_arr]
        fin = q[dwell[-100:]].mean(0) if len(dwell) > 100 else q[idx[-1]]
        start = q[idx[0]]
        m = []
        for j in range(3):
            dirn = np.sign(tgt[j] - start[j])
            ov = max(0.0, ((q[dwell, j] - fin[j]) * dirn).max()) if dirn and len(dwell) else 0.0
            bad = dwell[np.abs(q[dwell, j] - fin[j]) > 0.5]
            settle = (t[bad[-1]] - t[i_arr]) if len(bad) else 0.0
            m.append(dict(track=float(np.abs(p[mov, j] - q[mov, j]).max()), over=float(ov), settle=float(settle),
                          fin=float(fin[j] - tgt[j]), sat=float((np.abs(r["u"][idx, j]) > 0.999).mean() * 100),
                          umax=float(np.abs(r["u"][idx, j]).max()), tau=float(np.abs(r["tau"][idx, j]).max() / KGCM)))
        tcp_err = np.linalg.norm(r["tcp"][mov] - np.array([arm.fk(*x) for x in p[mov][:, :3]]), axis=1).max()
        out.append(dict(seg=SEQ_NAMES[k], T=float(t[i_arr] - t[idx[0]]), tcp=float(tcp_err), j=m))
    return out


def run_seq(cfg, v, limits=None):
    return simulate(cfg, HOME, moves=[(tgt, v, 0.8, obj) for tgt, obj in SEQ], limits=limits)


def plot_seq(r, cfg, title, path):
    sv = r["servos"]
    q, p = servo_angles(r)
    fig, ax = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
    for j, c in zip(range(3), ["C0", "C1", "C2"]):
        ax[0].plot(r["t"], p[:, j], c, lw=1, ls="--")
        ax[0].plot(r["t"], q[:, j], c, lw=1.2, label=NAMES[j])
        ax[1].plot(r["t"], p[:, j] - q[:, j], c, lw=1, label=NAMES[j])
        tav = np.array([sv[j].t_avail(w * math.pi / 180) for w in r["vel"][:, [0, 1, 3][j]]]) / KGCM
        ax[2].plot(r["t"], r["tau"][:, j] / KGCM, c, lw=1, label=f"{NAMES[j]} erogata")
        ax[2].fill_between(r["t"], -tav, tav, color=c, alpha=0.07)
    ax[0].set_ylabel("angolo albero °\n(-- planner)")
    ax[1].set_ylabel("errore inseguimento °")
    ax[2].set_ylabel("coppia kg·cm\n(fascia = disponibile a quella velocità)")
    ax[2].axhline(cfg["ts_kgcm"], color="k", lw=0.5, ls=":")
    ax[2].axhline(-cfg["ts_kgcm"], color="k", lw=0.5, ls=":")
    for j in range(4):
        ax[3].plot(r["t"], r["i"][:, j], lw=1, label=NAMES[j])
    ax[3].plot(r["t"], r["i"].sum(1), "k", lw=1, label="totale")
    ax[3].set_ylabel("corrente A")
    ax[3].set_xlabel("t s")
    for a in ax:
        a.grid(alpha=0.3)
        a.legend(fontsize=8, loc="upper right")
    ax[0].set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def seq_summary(ms):
    """Peggiore per servo sull'intera sequenza."""
    s = []
    for j in range(3):
        s.append(dict(track=max(m["j"][j]["track"] for m in ms), over=max(m["j"][j]["over"] for m in ms),
                      settle=max(m["j"][j]["settle"] for m in ms), sat=max(m["j"][j]["sat"] for m in ms),
                      umax=max(m["j"][j]["umax"] for m in ms), tau=max(m["j"][j]["tau"] for m in ms),
                      fin=max((m["j"][j]["fin"] for m in ms), key=abs)))
    return s


def scenario2():
    md.append("## 2. Pick & place tra pose estreme (planner del firmware)\n")
    md.append("Sequenza: " + ", ".join(f"{n} {t[:4]}" for n, (t, _) in zip(SEQ_NAMES, SEQ)) +
              f". Oggetto {OBJ:.0f} mm, payload attaccato per tutta la sequenza (prudente), sosta 0.8 s.\n")
    res["seq"] = {}
    for lname, pl, cam in [("0 g", 0.0, False), ("50 g", 0.05, False), ("30 g + CAM", 0.03, True)]:
        for v in (0.5, 1.0):
            cfg = dict(DEFAULT, payload=pl, cam=cam)
            r = run_seq(cfg, v)
            ms = seq_metrics(r)
            key = f"{lname} v={v}"
            res["seq"][key] = dict(segments=ms, worst=seq_summary(ms), viol=float(r["viol"].max()),
                                   i_peak=float(r["i"].sum(1).max()), i_mean=float(r["i"].sum(1).mean()),
                                   duration=float(r["t"][-1]))
            if lname == "50 g":
                plot_seq(r, cfg, f"Pick & place, {lname}, v={v}", FIG / f"seq_50g_v{v}.png")
                if v == 1.0:
                    write_csv(r)
            md.append(f"### {key}  (durata {r['t'][-1]:.1f} s, vincoli max {r['viol'].max() * 1000:.1f} µm)\n")
            rows = []
            for m in ms:
                for j in range(3):
                    x = m["j"][j]
                    rows.append([m["seg"] if j == 0 else "", f"{m['T']:.2f}" if j == 0 else "", NAMES[j],
                                 f"{x['track']:.2f}", f"{x['over']:.2f}", f"{x['settle']:.2f}", f"{x['fin']:+.2f}",
                                 f"{x['umax']:.2f}", f"{x['sat']:.0f}", f"{x['tau']:.2f}",
                                 f"{m['tcp']:.1f}" if j == 0 else ""])
            table(["moto", "durata s", "servo", "err inseg. max °", "overshoot °", "assest. s (±0.5°)",
                   "err finale °", "duty max", "% saturo", "|T| max kg·cm", "err TCP max mm"], rows)


PLANNER_VARIANTS = [("firmware 90°/s, 180°/s²", None),
                    ("135°/s, 540°/s²", ([135, 135, 135, 60], [540, 540, 540, 120])),
                    ("180°/s, 720°/s²", ([180, 180, 180, 60], [720, 720, 720, 120])),
                    ("90°/s, 720°/s²", ([90, 90, 90, 60], [720, 720, 720, 120]))]


def scenario2b():
    md.append("### 2b. What-if sui limiti del planner (v=1.0, copia di config.h solo in build/)\n")
    rows, res["planner"] = [], {}
    for sname, over in [("1.6 kg·cm", {}), ("1.2 kg·cm", dict(ts_kgcm=1.2))]:
        for pname, lim in PLANNER_VARIANTS:
            cfg = dict(DEFAULT, payload=0.05, **over)
            r = run_seq(cfg, 1.0, lim)
            w = seq_summary(seq_metrics(r))
            move_t = sum(m["T"] for m in seq_metrics(r))
            res["planner"][f"{sname} | {pname}"] = dict(worst=w, move_t=move_t)
            rows.append([sname, pname, f"{move_t:.1f}", " / ".join(f"{x['track']:.1f}" for x in w),
                         " / ".join(f"{x['umax']:.2f}" for x in w), " / ".join(f"{x['sat']:.0f}" for x in w),
                         " / ".join(f"{x['over']:.2f}" for x in w), f"{r['i'].sum(1).max():.2f}"])
    table(["SG90", "limiti planner", "tempo in moto s", "err inseg. max b/sp/gom °", "duty max b/sp/gom",
           "% saturo b/sp/gom", "overshoot b/sp/gom °", "I picco A"], rows)


def write_csv(r):
    """Profilo di corrente per l'analisi elettrica: 1 kHz."""
    data = np.column_stack([r["t"], r["i"], r["i"].sum(1)])
    np.savetxt(OUT / "current_profiles.csv", data, delimiter=",", fmt="%.4f",
               header="t_s,I_base_A,I_spalla_A,I_gomito_A,I_pinza_A,I_tot_A", comments="")


# ------------------------------------------------------------------ 3. caduta con servo sganciati


def fall_event(q, tcp):
    th2, phi = q[1], q[2]
    if tcp[2] <= 0:
        return "tavolo"
    if th2 < arm.LIM_TH2[0] - 5 or th2 > arm.LIM_TH2[1] + 5:
        return "fine corsa spalla"
    if not (arm.LIM_E[0] - 5 <= th2 - phi <= arm.LIM_E[1] + 5):
        return "vincolo th2-phi"
    if abs(phi) > arm.LIM_PHI[1] + 5:
        return "fine corsa gomito"
    return None


def scenario3():
    md.append("## 3. E-stop: PWM sganciato (servo liberi, motore aperto)\n")
    md.append("Tenuta 0.3 s, poi sgancio. L'evento è il primo tra: TCP sul tavolo, spalla o gomito 5° oltre il "
              "limite di giunto, th2−phi 5° oltre il vincolo (urto tra parti). Simulazione fino a 3 s.\n")
    rows, res["estop"] = [], []
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for pname, pose in [("REACH", REACH), ("alto avanti th2=60 phi=40", [0, 60, 40, 30]), ("HOME", HOME), ("BACK", BACK),
                          ("basso avanti th2=40 phi=-50", [0, 40, -50, 30])]:
        for cname, nc, na in [("4+2 piombi", 4, 2), ("senza piombi", 0, 0)]:
            for lname, pl in [("0 g", 0.0), ("50 g", 0.05)]:
                cfg = dict(DEFAULT, payload=pl, n_lead_crank=nc, n_lead_arm=na)
                ev = {}

                def stop(q, tcp, t, ev=ev):
                    e = fall_event(q, tcp) if t > 0.3 else None
                    if e:
                        ev["e"] = e
                    return bool(e)

                r = simulate(cfg, pose, t_max=3.3, estop_at=0.3, stop_on=stop)
                k = r["t"] > 0.3
                spd = np.linalg.norm(np.gradient(r["tcp"], r["t"], axis=0), axis=1) / 1000  # m/s
                q0, q1 = r["q"][k][0], r["q"][-1]
                d = dict(pose=pname, cw=cname, load=lname, event=ev.get("e", "nessuno"),
                         t=float(r["t"][-1] - 0.3), v_tcp=float(spd[-1]), w_s=float(r["vel"][-1, 1]),
                         w_e=float(r["vel"][-1, 2]), d_s=float(q1[1] - q0[1]), d_e=float(q1[2] - q0[2]))
                res["estop"].append(d)
                rows.append([pname, cname, lname, d["event"], f"{d['t']:.2f}" if ev else "> 3",
                             f"{d['d_s']:+.1f} / {d['d_e']:+.1f}", f"{d['w_s']:+.0f} / {d['w_e']:+.0f}",
                             f"{d['v_tcp']:.2f}"])
                if pname.startswith("alto"):
                    lab = f"{cname}, {lname}"
                    ax[0].plot(r["t"] - 0.3, r["q"][:, 1], label=f"th2 {lab}")
                    ax[0].plot(r["t"] - 0.3, r["q"][:, 2], "--", label=f"phi {lab}")
                    ax[1].plot(r["t"] - 0.3, spd, label=lab)
    table(["posa", "contrappesi", "carico", "evento", "t evento s", "Δth2 / Δphi °", "ω spalla / gomito °/s",
           "v TCP m/s"], rows)
    ax[0].set_title("alto avanti (th2=60, phi=40): angoli dopo lo sgancio")
    ax[0].set_xlim(-0.3, 1.5)
    ax[1].set_xlim(-0.3, 1.5)
    ax[0].set_ylabel("°")
    ax[1].set_title("velocità del TCP")
    ax[1].set_ylabel("m/s")
    for a in ax:
        a.set_xlabel("t dallo sgancio s")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "estop.png", dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ 4. sensibilità


SENS = [("nominale", {}),
        ("SG90 1.2 kg·cm", dict(ts_kgcm=1.2)),
        ("attrito alto", dict(mu_pin=0.5, f_axial=10.0, mu_crown=0.35, tf_int_kgcm=0.3)),
        ("manovella 2 piombi", dict(n_lead_crank=2)),
        ("manovella 0 piombi", dict(n_lead_crank=0)),
        ("braccio 0 piombi", dict(n_lead_arm=0)),
        ("gioco 2° + banda 8 µs", dict(backlash_deg=2.0, deadband_us=8.0)),
        ("anello morbido (100% a 8°)", dict(e_full_deg=8.0)),
        ("corona ingrassata μ 0.1", dict(mu_crown=0.1)),
        ("1.2 kg·cm + attrito alto", dict(ts_kgcm=1.2, mu_pin=0.5, f_axial=10.0, mu_crown=0.35, tf_int_kgcm=0.3))]


def scenario4():
    md.append("## 4. Sensibilità (REACH statico e sequenza a v=1.0)\n")
    rows, res["sens"] = [], {}
    labels, sat_s, sat_e = [], [], []
    for lname, pl, cam in [("50 g", 0.05, False), ("30 g + CAM", 0.03, True)]:
        for sname, over in SENS:
            cfg = dict(DEFAULT, payload=pl, cam=cam, **over)
            ts, te = static_torques(cfg, REACH[1], REACH[2])
            a, b = static_hold(cfg, REACH)
            r = run_seq(cfg, 1.0)
            w = seq_summary(seq_metrics(r))
            d = dict(Ts=ts / KGCM, Te=te / KGCM, err_s=max(abs(a[0][1]), abs(b[0][1])),
                     err_e=max(abs(a[0][2]), abs(b[0][2])), duty_s=max(a[1][1], b[1][1]),
                     duty_e=max(a[1][2], b[1][2]), worst=w, i_peak=float(r["i"].sum(1).max()))
            res["sens"][f"{lname} | {sname}"] = d
            rows.append([lname, sname, f"{ts / KGCM:+.2f} / {te / KGCM:+.2f}",
                         f"{cfg['ts_kgcm'] / max(abs(ts), abs(te)) * KGCM:.1f}",
                         f"{d['err_s']:.2f} / {d['err_e']:.2f}", f"{d['duty_s']:.2f} / {d['duty_e']:.2f}",
                         " / ".join(f"{x['track']:.1f}" for x in w), " / ".join(f"{x['sat']:.0f}" for x in w),
                         " / ".join(f"{x['over']:.2f}" for x in w), f"{d['i_peak']:.2f}"])
            labels.append(f"{lname}\n{sname}")
            sat_s.append(d["duty_s"])
            sat_e.append(d["duty_e"])
    table(["carico", "variante", "T statica sp/gom kg·cm", "SF min", "err statico sp/gom °", "duty statico sp/gom",
           "err inseg. max b/sp/gom °", "% saturo b/sp/gom", "overshoot b/sp/gom °", "I picco tot A"], rows)
    # velocità ammessa nei casi peggiori
    md.append("Fattore v del comando nei casi peggiori (50 g, sequenza completa):\n")
    rows = []
    for sname, over in [SENS[1], SENS[2], SENS[-1]]:
        for v in (0.5, 0.7, 1.0):
            w = seq_summary(seq_metrics(run_seq(dict(DEFAULT, payload=0.05, **over), v)))
            rows.append([sname, v, " / ".join(f"{x['umax']:.2f}" for x in w), " / ".join(f"{x['sat']:.0f}" for x in w),
                         " / ".join(f"{x['track']:.1f}" for x in w)])
            res["sens"][f"v | {sname} | {v}"] = w
    table(["variante", "v", "duty max b/sp/gom", "% saturo b/sp/gom", "err inseg. max b/sp/gom °"], rows)
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(labels))
    ax.bar(x - 0.2, sat_s, 0.4, label="spalla")
    ax.bar(x + 0.2, sat_e, 0.4, label="gomito")
    ax.axhline(1.0, color="r", lw=1, label="saturazione")
    ax.axhline(0.5, color="k", lw=0.6, ls=":", label="SF 2")
    ax.set_xticks(x, labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("duty statico in REACH (coppia usata / disponibile)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIG / "sensitivity.png", dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ 5. corrente


def scenario5():
    md.append("## 5. Corrente\n")
    d = np.loadtxt(OUT / "current_profiles.csv", delimiter=",", skiprows=1)
    rows = []
    for j, n in enumerate(NAMES + ["totale"]):
        c = d[:, 1 + j]
        rows.append([n, f"{c.max():.2f}", f"{c.mean():.3f}", f"{np.sqrt((c ** 2).mean()):.3f}"])
    md.append("Sequenza 50 g, v=1.0, nominale (`current_profiles.csv`, 1 kHz). "
              "I = I_idle 10 mA + 0.74 A × |coppia elettromagnetica| / stallo.\n")
    table(["servo", "picco A", "media A", "RMS A"], rows)
    res["current"] = {r[0]: dict(peak=float(r[1]), mean=float(r[2])) for r in rows}

    # presa: corrente e forza a regime in funzione di quanto si comanda la pinza sotto la larghezza del pezzo
    md.append("Presa di un pezzo da 25 mm: comando = larghezza − schiacciamento. Forza richiesta 1.6 N/dito "
              "(50 g, μ 0.3, SF 2).\n")
    rows, res["grip"] = [], []
    for sq in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 25.0):
        g = arm.Gripper(DEFAULT)
        g.obj = OBJ
        g.th = (OBJ - 29.5) * arm.GRIP_DEG_PER_MM * arm.D2R
        g.sv.reset(g.th)
        cmd = (OBJ - sq - 29.5) * arm.GRIP_DEG_PER_MM * arm.D2R
        for _ in range(4000):
            f = g.step(2.5e-4, cmd)
        res["grip"].append(dict(squeeze=sq, force=f, i=g.sv.current()))
        rows.append([f"{OBJ - sq:.1f} mm" + (" (chiudi tutto)" if sq == OBJ else ""), f"{sq:.1f}", f"{f:.1f}",
                     f"{g.sv.current():.2f}", "sì" if f >= 1.6 else "no"])
    table(["comando g", "schiacciamento mm", "forza/dito N", "I a regime A", "presa sicura"], rows)

    # enable con il braccio lontano da home: il servo salta alla posa a velocità piena
    r = simulate(dict(DEFAULT, payload=0.0), HOME, t_max=1.0, offset=(30, -40, -40))
    w = np.abs(r["vel"][:, [0, 1, 3]]).max(0)
    md.append(f"Enable con il braccio a 30°/40°/40° da home (base/spalla/gomito): velocità di picco "
              f"{w[0]:.0f} / {w[1]:.0f} / {w[2]:.0f} °/s, corrente totale di picco {r['i'].sum(1).max():.2f} A "
              f"per {((r['i'].sum(1) > 1.5).sum()) :.0f} ms sopra 1.5 A.\n")
    res["enable"] = dict(w=w.tolist(), i_peak=float(r["i"].sum(1).max()))


if __name__ == "__main__":
    t0 = time.time()
    arm.selfcheck()
    ts, te = static_torques(dict(DEFAULT, payload=0.05), 20, 0)
    md.append("# Risultati simulazione dinamica (generato da run_all.py)\n")
    md.append(f"Massa mobile totale (0 g, 4+2 piombi): {sum(arm.Arm(DEFAULT).m.body_mass) * 1000:.0f} g. "
              f"Coppie statiche REACH 50 g: spalla {ts / KGCM:.3f}, gomito {te / KGCM:.3f} kg·cm.\n")
    for f in (scenario1, scenario2, scenario2b, scenario3, scenario4, scenario5):
        f()
        print(f"{f.__name__} ok ({time.time() - t0:.0f} s)", flush=True)
    (OUT / "results.md").write_text("\n".join(md))
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    print("scritti results.md, results.json, current_profiles.csv, fig/*.png")
