# Risultati simulazione dinamica (generato da run_all.py)

Massa mobile totale (0 g, 4+2 piombi): 289 g. Coppie statiche REACH 50 g: spalla 0.728, gomito 0.385 kg·cm.

## 1. Tenuta statica

Errore a regime (comando − albero) dopo 2 s, avvicinamento da +2° e da −2°. T = coppia gravitazionale per lavoro virtuale. Duty = uscita del driver (1 = saturo).

| posa | carico | T spalla kg·cm | T gomito kg·cm | err spalla ° | err gomito ° | duty sp/gom | err TCP mm | I sp+gom mA | oscill. ° |
|---|---|---|---|---|---|---|---|---|---|
| REACH th2=20 phi=0 | 0 g | +0.35 (SF 4.5) | -0.02 (SF 102.5) | -1.24 … -1.12 | +0.76 … +0.78 | 0.20 / 0.08 | 0.8 | 230 | 0.07 |
| REACH th2=20 phi=0 | 30 g | +0.58 (SF 2.8) | +0.22 (SF 7.1) | -1.95 … -1.61 | -1.13 … -0.99 | 0.38 / 0.17 | 4.3 | 424 | 0.00 |
| REACH th2=20 phi=0 | 50 g | +0.73 (SF 2.2) | +0.38 (SF 4.2) | -2.13 … -2.00 | -1.67 … -1.40 | 0.42 / 0.30 | 5.1 | 533 | 0.00 |
| REACH th2=20 phi=0 | 30 g + CAM | +0.68 (SF 2.4) | +0.33 (SF 4.9) | -2.00 … -1.94 | -1.50 … -1.23 | 0.39 / 0.26 | 4.9 | 501 | 0.00 |
| REACH th2=20 phi=0 | 50 g + CAM | +0.83 (SF 1.9) | +0.49 (SF 3.3) | -2.44 … -2.02 | -1.91 … -1.70 | 0.50 / 0.36 | 5.8 | 619 | 0.00 |
| BACK th2=160 phi=10 | 0 g | -0.35 (SF 4.5) | -0.02 (SF 103.6) | +1.18 … +1.22 | -0.28 … +0.42 | 0.19 / 0.00 | 2.0 | 160 | 0.16 |
| BACK th2=160 phi=10 | 50 g + CAM | -0.83 (SF 1.9) | +0.48 (SF 3.3) | +2.49 … +2.57 | -1.70 … -1.63 | 0.53 / 0.31 | 5.8 | 639 | 0.00 |
| HOME | 0 g | +0.00 (SF ∞) | -0.02 (SF 102.5) | -0.57 … +0.54 | -0.05 … +0.67 | 0.03 / 0.06 | 1.2 | 80 | 0.16 |
| HOME | 50 g + CAM | +0.00 (SF ∞) | +0.49 (SF 3.3) | -0.26 … +0.55 | -1.84 … -1.37 | 0.03 / 0.35 | 2.7 | 296 | 0.03 |

Gioco dei perni (clr_pivot 0.3 mm diametrale → 0.15 mm radiale, 2 perni in serie per biella): rotazione libera dell'avambraccio = 0.3 mm / (crank_r·sin(th2−phi)), del polso = 0.3/(lev_r·sin th2) + 0.3/(lev2_r·cos phi). Sotto carico è un offset ripetibile, a carico nullo è gioco vero.

| th2−phi | gioco avambraccio | TCP mm (L2) |
|---|---|---|
| 20° | ±1.26° | ±1.75 |
| 45° | ±0.61° | ±0.85 |
| 90° | ±0.43° | ±0.60 |
| 150° | ±0.86° | ±1.20 |

## 2. Pick & place tra pose estreme (planner del firmware)

Sequenza: home->sbraccio [-90, 20, 0, 40], chiude [-90, 20, 0, 22], giro+indietro [90, 160, 10, 22], giù davanti [0, 60, -70, 22], apre [0, 60, -70, 40], ->home [0, 90, 0, 30]. Oggetto 25 mm, payload attaccato per tutta la sequenza (prudente), sosta 0.8 s.

