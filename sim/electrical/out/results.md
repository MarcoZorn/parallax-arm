### dt

| passo | I picco [A] | V servo min [V] | 3V3 min [V] |
|---|---|---|---|
| 50 us | 2.435 | 3.688 | 2.945 |
| 20 us | 2.436 | 3.684 | 2.943 |

### S1

| caso | I picco caricatore [A] | V servo min 1ms (istant.) [V] | V WAGO min [V] | 3V3 min [V] | offset massa max/min [V] | livello alto visto dal servo min [V] | I jumper massa max [A] | trip | ESITO |
|---|---|---|---|---|---|---|---|---|---|
| consigliato, tutti insieme | 3.20 | 4.33 (4.29) | 4.52 | 3.03 | +0.16/-0.03 | 2.93 | 0.43 | 0 | OK |
| consigliato, sfalsato 200 ms | 1.83 | 4.52 (4.46) | 4.81 | 3.22 | +0.17/-0.03 | 3.13 | 0.43 | 0 | OK |
| migliore, tutti insieme | 3.14 | 4.27 (4.22) | 4.45 | 3.02 | +0.16/-0.03 | 2.92 | 0.42 | 0 | riserva |
| migliore, sfalsato 200 ms | 1.80 | 4.47 (4.39) | 4.76 | 3.19 | +0.17/-0.03 | 3.13 | 0.41 | 0 | OK |
| nominale, tutti insieme | 2.68 | 3.94 (3.91) | 4.14 | 2.97 | +0.19/-0.02 | 2.84 | 0.77 | 0 | KO |
| nominale, sfalsato 200 ms | 1.76 | 4.23 (4.14) | 4.54 | 3.08 | +0.20/-0.02 | 3.00 | 0.48 | 0 | riserva |
| peggiore, tutti insieme | 2.44 | 3.69 (3.68) | 3.91 | 2.94 | +0.24/-0.03 | 2.77 | 0.85 | 0 | KO |
| peggiore, sfalsato 200 ms | 1.63 | 4.06 (3.95) | 4.40 | 3.01 | +0.24/-0.03 | 2.90 | 0.54 | 0 | riserva |

### S1_stagger

| cablaggio | sfalsamento [ms] | I picco [A] | V servo min [V] | 3V3 min [V] | enable completo dopo [ms] |
|---|---|---|---|---|---|
| nominale | 0 | 2.68 | 3.94 | 2.97 | 300 |
| nominale | 100 | 2.06 | 4.10 | 3.06 | 600 |
| nominale | 150 | 1.98 | 4.27 | 3.07 | 750 |
| nominale | 200 | 1.76 | 4.23 | 3.08 | 900 |
| nominale | 250 | 1.90 | 4.24 | 3.09 | 1050 |
| nominale | 300 | 1.76 | 4.33 | 3.08 | 1200 |
| peggiore | 0 | 2.44 | 3.69 | 2.94 | 300 |
| peggiore | 100 | 1.84 | 3.90 | 3.01 | 600 |
| peggiore | 150 | 1.76 | 3.97 | 3.01 | 750 |
| peggiore | 200 | 1.63 | 4.06 | 3.01 | 900 |
| peggiore | 250 | 1.83 | 3.88 | 3.02 | 1050 |
| peggiore | 300 | 1.61 | 4.10 | 3.00 | 1200 |

### S1_hotplug

| cablaggio | C [uF] | regolatore | I spunto picco [A] | 3V3 min [V] | ESITO |
|---|---|---|---|---|---|
| nominale | 470 | condiviso | 8.1 | 1.74 | KO |
| nominale | 1000 | condiviso | 9.0 | 1.22 | KO |
| nominale | 2200 | condiviso | 9.4 | 0.64 | KO |
| peggiore | 1000 | condiviso | 7.1 | 1.48 | KO |
| nominale | 1000 | separato | 9.1 | 2.72 | riserva |

### S2

