"""8. Monte Carlo delle tolleranze: errore del TCP (accuratezza dopo taratura e ripetibilità) e probabilità
che gli accoppiamenti critici non entrino o abbiano troppo gioco."""
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

import chain as K  # noqa: E402
import common as C  # noqa: E402

P, Y = C.P, C.Y
RNG = np.random.default_rng(2026)
N_ROB, N_REP = 2000, 10          # 20000 campioni per posa
T0 = 0.05 * C.TQ.KGCM * 1000     # N*mm: sotto questa coppia il giunto non sta appoggiato su un lato del gioco
F0 = 0.3                         # N: sotto questa forza un perno non sta appoggiato su un lato del foro
T_FRIC = 0.3 * 0.30 * C.G * 0.050 * 1000  # N*mm: attrito della corona (come calc/torque.py)
PAYLOAD = 0.030                  # prova a 30 g senza camera; taratura a pinza vuota
US_DEG = 11.11
R_TIP = P["horn_len"] / 2 - P["horn_tip_d"] / 2
HOLE_MU, HOLE_SD = -0.08, 0.06   # fori stampati: più stretti di ~0.08, ±0.12 a 2 sigma
EXT_MU, EXT_SD = 0.03, 0.04      # contorni esterni: un filo più grandi
GROUPS = ["banda morta", "cedimento servo", "gioco ingranaggi SG90", "squadrette", "giochi perni",
          "viti E/A inclinate", "lunghezze stampate", "assi dei servo", "cedevolezza struttura", "taratura"]
JOINTS = ["E", "Et", "W", "A", "B", "G", "P1", "U", "V"]


def robots(n):
    r = dict(shrink=RNG.uniform(0, 0.004, n))
    for k in ("L1", "rc", "lb", "L2", "Ld", "Lr1", "Lr2", "lp", "lu", "lv", "L3", "TZ"):
        r["h_" + k] = RNG.normal(0, 0.07, n)            # due fori, ±0.05 ciascuno
    r["dOc"] = RNG.normal(0, 0.15, (n, 2))              # albero gomito rispetto all'albero spalla
    r["dG"] = RNG.normal(0, 0.07, (n, 2))
    bolt = RNG.uniform(2.88, 2.98, (n, len(JOINTS)))
    fix = 3 + P["clr_hole"] + RNG.normal(HOLE_MU, HOLE_SD, (n, len(JOINTS)))
    piv = 3 + P["clr_pivot"] + RNG.normal(HOLE_MU, HOLE_SD, (n, len(JOINTS)))
    c_fix, c_piv = np.clip(fix - bolt, 0, None), np.clip(piv - bolt, 0, None)
    r["play"] = {j: (c_fix[:, i] + c_piv[:, i]) / 2 for i, j in enumerate(JOINTS)}   # gioco radiale relativo
    r["c_arm"], r["c_crank"] = c_fix[:, 0], c_fix[:, 3]
    r["db"] = RNG.uniform(5, 10, (n, 3)) / US_DEG          # banda morta [base, spalla, gomito] in gradi
    r["efull"] = RNG.uniform(2, 6, (n, 3))                 # errore a cui il servo dà la coppia di stallo
    r["bl"] = RNG.uniform(1, 2, (n, 3))                    # gioco degli ingranaggi
    r["spl"] = RNG.uniform(0.2, 0.6, (n, 3))               # scanalato squadretta/albero
    # squadretta a forma nella tasca (torretta e manovella; il braccio la avvita): gioco angolare
    tip = P["horn_tip_d"] + 2 * P["clr_pocket"] + RNG.normal(HOLE_MU, HOLE_SD, (n, 3)) - RNG.uniform(3.8, 4.2, (n, 3))
    r["horn"] = np.degrees(np.clip(tip, 0, None) / R_TIP)
    r["horn"][:, 1] = 0.0
    r["preload"] = RNG.uniform(0, 40, n)                   # N, "senza gioco ma gira libero"
    r["el_scale"] = RNG.uniform(0.7, 1.3, n)               # incertezza del modello di cedevolezza
    r["cal"] = RNG.normal(0, 0.3, (n, 3))                  # errore di lettura in taratura (gradi)
    r["kcal"] = RNG.normal(0, 0.3, (n, 3)) / 90            # errore di scala dalla taratura a 2 punti
    return r