### 0 g v=0.5  (durata 19.1 s, vincoli max 2.3 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.52 | 0.01 | 0.15 | +0.89 | 0.52 | 0 | 0.63 | 8.1 |
|  |  | spalla | 1.49 | 0.00 | 0.00 | -0.90 | 0.27 | 0 | 0.69 |  |
|  |  | gomito | 0.86 | 0.23 | 0.00 | -0.52 | 0.10 | 0 | 0.17 |  |
| chiude | 1.06 | base | 0.88 | 0.00 | 0.00 | +0.80 | 0.11 | 0 | 0.03 | 3.6 |
|  |  | spalla | 0.90 | 0.00 | 0.00 | -0.90 | 0.11 | 0 | 0.35 |  |
|  |  | gomito | 0.51 | 0.02 | 0.00 | +0.09 | 0.01 | 0 | 0.00 |  |
| giro+indietro | 4.46 | base | 2.69 | 0.01 | 0.18 | -0.89 | 0.57 | 0 | 0.97 | 9.5 |
|  |  | spalla | 2.25 | 0.00 | 0.00 | +0.93 | 0.45 | 0 | 0.78 |  |
|  |  | gomito | 0.83 | 0.02 | 0.00 | -0.73 | 0.10 | 0 | 0.15 |  |
| giù davanti | 2.70 | base | 2.47 | 0.01 | 0.17 | +0.89 | 0.51 | 0 | 0.85 | 4.5 |
|  |  | spalla | 2.31 | 0.02 | 0.00 | +0.09 | 0.47 | 0 | 0.56 |  |
|  |  | gomito | 1.36 | 0.00 | 0.00 | +0.77 | 0.23 | 0 | 0.24 |  |
| apre | 1.06 | base | 0.87 | 0.00 | 0.00 | +0.79 | 0.11 | 0 | 0.04 | 2.1 |
|  |  | spalla | 0.49 | 0.00 | 0.00 | -0.54 | 0.02 | 0 | 0.19 |  |
|  |  | gomito | 0.77 | 0.06 | 0.00 | +0.75 | 0.08 | 0 | 0.00 |  |
| ->home | 2.02 | base | 0.79 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.00 | 3.2 |
|  |  | spalla | 1.78 | 0.00 | 0.00 | -0.77 | 0.34 | 0 | 0.39 |  |
|  |  | gomito | 2.25 | 0.02 | 0.00 | -0.58 | 0.45 | 0 | 0.95 |  |

### 0 g v=1.0  (durata 13.6 s, vincoli max 2.4 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.20 | 0.01 | 0.05 | +0.87 | 0.69 | 0 | 0.72 | 9.8 |
|  |  | spalla | 1.81 | 0.00 | 0.00 | -0.90 | 0.34 | 0 | 0.91 |  |
|  |  | gomito | 0.98 | 0.23 | 0.00 | -0.55 | 0.13 | 0 | 0.29 |  |
| chiude | 0.74 | base | 0.86 | 0.00 | 0.00 | +0.80 | 0.10 | 0 | 0.02 | 3.6 |
|  |  | spalla | 0.90 | 0.00 | 0.00 | -0.90 | 0.11 | 0 | 0.35 |  |
|  |  | gomito | 0.53 | 0.02 | 0.00 | -0.04 | 0.02 | 0 | 0.00 |  |
| giro+indietro | 2.46 | base | 3.17 | 0.01 | 0.17 | -0.89 | 0.69 | 0 | 1.15 | 11.2 |
|  |  | spalla | 2.70 | 0.00 | 0.00 | +0.93 | 0.57 | 0 | 0.88 |  |
|  |  | gomito | 1.02 | 0.02 | 0.00 | -0.26 | 0.14 | 0 | 0.45 |  |
| giù davanti | 1.58 | base | 2.88 | 0.01 | 0.18 | +0.89 | 0.61 | 0 | 0.94 | 5.2 |
|  |  | spalla | 2.78 | 0.02 | 0.00 | +0.00 | 0.59 | 0 | 0.65 |  |
|  |  | gomito | 1.76 | 0.00 | 0.00 | +0.73 | 0.33 | 0 | 0.32 |  |
| apre | 0.74 | base | 0.88 | 0.00 | 0.00 | +0.79 | 0.11 | 0 | 0.04 | 2.1 |
|  |  | spalla | 0.44 | 0.10 | 0.00 | -0.54 | 0.02 | 0 | 0.19 |  |
|  |  | gomito | 0.72 | 0.05 | 0.00 | +0.70 | 0.07 | 0 | 0.00 |  |
| ->home | 1.24 | base | 0.79 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.00 | 3.5 |
|  |  | spalla | 1.73 | 0.00 | 0.00 | -0.70 | 0.32 | 0 | 0.41 |  |
|  |  | gomito | 2.17 | 0.02 | 0.00 | -0.56 | 0.43 | 0 | 0.86 |  |