| caso | I picco caricatore [A] | V servo min 1ms (istant.) [V] | V WAGO min [V] | 3V3 min [V] | offset massa max/min [V] | livello alto visto dal servo min [V] | I jumper massa max [A] | trip | ESITO |
|---|---|---|---|---|---|---|---|---|---|
| consigliato | 2.77 | 4.46 (4.33) | 4.64 | 3.09 | +0.12/-0.03 | 2.98 | 0.40 | 0 | OK |
| nominale | 2.31 | 4.12 (4.01) | 4.31 | 3.05 | +0.16/-0.02 | 2.91 | 0.66 | 0 | riserva |
| nominale, v=0.5 | 2.24 | 4.12 (4.00) | 4.32 | 3.03 | +0.15/-0.02 | 2.90 | 0.62 | 0 | riserva |
| peggiore | 2.09 | 3.92 (3.80) | 4.14 | 3.05 | +0.20/-0.02 | 2.87 | 0.72 | 0 | KO |
| peggiore, 2A | 2.09 | 3.92 (3.80) | 4.14 | 3.05 | +0.20/-0.02 | 2.87 | 0.72 | 0 | KO |
| nominale, senza C | 2.66 | 4.01 (3.71) | 4.20 | 2.80 | +0.16/-0.02 | 2.68 | 0.73 | 0 | riserva |
| nominale, senza massa comune | 2.22 | 4.06 (3.96) | 4.24 | 3.07 | +0.44/-0.11 | 2.86 | 0.00 | 0 | riserva |
| peggiore, senza massa comune | 1.96 | 3.82 (3.69) | 4.03 | 3.01 | +0.59/-0.12 | 2.71 | 0.00 | 0 | KO |
| nominale, profili sim/dynamics/current_profiles.csv | 2.43 | 4.10 (4.09) | 4.33 | 3.00 | +0.17/-0.00 | 2.89 | 0.65 | 0 | riserva |
| peggiore, profili sim/dynamics/current_profiles.csv | 2.39 | 3.75 (3.74) | 4.04 | 2.93 | +0.22/-0.00 | 2.78 | 0.78 | 0 | KO |

### S2_corr

| caso | I media caricatore [A] | I rms per servo [A] | I picco per servo [A] |
|---|---|---|---|
| consigliato | 0.81 | 0.42 / 0.34 / 0.36 / 0.22 | 0.77 / 0.84 / 0.84 / 0.76 |
| nominale | 0.81 | 0.41 / 0.33 / 0.35 / 0.21 | 0.75 / 0.82 / 0.81 / 0.73 |
| nominale, v=0.5 | 0.79 | 0.41 / 0.32 / 0.37 / 0.19 | 0.75 / 0.82 / 0.79 / 0.74 |
| peggiore | 0.81 | 0.40 / 0.33 / 0.35 / 0.21 | 0.74 / 0.81 / 0.80 / 0.72 |
| peggiore, 2A | 0.81 | 0.40 / 0.33 / 0.35 / 0.21 | 0.74 / 0.81 / 0.80 / 0.72 |
| nominale, senza C | 0.81 | 0.41 / 0.33 / 0.35 / 0.21 | 0.75 / 0.80 / 0.80 / 0.72 |
| nominale, senza massa comune | 0.81 | 0.41 / 0.33 / 0.35 / 0.21 | 0.75 / 0.82 / 0.81 / 0.73 |
| peggiore, senza massa comune | 0.81 | 0.40 / 0.32 / 0.34 / 0.21 | 0.74 / 0.81 / 0.80 / 0.72 |

### S3

| caso | duty driver | I media [A] | P iniziale [W] | forza/dito [N] | T avvolg. 60 s [°C] | T avvolg. regime [°C] | t a 80 °C [s] | t a 120 °C [s] | ESITO |
|---|---|---|---|---|---|---|---|---|---|
| comando 0 mm (45° oltre il contatto) | 1.00 | 0.70 | 3.04 | 4.8 | 84 | 141 | 44 | 285 | KO |
| comando 3° oltre il contatto | 0.28 | 0.19 | 1.04 | 1.5 | 48 | 73 | mai | mai | riserva |
| comando 2° oltre il contatto | 0.14 | 0.09 | 0.55 | 0.7 | 37 | 52 | mai | mai | OK |

### S4