def rep(a, k=N_REP):
    return np.repeat(a, k, axis=0)


def servo_err(T, j, r, n, on, scen):
    """Errore d'angolo del giunto j (gradi) con coppia T; r già ripetuto su n campioni."""
    loaded = abs(T) > T0
    s = -np.sign(T) if loaded else 0.0
    e = np.zeros(n)
    if on("cedimento servo"):
        e += s * abs(T) / C.SG90_T * r["efull"][:, j]
    bands = []
    if on("banda morta"):
        bands.append(r["db"][:, j])
    if on("squadrette"):
        bands.append(r["spl"][:, j] + r["horn"][:, j])
    if on("gioco ingranaggi SG90") and scen == "B":
        bands.append(r["bl"][:, j])
    for b in bands:
        e += s * b / 2 if loaded else RNG.uniform(-0.5, 0.5, n) * b
    return e


def base_err(r, n, on, scen):
    d = RNG.choice([-1.0, 1.0], n)       # verso di arrivo: l'attrito ferma la torretta prima del bersaglio
    e = np.zeros(n)
    if on("cedimento servo"):
        e += T_FRIC / C.SG90_T * r["efull"][:, 0]
    if on("banda morta"):
        e += r["db"][:, 0] / 2
    if on("squadrette"):
        e += (r["spl"][:, 0] + r["horn"][:, 0]) / 2
    if on("gioco ingranaggi SG90") and scen == "B":
        e += r["bl"][:, 0] / 2
    return -d * e


def pin_offset(F, p, n):
    """Il corpo si sposta del gioco nel verso dei carichi esterni (= -reazione del perno)."""
    if np.linalg.norm(F) > F0:
        return -np.outer(p, F / np.linalg.norm(F))
    a = RNG.uniform(0, 2 * math.pi, n)
    return (p * np.sqrt(RNG.uniform(0, 1, n)))[:, None] * np.stack([np.cos(a), np.sin(a)], -1)


def rod_play(f, p, n):
    return np.sign(f) * p if abs(f) > F0 else RNG.uniform(-1, 1, n) * p


