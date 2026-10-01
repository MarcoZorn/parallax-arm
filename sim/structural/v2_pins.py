"""2. Perni M3 su PLA: pressione nei fori, flessione delle viti, impegno del filetto, alberi dei servo."""
import math

import numpy as np

import common as C

P, MAT, Y, BOLT = C.P, C.MAT, C.Y, C.BOLT
D = 3.0          # diametro di contatto della vite
NUT_H = 2.4      # dado M3 normale
Z_CORE = math.pi * BOLT["d_core"] ** 3 / 32
Z_SHANK = math.pi * BOLT["d_shank"] ** 3 / 32


def joint_loads(s, k=1.0):
    """Per ogni giunto: (forza N, momento sulla vite N*mm, pressione max nel PLA MPa, parte che la subisce)."""
    th2 = s["th2"]
    fd, f1, f2 = k * s["fd"], k * s["f1"], k * s["f2"]
    bolt = [(k * F, y) for F, y in C.elbow_bolt_loads(s)]
    out = {}
    # E: mensola dal braccio (foro lungo t + 0.5), forze alle piastre L, R e al triangolo
    Lh = C.UA["t"] + 0.5
    Fs = sum(F for F, _ in bolt)
    Mf = np.linalg.norm(sum(F * (y - Y["arm_face"]) for F, y in bolt))
    FR = np.linalg.norm(bolt[2][0])
    out["E (M3x40)"] = (np.linalg.norm(Fs), Mf, np.linalg.norm(Fs) / (D * Lh) + 6 * Mf / (D * Lh**2),
                        "foro nel braccio (bordo, con il momento)", FR / (D * 4), "piastra R avambraccio")
    # W: vite appoggiata sulle due piastre, staffa al centro (mozzo 11 mm)
    RW = np.linalg.norm(k * s["R_W"])
    a, b = Y["bracket"] - Y["fore_l"], Y["fore_r"] - Y["bracket"]
    out["W (M3x35)"] = (RW, RW * a * b / (a + b), RW / (D * 11), "mozzo staffa", RW * a / (a + b) / (D * 4), "piastra R")
    # A: vite a sbalzo dalla piastra della manovella (4 mm) fino al piano della biella (9.1 mm)
    la = Y["crank"] - Y["rod"]
    fA = abs(fd)
    out["A (M3x14)"] = (fA, fA * la, fA / (D * 4) + 6 * fA * la / (D * 16), "foro nella manovella (bordo)",
                        fA / (D * (P["rod_t"] - 2.6) + 5.5 * 2.6), "biella (foro 1.4 + dado)")
    lb = Y["rod"] - Y["fore_r"]
    out["B (M3x8)"] = (fA, fA * lb, fA / (D * P["rod_t"]), "biella motrice",
                       fA / (D * 1.4 + 5.5 * 2.6) + 6 * fA * lb / (D * 4**2), "piastra R (foro + dado, bordo)")
    lg = Y["post"] - Y["lev"]
    out["G (M3x12)"] = (abs(f1), abs(f1) * lg, abs(f1) / (D * 3) + 6 * abs(f1) * lg / (D * 9), "montante (bordo)",
                        abs(f1) / (D * P["rod_t"]), "biella 1")
    out["P1 (M3x8)"] = (abs(f1), abs(f1) * (Y["lev"] - Y["link"]), abs(f1) / (D * P["rod_t"]), "biella 1",
                        abs(f1) / (D * 0.9 + 5.5 * 2.6), "triangolo (foro 0.9 + dado)")
    out["U (M3x6)"] = (abs(f2), abs(f2) * (Y["link"] - Y["rod2"]), abs(f2) / (D * P["rod2_t"]), "biella 2",
                       abs(f2) / (D * 0.9 + 5.5 * 2.6), "triangolo (foro 0.9 + dado)")
    out["V (M3x12)"] = (abs(f2), abs(f2) * (Y["link"] - Y["rod2"]), abs(f2) / (D * P["rod2_t"]), "biella 2",
                        abs(f2) / (D * 3.5), "leva V staffa")
    return out


