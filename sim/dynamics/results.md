# Risultati simulazione dinamica (generato da run_all.py)

Massa mobile totale (0 g, 4+2 piombi): 303 g. Coppie statiche REACH 50 g: spalla 0.646, gomito 0.399 kg·cm.

## 1. Tenuta statica

Errore a regime (comando − albero) dopo 2 s, avvicinamento da +2° e da −2°. T = coppia gravitazionale per lavoro virtuale. Duty = uscita del driver (1 = saturo).

| posa | carico | T spalla kg·cm | T gomito kg·cm | err spalla ° | err gomito ° | duty sp/gom | err TCP mm | I sp+gom mA | oscill. ° |
|---|---|---|---|---|---|---|---|---|---|
| REACH th2=35 phi=0 | 0 g | +0.32 (SF 5.0) | -0.00 (SF 1170.3) | -1.16 … -1.05 | +0.10 … +0.72 | 0.18 / 0.07 | 1.5 | 182 | 0.01 |
| REACH th2=35 phi=0 | 30 g | +0.52 (SF 3.1) | +0.24 (SF 6.7) | -1.90 … -1.47 | -1.18 … -0.97 | 0.36 / 0.18 | 4.1 | 423 | 0.00 |
| REACH th2=35 phi=0 | 50 g | +0.65 (SF 2.5) | +0.40 (SF 4.0) | -2.00 … -1.93 | -1.71 … -1.37 | 0.39 / 0.31 | 5.0 | 539 | 0.00 |
| REACH th2=35 phi=0 | 30 g + CAM | +0.60 (SF 2.7) | +0.34 (SF 4.7) | -2.00 … -1.77 | -1.55 … -1.21 | 0.39 / 0.27 | 4.8 | 510 | 0.00 |
| REACH th2=35 phi=0 | 50 g + CAM | +0.73 (SF 2.2) | +0.50 (SF 3.2) | -2.22 … -2.00 | -1.95 … -1.66 | 0.44 / 0.37 | 5.3 | 583 | 0.00 |
| BACK th2=160 phi=10 | 0 g | -0.37 (SF 4.4) | -0.00 (SF 1133.8) | +1.18 … +1.25 | -0.77 … -0.15 | 0.20 / 0.08 | 2.6 | 210 | 0.01 |
| BACK th2=160 phi=10 | 50 g + CAM | -0.84 (SF 1.9) | +0.50 (SF 3.2) | +2.50 … +2.59 | -1.73 … -1.65 | 0.53 / 0.32 | 5.9 | 649 | 0.00 |
| HOME | 0 g | +0.00 (SF ∞) | -0.00 (SF 1170.3) | -0.56 … +0.51 | -0.46 … +0.42 | 0.03 / 0.00 | 1.0 | 41 | 0.02 |
| HOME | 50 g + CAM | +0.00 (SF ∞) | +0.50 (SF 3.2) | -0.28 … +0.57 | -1.88 … -1.40 | 0.03 / 0.36 | 2.8 | 307 | 0.03 |

Gioco dei perni (clr_pivot 0.3 mm diametrale → 0.15 mm radiale, 2 perni in serie per biella): rotazione libera dell'avambraccio = 0.3 mm / (crank_r·sin(th2−phi)), del polso = 0.3/(lev_r·sin th2) + 0.3/(lev2_r·cos phi). Sotto carico è un offset ripetibile, a carico nullo è gioco vero.

| th2−phi | gioco avambraccio | TCP mm (L2) |
|---|---|---|
| 35° | ±0.75° | ±1.05 |
| 45° | ±0.61° | ±0.85 |
| 90° | ±0.43° | ±0.60 |
| 150° | ±0.86° | ±1.20 |

## 2. Pick & place tra pose estreme (planner del firmware)

Sequenza: home->sbraccio [-90, 35, 0, 40], chiude [-90, 35, 0, 22], giro+indietro [90, 160, 10, 22], giù davanti [0, 60, -70, 22], apre [0, 60, -70, 40], ->home [0, 90, 0, 30]. Oggetto 25 mm, payload attaccato per tutta la sequenza (prudente), sosta 0.8 s.