def perturb(th2, phi, s, r, n, on, scen, cal=None):
    """Perturbazioni del solutore per la posa (statica s) e i robot r (già ripetuti)."""
    kw = {}
    if on("lunghezze stampate"):
        sh = r["shrink"]
        for k, nom in (("L1", P["L1"]), ("rc", P["crank_r"]), ("lb", P["crank_r"]), ("L2", P["L2"]),
                       ("Ld", P["L1"]), ("Lr1", P["L1"]), ("Lr2", P["L2"]), ("lp", P["lev_r"]),
                       ("lu", P["lev2_r"]), ("lv", P["lev2_r"]), ("L3", P["L3"]), ("TZ", P["tcp_dz"])):
            kw["d" + k] = -sh * nom + r["h_" + k]
        kw["dG"] = r["dG"].copy()
    if on("assi dei servo"):
        kw["dOc"] = r["dOc"].copy()
    dq_sh = servo_err(s["T_sh"], 1, r, n, on, scen)
    dq_el = servo_err(s["T_el"], 2, r, n, on, scen)
    yaw = base_err(r, n, on, scen)
    if on("taratura"):
        dq_sh += r["kcal"][:, 1] * (th2 - 90)
        dq_el += r["kcal"][:, 2] * (phi - 0)
    if cal is not None:
        dq_sh, dq_el, yaw = dq_sh + cal[0], dq_el + cal[1], yaw + cal[2]
    kw.update(dq_sh=dq_sh, dq_el=dq_el)
    d0, ds = np.zeros((n, 2)), np.zeros((n, 2))
    lat = np.zeros(n)
    if on("giochi perni"):
        pl = r["play"]
        kw["eEf"] = pin_offset(s["R_Ef"], pl["E"], n)
        kw["eEt"] = pin_offset(s["R_Et"], pl["Et"], n)
        kw["eW"] = pin_offset(s["R_W"], pl["W"], n)
        kw["dLd"] = kw.get("dLd", 0) + rod_play(s["fd"], pl["A"] + pl["B"], n)
        kw["dLr1"] = kw.get("dLr1", 0) + rod_play(s["f1"], pl["G"] + pl["P1"], n)
        kw["dLr2"] = kw.get("dLr2", 0) + rod_play(s["f2"], pl["U"] + pl["V"], n)
    if on("viti E/A inclinate"):
        bolt = C.elbow_bolt_loads(s)
        Fs = sum(F for F, _ in bolt)
        Mf = np.linalg.norm(sum(F * (y - Y["arm_face"]) for F, y in bolt))
        th = np.where(Mf > r["preload"] * P["m3_head_d"] / 2, r["c_arm"] / (C.UA["t"] + 0.5), 0.0)
        u_ = Fs / max(np.linalg.norm(Fs), 1e-9)
        ds += th[:, None] * u_
        d0 -= th[:, None] * u_ * Y["arm"]
        MA = abs(s["fd"]) * (Y["crank"] - Y["rod"])
        thA = np.where(MA > r["preload"] * P["m3_head_d"] / 2, r["c_crank"] / P["crank_t"], 0.0)
        kw["dLd"] = kw.get("dLd", 0) + np.sign(s["fd"]) * thA * (Y["crank"] - Y["rod"])
    if on("cedevolezza struttura"):
        el, la = K.elastic(s)
        k = r["el_scale"]
        d0 += k[:, None] * el["d0"]
        ds += k[:, None] * el["ds"]
        kw["dOc"] = kw.get("dOc", 0) + k[:, None] * el["dOc"]
        for key in ("dLd", "dLr1", "dLr2"):
            kw[key] = kw.get(key, 0) + k * el[key]
        kw["dG"] = kw.get("dG", 0) + k[:, None] * el["dG"]
        lat += k * la
    kw.update(d0=d0, ds=ds)
    return K.pert(n, **kw), yaw, lat


def tcp_error(th2, phi, payload, r, n, on, scen, cal=None):
    s = C.statics(th2, phi, payload=payload, cam=False)
    p, yaw, lat = perturb(th2, phi, s, r, n, on, scen, cal)
    tcp, ph, _ = K.solve(th2, phi, p)
    nom = K.tcp_nominal(th2, phi)
    d = tcp - nom
    ylat = np.radians(yaw) * nom[0] + lat
    return np.column_stack([d[:, 0], d[:, 1], ylat]), p, ph, yaw


def calibrate(r, on, scen):
    """Taratura in home a pinza vuota: si legge l'angolo vero di braccio, avambraccio e base e si corregge ref_us."""
    n = len(r["shrink"])
    if not on("taratura"):
        return (np.zeros(n),) * 3
    s = C.statics(90, 0, payload=0.0, cam=False)
    p, yaw, _ = perturb(90, 0, s, r, n, on, scen)
    _, ph, _ = K.solve(90, 0, p)
    return (-p["dq_sh"] + r["cal"][:, 1], -(ph - 0.0) + r["cal"][:, 2], -yaw + r["cal"][:, 0])


def run_mc(poses, on=lambda g: True, scen="A", n_rob=N_ROB, n_rep=N_REP):
    r0 = robots(n_rob)
    cal = calibrate(r0, on, scen)
    r = {k: ({j: rep(v, n_rep) for j, v in r0[k].items()} if isinstance(v := r0[k], dict) else rep(v, n_rep))
         for k in r0}
    calr = tuple(rep(c, n_rep) for c in cal)
    out = {}
    for name, (a, b) in poses.items():
        e, *_ = tcp_error(a, b, PAYLOAD, r, n_rob * n_rep, on, scen, calr)
        e = e.reshape(n_rob, n_rep, 3)
        mean = e.mean(1)
        acc = np.linalg.norm(mean, axis=1)
        l = np.linalg.norm(e - mean[:, None, :], axis=2)
        rp = l.mean(1) + 3 * l.std(1)
        out[name] = dict(acc=acc, rp=rp, err=e.reshape(-1, 3))
    return out