def engagement():
    """Impegno del filetto nel dado incassato con le lunghezze di docs/04 (dado a filo della faccia)."""
    rows = []
    # (giunto, vite, quota testa, verso, faccia del dado lato inserimento, verso dell'incasso)
    cases = [("A", 14, P["y_crank_in"] + P["crank_t"], -1, P["y_rod"][0], +1),
             ("B", 8, P["y_rod"][1], -1, P["y_fore_r"][0], +1),
             ("P1", 8, P["y_lev"][1], -1, P["y_link"][0], +1),
             ("U", 6, P["y_rod2"][0], +1, P["y_link"][1], -1)]
    for name, L, head, sgn, face, into in cases:
        b = sorted([head, head + sgn * L])
        n = sorted([face, face + into * NUT_H])
        eng = max(0.0, min(b[1], n[1]) - max(b[0], n[0]))
        rows.append((name, f"M3x{L}", eng, eng / 0.5))
    return rows


def run():
    grid = [C.statics(a, b) for a, b in C.pose_grid()]
    home = C.statics(90, 0)
    worst = {}
    for s in grid:
        for k, v in joint_loads(s).items():
            if k not in worst or max(v[2], v[4]) > max(worst[k][0][2], worst[k][0][4]):
                worst[k] = (v, (s["th2"], s["phi"]))
    rows, es = [], []
    for k, (v, pose) in worst.items():
        F, M, p1, w1, p2, w2 = v
        p = max(p1, p2)
        where = w1 if p1 >= p2 else w2
        vh = joint_loads(home)[k]
        ph = max(vh[2], vh[4])
        sf_p = MAT["p_short"] / (C.DYN * p)
        sb = C.DYN * M / Z_CORE
        sf_b = BOLT["sy_A2"] / sb if sb else 99
        e = C.worst(C.sf_esito(sf_p), C.sf_esito(sf_b), "OK" if ph <= MAT["p_long"] else "riserva")
        es.append(e)
        rows.append([k, f"{pose[0]}/{pose[1]}", f"{F:.1f}", f"{p:.1f}", where, f"{C.DYN * p:.1f}", f"{sf_p:.1f}",
                     f"{ph:.1f}", f"{M:.0f}", f"{sb:.0f}", f"{sf_b:.1f}", e])
    # alberi dei servo: forza radiale e momento rispetto alla boccola
    sh_rows = []
    for name, sel in (("spalla", "sh"), ("gomito", "el")):
        Fmax, Mmax, pose = 0, 0, None
        for s in grid:
            if sel == "sh":
                bolt = C.elbow_bolt_loads(s)
                F = np.linalg.norm(s["F_sh"])
                M = np.linalg.norm(sum(F_ * (y - Y["sh_shaft"]) for F_, y in bolt))
            else:
                F = np.linalg.norm(s["F_el"])
                M = np.linalg.norm(s["F_A"]) * (Y["el_shaft"] - Y["rod"])
            if M > Mmax:
                Fmax, Mmax, pose = F, M, (s["th2"], s["phi"])
        sf = C.SG90_T / (C.DYN * Mmax)
        e = C.sf_esito(sf, 1.0, 0.5)
        es.append(e)
        sh_rows.append([f"albero {name}", f"{pose[0]}/{pose[1]}", f"{Fmax:.1f}", f"{Mmax:.0f}", f"{C.DYN * Mmax:.0f}",
                        f"{C.SG90_T:.0f}", f"{sf:.2f}", e])
    eng = engagement()
    e_eng = "OK" if min(r[2] for r in eng) >= 2.0 else "riserva"
    es.append(e_eng)
    eng_rows = [[n, b, f"{e:.1f}", f"{t:.1f}", "OK" if e >= 2.0 else "corto"] for n, b, e, t in eng]

    body = f"""Pressione di contatto p = F/(d·t) nei fori (con il momento della vite dove il perno è a sbalzo:
p = F/(d·L) + 6·F·a/(d·L²)). Ammissibile breve {MAT['p_short']:.0f} MPa, sostenuta per ore {MAT['p_long']:.0f} MPa
(oltre, il foro si ovalizza per scorrimento viscoso). Flessione della vite sul nocciolo d {BOLT['d_core']} (vite tutta filettata
dei kit), confrontata con inox A2-70 ({BOLT['sy_A2']:.0f} MPa); una 8.8 arriva a {BOLT['sy_88']:.0f}.

{C.md_table(["giunto", "posa peggiore", "F stat N", "p stat MPa", "dove", "p din MPa", "SF p din", "p in home MPa",
             "M vite N·mm", "σ vite din MPa", "SF vite", "ESITO"], rows)}

Osservazioni:
- **E** è l'unico perno serio: è una mensola di {Y['fore_r'] - Y['arm_face']:.0f} mm dal braccio, e la biella motrice
  carica la piastra R all'estremità libera. Il momento genera nel foro del braccio (lungo solo {C.UA['t'] + 0.5:.1f} mm)
  una pressione di bordo alta, che in poche ore di posa ovalizza il foro: il gioco del gomito cresce col tempo.
  Con mozzo d12 x 8 mm (foro lungo 14) la pressione di bordo scende di circa (6.5/14)² = 0.22 volte.
- **A** è il secondo: vite a sbalzo di {Y['crank'] - Y['rod']:.1f} mm dalla piastra della manovella da 4 mm.
- I perni ruotano sul filetto (viti dei kit tutte filettate): il filetto lima il foro. Dove ruota qualcosa (E, W, G, V, A, B, P1, U)
  conviene una vite a gambo parziale (ISO 4762 M3x40: filetto 18 mm, il gambo liscio copre braccio, piastra L e triangolo)
  oppure un tubetto di ottone 4/3 mm incollato nel foro come boccola.
- **A, B, P1, U ruotano con un dado normale nella sede**: la vite gira insieme alla parte che ruota e si avvita o svita da sola
  a ogni ciclo. Serve frenafiletti medio (o dadi autobloccanti sottili, sedi da 3.0 mm invece di 2.6).

Impegno del filetto nel dado incassato, lunghezze di docs/04 (dado da 2.4 mm a filo della faccia):

{C.md_table(["giunto", "vite", "impegno mm", "filetti", "esito"], eng_rows)}

Nota: l'intestazione di `cad/linkage.scad` indica A M3x20, B/P1/U M3x10, V M3x10, mentre docs/04 dice A M3x14, B/P1 M3x8,
U M3x6, V M3x12. Le lunghezze di docs/04 sono quelle giuste per A (con M3x20 la punta urta il montante G), per U no.

Alberi dei servo (SG90: boccole in plastica, nessun cuscinetto). Il momento flettente è preso rispetto alla boccola
(~3.5 mm dentro la guancia) e confrontato, come regola pratica, con la coppia nominale ({C.SG90_T:.0f} N·mm):

{C.md_table(["albero", "posa peggiore", "F radiale N", "M stat N·mm", "M din N·mm", "rif. N·mm", "SF", "ESITO"], sh_rows)}

La biella motrice chiude il suo anello di forze attraverso **entrambi** gli alberi (braccio → albero spalla → torretta →
albero gomito → manovella): la forza radiale non è "< 1.5 N" come in docs/01, ma 4–13 N statici, con braccio di leva fino
a {Y['fore_r'] - Y['sh_shaft']:.0f} mm.
"""
    recs = [
        "Perno E in acciaio d4 (vite M4x45 o spina) con fori 4.2/4.3; in alternativa M3 classe 12.9 a gambo parziale.",
        "A: integrare il distanziale d7 nella manovella (mozzo stampato pieno alto 4.9 mm) e crank_t 4 → 6 mm al perno.",
        "A, B, P1, U: frenafiletti medio sul dado incassato (ruotano: un dado normale si svita).",
        "U: M3x8 invece di M3x6 (oggi impegna ~1.4 mm, meno di 3 filetti); B: M3x10 invece di M3x8.",
        "Viti a gambo parziale (ISO 4762) o boccole in ottone 4/3 nei fori che ruotano, per non limare il PLA col filetto.",
        "Alberi SG90: aggiungere un appoggio esterno al braccio (anello coassiale d≈36 sulla guancia −Y che fa da boccola al mozzo, "
        "o un perno folle M3 dalla guancia +Y attraverso la manovella), oppure passare a MG90S (cuscinetto sull'uscita).",
    ]
    return dict(title="2. Perni M3, fori e alberi dei servo", esito=C.worst(*es), body=body, recs=recs,
                summary=f"perno E: p bordo din {[r for r in rows if r[0].startswith('E')][0][5]} MPa, "
                        f"vite {[r for r in rows if r[0].startswith('E')][0][9]} MPa; "
                        f"momento albero spalla {sh_rows[0][3]} N·mm statico")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