| caso | I picco caricatore [A] | V servo min 1ms (istant.) [V] | V WAGO min [V] | 3V3 min [V] | offset massa max/min [V] | livello alto visto dal servo min [V] | I jumper massa max [A] | trip | ESITO |
|---|---|---|---|---|---|---|---|---|---|
| 3A, nominale | 2.91 | 3.99 (3.98) | 4.19 | 3.11 | +0.16/-0.01 | 2.96 | 0.80 | 0 | KO |
| 3A, peggiore | 2.71 | 3.67 (3.67) | 3.90 | 3.03 | +0.21/-0.01 | 2.84 | 0.90 | 0 | KO |
| 3A, migliore | 3.20 | 4.38 (4.36) | 4.57 | 3.25 | +0.12/-0.01 | 3.14 | 0.43 | 0 | OK |
| 3A, consigliato | 3.26 | 4.46 (4.44) | 4.65 | 3.28 | +0.12/-0.02 | 3.18 | 0.29 | 0 | OK |
| 2A, nominale | 2.33 | 3.22 (3.21) | 3.38 | 2.20 | +0.15/-0.01 | 2.07 | 0.66 | 0 | KO |
| 2A, peggiore | 2.34 | 3.15 (3.13) | 3.34 | 2.34 | +0.20/-0.01 | 2.18 | 0.78 | 0 | KO |
| 3A, peggiore, regolatori separati | 2.40 | 3.69 (3.69) | 3.92 | 3.11 | +0.21/-0.01 | 2.92 | 0.88 | 0 | KO |

### S4_cavi

| caso | I per servo [A] | caduta jumper+contatti+cavetto servo, A/R [V] | P per jumper 26AWG [mW] | P per contatto [mW] | dT jumper [K] | I cavo B [A] | caduta cavo B A/R [V] | P cavo B [W] | dT cavo B [K] | I massa via ESP32 [A] |
|---|---|---|---|---|---|---|---|---|---|---|
| 3A, nominale | 0.64 | 0.20 | 11 | 8 | 1.1 | 2.58 | 0.90 | 1.78 | 8 | 0.77 |
| 3A, peggiore | 0.59 | 0.23 | 15 | 11 | 1.5 | 2.38 | 1.30 | 2.41 | 11 | 0.87 |
| 3A, migliore | 0.71 | 0.19 | 14 | 5 | 1.4 | 2.85 | 0.35 | 0.68 | 6 | 0.40 |
| 3A, consigliato | 0.73 | 0.19 | 14 | 5 | 1.4 | 2.91 | 0.24 | 0.36 | 4 | 0.27 |
| 2A, nominale | 0.52 | 0.16 | 7 | 6 | 0.8 | 2.10 | 0.73 | 1.18 | 5 | 0.62 |
| 2A, peggiore | 0.52 | 0.20 | 12 | 8 | 1.2 | 2.09 | 1.14 | 1.87 | 8 | 0.76 |
| 3A, peggiore, regolatori separati | 0.59 | 0.23 | 15 | 11 | 1.5 | 2.38 | 1.30 | 2.41 | 11 | 0.87 |

### S5

| caso | I picco caricatore [A] | V servo min 1ms (istant.) [V] | V WAGO min [V] | 3V3 min [V] | offset massa max/min [V] | livello alto visto dal servo min [V] | I jumper massa max [A] | trip | ESITO |
|---|---|---|---|---|---|---|---|---|---|
| 2A, nominale, enable tutti insieme | 2.36 | 3.59 (3.58) | 3.76 | 2.83 | +0.19/-0.02 | 2.70 | 0.64 | 0 | KO |
| 2A, peggiore, enable tutti insieme | 2.27 | 3.52 (3.52) | 3.73 | 2.88 | +0.23/-0.03 | 2.71 | 0.78 | 0 | KO |
| 2A, nominale, enable sfalsato 200 ms | 1.80 | 4.19 (4.09) | 4.50 | 3.02 | +0.19/-0.02 | 2.94 | 0.49 | 0 | riserva |
| 2A, peggiore, enable sfalsato 200 ms | 1.60 | 4.05 (3.93) | 4.38 | 2.96 | +0.24/-0.03 | 2.84 | 0.53 | 0 | riserva |

### S6

| C [uF] | V servo min 1ms [V] | V servo min istant. [V] | ripple WAGO pk-pk [V] | I picco caricatore [A] | 3V3 min [V] |
|---|---|---|---|---|---|
| 0 | 3.54 | 3.39 | 1.49 | 2.63 | 2.68 |
| 100 | 3.54 | 3.40 | 1.44 | 2.64 | 2.70 |
| 470 | 3.60 | 3.55 | 1.21 | 2.65 | 2.84 |
| 1000 | 3.69 | 3.68 | 1.04 | 2.44 | 2.94 |
| 2200 | 3.77 | 3.77 | 0.93 | 2.34 | 3.08 |
| 4700 | 3.84 | 3.84 | 0.86 | 2.22 | 3.16 |