# ---------------- accoppiamenti ----------------
def fits(n=100000):
    rng = np.random.default_rng(7)
    rows = []

    def row(name, p_bad, p_loose, note):
        rows.append([name, f"{100 * p_bad:.1f}", "–" if np.isnan(p_loose) else f"{100 * p_loose:.1f}", note])
        return p_bad

    sg = (rng.uniform(22.5, 23.2, n), rng.uniform(12.0, 12.6, n))
    cs = P.get("clr_servo", P["clr_pocket"])   # finestre servo: gioco dedicato in params.scad
    winL = P["sg_body"][0] + 2 * cs
    winW = P["sg_body"][1] + 2 * cs
    bridge = rng.uniform(0.05, 0.3, n)
    eL, eW_ = rng.normal(HOLE_MU, HOLE_SD, n), rng.normal(HOLE_MU, HOLE_SD, n)
    bad = {}
    bad["servo guance"] = row("SG90 nelle finestre delle guance (ponte in alto)",
                              np.mean((sg[0] > winL + eL - bridge) | (sg[1] > winW + eW_)),
                              np.mean((winL + eL - bridge - sg[0]) > 0.6), "finestra verticale: il lato alto è un ponte che cala")
    ef = rng.uniform(0, 0.2, n)
    bad["servo pinza"] = row("SG90 nel piano pinza (stampato capovolto)",
                             np.mean((sg[0] > winL + eL - ef) | (sg[1] > winW + eW_ - ef)), np.nan,
                             "foro sul piatto: piede d'elefante 0–0.2")
    bad["servo base"] = row("SG90 nella torre della base", np.mean((sg[0] > winL + eL) | (sg[1] > winW + eW_)), np.nan, "")
    hl, ht, hh = rng.uniform(31, 33.5, n), rng.uniform(3.8, 4.2, n), rng.uniform(6.9, 7.3, n)
    pl = P["horn_len"] + 2 * P["clr_pocket"] + rng.normal(-0.1, 0.07, n)
    pt = P["horn_tip_d"] + 2 * P["clr_pocket"] + rng.normal(HOLE_MU, HOLE_SD, n)
    ph = P["horn_hub_d"] + 2 * P["clr_pocket"] + rng.normal(HOLE_MU, HOLE_SD, n)
    play = np.degrees(np.clip(pt - ht, 0, None) / R_TIP)
    bad["squadretta"] = row(f"squadretta nella tasca (horn_len {P['horn_len']})", np.mean((hl > pl) | (ht > pt) | (hh > ph)),
                            np.mean(play > 1.0), f"gioco angolare mediano {np.median(play):.1f}° dove non è avvitata")
    s_nut = rng.uniform(5.32, 5.5, n)
    af = P["m3_nut_af"] + 2 * P["clr_pocket"] + rng.normal(HOLE_MU, HOLE_SD, n)
    bad["dadi"] = row("dado M3 nella sede esagonale", np.mean(s_nut > af), np.mean(af > 1.13 * s_nut * 0.98),
                      "gioco eccessivo = il dado gira nella sede")
    Ll, Dl = rng.normal(P["lead_l"], 0.15, n), rng.normal(P["lead_d"], 0.10, n)
    lw = P["lead_pocket"][1] + rng.normal(HOLE_MU, HOLE_SD, n)
    ll = P["lead_pocket"][0] + rng.normal(-0.1, 0.07, n)
    dep = P["lead_depth"] + rng.normal(0, 0.07, n)
    bad["piombi braccio"] = row("piombo nella sede del braccio", np.mean((Dl > lw) | (Ll > ll)), np.mean(Dl > dep),
                                "gioco eccessivo = sporge oltre la sede, il coperchio non chiude")
    bad["piombi manovella"] = row("piombo nella sede della manovella (aperta sul piatto)",
                                  np.mean((Dl > lw - ef) | (Ll > ll - ef)), np.mean(Dl > dep), "piede d'elefante sull'imbocco")
    groove = C.WR["dt_top"] + rng.normal(HOLE_MU, HOLE_SD, n)
    male = C.WR["dt_top"] - 2 * P["clr_slide"] + rng.normal(EXT_MU, EXT_SD, n)
    cusp = rng.uniform(0, 0.1, n)
    c = (groove - male) / 2 - cusp
    bad["cremagliere"] = row("cremagliera nella coda di rondine", np.mean(c < 0.03), np.mean(c > 0.4),
                             f"gioco per lato mediano {np.median(c):.2f} mm (gioco eccessivo > 0.4)")
    d_b = rng.uniform(2.88, 2.98, n)
    bad["fori"] = row(f"vite M3 nel foro passante {3 + P['clr_hole']:.1f}",
                      np.mean(3 + P["clr_hole"] + rng.normal(HOLE_MU, HOLE_SD, n) < d_b), np.nan, "va ripassato con punta da 3.2")
    row(f"vite M3 nel foro di rotazione {3 + P['clr_pivot']:.1f}",
        np.mean(3 + P["clr_pivot"] + rng.normal(HOLE_MU, HOLE_SD, n) < d_b), np.nan, "")
    # varianti
    for hlen in (33.5, 34.0):
        pl2 = hlen + 2 * P["clr_pocket"] + rng.normal(-0.1, 0.07, n)
        row(f"  variante horn_len {hlen}", np.mean((hl > pl2) | (ht > pt) | (hh > ph)), np.nan, "")
    for cp, extra in ((0.25, 0.0), (0.3, 0.0), (0.3, 0.3)):
        w2 = P["sg_body"][1] + 2 * cp
        L2 = P["sg_body"][0] + 2 * cp + extra
        row(f"  variante clr_pocket {cp}" + (f" + {extra} sul lato del ponte" if extra else "") + " (SG90 guance)",
            np.mean((sg[0] > L2 + eL - bridge) | (sg[1] > w2 + eW_)), np.nan, "")
    for cp in (0.3,):
        row(f"  variante clr_pocket {cp} (SG90 piano pinza)", np.mean((sg[0] > winL + 2 * (cp - P['clr_pocket']) + eL - ef)
            | (sg[1] > winW + 2 * (cp - P['clr_pocket']) + eW_ - ef)), np.nan, "")
        row(f"  variante clr_pocket {cp} (SG90 torre base)", np.mean((sg[0] > winL + 2 * (cp - P['clr_pocket']) + eL)
            | (sg[1] > winW + 2 * (cp - P['clr_pocket']) + eW_)), np.nan, "")
    return rows, bad