### 50 g v=0.5  (durata 19.1 s, vincoli max 4.5 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.69 | 0.02 | 0.07 | +1.04 | 0.56 | 0 | 0.69 | 8.6 |
|  |  | spalla | 1.78 | 0.00 | 0.00 | -1.78 | 0.33 | 0 | 0.74 |  |
|  |  | gomito | 1.35 | 0.00 | 0.00 | -1.31 | 0.22 | 0 | 0.45 |  |
| chiude | 1.06 | base | 1.02 | 0.00 | 0.00 | +0.81 | 0.14 | 0 | 0.10 | 5.6 |
|  |  | spalla | 1.79 | 0.00 | 0.00 | -1.79 | 0.34 | 0 | 0.74 |  |
|  |  | gomito | 1.31 | 0.00 | 0.00 | -1.31 | 0.21 | 0 | 0.38 |  |
| giro+indietro | 4.46 | base | 2.89 | 0.02 | 0.16 | -1.08 | 0.61 | 0 | 0.99 | 11.7 |
|  |  | spalla | 3.13 | 0.00 | 0.00 | +1.80 | 0.68 | 0 | 0.91 |  |
|  |  | gomito | 1.70 | 0.01 | 0.00 | -1.64 | 0.31 | 0 | 0.39 |  |
| giù davanti | 2.70 | base | 2.44 | 0.02 | 0.13 | +1.06 | 0.50 | 0 | 0.94 | 5.6 |
|  |  | spalla | 3.18 | 0.00 | 0.00 | -1.02 | 0.69 | 0 | 0.92 |  |
|  |  | gomito | 1.61 | 0.00 | 0.00 | +0.48 | 0.29 | 0 | 0.47 |  |
| apre | 1.06 | base | 1.04 | 0.00 | 0.00 | +0.80 | 0.15 | 0 | 0.11 | 2.8 |
|  |  | spalla | 1.02 | 0.00 | 0.00 | -1.02 | 0.14 | 0 | 0.40 |  |
|  |  | gomito | 0.49 | 0.00 | 0.00 | +0.49 | 0.01 | 0 | 0.14 |  |
| ->home | 2.02 | base | 0.80 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.0 |
|  |  | spalla | 1.95 | 0.02 | 0.00 | -0.80 | 0.37 | 0 | 0.48 |  |
|  |  | gomito | 2.42 | 0.00 | 0.00 | -1.68 | 0.50 | 0 | 0.58 |  |

### 50 g v=1.0  (durata 13.6 s, vincoli max 4.6 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.25 | 0.01 | 0.00 | +1.00 | 0.70 | 0 | 0.80 | 9.8 |
|  |  | spalla | 2.05 | 0.00 | 0.00 | -1.78 | 0.40 | 0 | 0.76 |  |
|  |  | gomito | 1.40 | 0.00 | 0.00 | -1.31 | 0.24 | 0 | 0.51 |  |
| chiude | 0.74 | base | 0.98 | 0.00 | 0.00 | +0.82 | 0.13 | 0 | 0.08 | 5.5 |
|  |  | spalla | 1.79 | 0.00 | 0.00 | -1.79 | 0.34 | 0 | 0.74 |  |
|  |  | gomito | 1.31 | 0.00 | 0.00 | -1.31 | 0.21 | 0 | 0.38 |  |
| giro+indietro | 2.46 | base | 3.83 | 0.02 | 0.12 | -1.07 | 0.85 | 0 | 1.16 | 14.2 |
|  |  | spalla | 3.59 | 0.00 | 0.00 | +1.80 | 0.79 | 0 | 0.98 |  |
|  |  | gomito | 1.74 | 0.01 | 0.00 | -1.66 | 0.32 | 0 | 0.41 |  |
| giù davanti | 1.58 | base | 2.95 | 0.02 | 0.13 | +1.06 | 0.63 | 0 | 1.07 | 6.1 |
|  |  | spalla | 3.59 | 0.00 | 0.00 | -1.02 | 0.79 | 0 | 0.98 |  |
|  |  | gomito | 1.60 | 0.00 | 0.00 | +0.47 | 0.29 | 0 | 0.55 |  |
| apre | 0.74 | base | 1.04 | 0.00 | 0.00 | +0.81 | 0.15 | 0 | 0.11 | 2.8 |
|  |  | spalla | 1.02 | 0.00 | 0.00 | -1.02 | 0.14 | 0 | 0.40 |  |
|  |  | gomito | 0.47 | 0.00 | 0.00 | +0.47 | 0.00 | 0 | 0.14 |  |
| ->home | 1.24 | base | 0.81 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.5 |
|  |  | spalla | 2.08 | 0.04 | 0.00 | -0.80 | 0.41 | 0 | 0.49 |  |
|  |  | gomito | 2.92 | 0.00 | 0.00 | -1.68 | 0.63 | 0 | 0.65 |  |

