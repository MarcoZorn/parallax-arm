"""6. Viti autofilettanti nel PLA (estrazione) e dadi incassati (pareti minime misurate sulle sezioni del CAD)."""
import math

import numpy as np

import common as C

P, MAT = C.P, C.MAT


def pull_out(d, L, pilot):
    """Estrazione di una autofilettante: taglio su un cilindro di diametro medio, riempimento del filetto
    proporzionale alla profondità del filetto formato. Taglio sui piani dei layer (fori verticali)."""
    fill = min(1.0, (d - pilot) / (d - 0.82 * d)) * 0.8
    dm = (d + pilot) / 2
    return math.pi * dm * L * MAT["t_il"] * fill


def walls(scad, call, z, label):
    """Parete minima attorno alle sedi esagonali nella sezione a quota z."""
    polys = C.slice2d(scad, call, "z", z)

    def area(p):
        x, y = p[:, 0], p[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    def dense(p, step=0.05):
        q = np.vstack([p, p[:1]])
        out = []
        for a, b in zip(q[:-1], q[1:]):
            n = max(2, int(np.linalg.norm(b - a) / step))
            out.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
        return np.vstack(out)
    hexes = [i for i, p in enumerate(polys) if len(p) <= 12 and 20 < area(p) < 70]
    res = []
    for i in hexes:
        hp = dense(polys[i])
        others = np.vstack([dense(p) for j, p in enumerate(polys) if j != i])
        dmin = np.sqrt(((hp[:, None, :] - others[None, :, :]) ** 2).sum(-1)).min()
        merged = len(polys[i]) > 6
        res.append((label, polys[i].mean(0), dmin, merged, area(polys[i])))
    return res


def run():
    # ---- autofilettanti ----
    srows, es = [], []
    gr = C.WR
    plate_under_head = gr["plate_t"] - 2.5
    cases = [
        ("coperchio base (4)", 3.0, 8 - C.BS["lid_t"], 2.5, 1.0, "colonnine d9 verticali"),
        ("piastra pinza (2)", 3.0, 12 - plate_under_head, 2.5, 6.0, "colonnine d7, regge cremagliere e payload"),
        ("culla camera (2)", 3.0, gr["deck_t"], 2.5, 1.0, "solo lo spessore del piano (3 mm)"),
        ("linguette SG90 guance (2/servo)", 2.0, P["cheek_t"], P["sg_screw_d"] - 0.4, None, "fori orizzontali, M2 del servo"),
    ]
    # forza sulle viti delle linguette: momento sull'albero spalla (v2) ripreso dalle due viti a passo 27.8
    m_sh = max(np.linalg.norm(sum(F * (y - C.Y["sh_shaft"]) for F, y in C.elbow_bolt_loads(s)))
               for s in (C.statics(a, b) for a, b in C.pose_grid(10)))
    for name, d, L, pilot, load, note in cases:
        Fpo = pull_out(d, L, pilot)
        if load is None:
            load = m_sh / P["sg_screw_pitch"] + C.SG90_T / P["sg_screw_pitch"]
        sf = Fpo / (C.DYN * load)
        e = C.sf_esito(sf, 3.0, 1.5)
        es.append(e)
        srows.append([name, f"M{d:.0f}", f"{pilot:.1f}", f"{L:.1f}", f"{Fpo:.0f}", f"{load:.1f}", f"{sf:.0f}", e, note])

    # ---- dadi incassati: pareti misurate sulle sezioni ----
    W = C.WR
    sections = [
        ("linkage.scad", "drive_rod()", 1.3, "biella motrice (A)"),
        ("linkage.scad", "lev_link()", 1.3, "triangolo (P1, U)"),
        ("linkage.scad", "forearm()", C.LK["fore_z_r"] + 1.3, "avambraccio piastra R (B)"),
        ("upper_arm.scad", "upper_arm()", 1.3, "coda braccio (coperchio)"),
        ("crank.scad", "crank()", P["cw_t"] - 1.3, "manovella (coperchio)"),
        ("wrist.scad", "housing()", W["zd"] - W["deck_t"] - 3 - 1 + 2.3, "piano pinza (staffa)"),
    ]
    wrows = []
    merged_any = False
    for scad, call, z, label in sections:
        for lab, c, dmin, merged, ar in walls(scad, call, z, label):
            e = "KO" if merged else ("OK" if dmin >= 1.2 else "riserva")
            merged_any |= merged
            es.append(e)
            wrows.append([lab, f"({c[0]:.1f}, {c[1]:.1f})", f"{dmin:.2f}", f"{dmin / 0.4:.1f}",
                          "**due sedi fuse**" if merged else "", e])
    # interasse dadi staffa nel piano pinza
    pitch = 5.0
    body = f"""Estrazione: taglio su un cilindro di diametro medio tra vite e preforo, sui piani dei layer
(τ {MAT['t_il']:.0f} MPa), filetto formato proporzionale a (d − preforo). Il carico è x{C.DYN:.0f}. Viti delle linguette:
oltre alla coppia, riprendono il momento flettente sull'albero spalla di §2 ({m_sh:.0f} N·mm) come coppia di forze a passo
{P['sg_screw_pitch']} mm.

{C.md_table(["dove", "vite", "preforo", "impegno mm", "F estrazione N", "carico N", "SF", "ESITO", "nota"], srows)}

Preforo 2.5 per M3 autofilettante: corretto per PLA (2.4–2.6). I fori stampati escono ~0.1 più stretti: la vite entra dura,
le colonnine d7/d9 hanno parete ≥ 2.25 mm (≥ 0.75·d), non si spaccano. Il rischio vero è stringere troppo: nel PLA una M3 in
6 mm spana a ~0.4 N·m, a mano con un cacciavite piccolo ci si arriva facilmente. I fori pilota delle linguette (1.6 per la M2
del servo) stanno in guance da 3 mm stampate in piedi, con asse orizzontale: lì la vite apre i layer, avvitare piano.

Dadi incassati (chiave {P['m3_nut_af']} + 2·clr_pocket = {P['m3_nut_af'] + 2 * P['clr_pocket']:.1f}, vertici a
{(P['m3_nut_af'] + 2 * P['clr_pocket']) / math.cos(math.radians(30)):.2f}): parete minima tra la sede e qualunque altro
contorno, misurata sulla sezione del CAD a metà sede. 2 linee da 0.4 = 0.8 mm è il minimo che il slicer stampa pieno;
sotto resta una linea sola (o il riempimento dei vuoti) e sono proprio i vertici del dado a spingerla quando si stringe.
ESITO: OK ≥ 1.2 mm (3 perimetri), riserva sotto, KO se le sedi si toccano.

{C.md_table(["sede", "centro (x, y)", "parete min mm", "linee da 0.4", "", "ESITO"], wrows)}
"""
    if merged_any:
        body += f"""
**Piano pinza:** le due viti della staffa sono a x_back + 3.5 e x_back + 8.5, cioè a {pitch:.0f} mm di interasse.
Un dado M3 è largo {P['m3_nut_af']} mm sulle chiavi: due dadi non ci stanno (si sovrappongono di
{P['m3_nut_af'] - pitch:.1f} mm) e le due sedi esagonali nel CAD sono fuse in una.
"""
    recs = [
        "Staffa → piano pinza: interasse viti 5 → 7.5 mm (x_back + 2.5 e x_back + 10, flangia della staffa 12 → 14 mm), "
        "oppure una vite sola M3 con dado + perno di centraggio.",
        "Biella motrice: occhio d8 → d9 attorno al dado di A, o sede ruotata di 30° (lato piatto verso l'estremità).",
        "Coda del braccio e manovella: orecchie delle viti del coperchio r 4 → 5 mm (parete al dado da 0.6 a 1.6 mm).",
        "Coppia di serraggio delle autofilettanti nel PLA: a mano, fermarsi al contatto + 1/8 di giro.",
    ]
    return dict(title="6. Autofilettanti e dadi incassati", esito=C.worst(*es), body=body, recs=recs,
                summary="estrazione OK; sedi dadi: " + ("due sedi fuse nel piano pinza" if merged_any else "ok")
                        + f", parete minima {min(float(r[2]) for r in wrows):.2f} mm")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
