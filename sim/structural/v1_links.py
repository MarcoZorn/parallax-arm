"""1. Link e bielle: tensioni (statico peggiore sulla griglia di pose, dinamico x2, stallo) e freccia al TCP."""
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import chain as K  # noqa: E402
import common as C  # noqa: E402

P, MAT, Y = C.P, C.MAT, C.Y


def member_stresses(s, k=1.0):
    """Tensioni (MPa) nei membri per la posa s, carichi x k. Ritorna {nome: (sigma_o_tau, ammissibile, nota)}."""
    th2, e = s["th2"], s["e"]
    fd, f1, f2 = k * s["fd"], k * s["f1"], k * s["f2"]
    bolt = [(k * F, y) for F, y in C.elbow_bolt_loads(s)]
    out = {}
    # braccio: nel piano alla sezione x=20 (foro cavo 4.5 + canalina), fuori piano e torsione costanti
    Fs = sum(F for F, _ in bolt)
    Fperp = abs(Fs @ C.u(th2 + 90))
    half = (9 - 2 * 20 / 80) - 2.25                          # ali ai lati del foro cavo
    I20 = 2 * (6 * half**3 / 12 + 6 * half * (2.25 + half / 2) ** 2)
    s_in = Fperp * (P["L1"] - 20) / (I20 / (half + 2.25))
    y_arm = Y["arm"] + K.ARM["yc"]
    M = sum(K._moment_xz(F, y - y_arm) for F, y in bolt)
    s_out = abs(M @ C.u(th2 + 90)) / (K.ARM["I"] / (3 + abs(K.ARM["yc"])))
    tau = abs(M @ C.u(th2)) / (2 * (16 - 1.2) * (6 - 0.8) * 0.8)   # Bredt, parete minima 0.8
    out["braccio (in piano)"] = (math.hypot(s_in + s_out, math.sqrt(3) * tau), MAT["s_xy"],
                                 "flessione nel piano + fuori piano + torsione, sezione al foro cavo x=20")
    # avambraccio: piastra R alla leva B (stampato di fianco: X nel piano, altezza 14 lungo Z stampa)
    Mfa = abs(fd) * P["crank_r"] * math.sin(math.radians(e))
    I_r = C.rect_I(4, 14, perim_b=MAT["perim"], perim_h=MAT["skin_tb"]) - 4 * 3.3**3 / 12
    out["avambraccio piastra R (di fianco)"] = (Mfa / (I_r / 7), MAT["s_xy"], "momento della leva B al perno E")
    out["avambraccio taglio tra layer"] = (1.5 * abs(fd) / (4 * 14), MAT["t_il"], "taglio all'asse neutro = piano dei layer")
    # bielle: trazione/compressione + instabilità (fuori piano, spessore t)
    for name, f, t in (("biella motrice", fd, P["rod_t"]), ("biella livell. 1", f1, P["rod_t"]),
                       ("biella livell. 2", f2, P["rod2_t"])):
        A = P["rod_w"] * t - 3.3 * t
        out[name + " (assiale)"] = (abs(f) / A, MAT["s_xy"], "sezione netta all'occhio")
        Pcr = math.pi**2 * MAT["E_xy"] * P["rod_w"] * t**3 / 12 / P["L1"] ** 2
        # secante con eccentricità 0.3 mm: sigma = P/A (1 + e c/r^2 sec(...)) -> la confrontiamo con s_xy
        if f < 0:
            r2 = t**2 / 12
            sec = 1 / math.cos(min(math.pi / 2 * 0.99, math.pi / 2 * math.sqrt(abs(f) / Pcr)))
            out[name + " (carico di punta)"] = (abs(f) / (P["rod_w"] * t) * (1 + 0.3 * (t / 2) / r2 * sec),
                                                 MAT["s_xy"], f"Pcr Euler {Pcr:.0f} N")
    # triangolo: leve P1 (20) e U (30), larghe ~10.5, spessore 3.5 (in piano)
    Zt = 3.5 * 10.5**2 / 6
    out["triangolo (leve P1/U)"] = (max(abs(f1) * P["lev_r"], abs(f2) * P["lev2_r"]) / Zt, MAT["s_xy"], "")
    # manovella: nel piano (coppia della biella) + fuori piano (biella a 9.1 mm dal piano)
    Mc_in = abs(fd) * P["crank_r"] * math.sin(math.radians(e))
    out["manovella"] = (Mc_in / (4 * 12**2 / 6) + abs(fd) * (Y["crank"] - Y["rod"]) / (12 * 4**2 / 6), MAT["s_xy"],
                        "piastra 4 mm, sezione 12 x 4 al mozzo")
    # montante G (in piedi: tensioni verticali = tra layer)
    FG = k * s["F_G"]
    h = P["sh_h"] - P["floor_t"]
    out["montante G (in piedi)"] = (abs(FG[0]) * h / (3 * 16**2 / 6) + abs(f1) * (Y["post"] - Y["lev"]) / (16 * 3**2 / 6),
                                    MAT["s_z"], "lastra 16 x 3 alla base, tensione verticale tra layer")
    # guance: momento fuori piano al livello dei fazzoletti (z 29), lastra 3 mm larga ~55 (tra layer)
    Msh = sum(K._moment_xz(F, y - Y["sh_shaft"]) for F, y in bolt)
    w = K._cheek_width()(29)
    out["guancia spalla (in piedi)"] = (abs(Msh[0]) / (w * P["cheek_t"] ** 2 / 6), MAT["s_z"],
                                        "flessione fuori piano sopra i fazzoletti")
    out["guancia spalla torsione"] = (3 * abs(Msh[1]) / (w * P["cheek_t"] ** 2), MAT["t_il"], "torsione attorno a Z")
    # staffa del polso: leva V (stampata di fianco, profilo nel piano)
    out["staffa polso (leva V)"] = (abs(k * s["M_gW"]) / (3.5 * 12**2 / 6), MAT["s_xy"], "")
    return out


