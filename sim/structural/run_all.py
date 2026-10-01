"""Rigenera tutta l'analisi strutturale e di tolleranze: grafici in out/ e REPORT.md.
Uso: python3 sim/structural/run_all.py   (legge le quote da cad/*.scad a ogni lancio; ~2 min, quasi tutto OpenSCAD)
"""
import datetime
import math
import sys
import time

import numpy as np

import common as C

C.OUT.mkdir(parents=True, exist_ok=True)


def self_check():
    """Il solutore senza perturbazioni ridà la FK nominale; la statica rispetta il lavoro virtuale."""
    import chain as K
    for th2, phi in C.POSES.values():
        tcp, ph, be = K.solve(th2, phi, K.pert(1))
        assert np.allclose(tcp[0], K.tcp_nominal(th2, phi), atol=1e-6) and abs(ph[0] - phi) < 1e-6 and abs(be[0]) < 1e-6
        s = C.statics(th2, phi)
        m = sum(m for _, m, _ in C.TQ.chain(0.05, True)) + 0.006
        vw = C.G * math.cos(math.radians(th2)) * (0.0132 * C.P["L1"] / 2 + m * C.P["L1"]
                                                  - C.N_SH * C.TQ.LEAD * C.TQ.R_CW_SHOULDER * 1000)
        assert abs(s["T_sh"] - vw) < 1e-6, (s["T_sh"], vw)
        assert np.allclose(sum(F for F, _ in C.elbow_bolt_loads(s)), -s["R_Ef"] - s["R_Et"])


def main():
    t0 = time.time()
    self_check()
    import v1_links, v2_pins, v3_gear, v4_dovetail, v5_snap, v6_screws, v7_creep, v8_montecarlo
    res = []
    for mod in (v1_links, v2_pins, v3_gear, v4_dovetail, v5_snap, v6_screws, v7_creep, v8_montecarlo):
        t = time.time()
        r = mod.run()
        print(f"{r['title']:<55} {r['esito']:<8} {time.time() - t:5.1f} s  {r['summary']}", flush=True)
        res.append(r)
    head = f"""# BRACCIO — analisi strutturale e di tolleranze

Generato da `sim/structural/run_all.py` il {datetime.date.today().isoformat()} sulle quote correnti di `cad/*.scad`
e sulle masse di `calc/torque.py`. PLA su Kobra S1: ugello 0.4, layer 0.2, 3 perimetri, gyroid 20%.
Materiale: E {C.MAT['E_xy']:.0f} MPa nel piano / {C.MAT['E_z']:.0f} tra layer, rottura {C.MAT['s_xy']:.0f} / {C.MAT['s_z']:.0f} MPa,
taglio interlaminare {C.MAT['t_il']:.0f} MPa; sezioni con guscio pieno (perimetri 1.2, top/bottom 0.8) e nucleo gyroid al 12% di
rigidezza. Orientamenti di stampa: quelli di `cad/export.sh`. Carico di verifica: 50 g + ESP32-CAM, {C.N_EL} piombi sulla manovella
e {C.N_SH} sulla coda del braccio (punto di progetto di docs/01).

## Esiti

| verifica | ESITO | in breve |
|---|---|---|
""" + "\n".join(f"| {r['title']} | **{r['esito']}** | {r['summary']} |" for r in res) + """

Il quadro in una riga: **i pezzi non si rompono, il braccio è cedevole**. Le tensioni sono basse quasi ovunque (eccezioni: il
dito della ganascia, il perno E e gli alberi dei servo). La rigidezza invece è dominata dall'eccentricità di ~33 mm tra il piano
del braccio e quello della biella motrice: la forza della biella flette fuori piano braccio, guancia e albero del servo spalla, e il
parallelogramma trasforma quelle piccole rotazioni in rotazioni dell'avambraccio, amplificate da 1/sin(e) vicino a e = 20°.
Ci sono poi tre difetti CAD che vanno corretti comunque (ganasce, dadi della staffa, dado di U corto).

"""
    sections = "\n\n".join(f"## {r['title']} — {r['esito']}\n\n{r['body']}" for r in res)
    recs = "\n".join(f"{i}. {rec}" for i, rec in enumerate((x for r in res for x in r["recs"]), 1))
    tail = f"""

## Raccomandazioni (in ordine di sezione)

{recs}

## Cosa misurare per tarare i modelli

- Freccia in `home` con 50 g in pinza (calibro a corsoio dal tavolo), poi la stessa premendo a mano il gomito verso la guancia
  del servo: la differenza è la parte fuori piano (braccio + guancia + albero) che il modello stima.
- Gioco del gomito a servo spento: spostamento della punta dell'avambraccio tra i due fine-gioco.
- Temperatura della cassa del servo gomito dopo 10 min in `home` con 50 g (dito o termometro IR).
- Larghezza della scheda ESP32 e lunghezza delle squadrette in casa: aggiornano subito le probabilità di §5 e §8.

## Limiti

Modelli a travi e lastre con rigidezze di bordo stimate, non FEM. La freccia elastica è lineare: oltre qualche grado di rotazione
dell'avambraccio (sbraccio, ripiegato) indica una cedevolezza eccessiva, non un valore esatto. Le distribuzioni del Monte Carlo
sono tipiche di una FDM tarata e di SG90 cloni; il provino di `cad/test/tolerance_coupon.scad` le sostituisce con misure.
Tempo di calcolo: {time.time() - t0:.0f} s.
"""
    (C.HERE / "REPORT.md").write_text(head + sections + tail)
    print(f"REPORT.md scritto ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
