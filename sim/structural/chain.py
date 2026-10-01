import pathlib
"""Catena cinematica perturbata + modello di cedevolezza (elastica) del braccio.

solve(): risolve in forma esatta (Newton vettoriale) i due parallelogrammi con lunghezze, giochi e spostamenti
perturbati e restituisce il TCP nel piano XZ. Lo usano sia la freccia elastica (v1) sia il Monte Carlo (v8).

Fuori piano: ogni carico piano applicato a una quota y diversa dal piano di chi lo regge genera momenti
attorno a X e Z (flessione fuori piano/torsione di braccio, guance, manovella). Le rotazioni che ne seguono
spostano nel piano i punti che stanno a un'altra quota y: è così che l'eccentricità tra il piano del braccio
(y -22.4) e quello della biella motrice (y +11) entra nel parallelogramma.
"""
import math

import numpy as np
from scipy.spatial import ConvexHull

import common as C

P, Y, MAT, BOLT = C.P, C.Y, C.MAT, C.BOLT
L1, L2, LB, LP, LU, LV = P["L1"], P["L2"], P["crank_r"], P["lev_r"], P["lev2_r"], P["lev2_r"]
L3, TZ = P["L3"], P["tcp_dz"]
K_EDGE = 0.5 * MAT["E_xy"]   # N/mm per mm di foro: rigidezza di bordo di un foro stampato (perno in acciaio)
K_SHAFT = 6e4                # N*mm/rad: rotazione dell'albero SG90 nelle boccole di plastica (assunzione)


def U(a):
    return np.stack([np.cos(a), np.sin(a)], -1)


# ---------------- sezioni composte (rettangoli pesati: guscio 1, nucleo gyroid infill_E) ----------------
def comp(rects):
    """rects = [(b, h, y0, w)]: base b, altezza h dalla quota y0, peso w. Ritorna (A, yc, I)."""
    A = sum(w * b * h for b, h, y0, w in rects)
    yc = sum(w * b * h * (y0 + h / 2) for b, h, y0, w in rects) / A
    I = sum(w * (b * h**3 / 12 + b * h * (y0 + h / 2 - yc) ** 2) for b, h, y0, w in rects)
    return A, yc, I


import re as _re
_CAD = pathlib.Path(__file__).resolve().parents[2] / "cad"
_ua = (_CAD / "upper_arm.scad").read_text()
# larghezza del braccio a metà luce = hub_r + elbow_r (inviluppo di due cerchi), letta dal CAD
ARM_W = float(_re.search(r"^hub_r = ([0-9.]+);", _ua, _re.M).group(1)) + float(_re.search(r"^elbow_r = ([0-9.]+);", _ua, _re.M).group(1))
# fazzoletti delle guance (profondità, altezza) letti da turret.scad
_fin = _re.search(r"polygon\(side > 0 \? \[\[0, 0\], \[([0-9.]+), 0\], \[0, ([0-9.]+)\]\]", (_CAD / "turret.scad").read_text())
FIN_D, FIN_H = float(_fin.group(1)), float(_fin.group(2))


def arm_section(rib=0.0, rib_w=2.5):
    """Braccio a metà luce, flessione FUORI piano (altezza = spessore t lungo Y, stampato in piano).
    Lastra 16 x 6 con canalina 5 x 3 sul lato servo; nervature laterali opzionali alte 'rib' sul lato servo."""
    t, w, cw, cd = 6.0, ARM_W, 5.0, 3.0
    tb, pr, ki = MAT["skin_tb"], MAT["perim"], MAT["infill_E"] - 1
    r = [(w, t, 0, 1), (cw, cd, 0, -1),
         # nucleo a gyroid: blocchi laterali e sotto la canalina (fuori dal guscio)
         ((w - 2 * pr - cw - 2 * pr) / 2, t - 2 * tb, tb, ki), ((w - 2 * pr - cw - 2 * pr) / 2, t - 2 * tb, tb, ki),
         (cw + 2 * pr, t - tb - cd - tb, cd + tb, ki)]
    if rib:
        r += [(rib_w, rib, -rib, 1), (rib_w, rib, -rib, 1)]
    A, yc, I = comp(r)
    return dict(A=A, yc=yc - t / 2, I=I)   # yc: spostamento del baricentro dalla mezzeria della lastra