def run():
    poses = {k: C.POSES[k] for k in ("home", "sbraccio", "basso", "alto")}
    res = {sc: run_mc(poses, scen=sc) for sc in ("A", "B")}
    rows = []
    for sc, lab in (("A", "anello chiuso"), ("B", "gioco SG90 non compensato")):
        for name in poses:
            a, rp = res[sc][name]["acc"], res[sc][name]["rp"]
            rows.append([lab, name, f"{np.median(a):.1f}", f"{np.percentile(a, 95):.1f}",
                         f"{np.median(rp):.1f}", f"{np.percentile(rp, 95):.1f}"])
    # sensibilità: un gruppo alla volta (scenario B)
    sens = []
    for g in GROUPS:
        on = (lambda gg: (lambda x: x == gg or (x == "taratura" and gg != "taratura")))(g)
        rr = run_mc({"home": (90, 0), "sbraccio": (20, 0)}, on=on, scen="B", n_rob=600, n_rep=8)
        sens.append([g] + [f"{np.percentile(rr[p][q], 95):.2f}" for p in ("home", "sbraccio") for q in ("acc", "rp")])
    fit_rows, bad = fits()
    # grafici
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for i, q in enumerate(("acc", "rp")):
        for name in poses:
            ax[i].hist(res["B"][name][q], bins=60, histtype="step", label=name, density=True)
        ax[i].set_xlabel("accuratezza dopo taratura [mm]" if q == "acc" else "ripetibilità ISO 9283 RP [mm]")
        ax[i].legend()
        ax[i].set_title(f"{N_ROB} robot x {N_REP} arrivi, scenario B, 30 g")
    vals = np.array([[float(s[1]), float(s[3])] for s in sens])
    y = np.arange(len(GROUPS))
    ax[2].barh(y - 0.2, vals[:, 0], 0.4, label="accuratezza p95 home")
    ax[2].barh(y + 0.2, vals[:, 1], 0.4, label="accuratezza p95 sbraccio")
    ax[2].set_yticks(y, GROUPS, fontsize=8)
    ax[2].set_xscale("log")
    ax[2].xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax[2].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax[2].set_xlabel("mm (solo questa fonte)")
    ax[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(C.OUT / "v8_montecarlo.png", dpi=110)
    plt.close(fig)
    # scatter dell'errore in home
    e = res["B"]["home"]["err"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
    ax[0].scatter(e[::5, 0], e[::5, 1], s=1, alpha=0.3)
    ax[0].set_xlabel("dx [mm]"); ax[0].set_ylabel("dz [mm]"); ax[0].set_title("home: errore nel piano")
    ax[0].axis("equal")
    ax[1].scatter(e[::5, 0], e[::5, 2], s=1, alpha=0.3)
    ax[1].set_xlabel("dx [mm]"); ax[1].set_ylabel("dy laterale [mm]"); ax[1].set_title("home: vista dall'alto")
    ax[1].axis("equal")
    fig.tight_layout()
    fig.savefig(C.OUT / "v8_scatter_home.png", dpi=110)
    plt.close(fig)

    accB = np.percentile(res["B"]["home"]["acc"], 95)
    rpB = np.percentile(res["B"]["home"]["rp"], 95)
    e_tcp = "OK" if accB < 2 and rpB < 1 else ("riserva" if accB < 5 and rpB < 3 else "KO")
    e_fit = "KO" if max(bad.values()) > 0.2 else ("riserva" if max(bad.values()) > 0.02 else "OK")
    body = f"""{N_ROB} robot virtuali x {N_REP} arrivi per posa ({N_ROB * N_REP} campioni), payload {PAYLOAD * 1000:.0f} g senza camera,
taratura in home a pinza vuota (si legge l'angolo vero di braccio, avambraccio e base; errore di lettura ±0.3°, scala ±0.3°/90°).
Accuratezza = distanza del baricentro degli arrivi dal punto comandato; ripetibilità = RP ISO 9283 (media + 3σ delle distanze
dal baricentro). Errore 3D: piano XZ dal solutore esatto dei parallelogrammi, laterale da imbardata della base e flessione.

Fonti e distribuzioni:
- fori stampati {HOLE_MU:+.2f} ± {HOLE_SD} mm sul diametro, viti M3 2.88–2.98; giochi radiali = metà della somma dei due fori;
  un perno con forza > {F0} N sta appoggiato dal lato del carico (offset ripetibile), sotto è in un punto a caso del gioco;
- interasse dei fori ±0.07 mm, ritiro del PLA 0–0.4% uguale per tutto il robot;
- asse del servo gomito rispetto a quello della spalla ±0.15 mm (finestre + linguette);
- SG90: banda morta 5–10 µs (0.45–0.9°), cedimento sotto carico fino a 2–6° alla coppia di stallo (anello proporzionale),
  gioco ingranaggi 1–2° (solo scenario B), scanalato 0.2–0.6°, squadretta nella tasca dove non è avvitata (torretta, manovella);
  sotto {T0:.0f} N·mm di coppia il giunto non è appoggiato a un lato e si ferma in un punto a caso;
- base: attrito della corona ({T_FRIC:.0f} N·mm) ferma la torretta prima del bersaglio, dal lato da cui arriva;
- viti E e A inclinate nel foro se il loro momento supera il precarico (0–40 N sulla testa);
- cedevolezza strutturale di §1 con incertezza ±30%.

Scenario A: l'anello del servo compensa il gioco degli ingranaggi (il potenziometro è sull'uscita). Scenario B: no.

{C.md_table(["scenario", "posa", "accuratezza mediana mm", "accuratezza p95 mm", "RP mediana mm", "RP p95 mm"], rows)}

Sensibilità (scenario B, una fonte alla volta + taratura; p95 in mm):

{C.md_table(["fonte", "home accuratezza", "home RP", "sbraccio accuratezza", "sbraccio RP"], sens)}

![mc](out/v8_montecarlo.png)

![scatter](out/v8_scatter_home.png)

#### Accoppiamenti (100000 campioni)

Componenti reali: SG90 cloni 22.5–23.2 x 12.0–12.6, squadrette 31–33.5 mm (punte 3.8–4.2, mozzo 6.9–7.3), dadi M3
chiave 5.32–5.50, piombi {P['lead_l']} x {P['lead_d']} (±0.15 / ±0.10 nel lotto). Fori/tasche stampati {HOLE_MU:+.2f} ± {HOLE_SD},
lunghezze delle tasche −0.10 ± 0.07, ponti delle finestre verticali che calano 0.05–0.3, piede d'elefante 0–0.2 sulle aperture
appoggiate al piatto, creste dei layer 0–0.1 sui fianchi della gola a coda di rondine.

{C.md_table(["accoppiamento", "P(non entra senza limare) %", "P(gioco eccessivo) %", "nota"], fit_rows)}
"""
    recs = [
        f"horn_len 32.5 → 33.5: con squadrette fino a 33.5 mm la tasca da 32.9 non le prende nel {100 * bad['squadretta']:.0f}% dei "
        "casi (0.1% con 33.5); la tasca un po' lunga non costa nulla, la squadretta è centrata dall'albero.",
        "Avvitare la squadretta anche nella torretta e nella manovella (2 viti autofilettanti nei fori delle punte, come nel braccio): "
        "toglie il gioco angolare della tasca (mediano 1.3°, sulla base ±1.4 mm al TCP in home).",
        f"Finestre SG90: clr_pocket 0.2 → 0.3 per i servo (guance {100 * bad['servo guance']:.0f}% → 10%, torre base "
        f"{100 * bad['servo base']:.0f}% → ~0%), e nelle guance altri 0.3 mm sul lato alto (ponte che cala) → 0%. "
        "Piano pinza: smusso 0.5 x 45° sul lato del piatto o compensazione del piede d'elefante nello slicer.",
        "Sedi dei piombi della manovella: smusso 0.4 x 45° sull'imbocco (lato piatto) contro il piede d'elefante.",
        "Corona della base: grasso al PTFE e appoggio su un anello più piccolo; l'attrito ferma la torretta prima del bersaglio "
        "dal lato da cui arriva (errore bimodale ±0.5–1° → ±2–3 mm al TCP). In firmware: arrivare sempre dallo stesso verso "
        "(piccolo sovra-corsa e ritorno) dimezza la ripetibilità della base.",
        "Ripetibilità della spalla in home: col braccio verticale la coppia di gravità è nulla con qualunque contrappeso, "
        "quindi il giunto si ferma in un punto a caso della banda morta e dei giochi. Un elastico o una molla a torsione "
        "tra braccio e torretta da ~0.1 kg·cm costanti lo tiene sempre appoggiato dallo stesso lato.",
    ]
    return dict(title="8. Monte Carlo delle tolleranze", esito=C.worst(e_tcp, e_fit), body=body, recs=recs,
                summary=f"home: accuratezza p95 {accB:.1f} mm, RP p95 {rpB:.1f} mm (scenario B); "
                        f"squadretta non entra {100 * bad['squadretta']:.0f}%, SG90 nelle guance {100 * bad['servo guance']:.0f}%")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