### 30 g + CAM v=0.5  (durata 19.1 s, vincoli max 4.2 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 2.46 | base | 2.67 | 0.02 | 0.12 | +1.05 | 0.56 | 0 | 0.68 | 8.6 |
|  |  | spalla | 1.67 | 0.00 | 0.00 | -1.66 | 0.30 | 0 | 0.68 |  |
|  |  | gomito | 1.11 | 0.00 | 0.00 | -1.07 | 0.16 | 0 | 0.39 |  |
| chiude | 1.06 | base | 1.03 | 0.00 | 0.00 | +0.81 | 0.14 | 0 | 0.10 | 5.2 |
|  |  | spalla | 1.67 | 0.00 | 0.00 | -1.67 | 0.31 | 0 | 0.69 |  |
|  |  | gomito | 1.07 | 0.00 | 0.00 | -1.07 | 0.15 | 0 | 0.33 |  |
| giro+indietro | 4.46 | base | 2.86 | 0.02 | 0.17 | -1.07 | 0.60 | 0 | 0.99 | 11.4 |
|  |  | spalla | 3.02 | 0.00 | 0.00 | +1.68 | 0.65 | 0 | 0.86 |  |
|  |  | gomito | 1.58 | 0.01 | 0.00 | -1.52 | 0.28 | 0 | 0.34 |  |
| giù davanti | 2.70 | base | 2.45 | 0.02 | 0.13 | +1.05 | 0.50 | 0 | 0.93 | 5.3 |
|  |  | spalla | 3.06 | 0.00 | 0.00 | -0.95 | 0.66 | 0 | 0.87 |  |
|  |  | gomito | 1.49 | 0.00 | 0.00 | +0.53 | 0.26 | 0 | 0.42 |  |
| apre | 1.06 | base | 1.02 | 0.00 | 0.00 | +0.80 | 0.15 | 0 | 0.10 | 2.7 |
|  |  | spalla | 0.95 | 0.00 | 0.00 | -0.95 | 0.13 | 0 | 0.37 |  |
|  |  | gomito | 0.53 | 0.00 | 0.00 | +0.53 | 0.02 | 0 | 0.12 |  |
| ->home | 2.02 | base | 0.80 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.00 | 3.8 |
|  |  | spalla | 1.88 | 0.02 | 0.00 | -0.80 | 0.36 | 0 | 0.45 |  |
|  |  | gomito | 2.29 | 0.00 | 0.00 | -1.55 | 0.47 | 0 | 0.53 |  |

### 30 g + CAM v=1.0  (durata 13.6 s, vincoli max 4.3 µm)