### 0 g v=0.5  (durata 19.1 s, vincoli max 1.7 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.52 | 0.01 | 0.14 | +0.90 | 0.52 | 0 | 0.63 | 7.6 |
|  |  | spalla | 1.25 | 0.00 | 0.00 | -0.84 | 0.20 | 0 | 0.46 |  |
|  |  | gomito | 0.97 | 0.03 | 0.00 | -0.76 | 0.13 | 0 | 0.28 |  |
| chiude | 1.06 | base | 0.88 | 0.00 | 0.00 | +0.80 | 0.11 | 0 | 0.04 | 3.6 |
|  |  | spalla | 0.84 | 0.00 | 0.00 | -0.84 | 0.10 | 0 | 0.32 |  |
|  |  | gomito | 0.76 | 0.00 | 0.00 | -0.71 | 0.08 | 0 | 0.00 |  |
| giro+indietro | 4.46 | base | 2.68 | 0.01 | 0.18 | -0.90 | 0.56 | 0 | 0.97 | 9.1 |
|  |  | spalla | 2.08 | 0.00 | 0.00 | +0.96 | 0.41 | 0 | 0.65 |  |
|  |  | gomito | 0.85 | 0.01 | 0.00 | -0.76 | 0.10 | 0 | 0.19 |  |
| giù davanti | 2.70 | base | 2.48 | 0.01 | 0.13 | +0.89 | 0.51 | 0 | 0.86 | 4.5 |
|  |  | spalla | 2.37 | 0.00 | 0.00 | -0.56 | 0.48 | 0 | 0.58 |  |
|  |  | gomito | 1.36 | 0.01 | 0.00 | +0.00 | 0.23 | 0 | 0.52 |  |
| apre | 1.06 | base | 0.87 | 0.00 | 0.00 | +0.79 | 0.11 | 0 | 0.04 | 1.8 |
|  |  | spalla | 0.56 | 0.00 | 0.00 | -0.56 | 0.03 | 0 | 0.20 |  |
|  |  | gomito | 0.00 | 0.00 | 0.00 | +0.01 | 0.00 | 0 | 0.00 |  |
| ->home | 2.02 | base | 0.79 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.00 | 3.0 |
|  |  | spalla | 1.43 | 0.02 | 0.00 | -0.79 | 0.25 | 0 | 0.26 |  |
|  |  | gomito | 1.51 | 0.00 | 0.00 | -0.79 | 0.27 | 0 | 0.23 |  |

### 0 g v=1.0  (durata 13.6 s, vincoli max 1.8 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.20 | 0.01 | 0.03 | +0.87 | 0.69 | 0 | 0.72 | 9.5 |
|  |  | spalla | 1.51 | 0.00 | 0.00 | -0.84 | 0.27 | 0 | 0.68 |  |
|  |  | gomito | 1.03 | 0.03 | 0.00 | -0.79 | 0.14 | 0 | 0.32 |  |
| chiude | 0.74 | base | 0.86 | 0.00 | 0.00 | +0.80 | 0.10 | 0 | 0.03 | 3.6 |
|  |  | spalla | 0.84 | 0.00 | 0.00 | -0.84 | 0.10 | 0 | 0.32 |  |
|  |  | gomito | 0.79 | 0.00 | 0.00 | -0.74 | 0.08 | 0 | 0.00 |  |
| giro+indietro | 2.46 | base | 3.11 | 0.02 | 0.17 | -0.90 | 0.67 | 0 | 1.15 | 10.3 |
|  |  | spalla | 2.48 | 0.00 | 0.00 | +0.96 | 0.51 | 0 | 0.84 |  |
|  |  | gomito | 0.88 | 0.01 | 0.00 | -0.77 | 0.11 | 0 | 0.23 |  |
| giù davanti | 1.58 | base | 2.91 | 0.01 | 0.12 | +0.88 | 0.62 | 0 | 0.95 | 5.4 |
|  |  | spalla | 3.32 | 0.04 | 0.18 | -0.41 | 0.72 | 0 | 0.79 |  |
|  |  | gomito | 2.46 | 0.00 | 0.00 | +0.76 | 0.51 | 0 | 0.92 |  |
| apre | 0.74 | base | 0.87 | 0.00 | 0.00 | +0.79 | 0.11 | 0 | 0.03 | 2.3 |
|  |  | spalla | 0.56 | 0.00 | 0.00 | -0.56 | 0.03 | 0 | 0.20 |  |
|  |  | gomito | 0.77 | 0.00 | 0.00 | +0.77 | 0.08 | 0 | 0.02 |  |
| ->home | 1.24 | base | 0.79 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.00 | 3.5 |
|  |  | spalla | 1.56 | 0.03 | 0.00 | -0.75 | 0.28 | 0 | 0.30 |  |
|  |  | gomito | 2.05 | 0.00 | 0.00 | -0.79 | 0.41 | 0 | 0.34 |  |

