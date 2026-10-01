"""5. Incastri a scatto della culla ESP32 nella base (lamella 2 x 5 stampata in piedi)."""
import numpy as np

import common as C

B, P, MAT = C.BS, C.P, C.MAT
RNG = np.random.default_rng(5)


def latch_geom(hook=None):
    t, w = 2.0, 5.0
    lip_z = B["esp_z"] + B["esp"][2] + 0.1
    L = lip_z + 2.5 - B["floor_h"]                 # lamella dal fondo del vassoio alla punta
    L_hook = lip_z - B["floor_h"]                  # quota della faccia di ritegno
    h = P["snap_hook"] if hook is None else hook
    return dict(t=t, w=w, L=L, Lh=L_hook, h=h, I=w * t**3 / 12)


def forces(g, y, mu=MAT["mu_pla"]):
    """Deformazione al piede, forza laterale, forza di inserimento e di sfilamento per una freccia y al dente."""
    E = MAT["E_z"]
    eps = 1.5 * g["t"] * y / g["Lh"] ** 2            # mensola con carico alla quota del dente
    P_lat = 3 * E * g["I"] * y / g["Lh"] ** 3
    tb = g["h"] / 2.5
    F_in = P_lat * (tb + mu) / (1 - mu * tb)
    e = g["t"] / 2 + y / 2                            # eccentricità del contatto sulla faccia di ritegno
    F_out = 2 * E * g["I"] * y / (e * g["Lh"] ** 2) + mu * P_lat
    return eps, P_lat, F_in, F_out


def mc(hook, n=20000):
    """Sovrapposizione reale dente/PCB su ciascun lato: dente stampato più basso (spigolo di 1 linea),
    PCB 38 pin dei cloni 28.0-28.6 mm, posizione della lamella +-0.05."""
    g = latch_geom(hook)
    pcb = RNG.uniform(28.0, 28.6, n)
    h_eff = np.clip(hook - np.abs(RNG.normal(0.1, 0.05, (2, n))), 0, None)
    pos = RNG.normal(0, 0.05, (2, n))
    ov = h_eff - P["clr_pocket"] - pos + (pcb - B["esp"][1]) / 2
    min_ov = ov.min(0)
    eps = 1.5 * g["t"] * np.clip(ov.max(0), 0, None) / g["Lh"] ** 2
    return dict(p_loose=np.mean(min_ov < 0.05), p_strain=np.mean(eps > 0.01), ov_med=np.median(min_ov),
                eps95=np.percentile(eps, 95), ov=min_ov)


def run():
    rows, mcs = [], {}
    for hook in (P["snap_hook"], 0.6, 0.8):
        g = latch_geom(hook)
        y = hook - P["clr_pocket"]
        eps, P_lat, F_in, F_out = forces(g, y)
        m = mc(hook)
        mcs[hook] = m
        rows.append([hook, f"{y:.2f}", f"{100 * eps:.2f}", f"{P_lat:.2f}", f"{2 * F_in:.2f}", f"{2 * F_out:.1f}",
                     f"{100 * m['p_loose']:.1f}", f"{100 * m['p_strain']:.2f}"])
    g = latch_geom()
    m0 = mcs[P["snap_hook"]]
    esito = "OK" if m0["p_loose"] < 0.01 else ("riserva" if m0["p_loose"] < 0.1 else "KO")
    body = f"""Lamella {g['t']:.0f} x {g['w']:.0f} mm alta {g['L']:.1f} mm (dente a {g['Lh']:.1f} mm dal fondo), stampata in piedi:
la tensione di flessione al piede è verticale, cioè **tra i layer** (E {MAT['E_z']:.0f} MPa, allungamento a rottura ~1%,
non il 2% del PLA nel piano). La lamella sta a clr_pocket {P['clr_pocket']} dal bordo del PCB, quindi il dente sovrappone
snap_hook − clr_pocket al PCB nominale ({B['esp'][1]} mm). Forze per **due** ganci.

{C.md_table(["snap_hook mm", "sovrapposizione mm", "ε al piede %", "forza laterale N", "inserimento N (2 ganci)",
             "sfilamento N (2 ganci)", "P(non trattiene) %", "P(ε > 1%) %"], rows)}

Monte Carlo (20000): PCB dei cloni 28.0–28.6 mm, dente stampato più basso di 0.1 ± 0.05 (è largo quanto una linea),
posizione della lamella ±0.05. "Non trattiene" = sovrapposizione < 0.05 mm su almeno un lato.

La lamella è lunghissima rispetto al dente: la deformazione è un decimo del limite, ma il gancio tiene poco e il dente
da 0.4 mm è al limite di ciò che un ugello da 0.4 riproduce. Il rischio non è rompere, è che la scheda non resti in sede
(i Dupont tirano la scheda verso il basso: lì la spingono contro gli appoggi, quindi il gancio lavora poco in esercizio).
"""
    recs = [f"snap_hook 0.4 → 0.8 mm nella base (solo per la culla ESP32): sovrapposizione 0.6, ε "
            f"{100 * forces(latch_geom(0.8), 0.6)[0]:.2f}%, P(non trattiene) da {100 * m0['p_loose']:.0f}% a "
            f"{100 * mcs[0.8]['p_loose']:.1f}%.",
            "Raccordo r 1 mm al piede della lamella (oggi spigolo vivo su un piano di layer)."]
    return dict(title="5. Incastri a scatto (culla ESP32)", esito=esito, body=body, recs=recs,
                summary=f"ε {100 * forces(g, P['snap_hook'] - P['clr_pocket'])[0]:.2f}% (ok), "
                        f"P(scheda non trattenuta) {100 * m0['p_loose']:.0f}%")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
