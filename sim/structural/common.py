"""Base comune: quote lette dal CAD, materiale PLA FDM, masse, statica piana del meccanismo.
Unità: mm, N, N*mm, MPa, kg per le masse. Angoli in gradi come in docs/03.
"""
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAD = ROOT / "cad"
OUT = HERE / "out"
sys.path.insert(0, str(ROOT / "calc"))
import torque as TQ  # noqa: E402  masse della catena: unica fonte (calc/torque.py)

# ---------------- quote dai sorgenti OpenSCAD ----------------
_FN = dict(sin=lambda a: math.sin(math.radians(a)), cos=lambda a: math.cos(math.radians(a)),
           tan=lambda a: math.tan(math.radians(a)), asin=lambda x: math.degrees(math.asin(x)),
           acos=lambda x: math.degrees(math.acos(x)), atan=lambda x: math.degrees(math.atan(x)),
           sqrt=math.sqrt, PI=math.pi, abs=abs, max=max, min=min, pow=pow, ceil=math.ceil, floor=math.floor)


def scad_vars(*files):
    """Assegnazioni top-level 'nome = espr;' dei file .scad (in ordine). Quelle non valutabili si saltano."""
    ns = {}
    for f in files:
        for line in (CAD / f).read_text().splitlines():
            line = line.split("//")[0]
            if not line or line[0] in " \t}":
                continue
            for st in line.split(";"):
                m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)$", st)
                if not m:
                    continue
                expr = re.sub(r"([A-Za-z_]\w*)\.([xyz])\b", lambda k: f"{k[1]}[{'xyz'.index(k[2])}]", m[2])
                try:
                    ns[m[1]] = eval(expr, {"__builtins__": {}}, {**_FN, **ns})
                except Exception:
                    pass
    return ns


P = scad_vars("params.scad")
WR = scad_vars("params.scad", "wrist.scad")
BS = scad_vars("params.scad", "base.scad")
LK = scad_vars("params.scad", "linkage.scad")
UA = scad_vars("params.scad", "upper_arm.scad")

# ---------------- materiale (PLA, Kobra S1, 0.4/0.2, 3 perimetri, gyroid 20%) ----------------
MAT = dict(
    E_xy=3200.0,     # MPa, nel piano dei layer
    E_z=2600.0,      # MPa, attraverso i layer
    s_xy=50.0,       # MPa trazione nel piano
    s_z=27.0,        # MPa trazione tra layer
    t_xy=28.0,       # MPa taglio nel piano
    t_il=15.0,       # MPa taglio interlaminare (sul piano dei layer)
    p_short=35.0,    # MPa pressione di contatto ammissibile breve (foro stampato, perno acciaio)
    p_long=10.0,     # MPa pressione sostenuta per ore a 23 °C (scorrimento viscoso)
    nu=0.35,
    perim=1.2,       # 3 perimetri x 0.4
    skin_tb=0.8,     # 4 layer pieni sopra/sotto x 0.2
    infill_E=0.12,   # rigidezza relativa del gyroid 20%
    mu_pla=0.35,     # attrito PLA/PLA secco (0.25-0.5)
)
BOLT = dict(E=200000.0, d_major=2.92, d_shank=2.90, d_core=2.39,
            sy_A2=450.0, sy_88=640.0)  # viti M3: inox A2-70 (tipico kit) e 8.8
G = 9.81
SG90_T = TQ.SG90_T * TQ.KGCM * 1000   # N*mm dichiarati
SG90_T_REAL = 2.0 * TQ.KGCM * 1000    # N*mm: picco di un clone a 5 V (stallo contro ostacolo)
DYN = 2.0                              # fattore dinamico richiesto


def sf_esito(sf, ok=2.0, ris=1.2):
    return "OK" if sf >= ok else ("riserva" if sf >= ris else "KO")


def worst(*es):
    order = {"OK": 0, "riserva": 1, "KO": 2}
    return max(es, key=lambda e: order[e])


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(f"{c:.3g}" if isinstance(c, float) else str(c) for c in r) + " |")
    return "\n".join(out)


# ---------------- sezioni FDM ----------------
def rect_I(b, h, infill=True, perim_b=None, perim_h=None):
    """Momento d'inerzia per flessione con altezza h (direzione del carico) e base b.
    Guscio pieno (perimetri/skin) + nucleo a gyroid con rigidezza ridotta."""
    pb = MAT["perim"] if perim_b is None else perim_b
    ph = MAT["perim"] if perim_h is None else perim_h
    I = b * h**3 / 12
    if infill:
        bc, hc = max(b - 2 * pb, 0), max(h - 2 * ph, 0)
        I -= (1 - MAT["infill_E"]) * bc * hc**3 / 12
    return I


def bredt_J(b, h, tb, th):
    """Rigidezza torsionale di una sezione a guscio chiuso (pareti tb sui lati b, th sui lati h)."""
    am = (b - th) * (h - tb)
    return 4 * am**2 / (2 * (b - th) / tb + 2 * (h - tb) / th)