| moto | durata s | servo | err inseg. max ° | overshoot ° | assest. s (±0.5°) | err finale ° | duty max | % saturo | |T| max kg·cm | err TCP max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| home->sbraccio | 1.46 | base | 3.21 | 0.02 | 0.04 | +1.01 | 0.69 | 0 | 0.79 | 9.8 |
|  |  | spalla | 1.94 | 0.00 | 0.00 | -1.66 | 0.37 | 0 | 0.72 |  |
|  |  | gomito | 1.16 | 0.00 | 0.00 | -1.07 | 0.18 | 0 | 0.45 |  |
| chiude | 0.74 | base | 0.99 | 0.00 | 0.00 | +0.82 | 0.13 | 0 | 0.08 | 5.1 |
|  |  | spalla | 1.67 | 0.00 | 0.00 | -1.67 | 0.31 | 0 | 0.69 |  |
|  |  | gomito | 1.07 | 0.00 | 0.00 | -1.07 | 0.15 | 0 | 0.33 |  |
| giro+indietro | 2.46 | base | 3.79 | 0.02 | 0.13 | -1.06 | 0.84 | 0 | 1.16 | 14.0 |
|  |  | spalla | 3.47 | 0.00 | 0.00 | +1.68 | 0.76 | 0 | 0.92 |  |
|  |  | gomito | 1.60 | 0.01 | 0.00 | -1.53 | 0.29 | 0 | 0.35 |  |
| giù davanti | 1.58 | base | 2.94 | 0.02 | 0.15 | +1.06 | 0.63 | 0 | 1.07 | 5.8 |
|  |  | spalla | 3.48 | 0.00 | 0.00 | -0.95 | 0.76 | 0 | 0.93 |  |
|  |  | gomito | 1.47 | 0.00 | 0.00 | +0.53 | 0.25 | 0 | 0.47 |  |
| apre | 0.74 | base | 1.04 | 0.00 | 0.00 | +0.81 | 0.15 | 0 | 0.11 | 2.7 |
|  |  | spalla | 0.95 | 0.00 | 0.00 | -0.95 | 0.13 | 0 | 0.37 |  |
|  |  | gomito | 0.53 | 0.00 | 0.00 | +0.53 | 0.02 | 0 | 0.12 |  |
| ->home | 1.24 | base | 0.81 | 0.00 | 0.00 | +0.79 | 0.09 | 0 | 0.01 | 4.4 |
|  |  | spalla | 2.01 | 0.05 | 0.00 | -0.80 | 0.39 | 0 | 0.47 |  |
|  |  | gomito | 2.79 | 0.00 | 0.00 | -1.55 | 0.60 | 0 | 0.60 |  |

### 2b. What-if sui limiti del planner (v=1.0, copia di config.h solo in build/)

| SG90 | limiti planner | tempo in moto s | err inseg. max b/sp/gom ° | duty max b/sp/gom | % saturo b/sp/gom | overshoot b/sp/gom ° | I picco A |
|---|---|---|---|---|---|---|---|
| 1.6 kg·cm | firmware 90°/s, 180°/s² | 8.2 | 3.8 / 3.6 / 2.9 | 0.85 / 0.79 / 0.63 | 0 / 0 / 0 | 0.02 / 0.04 / 0.01 | 2.12 |
| 1.6 kg·cm | 135°/s, 540°/s² | 5.6 | 6.2 / 4.5 / 3.6 | 1.00 / 1.00 / 0.79 | 6 / 0 / 0 | 0.07 / 0.03 / 0.02 | 2.31 |
| 1.6 kg·cm | 180°/s, 720°/s² | 4.8 | 7.3 / 5.3 / 4.2 | 1.00 / 1.00 / 0.94 | 12 / 2 / 0 | 0.20 / 0.13 / 0.05 | 2.41 |
| 1.6 kg·cm | 90°/s, 720°/s² | 6.8 | 6.1 / 4.3 / 3.0 | 1.00 / 0.96 / 0.65 | 5 / 0 / 0 | 0.25 / 0.02 / 0.03 | 2.38 |
| 1.2 kg·cm | firmware 90°/s, 180°/s² | 8.2 | 4.4 / 4.3 / 3.4 | 0.99 / 0.97 / 0.75 | 0 / 0 / 0 | 0.03 / 0.01 / 0.01 | 2.38 |
| 1.2 kg·cm | 135°/s, 540°/s² | 5.6 | 8.9 / 5.6 / 4.1 | 1.00 / 1.00 / 0.93 | 20 / 6 / 0 | 0.10 / 0.04 / 0.04 | 2.47 |
| 1.2 kg·cm | 180°/s, 720°/s² | 4.8 | 13.3 / 7.1 / 4.9 | 1.00 / 1.00 / 1.00 | 28 / 15 / 1 | 0.44 / 0.12 / 0.08 | 2.48 |
| 1.2 kg·cm | 90°/s, 720°/s² | 6.8 | 7.8 / 5.4 / 3.7 | 1.00 / 1.00 / 0.83 | 12 / 2 / 0 | 1.31 / 0.03 / 0.06 | 2.47 |