### 50 g v=0.5  (durata 19.1 s, vincoli max 3.4 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.70 | 0.02 | 0.14 | +1.09 | 0.56 | 0 | 0.69 | 8.2 |
|  |  | spalla | 1.55 | 0.00 | 0.00 | -1.60 | 0.29 | 0 | 0.66 |  |
|  |  | gomito | 1.41 | 0.00 | 0.00 | -1.37 | 0.24 | 0 | 0.46 |  |
| chiude | 1.06 | base | 1.07 | 0.00 | 0.00 | +0.82 | 0.15 | 0 | 0.12 | 5.3 |
|  |  | spalla | 1.61 | 0.00 | 0.00 | -1.61 | 0.29 | 0 | 0.66 |  |
|  |  | gomito | 1.37 | 0.00 | 0.00 | -1.37 | 0.23 | 0 | 0.40 |  |
| giro+indietro | 4.46 | base | 2.84 | 0.02 | 0.16 | -1.09 | 0.60 | 0 | 0.99 | 10.9 |
|  |  | spalla | 2.86 | 0.00 | 0.00 | +1.83 | 0.60 | 0 | 0.81 |  |
|  |  | gomito | 1.75 | 0.01 | 0.00 | -1.68 | 0.33 | 0 | 0.41 |  |
| giù davanti | 2.70 | base | 2.45 | 0.02 | 0.13 | +1.07 | 0.50 | 0 | 0.94 | 5.7 |
|  |  | spalla | 3.22 | 0.00 | 0.00 | -1.04 | 0.70 | 0 | 0.93 |  |
|  |  | gomito | 1.65 | 0.00 | 0.00 | +0.48 | 0.30 | 0 | 0.48 |  |
| apre | 1.06 | base | 1.05 | 0.00 | 0.00 | +0.80 | 0.15 | 0 | 0.11 | 2.8 |
|  |  | spalla | 1.04 | 0.00 | 0.00 | -1.04 | 0.15 | 0 | 0.41 |  |
|  |  | gomito | 0.48 | 0.00 | 0.00 | +0.48 | 0.01 | 0 | 0.14 |  |
| ->home | 2.02 | base | 0.80 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.0 |
|  |  | spalla | 1.96 | 0.02 | 0.00 | -0.80 | 0.38 | 0 | 0.48 |  |
|  |  | gomito | 2.46 | 0.00 | 0.00 | -1.71 | 0.51 | 0 | 0.59 |  |

### 50 g v=1.0  (durata 13.6 s, vincoli max 3.4 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.24 | 0.02 | 0.08 | +1.05 | 0.70 | 0 | 0.80 | 9.5 |
|  |  | spalla | 1.64 | 0.00 | 0.00 | -1.60 | 0.29 | 0 | 0.66 |  |
|  |  | gomito | 1.42 | 0.00 | 0.00 | -1.37 | 0.24 | 0 | 0.48 |  |
| chiude | 0.74 | base | 1.03 | 0.00 | 0.00 | +0.82 | 0.14 | 0 | 0.10 | 5.2 |
|  |  | spalla | 1.61 | 0.00 | 0.00 | -1.61 | 0.29 | 0 | 0.66 |  |
|  |  | gomito | 1.37 | 0.00 | 0.00 | -1.37 | 0.23 | 0 | 0.40 |  |
| giro+indietro | 2.46 | base | 3.77 | 0.02 | 0.14 | -1.09 | 0.84 | 0 | 1.15 | 13.1 |
|  |  | spalla | 3.25 | 0.00 | 0.00 | +1.83 | 0.70 | 0 | 0.88 |  |
|  |  | gomito | 1.79 | 0.00 | 0.00 | -1.69 | 0.33 | 0 | 0.43 |  |
| giù davanti | 1.58 | base | 2.92 | 0.02 | 0.13 | +1.07 | 0.62 | 0 | 1.08 | 6.2 |
|  |  | spalla | 3.62 | 0.00 | 0.00 | -1.03 | 0.80 | 0 | 0.99 |  |
|  |  | gomito | 1.63 | 0.00 | 0.00 | +0.46 | 0.29 | 0 | 0.57 |  |
| apre | 0.74 | base | 1.05 | 0.00 | 0.00 | +0.81 | 0.15 | 0 | 0.12 | 2.8 |
|  |  | spalla | 1.04 | 0.00 | 0.00 | -1.04 | 0.15 | 0 | 0.41 |  |
|  |  | gomito | 0.46 | 0.00 | 0.00 | +0.46 | 0.00 | 0 | 0.14 |  |
| ->home | 1.24 | base | 0.81 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.6 |
|  |  | spalla | 2.09 | 0.04 | 0.00 | -0.80 | 0.41 | 0 | 0.50 |  |
|  |  | gomito | 2.96 | 0.00 | 0.00 | -1.71 | 0.63 | 0 | 0.66 |  |

