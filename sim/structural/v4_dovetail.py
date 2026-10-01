"""4. Code di rondine delle cremagliere: attrito, effetto cassetto, forza persa sulla presa."""
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import common as C  # noqa: E402

W = C.WR
K_H = 1 / math.cos(math.radians(30)) + math.tan(math.radians(30))   # forza laterale su fianco a 60°: 1.73
K_UP, K_DN = 2.0, 1.0                                                 # verticale: cuneo sui fianchi / fondo piano


def geometry():
    """Leve nel frame cremagliera: linea primitiva x=0, z=0 al fondo cremagliera."""
    x_grip = -W["rp"]                                   # le dita stringono sull'asse del pignone (TCP)
    z_grip = W["tcp_z"] - W["rack_bot"]
    z_tooth = ((W["gear_bot"] + W["rack_top"]) / 2) - W["rack_bot"]
    x_guide = W["rail_x"] - W["rp"]
    z_guide = -W["dt_h"] / 2
    return dict(dx=0 - x_grip, dz=z_tooth - z_grip, dx0=x_guide, dz0=z_tooth - z_guide, L=W["rack_len"])


def efficiency(mu, L=None, dx=None, dz=None):
    """Forza di presa / forza al dente. Coppia F·(dx, dz) tra dente e dito ripresa da due appoggi alle estremità."""
    g = geometry()
    L = L or g["L"]
    dx = g["dx"] if dx is None else dx
    dz = g["dz"] if dz is None else dz
    lever = (2 * K_H * dx + (K_UP + K_DN) * dz) / L
    return (1 - K_H * mu * math.tan(math.radians(20))) / (1 + mu * lever)


def run():
    g = geometry()
    F_t = C.SG90_T / (2 * W["rp"])
    need = C.TQ.PAYLOAD_MAX * C.G * C.TQ.SF_MIN / (2 * 0.3)   # come calc/torque.py: 50 g, mu 0.3, SF 2
    rows = []
    for mu in (0.15, 0.25, 0.35, 0.5):
        eta = efficiency(mu)
        rows.append([mu, f"{eta:.2f}", f"{F_t * eta:.2f}", f"{F_t * eta / need:.2f}", f"{efficiency(mu, L=50):.2f}"])
    # autobloccaggio in corsa libera: spinta al dente sfalsata dal centro guida
    mu_lock = g["L"] / (2 * K_H * g["dx0"] + (K_UP + K_DN) * g["dz0"])
    # rotazione libera della cremagliera nel gioco e spostamento del dito
    c = C.P["clr_slide"]
    yaw = 2 * c / math.sin(math.radians(60)) / g["L"]
    pitch = 2 * c / g["L"]
    tip = math.degrees(yaw), math.degrees(pitch), yaw * g["dx"] + pitch * abs(g["dz"])
    eta_n = efficiency(C.MAT["mu_pla"])
    ratio = F_t * eta_n / need
    esito = "OK" if ratio >= 1.5 else ("riserva" if ratio >= 1.0 else "KO")
    # grafico
    mus = np.linspace(0.05, 0.6, 50)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for L in (40, 50, 60):
        ax.plot(mus, [F_t * efficiency(m, L=L) for m in mus], label=f"guida {L} mm")
    ax.axhline(need, color="k", ls="--", label=f"richiesta {need:.1f} N (50 g, SF 2)")
    ax.set_xlabel("attrito PLA/PLA μ")
    ax.set_ylabel("forza per dito allo stallo [N]")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(C.OUT / "v4_presa.png", dpi=110)
    plt.close(fig)
    body = f"""Leve (frame cremagliera): la presa avviene sull'asse del pignone, {g['dx']:.1f} mm in X e {g['dz']:.1f} mm in Z
dalla linea dei denti. La coppia F·(dx, dz) ruota la cremagliera nella guida (lunga {g['L']:.0f} mm, sempre tutta impegnata):
due reazioni alle estremità, amplificate dal cuneo della coda di rondine a 60° ({K_H:.2f} per le forze laterali,
{K_UP:.0f} verso l'alto). In più la spinta radiale del dente (tan 20°).

{C.md_table(["μ", "rendimento presa", "forza per dito N", "rispetto al richiesto", "rendimento con guida 50 mm"], rows)}

Forza al dente {F_t:.1f} N per cremagliera (1.6 kg·cm); torque.py assume {F_t:.1f} N per dito e ne chiede {need:.1f}.
Con μ {C.MAT['mu_pla']} si perde il {100 * (1 - eta_n):.0f}% nelle guide: la presa reale è {F_t * eta_n:.1f} N per dito
(margine {ratio:.2f} sul richiesto, che già contiene SF 2).

**Effetto cassetto.** In corsa libera la spinta al dente è sfalsata dal centro guida di {g['dx0']:.1f} mm (X) e
{g['dz0']:.1f} mm (Z): si impunta solo con μ > {mu_lock:.2f}. Rapporto lunghezza guida / leva della presa
{g['L'] / math.hypot(g['dx'], g['dz']):.2f} (regola pratica ≥ 1.5): ok, ma con poco margine.

**Gioco.** Con clr_slide {c} la cremagliera ruota liberamente di {tip[0]:.2f}° (imbardata) e {tip[1]:.2f}° (beccheggio)
prima di toccare: il centro del dito si sposta di ±{tip[2] / 2:.2f} mm. I fianchi a 60° della gola, stampata in piano, hanno il
gradino dei layer da 0.2 mm (creste da {0.2 * math.cos(math.radians(60)):.2f} mm): i primi movimenti le spianano.

![presa](out/v4_presa.png)
"""
    recs = [
        f"Grasso al PTFE/silicone sulle code di rondine: μ 0.35 → 0.15 porta la presa da {F_t * eta_n:.1f} a "
        f"{F_t * efficiency(0.15):.1f} N per dito.",
        f"rack_len 40 → 50 mm (e y_half 36 → 41) se c'è spazio: rendimento {eta_n:.2f} → {efficiency(C.MAT['mu_pla'], L=50):.2f}.",
        "clr_slide: tenere 0.3 finché il provino non dice altro; sotto 0.2 le creste dei layer della gola fanno impuntare.",
    ]
    return dict(title="4. Code di rondine: attrito e impuntamento", esito=esito, body=body, recs=recs,
                summary=f"presa {F_t * eta_n:.1f} N/dito con μ {C.MAT['mu_pla']} (rendimento {eta_n:.2f}), "
                        f"richiesti {need:.1f} N; impuntamento solo con μ > {mu_lock:.2f}")


if __name__ == "__main__":
    r = run()
    print(r["esito"], r["summary"])
    print(r["body"])
