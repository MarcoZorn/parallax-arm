# Verifiche e simulazioni

Tutto si rigenera da zero con gli script indicati; i numeri qui sotto vengono dall'ultima esecuzione.
Sono simulazioni e modelli: **nessun pezzo è ancora stato stampato o provato su hardware**.

| Area | Come | Comando |
|---|---|---|
| Coppie statiche | lavoro virtuale, masse dagli STL | `python3 calc/torque.py` |
| Collisioni | intersezione di tutte le coppie di parti + viti/dadi/distanziali su una griglia di pose | `cad/check_grid.sh` |
| Dinamica | MuJoCo, catene chiuse, modello SG90 (anello P, banda morta, gioco, curva coppia-velocità), attriti, planner **vero** del firmware via ctypes | `sim/.venv/bin/python sim/dynamics/run_all.py` |
| Strutture e tolleranze | travi/lastre con anisotropia FDM, perni, ingranaggi, code di rondine, incastri, viti, creep, Monte Carlo 2000 robot | `python3 sim/structural/run_all.py` |
| Alimentazione | rete a nodi nel tempo (50 µs): caricatore, cavi, WAGO, condensatore, 4 SG90, ESP32 | `python3 sim/electrical/run_all.py` |
| Software | firmware ↔ twin su 6000 scenari, IK/FK su 1.5 M pose, fuzz (ASan/UBSan), protocollo end-to-end, UI in Chrome headless | `sim/software/run_all.sh` |

## Esiti

| Verifica | Esito | Numeri |
|---|---|---|
| Coppie, 50 g + ESP32-CAM | ✅ | SF ≥ 2.0 (calc), ≥ 1.9 nella pose peggiore della simulazione (spalla, braccio tutto indietro) |
| Collisioni | ✅ | 0 su tutta la griglia, incluso il cedimento della spalla a 17°; controllo negativo verificato |
| Moto pick&place a v=0.5 e v=1 | ✅ | nessun servo satura, duty max 0.72, overshoot < 0.05°, assestamento < 0.2 s |
| Precisione dei servo (banda morta + gioco) | ⚠️ | errore statico al TCP 1–6 mm a seconda del carico, errore d'arresto ~0.8–1° |
| Cedevolezza strutturale | ⚠️ | flessione elastica del TCP con 50 g + camera: **~5.5–6 mm** in home, **~13–14 mm** a sbraccio massimo (±30–50 %; le nervature coprono x 12–45, dove il momento è massimo) |
| Ripetibilità/accuratezza (Monte Carlo) | ⚠️ | p95 ~15 mm: è un braccio da pick&place di oggetti da 10–50 mm, non da precisione |
| E-stop (servo sganciati) | ✅ | il braccio scende lentamente, impatto ≤ 0.44 m/s con i piombi |
| Ingranaggi pinza | ✅ | 2.4 MPa allo stallo, ricoprimento 1.53, nessuna interferenza su tutta la rotazione |
| Incastri, viti, dadi | ✅ / ⚠️ | ESP32 trattenuto nel 100 % dei casi; pareti minime attorno ad alcuni dadi 0.55 mm |
| Accoppiamenti (cloni SG90, squadrette) | ⚠️ | squadretta 0 % da limare; SG90 nelle guance ~10 % da limare con una lima piatta |
| Alimentazione | ✅ con il cablaggio consigliato | cavo USB-C 3A corto, 2200 µF, enable sfalsato: servo ≥ 4.3 V. Con cavo da 1 m sottile: KO |
| Pinza in stallo | ❌ se chiusa a 0 mm su un oggetto | 0.7 A, >120 °C in 5 min → usa **Prendi** (larghezza − 1.5 mm) |
| Perno E / albero spalla | ⚠️ | vite M3 molto sollecitata a flessione: usa **acciaio 8.8 o 12.9**, non inox; l'albero dell'SG90 spalla porta ~20 N radiali |
| Software | ✅ | twin = firmware entro 0.004°, 0 crash nel fuzz, protocollo 17/17, UI 17/17 |

## Cosa è stato cambiato grazie alle verifiche

- **Dinamica:** il gomito con 4 piombi era perfettamente bilanciato e girava libero nel gioco → **2 piombi sulla manovella, 4 sulla coda del braccio**. Il calcolo statico era pessimista: la pinza livellata carica il gomito solo con leva L2.
- **Strutture:**
  - coda di rondine delle ganasce **staccata dal corpo** (fessura 0.3 mm) → collo aggiunto;
  - dadi della staffa del polso **sovrapposti** → interasse 7.5 mm;
  - braccio più largo con **nervature**, fazzoletti delle guance alti 50 mm;
  - vincolo **th2 − phi ≥ 35°** (era 20°): cedevolezza a sbraccio da ~54 a ~13 mm, sbraccio da 202 a 188 mm;
  - gioco servo e squadretta allargati, ganci ESP32 0.8 mm.
- **Elettrica:** servo agganciati **uno ogni 200 ms** all'enable (picco da ~2.7 a ~1.7 A); raccomandazioni su cavo, condensatore, interruttore e massa in [02-cablaggio.md](02-cablaggio.md).
- **Software:**
  - 4 bug del planner del firmware corretti;
  - il twin ora è il planner del firmware riga per riga;
  - E-STOP che scarta i comandi in coda;
  - `raw` che rispetta il vincolo;
  - taratura che non può allargare i limiti meccanici;
  - comando **Prendi** nella web app.

## Limiti onesti

- Un braccio SG90 + PLA + perni M3 ha **gioco e cedevolezza di qualche millimetro**: è normale per questa classe (MeArm, EEZYbot). Va bene per spostare oggetti leggeri; per la precisione servirebbero servo con cuscinetto (MG90S), perni d4 e un braccio a forcella.
- Il cedimento sotto carico è soprattutto elastico e ripetibile: una futura **compensazione di gravità** nel firmware (offset proporzionale al carico, coefficienti da misurare) può ridurre l'errore statico a ~1.5 mm.
- Le stime di rigidezza hanno ±30–50 % di incertezza (rigidezze di bordo fori, albero SG90, vincolo delle guance). La prova al banco consigliata: freccia del TCP in home con 50 g in pinza.
- Non tenere pose cariche per ore (creep del PLA e servo caldi): parcheggia appoggiato o premi E-STOP.