## 3. E-stop: PWM sganciato (servo liberi, motore aperto)

Tenuta 0.3 s, poi sgancio. L'evento è il primo tra: TCP sul tavolo, spalla o gomito 5° oltre il limite di giunto, th2−phi 5° oltre il vincolo (urto tra parti). Simulazione fino a 3 s.

| posa | contrappesi | carico | evento | t evento s | Δth2 / Δphi ° | ω spalla / gomito °/s | v TCP m/s |
|---|---|---|---|---|---|---|---|
| REACH | 4+2 piombi | 0 g | fine corsa spalla | 0.10 | -3.8 / -0.0 | -65 / -1 | 0.09 |
| REACH | 4+2 piombi | 50 g | fine corsa spalla | 0.05 | -2.7 / -0.4 | -120 / -9 | 0.18 |
| REACH | senza piombi | 0 g | fine corsa spalla | 0.07 | -3.5 / -1.5 | -94 / -47 | 0.19 |
| REACH | senza piombi | 50 g | fine corsa spalla | 0.05 | -2.6 / -1.9 | -110 / -79 | 0.26 |
| alto avanti th2=60 phi=40 | 4+2 piombi | 0 g | nessuno | > 3 | -2.5 / -0.2 | -1 / -0 | 0.00 |
| alto avanti th2=60 phi=40 | 4+2 piombi | 50 g | vincolo th2-phi | 0.17 | -10.1 / -5.3 | -122 / -61 | 0.25 |
| alto avanti th2=60 phi=40 | senza piombi | 0 g | vincolo th2-phi | 0.49 | -39.8 / -34.8 | -227 / -163 | 0.54 |
| alto avanti th2=60 phi=40 | senza piombi | 50 g | fine corsa spalla | 0.26 | -43.7 / -43.4 | -423 / -314 | 1.01 |
| HOME | 4+2 piombi | 0 g | nessuno | > 3 | +0.0 / +0.0 | +0 / +0 | 0.00 |
| HOME | 4+2 piombi | 50 g | nessuno | > 3 | -0.7 / -63.7 | +0 / -0 | 0.00 |
| HOME | senza piombi | 0 g | nessuno | > 3 | -0.7 / -47.3 | +0 / -3 | 0.00 |
| HOME | senza piombi | 50 g | fine corsa gomito | 0.25 | -18.2 / -73.0 | -245 / -474 | 0.42 |
| BACK | 4+2 piombi | 0 g | fine corsa spalla | 0.10 | +3.9 / +0.2 | +65 / -0 | 0.09 |
| BACK | 4+2 piombi | 50 g | vincolo th2-phi | 0.03 | +1.3 / +0.1 | +74 / -7 | 0.11 |
| BACK | senza piombi | 0 g | vincolo th2-phi | 0.05 | +2.2 / -0.2 | +83 / -5 | 0.12 |
| BACK | senza piombi | 50 g | vincolo th2-phi | 0.01 | +0.1 / -0.0 | +26 / -4 | 0.04 |
| basso avanti th2=40 phi=-50 | 4+2 piombi | 0 g | fine corsa spalla | 0.43 | -24.1 / -1.5 | -109 / +0 | 0.15 |
| basso avanti th2=40 phi=-50 | 4+2 piombi | 50 g | fine corsa spalla | 0.15 | -23.0 / -3.2 | -311 / -6 | 0.44 |
| basso avanti th2=40 phi=-50 | senza piombi | 0 g | fine corsa spalla | 0.22 | -23.8 / -5.2 | -227 / -22 | 0.33 |
| basso avanti th2=40 phi=-50 | senza piombi | 50 g | fine corsa spalla | 0.13 | -22.8 / -10.8 | -364 / -104 | 0.56 |