### 30 g + CAM v=0.5  (durata 19.1 s, vincoli max 3.1 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.68 | 0.02 | 0.16 | +1.09 | 0.56 | 0 | 0.69 | 8.0 |
|  |  | spalla | 1.45 | 0.00 | 0.00 | -1.50 | 0.26 | 0 | 0.61 |  |
|  |  | gomito | 1.18 | 0.00 | 0.00 | -1.13 | 0.18 | 0 | 0.40 |  |
| chiude | 1.06 | base | 1.07 | 0.00 | 0.00 | +0.81 | 0.15 | 0 | 0.12 | 5.0 |
|  |  | spalla | 1.50 | 0.00 | 0.00 | -1.50 | 0.26 | 0 | 0.61 |  |
|  |  | gomito | 1.13 | 0.00 | 0.00 | -1.13 | 0.17 | 0 | 0.34 |  |
| giro+indietro | 4.46 | base | 2.81 | 0.02 | 0.17 | -1.08 | 0.59 | 0 | 0.99 | 10.6 |
|  |  | spalla | 2.76 | 0.00 | 0.00 | +1.71 | 0.58 | 0 | 0.76 |  |
|  |  | gomito | 1.62 | 0.01 | 0.00 | -1.55 | 0.29 | 0 | 0.36 |  |
| giù davanti | 2.70 | base | 2.45 | 0.02 | 0.13 | +1.06 | 0.50 | 0 | 0.94 | 5.4 |
|  |  | spalla | 3.09 | 0.00 | 0.00 | -0.97 | 0.67 | 0 | 0.88 |  |
|  |  | gomito | 1.52 | 0.00 | 0.00 | +0.51 | 0.27 | 0 | 0.43 |  |
| apre | 1.06 | base | 1.04 | 0.00 | 0.00 | +0.80 | 0.15 | 0 | 0.11 | 2.7 |
|  |  | spalla | 0.97 | 0.00 | 0.00 | -0.97 | 0.13 | 0 | 0.38 |  |
|  |  | gomito | 0.51 | 0.00 | 0.00 | +0.51 | 0.01 | 0 | 0.12 |  |
| ->home | 2.02 | base | 0.80 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 3.9 |
|  |  | spalla | 1.90 | 0.02 | 0.00 | -0.80 | 0.36 | 0 | 0.45 |  |
|  |  | gomito | 2.33 | 0.00 | 0.00 | -1.58 | 0.47 | 0 | 0.54 |  |

