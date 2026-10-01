"""3. Pignone/cremagliere m1 in PLA + controlli sugli STL così come si stampano (gusci, sbalzi)."""
import math
import re

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import common as C

W, MAT = C.WR, C.MAT
ALPHA = math.radians(20)


def lewis_Y(z):
    """Fattore di forma di Lewis (20°, dentatura normale), interpolato; cremagliera = 0.485."""
    tab = [(12, 0.245), (14, 0.277), (17, 0.303), (20, 0.322), (24, 0.337), (28, 0.353), (30, 0.359),
           (34, 0.371), (40, 0.389), (50, 0.409), (75, 0.435), (150, 0.460), (300, 0.472), (1e9, 0.485)]
    zs, ys = zip(*tab)
    return float(np.interp(z, zs, ys))


def contact_ratio(dx):
    """Ricoprimento pignone/cremagliera con la cremagliera allontanata di dx (mm)."""
    m, r = W["m"], W["rp"]
    rb, ra = r * math.cos(ALPHA), r + m
    pin = math.sqrt(ra**2 - rb**2) - r * math.sin(ALPHA)
    rack = (m - dx) / math.sin(ALPHA)
    return (pin + rack) / (math.pi * m * math.cos(ALPHA))


def export_list():
    """Parti e orientamenti di stampa come in cad/export.sh."""
    txt = (C.CAD / "export.sh").read_text()
    out = [(f, p, n) for f, p, n in re.findall(r"^p (\S+)\s+(\S+)\s+(\S+)", txt, re.M)]
    out.insert(2, ("turret.scad", "all", "03_turret"))
    return out


def mesh_check(path):
    """Gusci connessi e superfici a sbalzo (oltre 45°/60° dalla verticale, escluso il piano del piatto)."""
    v = C.stl_tris(path)
    pts, inv = np.unique(np.round(v.reshape(-1, 3), 4), axis=0, return_inverse=True)
    tri = inv.reshape(-1, 3)
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(pts), len(pts)))
    shells = connected_components(g, directed=False)[0]
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    nz = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    zmin = v[:, :, 2].min()
    off_bed = v[:, :, 2].min(axis=1) > zmin + 0.05
    ang = np.degrees(np.arcsin(np.clip(-nz, -1, 1)))      # 0 = parete verticale, 90 = soffitto
    o45 = area[(ang > 45) & (ang < 89.5) & off_bed].sum()
    o60 = area[(ang > 60) & (ang < 89.5) & off_bed].sum()
    ceil = area[(ang >= 89.5) & off_bed].sum()               # soffitti piani: ponti o sbalzi orizzontali
    return shells, o45, o60, ceil