## 4. Sensibilità (REACH statico e sequenza a v=1.0)

| carico | variante | T statica sp/gom kg·cm | SF min | err statico sp/gom ° | duty statico sp/gom | err inseg. max b/sp/gom ° | % saturo b/sp/gom | overshoot b/sp/gom ° | I picco tot A |
|---|---|---|---|---|---|---|---|---|---|
| 50 g | nominale | +0.73 / +0.38 | 2.2 | 2.13 / 1.67 | 0.42 / 0.30 | 3.8 / 3.6 / 2.9 | 0 / 0 / 0 | 0.02 / 0.04 / 0.01 | 2.12 |
| 50 g | SG90 1.2 kg·cm | +0.73 / +0.38 | 1.6 | 2.42 / 1.99 | 0.49 / 0.38 | 4.4 / 4.3 / 3.4 | 0 / 0 / 0 | 0.03 / 0.01 / 0.01 | 2.38 |
| 50 g | attrito alto | +0.73 / +0.38 | 2.2 | 2.44 / 1.89 | 0.50 / 0.36 | 4.1 / 4.5 / 4.1 | 0 / 0 / 0 | 0.02 / 0.04 / 0.09 | 2.36 |
| 50 g | manovella 2 piombi | +0.73 / +0.53 | 2.2 | 2.21 / 1.98 | 0.44 / 0.38 | 3.8 / 3.6 / 3.3 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.18 |
| 50 g | manovella 0 piombi | +0.73 / +0.70 | 2.2 | 2.21 / 2.14 | 0.44 / 0.42 | 3.8 / 3.6 / 3.6 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.25 |
| 50 g | braccio 0 piombi | +0.84 / +0.38 | 1.9 | 2.41 / 1.67 | 0.49 / 0.30 | 3.8 / 3.8 / 2.9 | 0 / 0 / 0 | 0.02 / 0.03 / 0.01 | 2.16 |
| 50 g | gioco 2° + banda 8 µs | +0.73 / +0.38 | 2.2 | 2.40 / 1.94 | 0.42 / 0.30 | 4.1 / 3.9 / 3.2 | 0 / 0 / 0 | 0.02 / 0.03 / 0.01 | 2.11 |
| 50 g | anello morbido (100% a 8°) | +0.73 / +0.38 | 2.2 | 3.76 / 2.17 | 0.41 / 0.21 | 6.6 / 6.4 / 4.6 | 0 / 0 / 0 | 0.04 / 0.01 / 0.01 | 1.68 |
| 50 g | corona ingrassata μ 0.1 | +0.73 / +0.38 | 2.2 | 2.13 / 1.67 | 0.42 / 0.30 | 3.4 / 3.6 / 2.9 | 0 / 0 / 0 | 0.09 / 0.04 / 0.01 | 1.97 |
| 50 g | 1.2 kg·cm + attrito alto | +0.73 / +0.38 | 1.6 | 2.84 / 2.00 | 0.60 / 0.39 | 4.7 / 17.4 / 5.0 | 1 / 30 / 5 | 0.03 / 0.04 / 0.09 | 2.48 |
| 30 g + CAM | nominale | +0.68 / +0.33 | 2.4 | 2.00 / 1.50 | 0.39 / 0.26 | 3.8 / 3.5 / 2.8 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.08 |
| 30 g + CAM | SG90 1.2 kg·cm | +0.68 / +0.33 | 1.8 | 2.28 / 1.87 | 0.46 / 0.35 | 4.3 / 4.2 / 3.2 | 0 / 0 / 0 | 0.03 / 0.01 / 0.00 | 2.29 |
| 30 g + CAM | attrito alto | +0.68 / +0.33 | 2.4 | 2.35 / 1.78 | 0.47 / 0.33 | 4.1 / 4.4 / 4.0 | 0 / 0 / 0 | 0.02 / 0.21 / 0.08 | 2.31 |
| 30 g + CAM | manovella 2 piombi | +0.68 / +0.47 | 2.4 | 2.04 / 1.88 | 0.40 / 0.36 | 3.8 / 3.5 / 3.1 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.13 |
| 30 g + CAM | manovella 0 piombi | +0.68 / +0.64 | 2.4 | 2.06 / 2.00 | 0.40 / 0.39 | 3.8 / 3.5 / 3.5 | 0 / 0 / 0 | 0.02 / 0.05 / 0.01 | 2.20 |
| 30 g + CAM | braccio 0 piombi | +0.79 / +0.33 | 2.0 | 2.22 / 1.50 | 0.44 / 0.26 | 3.8 / 3.7 / 2.8 | 0 / 0 / 0 | 0.02 / 0.04 / 0.01 | 2.12 |
| 30 g + CAM | gioco 2° + banda 8 µs | +0.68 / +0.33 | 2.4 | 2.21 / 1.82 | 0.37 / 0.27 | 4.1 / 3.7 / 3.1 | 0 / 0 / 0 | 0.02 / 0.03 / 0.01 | 2.07 |
| 30 g + CAM | anello morbido (100% a 8°) | +0.68 / +0.33 | 2.4 | 3.62 / 2.05 | 0.40 / 0.20 | 6.5 / 6.1 / 4.3 | 0 / 0 / 0 | 0.04 / 0.01 / 0.00 | 1.61 |
| 30 g + CAM | corona ingrassata μ 0.1 | +0.68 / +0.33 | 2.4 | 2.00 / 1.50 | 0.39 / 0.26 | 3.5 / 3.5 / 2.8 | 0 / 0 / 0 | 0.09 / 0.05 / 0.01 | 1.93 |
| 30 g + CAM | 1.2 kg·cm + attrito alto | +0.68 / +0.33 | 1.8 | 2.58 / 2.00 | 0.53 / 0.39 | 4.6 / 8.0 / 4.8 | 0 / 19 / 3 | 0.03 / 0.04 / 0.09 | 2.44 |