### 30 g + CAM v=1.0  (durata 13.6 s, vincoli max 3.2 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.21 | 0.02 | 0.12 | +1.06 | 0.69 | 0 | 0.79 | 9.5 |
|  |  | spalla | 1.56 | 0.00 | 0.00 | -1.50 | 0.28 | 0 | 0.65 |  |
|  |  | gomito | 1.19 | 0.00 | 0.00 | -1.13 | 0.18 | 0 | 0.43 |  |
| chiude | 0.74 | base | 1.04 | 0.00 | 0.00 | +0.82 | 0.15 | 0 | 0.11 | 4.9 |
|  |  | spalla | 1.50 | 0.00 | 0.00 | -1.50 | 0.26 | 0 | 0.61 |  |
|  |  | gomito | 1.13 | 0.00 | 0.00 | -1.13 | 0.17 | 0 | 0.34 |  |
| giro+indietro | 2.46 | base | 3.74 | 0.02 | 0.15 | -1.08 | 0.83 | 0 | 1.15 | 12.9 |
|  |  | spalla | 3.15 | 0.00 | 0.00 | +1.71 | 0.68 | 0 | 0.83 |  |
|  |  | gomito | 1.64 | 0.01 | 0.00 | -1.56 | 0.30 | 0 | 0.37 |  |
| giù davanti | 1.58 | base | 2.92 | 0.02 | 0.15 | +1.07 | 0.62 | 0 | 1.08 | 5.9 |
|  |  | spalla | 3.51 | 0.00 | 0.00 | -0.97 | 0.77 | 0 | 0.94 |  |
|  |  | gomito | 1.51 | 0.00 | 0.00 | +0.52 | 0.26 | 0 | 0.49 |  |
| apre | 0.74 | base | 1.05 | 0.00 | 0.00 | +0.81 | 0.15 | 0 | 0.11 | 2.8 |
|  |  | spalla | 0.97 | 0.00 | 0.00 | -0.97 | 0.13 | 0 | 0.38 |  |
|  |  | gomito | 0.52 | 0.00 | 0.00 | +0.52 | 0.02 | 0 | 0.12 |  |
| ->home | 1.24 | base | 0.81 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.4 |
|  |  | spalla | 2.03 | 0.05 | 0.00 | -0.80 | 0.39 | 0 | 0.47 |  |
|  |  | gomito | 2.83 | 0.00 | 0.00 | -1.59 | 0.60 | 0 | 0.62 |  |

### 2b. What-if sui limiti del planner (v=1.0, copia di config.h solo in build/)

| SG90 | limiti planner | tempo in moto s | err inseg. max b/sp/gom ° | duty max b/sp/gom | % saturo b/sp/gom | overshoot b/sp/gom ° | I picco A |
|---|---|---|---|---|---|---|---|
| 1.6 kg·cm | firmware 90°/s, 180°/s² | 8.2 | 3.8 / 3.6 / 3.0 | 0.84 / 0.80 / 0.63 | 0 / 0 / 0 | 0.02 / 0.04 / 0.00 | 2.07 |
| 1.6 kg·cm | 135°/s, 540°/s² | 5.6 | 5.8 / 4.5 / 3.6 | 1.00 / 1.00 / 0.80 | 4 / 0 / 0 | 0.02 / 0.03 / 0.03 | 2.25 |
| 1.6 kg·cm | 180°/s, 720°/s² | 4.8 | 6.9 / 5.2 / 4.2 | 1.00 / 1.00 / 0.95 | 10 / 2 / 0 | 0.13 / 0.16 / 0.05 | 2.32 |
| 1.6 kg·cm | 90°/s, 720°/s² | 6.8 | 5.9 / 4.0 / 3.1 | 1.00 / 0.91 / 0.66 | 3 / 0 / 0 | 0.41 / 0.02 / 0.03 | 2.33 |
| 1.2 kg·cm | firmware 90°/s, 180°/s² | 8.2 | 4.3 / 4.4 / 3.5 | 0.96 / 0.98 / 0.76 | 0 / 0 / 0 | 0.03 / 0.01 / 0.00 | 2.30 |
| 1.2 kg·cm | 135°/s, 540°/s² | 5.6 | 8.4 / 5.5 / 4.2 | 1.00 / 1.00 / 0.94 | 18 / 5 / 0 | 0.08 / 0.04 / 0.05 | 2.48 |
| 1.2 kg·cm | 180°/s, 720°/s² | 4.8 | 11.8 / 6.9 / 4.9 | 1.00 / 1.00 / 1.00 | 26 / 10 / 1 | 0.37 / 0.08 / 0.09 | 2.49 |
| 1.2 kg·cm | 90°/s, 720°/s² | 6.8 | 7.5 / 5.0 / 3.7 | 1.00 / 1.00 / 0.83 | 10 / 2 / 0 | 0.78 / 0.02 / 0.06 | 2.49 |

## 3. E-stop: PWM sganciato (servo liberi, motore aperto)

