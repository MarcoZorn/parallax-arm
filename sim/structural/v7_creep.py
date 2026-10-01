"""7. Scorrimento viscoso del PLA sotto carico costante e temperatura vicino ai servo."""
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import chain as K  # noqa: E402
import common as C  # noqa: E402
import v1_links  # noqa: E402
import v2_pins  # noqa: E402

MAT = C.MAT
EA = 200e3          # J/mol, energia di attivazione apparente sotto Tg (assunzione, PLA amorfo/semicristallino)
N_F, A_F = 0.25, 0.8 / 1000**0.25   # Findley: phi(t) = a t^n, tarata su E_creep(1000 h, 23 °C) = E/1.8
R_TH = 35.0         # K/W tra cassa SG90 e aria (convezione + conduzione nei supporti), assunzione
I_STALL, V = C.TQ.SG90_I, 5.0
R_COIL = V / I_STALL


def E_T(T):
    """Modulo del PLA in funzione della temperatura (°C), rapporto rispetto a 23 °C."""
    return float(np.interp(T, [23, 35, 40, 45, 50, 55, 60], [1.0, 0.95, 0.9, 0.82, 0.7, 0.5, 0.15]))


def phi(t_h, T):
    aT = math.exp(EA / 8.314 * (1 / 296.15 - 1 / (T + 273.15)))
    return A_F * (t_h * aT) ** N_F


def compliance_factor(t_h, T):
    """Cedevolezza(t, T) / cedevolezza elastica a 23 °C."""
    return (1 + phi(t_h, T)) / E_T(T)


def servo_heat(T_load):
    """Driver analogico: impulsi a piena tensione con duty ~ coppia/stallo -> P = duty * V * I_stallo."""
    duty = min(1.0, abs(T_load) / C.SG90_T)
    P = duty * V * I_STALL
    return duty, P, P * R_TH