# nervature del braccio lette dal CAD (rib = [larghezza, altezza, da x, a x]); il modello le mette su una faccia,
# per I fuori piano il lato conta poco (sezione quasi simmetrica)
_rib = _re.search(r"^rib = \[([0-9.]+), ([0-9.]+),", _ua, _re.M)
ARM = arm_section(rib=float(_rib.group(2)), rib_w=float(_rib.group(1))) if _rib else arm_section()
ARM_I_IN = C.rect_I(6, ARM_W, perim_b=MAT["skin_tb"], perim_h=MAT["perim"])     # nel piano
ARM_J = C.bredt_J(ARM_W, 6, MAT["skin_tb"], MAT["perim"])
G_XY = MAT["E_xy"] / (2 * (1 + MAT["nu"]))
G_Z = MAT["E_z"] / (2 * (1 + MAT["nu"]))


# ---------------- guance della torretta (lastra verticale 3 mm, layer orizzontali) ----------------
def _cheek_width():
    pts = [(x, z) for x in (-32, 32) for z in (0, P["floor_t"] + 1)]
    for cx, r in ((0, 16), (-22, 7)):
        pts += [(cx + r * math.cos(a), P["sh_h"] + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 72)]
    pts = np.array(pts)
    h = ConvexHull(pts)

    def w(z):
        xs = []
        for i in range(len(h.vertices)):
            a, b = pts[h.vertices[i]], pts[h.vertices[(i + 1) % len(h.vertices)]]
            if (a[1] - z) * (b[1] - z) <= 0 and a[1] != b[1]:
                xs.append(a[0] + (z - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
        return max(xs) - min(xs) if len(xs) >= 2 else 0.0
    return w


def cheek_compliance(fin_h=None, fin_d=None, t=None):
    """Rotazione per unità di momento al livello del servo: flessione attorno a X (stress verticale = tra layer)
    e torsione attorno a Z. Fazzoletti esterni fin_d x fin_h a x = +-24 (rigidi a torsione nella loro altezza)."""
    w = _cheek_width()
    fin_h = FIN_H if fin_h is None else fin_h
    fin_d = FIN_D if fin_d is None else fin_d
    t = P["cheek_t"] if t is None else t
    ft, z0 = 3.0, P["floor_t"]
    z_srv = P["sh_h"] - (P["sg_body"][0] - P["sg_shaft_x"]) - 2   # vite inferiore della linguetta, circa
    zs = np.linspace(z0, z_srv, 200)
    dz = zs[1] - zs[0]
    cb = ct = 0.0
    for z in zs:
        d = max(0.0, fin_d * (1 - (z - z0) / fin_h))      # profondità del fazzoletto
        I = comp([(w(z), t, 0, 1)] + ([(2 * ft, d, t, 1)] if d > 0 else []))[2]
        cb += dz / (MAT["E_z"] * I)
        if d == 0:
            ct += dz / (G_Z * C.rect_J(w(z), t))
    return cb, ct, z_srv


CHEEK_CB, CHEEK_CT, CHEEK_Z = cheek_compliance()
CHEEK_FIX = cheek_compliance(fin_h=50.0, fin_d=12.0)[:2]   # variante: fazzoletti fino a z 54 (sotto la linguetta)


def lap(a, t1, t2, d=BOLT["d_core"]):
    """Cedevolezza (mm/N) di un giunto a sovrapposizione su vite M3 con leva a tra le mezzerie:
    flessione della vite + schiacciamento dei fori + rotazione della vite nel foro della parte lato dado."""
    Ib = math.pi * d**4 / 64
    return a**3 / (3 * BOLT["E"] * Ib) + 1 / (K_EDGE * t1) + 1 / (K_EDGE * t2) + 12 * a**2 / (K_EDGE * t2**3)


JOINT = dict(  # leva tra le mezzerie, spessore parte mobile, parte che serra la vite
    A=lap(Y["crank"] - Y["rod"], P["rod_t"], P["crank_t"]),
    B=lap(Y["rod"] - Y["fore_r"], P["rod_t"], P["y_fore_r"][1] - P["y_fore_r"][0] - 2.6 + 2.0),
    G=lap(Y["post"] - Y["lev"], P["rod_t"], P["y_post"][1] - P["y_post"][0]),
    P1=lap(Y["lev"] - Y["link"], P["rod_t"], 3.5),
    U=lap(Y["link"] - Y["rod2"], P["rod2_t"], 3.5),
    V=lap(Y["link"] - Y["rod2"], P["rod2_t"], 3.5),
)
ROD_C = {k: L / (MAT["E_xy"] * 0.9 * P["rod_w"] * t) for k, L, t in
         (("d", L1, P["rod_t"]), ("r1", L1, P["rod_t"]), ("r2", L2, P["rod2_t"]))}


def post_compliance():
    """Montante G: lastra 3 mm rastremata (16 -> 8 mm in X), alta sh_h dal pavimento. Stampato in piedi:
    flessione nel piano con tensioni verticali (E_z). Ritorna mm/N per forza orizzontale in G."""
    h = P["sh_h"] - P["floor_t"]
    zs = np.linspace(0, h, 300)
    wz = 16 - 8 * zs / h
    I = (P["y_post"][1] - P["y_post"][0]) * wz**3 / 12
    return np.trapezoid((h - zs) ** 2 / (MAT["E_z"] * I), zs)


POST_C = post_compliance()
CRANK_C = 12.0 / (MAT["E_xy"] * C.rect_I(12, P["crank_t"], perim_b=MAT["perim"], perim_h=MAT["skin_tb"]))  # rad/(N*mm)


# ---------------- solutore della catena perturbata ----------------
ZERO2 = np.zeros(2)


def pert(n=1, **kw):
    """Dizionario di perturbazioni a zero (scalari o vettori 2D per campione)."""
    p = dict(dq_sh=0.0, dq_el=0.0, dOc=ZERO2, dL1=0.0, drc=0.0, dlb=0.0, dL2=0.0, dLd=0.0, dLr1=0.0, dLr2=0.0,
             dlp=0.0, dlu=0.0, dlv=0.0, dL3=0.0, dTZ=0.0, d0=ZERO2, ds=ZERO2, eEf=ZERO2, eEt=ZERO2, eW=ZERO2,
             dG=ZERO2, lat=0.0)
    p.update(kw)
    return {k: (np.broadcast_to(np.asarray(v, float), (n, 2)).copy() if np.ndim(v) and np.shape(v)[-1:] == (2,)
                and k not in ("dq_sh",) else np.broadcast_to(np.asarray(v, float), (n,)).copy())
            for k, v in p.items()}


def _newton(f, x0, it=12):
    x = x0.copy()
    for _ in range(it):
        g, dg = f(x)
        x = x - g / dg
    return x


def solve(th2, phi, p):
    """TCP (x, z) nel frame yaw con origine sull'asse spalla. p da pert(); d(y) = d0 + ds*y è lo spostamento
    nel piano della linea del perno E alla quota y (cedevolezze fuori piano), uguale per tutto ciò che vi è appeso."""
    n = len(p["dL1"])
    d = lambda y: p["d0"] + p["ds"] * y  # noqa: E731
    t2 = np.radians(th2 + p["dq_sh"])
    E = (L1 + p["dL1"])[:, None] * U(t2)
    A = p["dOc"] + (LB + p["drc"])[:, None] * U(np.radians(phi + 180 + p["dq_el"]))
    Ef = E + d(Y["rod"]) + p["eEf"]
    lb, Ld = LB + p["dlb"], L1 + p["dLd"]

    def fphi(f):
        D = Ef - lb[:, None] * U(f) - A
        dD = -lb[:, None] * np.stack([-np.sin(f), np.cos(f)], -1)
        return (D**2).sum(-1) - Ld**2, 2 * (D * dD).sum(-1)
    ph = _newton(fphi, np.full(n, math.radians(phi)))
    # triangolo: P1 = Et + R(g)(-lp, 0), U = Et + R(g)(0, lu)
    Et = E + d(Y["link"]) + p["eEt"]
    Gp = np.array([-LP, 0.0]) + p["dG"]
    lp, lu, Lr1 = LP + p["dlp"], LU + p["dlu"], L1 + p["dLr1"]

    def fg(g):
        D = Et + lp[:, None] * np.stack([-np.cos(g), -np.sin(g)], -1) - Gp
        dD = lp[:, None] * np.stack([np.sin(g), -np.cos(g)], -1)
        return (D**2).sum(-1) - Lr1**2, 2 * (D * dD).sum(-1)
    ga = _newton(fg, np.zeros(n))
    Up = Et + lu[:, None] * np.stack([-np.sin(ga), np.cos(ga)], -1)
    # polso: V = Wb + R(b)(0, lv)
    Wb = E + d(Y["bracket"]) + p["eEf"] + (L2 + p["dL2"])[:, None] * U(ph) + p["eW"]
    lv, Lr2 = LV + p["dlv"], L2 + p["dLr2"]

    def fb(b):
        D = Wb + lv[:, None] * np.stack([-np.sin(b), np.cos(b)], -1) - Up
        dD = lv[:, None] * np.stack([-np.cos(b), -np.sin(b)], -1)
        return (D**2).sum(-1) - Lr2**2, 2 * (D * dD).sum(-1)
    be = _newton(fb, np.zeros(n))
    c, s = np.cos(be), np.sin(be)
    l3, tz = L3 + p["dL3"], TZ + p["dTZ"]
    tcp = Wb + np.stack([c * l3 - s * tz, s * l3 + c * tz], -1) + (d(0.0) - d(Y["bracket"]))
    return tcp, np.degrees(ph), np.degrees(be)


def tcp_nominal(th2, phi):
    return L1 * C.u(th2) + L2 * C.u(phi) + np.array([L3, TZ])


# ---------------- modello elastico ----------------
def _moment_xz(F, dy):
    """Momento (Mx, Mz) nel mondo di una forza piana F=(Fx,Fz) applicata a distanza dy lungo Y."""
    return dy * np.array([F[1], -F[0]])


def elastic(s, k=1.0, only=None, arm=ARM, cheek=None, k_shaft=K_SHAFT, e_hole=None, e_bolt_d=None):
    """Perturbazioni elastiche per la posa della statica s, carichi scalati di k.
    only = insieme di contributi da attivare (None = tutti). Ritorna (pert, lat) con lat = spostamento laterale (Y) del TCP."""
    on = (lambda key: True) if only is None else (lambda key: key in only)
    cb, ct = (CHEEK_CB, CHEEK_CT) if cheek is None else cheek
    th2, phi = s["th2"], s["phi"]
    a_ax, n_ax = C.u(th2), C.u(th2 + 90)
    bolt = [(k * F, y) for F, y in C.elbow_bolt_loads(s)]
    y_arm = Y["arm"] + arm["yc"]
    kw = dict(d0=np.zeros(2), ds=np.zeros(2))
    lat = 0.0
    r_tcp = tcp_nominal(th2, phi)                 # TCP dal centro spalla
    r_tcp_E = r_tcp - L1 * a_ax                    # TCP dal gomito

    def add_rot(wx, wz, y_c, r_c):
        """Rotazione (wx, wz) attorno a un punto a quota y_c, r_c = TCP relativo al centro nel piano."""
        nonlocal lat
        # punto alla quota y: spostamento nel piano (-wz, wx) * (y - y_c)
        kw["d0"] += np.array([-wz, wx]) * (0 - y_c)
        kw["ds"] += np.array([-wz, wx])
        lat += wz * r_c[0] - wx * r_c[1]

    # 1) braccio: flessione fuori piano e torsione per il momento costante delle forze al perno E
    M = sum(_moment_xz(F, y - y_arm) for F, y in bolt)
    T = M @ a_ax
    Mn = M @ n_ax
    if on("braccio"):
        Lb = L1 - 9                                            # dal bordo del mozzo
        th_n = Mn * Lb / (MAT["E_xy"] * arm["I"])
        th_t = T * Lb / (0.5 * (G_XY + G_Z) * ARM_J)
        w = th_t * a_ax + th_n * n_ax
        add_rot(w[0], w[1], y_arm, r_tcp_E)
        lat += Mn * Lb**2 / (2 * MAT["E_xy"] * arm["I"])
        Fsum = sum(F for F, _ in bolt)
        kw["d0"] += (Fsum @ n_ax) * Lb**3 / (3 * MAT["E_xy"] * ARM_I_IN) * n_ax   # flessione nel piano
    # 2) vite E: mensola dalla faccia del braccio + rotazione nel foro (lungo 6.5)
    if on("perno E"):
        Ib = math.pi * (e_bolt_d or BOLT["d_core"]) ** 4 / 64
        Lh = e_hole or C.UA["t"] + 0.5
        Mf = sum(F * (y - Y["arm_face"]) for F, y in bolt)       # vettore piano
        slope = 12 * Mf / (K_EDGE * Lh**3)                       # rotazione nel foro (per mm di y)
        ys = np.array([Y["rod"], Y["link"]])
        defl = []
        for yy in ys:
            x = yy - Y["arm_face"]
            dv = np.zeros(2)
            for F, y in bolt:
                a = y - Y["arm_face"]
                dv += F * (a**2 * (3 * x - a) if x >= a else x**2 * (3 * a - x)) / (6 * BOLT["E"] * Ib)
            defl.append(dv + slope * (yy - Y["arm"]) + sum(F for F, _ in bolt) / (K_EDGE * Lh))
        # campo lineare che passa per i due piani principali
        ds = (defl[0] - defl[1]) / (ys[0] - ys[1])
        kw["d0"] += defl[0] - ds * ys[0]
        kw["ds"] += ds
    # 3) guancia sinistra + albero spalla: momento di tutte le forze sul braccio attorno al servo
    if on("guancia/albero spalla"):
        Msh = sum(_moment_xz(F, y - Y["sh_shaft"]) for F, y in bolt)
        wx = Msh[0] * cb + Msh[0] / k_shaft
        wz = Msh[1] * ct + Msh[1] / k_shaft
        add_rot(wx, wz, Y["sh_shaft"], r_tcp)
    # 4) lato manovella: piastra fuori piano + guancia destra + albero gomito -> sposta A lungo la biella
    FA = k * s["F_A"]
    if on("manovella/guancia gomito"):
        th_c = (FA * (Y["crank"] - Y["rod"])) * CRANK_C       # rotazione vettoriale (per componente)
        Mel = _moment_xz(FA, Y["rod"] - Y["el_shaft"])
        wvec = np.array([Mel[0] * (cb + 1 / k_shaft), Mel[1] * (ct + 1 / k_shaft)])
        dA = np.array([-wvec[1], wvec[0]]) * (Y["rod"] - Y["el_shaft"]) + th_c * (Y["crank"] - Y["rod"])
        kw["dOc"] = dA
    # 5) giunti a sovrapposizione e allungamento delle bielle
    fd, f1, f2 = k * s["fd"], k * s["f1"], k * s["f2"]
    if on("giunti A/B"):
        kw["dLd"] = fd * (JOINT["A"] + JOINT["B"])
    if on("bielle"):
        kw["dLd"] = kw.get("dLd", 0.0) + fd * ROD_C["d"]
        kw["dLr1"] = f1 * ROD_C["r1"]
        kw["dLr2"] = f2 * ROD_C["r2"]
    if on("giunti livellamento"):
        kw["dLr1"] = kw.get("dLr1", 0.0) + f1 * (JOINT["G"] + JOINT["P1"])
        kw["dLr2"] = kw.get("dLr2", 0.0) + f2 * (JOINT["U"] + JOINT["V"])
    # 6) montante G: flessione nel piano (componente orizzontale della biella 1)
    if on("montante G"):
        FG = k * s["F_G"]
        kw["dG"] = np.array([FG[0] * POST_C, 0.0])
    return pert(1, **kw), lat


CONTRIB = ["braccio", "perno E", "guancia/albero spalla", "manovella/guancia gomito", "giunti A/B", "bielle",
           "giunti livellamento", "montante G"]


def tcp_deflection(s, k=1.0, only=None, **kw):
    """Spostamento del TCP (dx, dz, dy) dovuto alle cedevolezze, rispetto alla posa nominale."""
    p, lat = elastic(s, k, only, **kw)
    tcp, _, _ = solve(s["th2"], s["phi"], p)
    d = tcp[0] - tcp_nominal(s["th2"], s["phi"])
    return np.array([d[0], d[1], lat])


if __name__ == "__main__":
    # verifica: senza perturbazioni il solutore ridà la FK nominale
    for th2, phi in C.POSES.values():
        tcp, ph, be = solve(th2, phi, pert(1))
        assert np.allclose(tcp[0], tcp_nominal(th2, phi), atol=1e-6) and abs(ph[0] - phi) < 1e-6 and abs(be[0]) < 1e-6
    print("solve ok; ARM", ARM, "J", round(ARM_J), "I_in", round(ARM_I_IN))
    print("cheek cb %.3g ct %.3g z %.1f post %.4f crank %.3g" % (CHEEK_CB, CHEEK_CT, CHEEK_Z, POST_C, CRANK_C))
    print({k: round(v, 5) for k, v in JOINT.items()})
    for name, (a, b) in C.POSES.items():
        s = C.statics(a, b)
        print(name, np.round(tcp_deflection(s), 3), {c: np.round(tcp_deflection(s, only={c}), 2).tolist() for c in CONTRIB})