Tenuta 0.3 s, poi sgancio. L'evento è il primo tra: TCP sul tavolo, spalla o gomito 5° oltre il limite di giunto, th2−phi 5° oltre il vincolo (urto tra parti). Simulazione fino a 3 s.

| posa | contrappesi | carico | evento | t evento s | Δth2 / Δphi ° | ω spalla / gomito °/s | v TCP m/s |
|---|---|---|---|---|---|---|---|
| REACH | 4+2 piombi | 0 g | fine corsa spalla | 0.30 | -19.0 / -1.0 | -118 / -4 | 0.17 |
| REACH | 4+2 piombi | 50 g | fine corsa spalla | 0.14 | -18.0 / -3.3 | -279 / -28 | 0.43 |
| REACH | senza piombi | 0 g | fine corsa spalla | 0.18 | -18.6 / -13.2 | -207 / -131 | 0.46 |
| REACH | senza piombi | 50 g | fine corsa spalla | 0.13 | -17.9 / -15.9 | -295 / -218 | 0.69 |
| alto avanti th2=60 phi=40 | 4+2 piombi | 0 g | vincolo th2-phi | 2.04 | -6.2 / -1.4 | -12 / -0 | 0.02 |
| alto avanti th2=60 phi=40 | 4+2 piombi | 50 g | vincolo th2-phi | 0.18 | -10.9 / -6.1 | -130 / -68 | 0.27 |
| alto avanti th2=60 phi=40 | senza piombi | 0 g | vincolo th2-phi | 0.47 | -42.3 / -37.3 | -248 / -181 | 0.59 |
| alto avanti th2=60 phi=40 | senza piombi | 50 g | fine corsa spalla | 0.26 | -43.6 / -43.9 | -425 / -318 | 1.02 |
| HOME | 4+2 piombi | 0 g | nessuno | > 3 | +0.0 / +0.0 | +0 / +0 | 0.00 |
| HOME | 4+2 piombi | 50 g | vincolo th2-phi | 0.60 | -0.7 / -64.6 | +0 / -49 | 0.07 |
| HOME | senza piombi | 0 g | nessuno | > 3 | -0.7 / -50.4 | +0 / -2 | 0.00 |
| HOME | senza piombi | 50 g | fine corsa gomito | 0.25 | -18.7 / -73.1 | -257 / -485 | 0.43 |
| BACK | 4+2 piombi | 0 g | fine corsa spalla | 0.09 | +3.8 / +0.3 | +68 / -0 | 0.10 |
| BACK | 4+2 piombi | 50 g | vincolo th2-phi | 0.03 | +1.2 / +0.1 | +74 / -6 | 0.11 |
| BACK | senza piombi | 0 g | vincolo th2-phi | 0.05 | +2.1 / -0.2 | +82 / -6 | 0.12 |
| BACK | senza piombi | 50 g | vincolo th2-phi | 0.01 | +0.0 / +0.0 | +14 / -1 | 0.02 |
| basso avanti th2=40 phi=-50 | 4+2 piombi | 0 g | fine corsa spalla | 0.39 | -24.1 / -1.5 | -123 / +0 | 0.17 |
| basso avanti th2=40 phi=-50 | 4+2 piombi | 50 g | fine corsa spalla | 0.15 | -23.2 / -3.5 | -314 / -8 | 0.44 |
| basso avanti th2=40 phi=-50 | senza piombi | 0 g | fine corsa spalla | 0.21 | -23.6 / -5.9 | -233 / -28 | 0.34 |
| basso avanti th2=40 phi=-50 | senza piombi | 50 g | fine corsa spalla | 0.13 | -22.8 / -11.0 | -364 / -107 | 0.56 |

## 4. Sensibilità (REACH statico e sequenza a v=1.0)