def run():
    T_amb = 23.0
    scen = [("home, pinza vuota", 90, 0, 0.0, False), ("home, 50 g + camera", 90, 0, 0.050, True),
            ("sbraccio, 50 g + camera", 20, 0, 0.050, True)]
    rows, heat = [], {}
    for name, a, b, pl, cam in scen:
        s = C.statics(a, b, payload=pl, cam=cam)
        out = []
        for jn, T in (("spalla", s["T_sh"]), ("gomito", s["T_el"])):
            d, P, dT = servo_heat(T)
            out.append((jn, d, P, dT))
        heat[name] = out
        rows.append([name] + [f"{d:.2f} / {P:.2f} W / +{dT:.0f} K" for _, d, P, dT in out])
    T_hot = T_amb + max(dT for v in heat.values() for *_, dT in v)
    T_warm = T_amb + heat["home, 50 g + camera"][1][3]
    # crescita della freccia nel tempo (parte in PLA: tutto tranne l'albero del servo)
    tt = np.logspace(-1, 3, 60)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    grow = []
    for name, a, b, pl, cam in scen[1:]:
        s = C.statics(a, b, payload=pl, cam=cam)
        d_pla = np.linalg.norm(K.tcp_deflection(s, k_shaft=1e12))
        d_all = np.linalg.norm(K.tcp_deflection(s))
        for T in (T_amb, 40.0, 50.0):
            ax.plot(tt, d_all + d_pla * (np.array([compliance_factor(t, T) for t in tt]) - 1),
                    label=f"{name}, PLA a {T:.0f} °C")
        grow.append([name, f"{d_all:.1f}"] + [f"{d_all + d_pla * (compliance_factor(t, T) - 1):.1f}"
                                              for T in (T_amb, 40.0, 50.0) for t in (8, 100)])
    ax.set_xscale("log")
    ax.set_xlabel("ore in posa")
    ax.set_ylabel("|freccia TCP| [mm]")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7)
    ax.set_title("Freccia sotto carico costante (scorrimento viscoso)")
    fig.tight_layout()
    fig.savefig(C.OUT / "v7_creep.png", dpi=110)
    plt.close(fig)
    # tensioni sostenute in home (posa di riposo) contro il limite a lungo termine alla temperatura locale
    home = C.statics(90, 0)
    ms = v1_links.member_stresses(home)
    jl = v2_pins.joint_loads(home)
    fing = v1_links.finger(C.SG90_T / (2 * C.WR["rp"]))
    sus = [  # (nome, valore MPa, limite a 23 °C, temperatura locale)
        ("braccio (fuori piano), home", ms["braccio (in piano)"][0], 0.3 * MAT["s_xy"], T_amb),
        ("foro E nel braccio, bordo", jl["E (M3x40)"][2], MAT["p_long"], T_amb),
        ("foro A nella manovella, bordo", jl["A (M3x14)"][2], MAT["p_long"], T_amb),
        ("guancia spalla attorno al servo", ms["guancia spalla (in piedi)"][0], 0.3 * MAT["s_z"], T_amb + heat["home, 50 g + camera"][0][3]),
        ("guancia gomito attorno al servo", np.linalg.norm(home["F_A"]) * (C.Y["el_shaft"] - C.Y["rod"])
         / (K._cheek_width()(29) * C.P["cheek_t"] ** 2 / 6), 0.3 * MAT["s_z"], T_warm),
        ("dito che stringe a stallo per ore", fing["tau"], 0.3 * MAT["t_il"], T_amb),
    ]
    srows, es = [], []
    for name, v, lim, T in sus:
        lim_T = lim * E_T(T) if T < 55 else 0.0          # oltre ~55 °C il PLA a contatto non regge carichi
        e = "OK" if v <= 0.7 * lim_T else ("riserva" if v <= lim_T else "KO")
        es.append(e)
        srows.append([name, f"{v:.1f}", f"{T:.0f}", f"{lim_T:.1f}", e])
    crows = [[f"{T:.0f} °C"] + [f"{compliance_factor(t, T):.2f}" for t in (1, 8, 100, 1000)] for T in (23, 35, 40, 45, 50)]
    body = f"""Modello: cedevolezza J(t,T) = [1 + a·(t·a_T)^{N_F}]/E(T), a tarato perché a 23 °C dopo 1000 h il modulo apparente sia
E/1.8; spostamento tempo-temperatura di Arrhenius (Ea {EA / 1000:.0f} kJ/mol); E(T) cala del 10% a 40 °C e del 30% a 50 °C
(Tg del PLA ~58 °C). Valori tipici di letteratura per PLA stampato: ordine di grandezza, non dati del filamento.

Fattore di aumento della freccia (rispetto all'elastica a 23 °C):

{C.md_table(["T", "1 h", "8 h", "100 h", "1000 h"], crows)}

**Temperatura dei servo.** Il driver analogico dell'SG90 manda impulsi a piena tensione con duty ~ coppia/stallo, quindi
tenere una coppia costa P ≈ duty·5 V·{I_STALL} A. Con R_th {R_TH:.0f} K/W tra cassa e aria (assunzione):

{C.md_table(["posa tenuta", "spalla: duty / P / ΔT cassa", "gomito: duty / P / ΔT cassa"], rows)}

Il gomito con 2 piombi resta sempre caricato (scelta voluta, per non flottare nel gioco): in home con 50 g + camera la cassa
arriva a ~{T_warm:.0f} °C a regime (costante di tempo di qualche minuto). È sopra la Tg del PLA (~58 °C): il bordo della
finestra nella guancia e le viti delle linguette perdono presa. Già a 45 °C il PLA scorre {compliance_factor(8, 45) / compliance_factor(8, 23):.1f}
volte più che a 23 °C. Lo stesso vale per la spalla tenuta a sbraccio. È anche un limite del servo, non solo del PLA.

Freccia del TCP sotto carico costante (mm; la parte dell'albero del servo non scorre):

{C.md_table(["posa", "elastica", "23 °C 8 h", "23 °C 100 h", "40 °C 8 h", "40 °C 100 h", "50 °C 8 h", "50 °C 100 h"], grow)}

Tensioni sostenute in `home` contro il limite a lungo termine (30% della rottura, ridotto con E(T); fori: {MAT['p_long']:.0f} MPa):

{C.md_table(["dove", "valore MPa", "T locale °C", "limite MPa", "ESITO"], srows)}

I piombi non sono un problema di scorrimento: 20 g ciascuno, tensioni nelle sedi < 0.1 MPa. Lo sono indirettamente: tengono
il braccio bilanciato, quindi la spalla in home lavora a coppia quasi nulla e resta fredda.

![creep](out/v7_creep.png)
"""
    recs = [
        "Riposo: non lasciare il braccio alimentato in posa per ore con payload; a fine lavoro `estop` o una posa di "
        "parcheggio appoggiata (pinza sul tavolo) così nessun servo tiene coppia.",
        "Guance: fori di aerazione o 2 mm di distanza tra cassa del servo e PLA sui lati lunghi (la finestra ora è a contatto).",
        "Se si vuole lasciare il braccio in posa a lungo, stampare torretta e braccio in PETG o PLA+ ricotto (HDT 60 → 80+ °C).",
        "Pinza: non chiudere a stallo su un oggetto per ore (dito in taglio interlaminare): il firmware dovrebbe aprire di "
        "0.5 mm dopo il contatto.",
    ]
    return dict(title="7. Scorrimento viscoso e temperatura", esito=C.worst(*es), body=body, recs=recs,
                summary=f"servo gomito in home 50 g: +{heat['home, 50 g + camera'][1][3]:.0f} K; "
                        f"freccia TCP x{compliance_factor(100, T_amb):.1f} dopo 100 h a 23 °C")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