Fattore v del comando nei casi peggiori (50 g, sequenza completa):

| variante | v | duty max b/sp/gom | % saturo b/sp/gom | err inseg. max b/sp/gom ° |
|---|---|---|---|---|
| SG90 1.2 kg·cm | 0.5 | 0.81 / 0.86 / 0.61 | 0 / 0 / 0 | 3.7 / 3.9 / 2.9 |
| SG90 1.2 kg·cm | 0.7 | 0.87 / 0.91 / 0.66 | 0 / 0 / 0 | 3.9 / 4.1 / 3.1 |
| SG90 1.2 kg·cm | 1.0 | 0.99 / 0.97 / 0.75 | 0 / 0 / 0 | 4.4 / 4.3 / 3.4 |
| attrito alto | 0.5 | 0.69 / 0.87 / 0.78 | 0 / 0 / 0 | 3.2 / 3.9 / 3.6 |
| attrito alto | 0.7 | 0.75 / 0.94 / 0.84 | 0 / 0 / 0 | 3.4 / 4.2 / 3.8 |
| attrito alto | 1.0 | 0.93 / 1.00 / 0.93 | 0 / 0 / 0 | 4.1 / 4.5 / 4.1 |
| 1.2 kg·cm + attrito alto | 0.5 | 0.88 / 1.00 / 0.96 | 0 / 6 / 0 | 4.0 / 5.0 / 4.3 |
| 1.2 kg·cm + attrito alto | 0.7 | 0.97 / 1.00 / 1.00 | 0 / 16 / 1 | 4.3 / 7.5 / 4.5 |
| 1.2 kg·cm + attrito alto | 1.0 | 1.00 / 1.00 / 1.00 | 1 / 30 / 5 | 4.7 / 17.4 / 5.0 |

## 5. Corrente

Sequenza 50 g, v=1.0, nominale (`current_profiles.csv`, 1 kHz). I = I_idle 10 mA + 0.74 A × |coppia elettromagnetica| / stallo.

| servo | picco A | media A | RMS A |
|---|---|---|---|
| base | 0.58 | 0.161 | 0.190 |
| spalla | 0.55 | 0.185 | 0.217 |
| gomito | 0.43 | 0.151 | 0.176 |
| pinza | 0.75 | 0.420 | 0.531 |
| totale | 2.12 | 0.917 | 1.020 |

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

Enable con il braccio a 30°/40°/40° da home (base/spalla/gomito): velocità di picco 396 / 417 / 534 °/s, corrente totale di picco 2.52 A per 113 ms sopra 1.5 A.