| carico | variante | T statica sp/gom kg·cm | SF min | err statico sp/gom ° | duty statico sp/gom | err inseg. max b/sp/gom ° | % saturo b/sp/gom | overshoot b/sp/gom ° | I picco tot A |
|---|---|---|---|---|---|---|---|---|---|
| 50 g | nominale | +0.65 / +0.40 | 2.5 | 2.00 / 1.71 | 0.39 / 0.31 | 3.8 / 3.6 / 3.0 | 0 / 0 / 0 | 0.02 / 0.04 / 0.00 | 2.07 |
| 50 g | SG90 1.2 kg·cm | +0.65 / +0.40 | 1.9 | 2.18 / 2.00 | 0.43 / 0.39 | 4.3 / 4.4 / 3.5 | 0 / 0 / 0 | 0.03 / 0.01 / 0.00 | 2.30 |
| 50 g | attrito alto | +0.65 / +0.40 | 2.5 | 2.26 / 1.93 | 0.45 / 0.37 | 4.1 / 4.6 / 4.2 | 0 / 1 / 0 | 0.02 / 0.11 / 0.08 | 2.31 |
| 50 g | manovella 2 piombi | +0.65 / +0.54 | 2.5 | 2.00 / 2.00 | 0.39 / 0.39 | 3.8 / 3.6 / 3.3 | 0 / 0 / 0 | 0.02 / 0.04 / 0.01 | 2.13 |
| 50 g | manovella 0 piombi | +0.65 / +0.71 | 2.2 | 2.00 / 2.13 | 0.39 / 0.42 | 3.7 / 3.6 / 3.7 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.20 |
| 50 g | braccio 0 piombi | +0.74 / +0.40 | 2.1 | 2.17 / 1.71 | 0.43 / 0.31 | 3.8 / 3.9 / 3.0 | 0 / 0 / 0 | 0.02 / 0.03 / 0.01 | 2.11 |
| 50 g | gioco 2° + banda 8 µs | +0.65 / +0.40 | 2.5 | 2.21 / 1.98 | 0.37 / 0.31 | 4.0 / 3.9 / 3.2 | 0 / 0 / 0 | 0.02 / 0.02 / 0.00 | 2.07 |
| 50 g | anello morbido (100% a 8°) | +0.65 / +0.40 | 2.5 | 3.58 / 2.31 | 0.39 / 0.23 | 6.5 / 6.2 / 4.6 | 0 / 0 / 0 | 0.04 / 0.01 / 0.00 | 1.62 |
| 50 g | corona ingrassata μ 0.1 | +0.65 / +0.40 | 2.5 | 2.00 / 1.71 | 0.39 / 0.31 | 3.1 / 3.6 / 3.0 | 0 / 0 / 0 | 0.10 / 0.04 / 0.01 | 1.91 |
| 50 g | 1.2 kg·cm + attrito alto | +0.65 / +0.40 | 1.9 | 2.45 / 2.00 | 0.50 / 0.39 | 4.6 / 8.6 / 5.1 | 0 / 26 / 6 | 0.03 / 0.05 / 0.08 | 2.47 |
| 30 g + CAM | nominale | +0.60 / +0.34 | 2.7 | 2.00 / 1.55 | 0.39 / 0.27 | 3.7 / 3.5 / 2.8 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.03 |
| 30 g + CAM | SG90 1.2 kg·cm | +0.60 / +0.34 | 2.0 | 2.06 / 1.92 | 0.40 / 0.37 | 4.2 / 4.2 / 3.3 | 0 / 0 / 0 | 0.03 / 0.01 / 0.00 | 2.24 |
| 30 g + CAM | attrito alto | +0.60 / +0.34 | 2.7 | 2.17 / 1.81 | 0.43 / 0.34 | 4.0 / 4.5 / 4.1 | 0 / 0 / 0 | 0.02 / 0.04 / 0.07 | 2.26 |
| 30 g + CAM | manovella 2 piombi | +0.60 / +0.49 | 2.7 | 2.00 / 1.92 | 0.39 / 0.36 | 3.7 / 3.5 / 3.2 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.08 |
| 30 g + CAM | manovella 0 piombi | +0.60 / +0.66 | 2.4 | 2.00 / 2.00 | 0.39 / 0.39 | 3.7 / 3.5 / 3.6 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.14 |
| 30 g + CAM | braccio 0 piombi | +0.70 / +0.34 | 2.3 | 2.00 / 1.55 | 0.39 / 0.27 | 3.7 / 3.7 / 2.8 | 0 / 0 / 0 | 0.02 / 0.04 / 0.01 | 2.06 |
| 30 g + CAM | gioco 2° + banda 8 µs | +0.60 / +0.34 | 2.7 | 2.05 / 1.85 | 0.33 / 0.28 | 4.0 / 3.8 / 3.1 | 0 / 0 / 0 | 0.02 / 0.03 / 0.01 | 2.03 |
| 30 g + CAM | anello morbido (100% a 8°) | +0.60 / +0.34 | 2.7 | 3.46 / 2.18 | 0.38 / 0.22 | 6.4 / 6.0 / 4.4 | 0 / 0 / 0 | 0.04 / 0.01 / 0.01 | 1.55 |
| 30 g + CAM | corona ingrassata μ 0.1 | +0.60 / +0.34 | 2.7 | 2.00 / 1.55 | 0.39 / 0.27 | 3.2 / 3.5 / 2.8 | 0 / 0 / 0 | 0.09 / 0.05 / 0.01 | 1.90 |
| 30 g + CAM | 1.2 kg·cm + attrito alto | +0.60 / +0.34 | 2.0 | 2.22 / 2.00 | 0.44 / 0.39 | 4.5 / 6.8 / 4.8 | 0 / 19 / 3 | 0.03 / 0.04 / 0.07 | 2.45 |