def finger(F):
    """Dito della ganascia: forza di presa F (N) al centro del cuscinetto, sull'asse del pignone.
    Gambo 3.5 x 4 (y = Z di stampa) in torsione + flessione; cuscinetto 16 x 4 a sbalzo in X."""
    W = C.WR
    x_stem = W["rack_out"] - W["rp"] + W["stem_t"] / 2             # asse gambo dalla linea primitiva
    arm_x = x_stem + W["rp"]                                        # fino all'asse del pignone (TCP)
    z_pad = W["rack_bot"] - W["tcp_z"]                              # dal fondo cremagliera al centro dita
    b, c = W["tab"][1], W["stem_t"]
    tau = C.rect_tau(F * arm_x, b, c)
    sig = F * z_pad / (W["stem_t"] * b**2 / 6)
    pad = F * (arm_x - W["stem_t"] / 2) / (W["pad"][1] * b**2 / 6)
    defl = F * arm_x**2 * (z_pad) / (K.G_Z * C.rect_J(b, c)) + F * arm_x**3 / (3 * MAT["E_xy"] * W["pad"][1] * b**3 / 12)
    return dict(tau=tau, sig=sig, pad=pad, defl=defl, arm_x=arm_x)


def run():
    OUTD = C.OUT
    grid = list(C.pose_grid())
    stats = [C.statics(a, b) for a, b in grid]
    # ---- tensioni: peggiore sulla griglia, statico e dinamico ----
    worst = {}
    for s in stats:
        for k, (v, allow, note) in member_stresses(s).items():
            if k not in worst or v > worst[k][0]:
                worst[k] = (v, allow, note, (s["th2"], s["phi"]))
    # stallo del servo gomito contro un ostacolo (coppia reale 2 kg*cm) a e minimo: forza nella biella
    s_st = C.statics(20, 0)
    k_stall = C.SG90_T_REAL / abs(s_st["fd"] * P["crank_r"] * math.sin(math.radians(20)))
    stall = member_stresses(s_st, k_stall)
    rows, es = [], []
    for k, (v, allow, note, pose) in worst.items():
        sf_dyn = allow / (C.DYN * v)
        vst = stall.get(k, (float("nan"),))[0]
        e = C.sf_esito(sf_dyn)
        es.append(e)
        rows.append([k, f"{pose[0]}/{pose[1]}", f"{v:.2f}", f"{C.DYN * v:.2f}", f"{vst:.2f}", f"{allow:.0f}",
                     f"{sf_dyn:.1f}", e, note])
    fg = [finger(C.SG90_T / (2 * C.WR["rp"])), finger(C.SG90_T_REAL / (2 * C.WR["rp"]))]
    sf_f = MAT["t_il"] / fg[1]["tau"]
    e_f = C.sf_esito(sf_f, 2.0, 1.2)
    es.append(e_f)
    rows.append(["dito ganascia: torsione gambo", "presa", f"{fg[0]['tau']:.2f}", "-", f"{fg[1]['tau']:.2f}",
                 f"{MAT['t_il']:.0f}", f"{sf_f:.1f} (stallo)", e_f,
                 f"gambo {C.WR['stem_t']} x {C.WR['tab'][1]}, leva {fg[0]['arm_x']:.0f} mm, taglio sui piani dei layer"])
    # dito ridimensionato
    Wd = dict(C.WR)
    C.WR.update(stem_t=6.0, tab=[3.5, 5.0])
    fg_fix = finger(C.SG90_T_REAL / (2 * C.WR["rp"]))
    C.WR.clear(); C.WR.update(Wd)

    # ---- freccia al TCP ----
    var = {
        "attuale": {},
        "A: nervature braccio 6 mm + fazzoletti 50 mm": dict(arm=K.arm_section(rib=6), cheek=K.CHEEK_FIX),
        "B: A + mozzo E 14 mm e perno d4": dict(arm=K.arm_section(rib=6), cheek=K.CHEEK_FIX, e_hole=14.0, e_bolt_d=3.4),
    }
    pose_rows, contrib_rows = [], []
    for name, (a, b) in C.POSES.items():
        s = C.statics(a, b)
        tot = {vn: np.linalg.norm(K.tcp_deflection(s, **kw)) for vn, kw in var.items()}
        d = K.tcp_deflection(s)
        pose_rows.append([f"{name} ({a}/{b}, e={a - b})", f"{d[0]:+.2f}", f"{d[1]:+.2f}", f"{d[2]:+.2f}",
                          f"{tot['attuale']:.2f}", f"{C.DYN * tot['attuale']:.2f}"]
                         + [f"{tot[v]:.2f}" for v in list(var)[1:]])
        contrib_rows.append([name] + [f"{np.linalg.norm(K.tcp_deflection(s, only={c})):.2f}" for c in K.CONTRIB])
    # e minimo: freccia a sbraccio con lim_e 20 / 30 / 35 / 45 (avambraccio orizzontale)
    e_rows = []
    for emin in (20, 30, 35, 45):
        s = C.statics(emin, 0)
        reach = P["L1"] * math.cos(math.radians(emin)) + P["L2"] + P["L3"]
        e_rows.append([emin, f"{reach:.0f}", f"{np.linalg.norm(K.tcp_deflection(s)):.1f}",
                       f"{np.linalg.norm(K.tcp_deflection(s, **var['B: A + mozzo E 14 mm e perno d4'])):.1f}",
                       f"{abs(s['fd']):.1f}"])
    # mappa della freccia statica sulla griglia
    th = np.arange(20, 161, 5)
    ph = np.arange(-70, 71, 5)
    Z = np.full((len(ph), len(th)), np.nan)
    for i, b in enumerate(ph):
        for j, a in enumerate(th):
            if 20 <= a - b <= 150:
                Z[i, j] = np.linalg.norm(K.tcp_deflection(C.statics(a, b)))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    im = ax[0].pcolormesh(th, ph, Z, shading="nearest", cmap="magma_r", vmax=np.nanpercentile(Z, 95))
    fig.colorbar(im, ax=ax[0], label="|freccia TCP| statica [mm]")
    ax[0].set_xlabel("th2 [°]"); ax[0].set_ylabel("phi [°]")
    ax[0].set_title("Freccia elastica statica, 50 g + camera")
    names = [r[0] for r in contrib_rows]
    bottom = np.zeros(len(names))
    for j, c in enumerate(K.CONTRIB):
        v = np.array([float(r[j + 1]) for r in contrib_rows])
        ax[1].bar(names, v, bottom=bottom, label=c)
        bottom += v
    ax[1].set_ylabel("contributo |ΔTCP| [mm] (somma dei moduli)")
    ax[1].legend(fontsize=7)
    ax[1].set_title("Da dove viene la freccia")
    fig.tight_layout()
    fig.savefig(OUTD / "v1_freccia.png", dpi=110)
    plt.close(fig)

    home = C.statics(90, 0)
    defl_home = np.linalg.norm(K.tcp_deflection(home))
    e_defl = "OK" if defl_home < 0.5 else ("riserva" if defl_home < 2 else "KO")
    es.append(e_defl)
    body = f"""Carichi: 50 g + ESP32-CAM, {C.N_EL} piombi manovella + {C.N_SH} braccio. Statico = posa peggiore sulla griglia
(th2 20…160, phi −70…70, vincolo e = th2 − phi in 20…150, passo 5°). Dinamico = statico x {C.DYN:.0f}.
Stallo = servo gomito a 2 kg·cm contro un ostacolo con e = 20° (biella {abs(s_st['fd']) * k_stall:.1f} N).
Ammissibili: {MAT['s_xy']:.0f} MPa nel piano dei layer, {MAT['s_z']:.0f} MPa tra layer, {MAT['t_il']:.0f} MPa taglio interlaminare.
ESITO sul dinamico: OK se SF ≥ 2, riserva se 1.2–2, KO sotto.

{C.md_table(["membro", "posa peggiore th2/phi", "σ stat MPa", "σ din MPa", "σ stallo MPa", "amm. MPa", "SF din", "ESITO", "nota"], rows)}

Dito ganascia: freccia sotto la presa di stallo {fg[1]['defl']:.2f} mm. Con gambo 6 mm e dito spesso 5 mm il taglio
scende da {fg[1]['tau']:.1f} a {fg_fix['tau']:.1f} MPa (SF {MAT['t_il'] / fg_fix['tau']:.1f}).

**Tensioni basse ovunque, tranne il dito.** I link reggono con margini ampi: il problema è la **rigidezza**.

#### Freccia elastica al TCP (statica, mm; colonne x,z nel piano, y laterale)

La catena è sommata risolvendo i due parallelogrammi con le cedevolezze di ogni elemento (`chain.py`).
Il meccanismo che domina: il braccio (y {Y['arm']:.1f}) e la biella motrice (y {Y['rod']:.1f}) stanno su piani distanti
{Y['rod'] - Y['arm']:.0f} mm. La forza della biella arriva al braccio tramite la vite E a sbalzo e lo flette **fuori piano**;
la stessa eccentricità torce/flette la guancia del servo spalla e l'albero dell'SG90. Ogni rotazione fuori piano θ sposta il piano
della biella di θ·Δy lungo il braccio, e il parallelogramma lo trasforma in una rotazione dell'avambraccio di θ·Δy/(20·sin e).

{C.md_table(["posa", "dx", "dz", "dy", "|δ| statico", "|δ| x2"] + [v + " |δ|" for v in list(var)[1:]], pose_rows)}

Contributi (modulo del solo contributo, mm):

{C.md_table(["posa"] + K.CONTRIB, contrib_rows)}

Effetto di e minimo (sbraccio con avambraccio orizzontale):

{C.md_table(["lim e min °", "sbraccio mm", "|δ| attuale", "|δ| variante B", "biella motrice N"], e_rows)}

![freccia](out/v1_freccia.png)

Ipotesi del modello (da tarare con una prova): rigidezza di bordo dei fori {K.K_EDGE:.0f} N/mm per mm, albero SG90
{K.K_SHAFT:.0e} N·mm/rad, guance come lastre 3 mm (fazzoletti rigidi a torsione), vite E con nocciolo d {C.BOLT['d_core']}.
Prova consigliata: in `home` con 50 g in pinza misura l'abbassamento del TCP con un calibro a corsoio sul tavolo:
il modello prevede {defl_home:.1f} mm, di cui la parte da braccio+guancia+albero sparisce se premi a mano il gomito verso il servo.
"""
    recs = [
        "Braccio: due nervature 2.5 x 6 mm sui bordi della faccia lato servo (x 24…74, la canalina resta in mezzo): "
        f"I fuori piano da {K.ARM['I']:.0f} a {K.arm_section(rib=6)['I']:.0f} mm⁴. Ricontrollare con cad/check_grid.sh.",
        "Guance torretta: fazzoletti esterni da 25 a 50 mm di altezza e profondi 12 (stanno a x ±24, fuori dal servo).",
        "Gomito: mozzo esterno d12 x 8 mm sul braccio attorno al foro E (foro lungo 14 invece di 6.5) e perno E da 4 mm "
        "(vite M4 o spina rettificata): con le due modifiche sopra la freccia in home scende da "
        f"{defl_home:.1f} a {np.linalg.norm(K.tcp_deflection(home, **var['B: A + mozzo E 14 mm e perno d4'])):.1f} mm.",
        "Strutturale vero: il rimedio di fondo è eliminare l'eccentricità (braccio a forcella con una seconda piastra "
        "oltre il piano della biella, perno E in doppio taglio). Tutte le cedevolezze del gomito scalano con Δy².",
        "lim_e minimo da 20° a 35°: perde 10 mm di sbraccio ma divide per ~3 forza nella biella e sensibilità (1/sin²e).",
        f"Dito ganascia: stem_t 3.5 → 6 mm e tab[1] 4 → 5 mm (taglio interlaminare {fg[1]['tau']:.1f} → {fg_fix['tau']:.1f} MPa).",
    ]
    return dict(title="1. Link e bielle: tensioni e freccia al TCP", esito=C.worst(*es), body=body, recs=recs,
                summary=f"tensioni OK nei link (SF din min {min(float(r[6]) for r in rows[:-1]):.1f}), dito ganascia SF "
                        f"{sf_f:.1f} allo stallo; "
                        f"freccia TCP statica {defl_home:.1f} mm in home, "
                        f"{np.linalg.norm(K.tcp_deflection(C.statics(20, 0))):.0f} mm a sbraccio")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