def rect_J(a, b):
    """Torsione di un rettangolo pieno a x b (Roark)."""
    a, b = max(a, b), min(a, b)
    return a * b**3 * (1 / 3 - 0.21 * b / a * (1 - b**4 / (12 * a**4)))


def rect_tau(T, a, b):
    """Taglio massimo di torsione in un rettangolo pieno (Roark), a lato lungo."""
    a, b = max(a, b), min(a, b)
    return T * (3 * a + 1.8 * b) / (a**2 * b**2)


# ---------------- masse ----------------
def part_stl(scad, part, name=None):
    """STL di una parte generato da OpenSCAD in out/stl (rigenerato se i sorgenti sono più nuovi).
    Non si usa cad/stl: export.sh lo cancella e lo riscrive."""
    import subprocess
    name = name or f"{Path(scad).stem}_{part}"
    dst = OUT / "stl" / f"{name}.stl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    newest = max(f.stat().st_mtime for f in CAD.rglob("*.scad"))
    if not dst.exists() or dst.stat().st_mtime < newest:
        subprocess.run(["openscad", "-D", f'part="{part}"', "-o", str(dst), str(CAD / scad)],
                       check=True, capture_output=True)
    return dst


def stl_tris(path):
    txt = Path(path).read_text()
    return np.array(re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", txt), float).reshape(-1, 3, 3)


def stl_volume(path):
    v = stl_tris(path)
    return abs(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum()) / 6


def stl_mass(path, fill=0.6):
    return stl_volume(path) * 1.24e-6 * fill  # kg (stessa convenzione di calc/torque.py)


# ---------------- pose ----------------
def u(a):
    a = np.radians(a)
    return np.array([np.cos(a), np.sin(a)])


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


POSES = {  # th2, phi (q1 = 0)
    "home": (90, 0),
    "sbraccio": (20, 0),
    "basso": (35, -60),
    "alto": (130, 50),
    "ripiegato": (150, 0),
}


def pose_grid(step=5):
    for th2 in range(20, 161, step):
        for phi in range(-70, 71, step):
            if 20 <= th2 - phi <= 150:
                yield th2, phi


# piani lungo Y (mezzerie) per la ripartizione fuori piano
Y = dict(arm=P["y_arm"] + UA["t"] / 2, fore_l=sum(P["y_fore_l"]) / 2, fore_r=sum(P["y_fore_r"]) / 2,
         link=sum(P["y_link"]) / 2, rod=sum(P["y_rod"]) / 2, lev=sum(P["y_lev"]) / 2, rod2=sum(P["y_rod2"]) / 2,
         post=sum(P["y_post"]) / 2, bracket=sum(P["y_bracket"]) / 2,
         crank=P["y_crank_in"] + P["crank_t"] / 2, wrist_cg=0.0)
Y["arm_face"] = P["y_arm"] + UA["t"]          # faccia del braccio verso l'avambraccio
Y["sh_shaft"] = -P["y_wall"] + 3.5             # appoggio dell'albero spalla (boccola SG90), circa
Y["el_shaft"] = P["y_wall"] - 3.5


# baricentri delle parti livellate davanti al perno W (mm): pinza, payload al TCP (xp), culla camera
WRIST_X = {"pinza": 38.0, "payload": float(WR["xp"]), "ESP32": 55.0}
N_EL, N_SH = 2, 4   # piombi del punto di progetto: 2 sulla manovella, 4 sulla coda del braccio (docs/01)


def statics(th2, phi, payload=0.050, cam=True, n_el=N_EL, n_sh=N_SH):
    """Equilibrio piano (XZ) del meccanismo a parallelogrammi. Forze in N, momenti in N*mm.
    Convenzioni: f>0 = biella in trazione. R_* = forza che il perno esercita sul corpo indicato."""
    L1, L2 = P["L1"], P["L2"]
    lb, lp, lu, lv = P["crank_r"], P["lev_r"], P["lev2_r"], P["lev2_r"]
    g = np.array([0.0, -G])
    E = L1 * u(th2)
    wrist, fore = [], []
    for name, m, d in TQ.chain(payload, cam):   # masse da torque.py, posizioni dal CAD
        x = next((v for k, v in WRIST_X.items() if name.startswith(k)), None)
        (wrist.append((m, x)) if x is not None else fore.append((m, min(d * 1000, L2))))
    # polso (livellato): momento attorno a W portato dalla biella 2 sulla leva V verticale
    Fg_w = sum(m for m, _ in wrist) * g
    M_gW = sum(cross(np.array([x, 0.0]), m * g) for m, x in wrist)
    f2 = -M_gW / (lv * math.cos(math.radians(phi)))
    R_W = -(Fg_w + f2 * (-u(phi)))
    # triangolo al gomito: biella 2 su U (alto), biella 1 su P1 (dietro)
    f1 = lu * f2 * math.cos(math.radians(phi)) / (lp * math.sin(math.radians(th2)))
    R_Et = -(f2 * u(phi) - f1 * u(th2))
    # avambraccio: E, W, leva B
    Fg_f = sum(m for m, _ in fore) * g
    M = cross(L2 * u(phi), -R_W) + sum(cross(d * u(phi), m * g) for m, d in fore)
    fd = -M / (lb * math.sin(math.radians(th2 - phi)))
    R_Ef = -(-R_W + Fg_f + fd * (-u(th2)))
    # braccio: carichi al perno E, peso proprio, piombi di coda
    F_E = -R_Ef - R_Et + 0.006 * g  # + perno E e mezza biella motrice (come torque.py)
    arm = [(0.0132, L1 / 2), (n_sh * TQ.LEAD, -TQ.R_CW_SHOULDER * 1000)]
    T_sh = -(cross(E, F_E) + sum(cross(d * u(th2), m * g) for m, d in arm))
    F_sh = F_E + sum(m for m, _ in arm) * g          # forza che il braccio scarica sull'albero spalla
    # manovella: biella motrice in A, piombi ad arco
    A = lb * u(phi + 180)
    F_A = fd * u(th2)
    r_cw = TQ.R_CW_ELBOW[n_el] * 1000 if n_el else 0.0
    m_cw = n_el * TQ.LEAD
    T_el = -(cross(A, F_A) + cross(r_cw * u(phi + 180), m_cw * g))
    m_crank = stl_mass_cached("crank.scad", "crank") + stl_mass_cached("crank.scad", "lid")
    F_el = F_A + (m_cw + m_crank) * g
    return dict(th2=th2, phi=phi, e=th2 - phi, f2=f2, f1=f1, fd=fd, R_W=R_W, R_Et=R_Et, R_Ef=R_Ef,
                F_E=F_E, T_sh=T_sh, F_sh=F_sh, T_el=T_el, F_el=F_el, F_A=F_A, F_G=f1 * u(th2),
                M_gW=M_gW, wrist_w=-Fg_w[1], fore_w=-Fg_f[1], E=E, A=A)


_MC = {}


def stl_mass_cached(scad, part):
    if (scad, part) not in _MC:
        _MC[scad, part] = stl_mass(part_stl(scad, part))
    return _MC[scad, part]


def two_support(F_list, y1, y2):
    """Reazioni (vettori piani) di due appoggi a quote y1, y2 per carichi [(F, y)] (equilibrio fuori piano)."""
    S = sum(F for F, _ in F_list)
    My = sum(F * y for F, y in F_list)
    R2 = -(My - S * y1) / (y2 - y1)
    R1 = -S - R2
    return R1, R2


def elbow_bolt_loads(s):
    """Carichi sul perno E (vite M3x40) alle quote y: piastra L, triangolo, piastra R.
    Avambraccio: biella motrice su B (piano biella, entra nella piastra R), carico del polso ripartito
    tra piastra L e R dal perno W (staffa centrata in y_bracket), peso proprio al centro della U."""
    W_on_fore = -s["R_W"]                                  # forza del polso sull'avambraccio
    wl, wr = two_support([(W_on_fore, Y["bracket"])], Y["fore_l"], Y["fore_r"])
    fd_vec = s["fd"] * (-u(s["th2"]))                      # biella motrice sulla leva B
    Fg_f = np.array([0.0, -s["fore_w"]])
    loads = [(-wl, Y["fore_l"]), (-wr, Y["fore_r"]), (fd_vec, Y["rod"]),
             (Fg_f, (Y["fore_l"] + Y["fore_r"]) / 2)]
    RL, RR = two_support(loads, Y["fore_l"], Y["fore_r"])  # reazioni del perno sulle piastre
    # sul perno: opposto delle reazioni; triangolo: opposto di R_Et
    return [(-RL, Y["fore_l"]), (-s["R_Et"], Y["link"]), (-RR, Y["fore_r"])]


def slice2d(scad, call, plane="z", at=0.0):
    """Sezione piana di un modulo OpenSCAD (projection cut). call = chiamata del modulo, es. 'jaw()'.
    plane 'z' taglia a z=at; 'y' taglia a y=at (sezione XZ, z del pezzo -> y del 2D).
    Ritorna la lista dei contorni (array Nx2)."""
    import subprocess
    import tempfile
    rot = {"z": "", "y": "rotate([-90, 0, 0])", "x": "rotate([0, 90, 0])"}[plane]
    shift = {"z": f"[0, 0, {-at}]", "y": f"[0, {-at}, 0]", "x": f"[{-at}, 0, 0]"}[plane]
    with tempfile.TemporaryDirectory() as td:
        src, dst = Path(td) / "s.scad", Path(td) / "s.svg"
        src.write_text(f"use <{CAD / scad}>\nprojection(cut = true) {rot} translate({shift}) {call};\n")
        subprocess.run(["openscad", "-o", str(dst), str(src)], check=True, capture_output=True)
        svg = dst.read_text()
    polys = []
    for d in re.findall(r'd="([^"]*)"', svg):
        for part in re.findall(r"M([^z]*)z", d):
            xy = np.array(re.findall(r"(-?[\d.e+-]+),(-?[\d.e+-]+)", part), float)
            xy[:, 1] *= -1  # SVG ha y verso il basso
            polys.append(xy)
    return polys