Fattore v del comando nei casi peggiori (50 g, sequenza completa):

| variante | v | duty max b/sp/gom | % saturo b/sp/gom | err inseg. max b/sp/gom ° |
|---|---|---|---|---|
| SG90 1.2 kg·cm | 0.5 | 0.79 / 0.87 / 0.62 | 0 / 0 / 0 | 3.6 / 3.9 / 2.9 |
| SG90 1.2 kg·cm | 0.7 | 0.85 / 0.92 / 0.67 | 0 / 0 / 0 | 3.8 / 4.1 / 3.1 |
| SG90 1.2 kg·cm | 1.0 | 0.96 / 0.98 / 0.76 | 0 / 0 / 0 | 4.3 / 4.4 / 3.5 |
| attrito alto | 0.5 | 0.68 / 0.89 / 0.79 | 0 / 0 / 0 | 3.2 / 4.0 / 3.6 |
| attrito alto | 0.7 | 0.75 / 0.95 / 0.85 | 0 / 0 / 0 | 3.4 / 4.2 / 3.8 |
| attrito alto | 1.0 | 0.91 / 1.00 / 0.94 | 0 / 1 / 0 | 4.1 / 4.6 / 4.2 |
| 1.2 kg·cm + attrito alto | 0.5 | 0.87 / 1.00 / 0.97 | 0 / 8 / 0 | 3.9 / 5.0 / 4.3 |
| 1.2 kg·cm + attrito alto | 0.7 | 0.95 / 1.00 / 1.00 | 0 / 17 / 1 | 4.2 / 6.0 / 4.6 |
| 1.2 kg·cm + attrito alto | 1.0 | 1.00 / 1.00 / 1.00 | 0 / 26 / 6 | 4.6 / 8.6 / 5.1 |

## 5. Corrente

Sequenza 50 g, v=1.0, nominale (`current_profiles.csv`, 1 kHz). I = I_idle 10 mA + 0.74 A × |coppia elettromagnetica| / stallo.

| servo | picco A | media A | RMS A |
|---|---|---|---|
| base | 0.58 | 0.163 | 0.191 |
| spalla | 0.55 | 0.174 | 0.203 |
| gomito | 0.44 | 0.158 | 0.183 |
| pinza | 0.75 | 0.420 | 0.531 |
| totale | 2.08 | 0.915 | 1.016 |

Presa di un pezzo da 25 mm: comando = larghezza − schiacciamento. Forza richiesta 1.6 N/dito (50 g, μ 0.3, SF 2).

| comando g | schiacciamento mm | forza/dito N | I a regime A | presa sicura |
|---|---|---|---|---|
| 24.5 mm | 0.5 | 0.5 | 0.08 | no |
| 24.0 mm | 1.0 | 1.7 | 0.23 | sì |
| 23.5 mm | 1.5 | 2.5 | 0.38 | sì |
| 23.0 mm | 2.0 | 3.5 | 0.53 | sì |
| 22.0 mm | 3.0 | 5.5 | 0.75 | sì |
| 20.0 mm | 5.0 | 5.5 | 0.75 | sì |
| 0.0 mm (chiudi tutto) | 25.0 | 5.5 | 0.75 | sì |

Enable con il braccio a 30°/40°/40° da home (base/spalla/gomito): velocità di picco 394 / 414 / 529 °/s, corrente totale di picco 2.55 A per 119 ms sopra 1.5 A.