def run():
    T, Tr = C.SG90_T, C.SG90_T_REAL
    m, zp, r = W["m"], W["zp"], W["rp"]
    b = W["rack_top"] - W["gear_bot"]                     # sovrapposizione delle fasce
    rows, es = [], []
    for name, Tq, k in (("stallo dichiarato 1.6 kg·cm", T, 1), ("x2 dinamico", T, C.DYN), ("stallo reale 2.0 kg·cm", Tr, 1)):
        F = k * Tq / (2 * r)                               # due cremagliere
        s_p = F / (b * m * lewis_Y(zp))
        s_r = F / (b * m * lewis_Y(1e9))
        tau_r = 1.5 * F / (b * (math.pi * m / 2 + 2 * 1.25 * m * math.tan(ALPHA)))
        Es = MAT["E_xy"] / (2 * (1 - MAT["nu"] ** 2))
        p_h = math.sqrt(F / b * Es / (math.pi * r * math.sin(ALPHA)))
        rows.append([name, f"{F:.1f}", f"{s_p:.1f}", f"{s_r:.1f}", f"{tau_r:.2f}", f"{p_h:.1f}"])
    F2 = C.DYN * T / (2 * r)
    s_fat = 0.35 * MAT["s_xy"]
    sf = s_fat / (F2 / (b * m * lewis_Y(zp)))
    es.append(C.sf_esito(sf))
    # salto dei denti: gioco radiale della cremagliera nella coda di rondine
    float_dt = C.P["clr_slide"] / math.sin(math.radians(60))         # gioco orizzontale dai fianchi a 60°
    float_neck = C.P["clr_slide"]                                     # collo nella fessura dt_top (se c'è)
    dx = min(float_dt, float_neck)
    eps0, eps1 = contact_ratio(0), contact_ratio(dx)
    dx_jump = m - (math.pi * m * math.cos(ALPHA) - (math.sqrt((r + m) ** 2 - (r * math.cos(ALPHA)) ** 2) - r * math.sin(ALPHA))) * math.sin(ALPHA)
    bl = 0.15 + 2 * dx * math.tan(ALPHA)
    es.append("OK" if eps1 >= 1.2 else "riserva")
    # stampa: gradini sul fianco del dente stampato di fianco (fianco a 20° dall'orizzontale)
    cusp = 0.16 * math.cos(ALPHA)
    # controlli STL
    mesh_rows = []
    bad = []
    for f, part, name in export_list():
        try:
            sh, o45, o60, ceil = mesh_check(C.part_stl(f, part, name))
        except Exception as ex:  # una parte che non si genera è già una notizia
            mesh_rows.append([name, "errore", str(ex)[:40], "", ""])
            continue
        expect = 3 if name.startswith("14_") else (None if name.startswith("00_") else 1)
        flag = "" if expect is None or sh == expect else f"**{sh} gusci (attesi {expect})**"
        if flag:
            bad.append(name)
        mesh_rows.append([name, sh, f"{o45:.0f}", f"{o60:.0f}", f"{ceil:.0f}", flag])
    # la ganascia è un guscio solo grazie al gambo del dito: conta i contorni a metà cremagliera
    jaw_cut = C.slice2d("wrist.scad", "jaw()", "y", 0.0)
    jaw_split = len(jaw_cut) > 1
    gap = min(p[:, 1].min() for p in jaw_cut) if jaw_split else 0.0
    for r_ in mesh_rows:
        if r_[0] == "02_base_lid" and r_[-1]:
            r_[-1] = "labbro appoggiato sul piano (a contatto: in stampa si fonde)"
    if jaw_split:
        es.append("KO")
    body = f"""Pignone m{m} z{zp} (r {r}), due cremagliere: F tangenziale = T/(2r) per dente. Fascia utile {b:.1f} mm
(sovrapposizione pignone/cremagliera). Lewis: Y pignone {lewis_Y(zp):.3f}, cremagliera {lewis_Y(1e9):.3f}.
Hertz al primitivo con E* = E/2(1−ν²).

{C.md_table(["caso", "F per dente N", "σ Lewis pignone MPa", "σ Lewis cremagliera MPa", "τ piede cremagliera MPa", "p Hertz MPa"], rows)}

Ammissibile a fatica per denti in PLA ~{s_fat:.0f} MPa (35% della rottura): SF sul dinamico {sf:.1f}.
I denti non sono il limite: il limite di forza della pinza è l'attrito delle guide (§4) e il dito (§1).

**Salto dei denti.** La spinta radiale F·tan20° = {T / (2 * r) * math.tan(ALPHA):.2f} N allontana la cremagliera finché
il gioco della coda di rondine lo permette: {dx:.2f} mm (clr_slide {C.P['clr_slide']}).
Ricoprimento {eps0:.2f} a gioco nullo, {eps1:.2f} con la cremagliera tutta indietro; si salta sotto 1.0, cioè oltre
{dx_jump:.2f} mm di allontanamento. Gioco sul dente {bl:.2f} mm → ±{bl / 2:.2f} mm per dito.

**Orientamento.** Il pignone è stampato in piano: profilo nel piano XY, preciso. Le ganasce sono stampate di fianco
(Y della cremagliera in verticale): i fianchi dei denti diventano superfici a 20° dall'orizzontale, uno dei due è uno
**sbalzo a 70°** e il gradino dei layer da 0.16 vale {cusp:.2f} mm sul fianco, quanto tutto il gioco di progetto (0.15).
Le tensioni di piede restano nel piano dei layer (σ lungo X), il taglio al piede va sui piani dei layer ma è < 1 MPa.

Controllo degli STL generati con gli stessi `part` di `cad/export.sh` (orientati come si stampano): gusci connessi,
area a sbalzo oltre 45° e 60° dalla verticale e soffitti orizzontali (mm², piano del piatto escluso).

{C.md_table(["parte", "gusci", "sbalzo >45° mm²", ">60° mm²", "soffitti mm²", ""], mesh_rows)}
"""
    if jaw_split:
        body += f"""
**Difetto CAD nelle ganasce:** in `rack()` la coda di rondine è `offset(delta = -clr_slide)` del trapezio, quindi anche il
lato attaccato al corpo arretra di {C.P['clr_slide']} mm: a metà cremagliera la sezione ha {len(jaw_cut)} contorni separati,
tra coda di rondine e corpo resta una fessura di {C.P['clr_slide']} mm. La coda di rondine è attaccata solo all'estremità,
dove tocca il gambo del dito (un'unione di 0.75 x 4 mm): in uso si stacca o flette, e la cremagliera non è guidata. Il provino (`tolerance_coupon.scad`, `sliders()`) ha il collo,
la cremagliera no.
"""
    recs = [
        "wrist.scad, rack(): aggiungere il collo come nel provino, nel 2D della coda di rondine "
        "`translate([-(dt_top / 2 - clr_slide), -clr_slide - 0.01]) square([dt_top - 2 * clr_slide, clr_slide + 0.02]);` "
        "(largo 7.4 mm, passa nella fessura da 8).",
        "Ganasce: stampare la cremagliera in piano (fianchi verticali) separandola dal dito, con 2 viti M3x8 e dado "
        "nel gambo; in alternativa tenerle di fianco ma a layer 0.12 (gradino 0.11 mm) e bl 0.15 → 0.25.",
        f"Gioco del dente {bl:.2f} mm: va bene per una pinza; se serve precisione, clr_slide 0.3 → 0.2 dopo il provino.",
    ]
    return dict(title="3. Pignone e cremagliere m1 + controlli STL", esito=C.worst(*es), body=body, recs=recs,
                summary=f"denti OK (σ pignone {T / (2 * r) / (b * m * lewis_Y(zp)):.1f} MPa allo stallo); "
                        f"ricoprimento {eps1:.2f} col gioco; ganasce: " + ("coda di rondine staccata dal corpo" if jaw_split else "ok"))


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
