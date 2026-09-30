# BRACCIO — Step 1: analisi carichi, cinematica, elettronica (rev. B: solo SG90)

Vincoli rev. B:
- solo gli SG90 180° già in casa;
- niente alimentatore industriale;
- tutto stampato in PLA sulla Anycubic Kobra S1 Combo (piano 250×250×250 mm).

Numeri riproducibili: `python3 calc/torque.py`. Ogni verifica ha un assert.

## 1. Perché la topologia cambia

Con i servo in serie (servo del gomito montato sul gomito), la spalla di un SG90 porta tutta la catena **più** il servo del gomito,
a leva piena. Il risultato è un SF < 1.5 già con link da 80 mm.

Si passa quindi alla **topologia parallela** (famiglia MeArm/EEZYbot):
- **Servo spalla e servo gomito stanno entrambi sulla torretta**, coassiali all'asse della spalla, uno per lato.
- **Il gomito è mosso da manovella e biella a parallelogramma:** manovella lunga quanto la leva posteriore dell'avambraccio, biella lunga L1.
  L'angolo del servo gomito è quindi l'angolo **assoluto** dell'avambraccio.
- **Lavoro virtuale:**
  - T_gomito = g·Σ mᵢ·dᵢ, dove i momenti sono quelli della catena dell'avambraccio attorno al gomito.
  - T_spalla = g·(m_braccio·L1/2 + M_catena·L1): la catena pesa sulla spalla solo come massa concentrata al gomito.
- **Secondo parallelogramma passivo (livellamento):** tiene la pinza sempre orizzontale senza un servo al polso.
- **Contrappesi (monete da 1€, 7.5 g):**
  - Stanno sulla coda della manovella gomito e sulla coda del braccio.
  - Coda e segmento ruotano insieme, quindi la compensazione vale a **ogni** angolo, non solo in un punto.
  - La manovella gira sull'asse della torretta, quindi il suo contrappeso non carica la spalla.
- **Singolarità:** l'angolo relativo braccio/avambraccio va tenuto in [20°, 160°], perché il parallelogramma non deve appiattirsi. Il limite si applica nel firmware.

## 2. Cinematica

| Giunto | Servo | Range | Note |
|---|---|---|---|
| J1 base yaw | SG90 | 0–180° | la torretta poggia su un anello di scorrimento stampato. L'albero del servo trasmette solo coppia |
| J2 spalla | SG90 | ~20–160° | |
| J3 gomito (angolo assoluto dell'avambraccio) | SG90 | vincolo: 20° ≤ J2−J3 ≤ 160° | |
| J4 pinza | SG90 | 0–59 mm | cremagliera simmetrica, pignone m1 z20 |
| (polso roll) | — | — | **escluso:** richiederebbe 148 g di contrappeso (vedi calcolo). Restano 4 SG90 liberi di scorta |

L1 = 80 mm, L2 = 80 mm, L3 = 45 mm (dal perno del polso al centro delle dita). Sbraccio orizzontale dall'asse della spalla: **205 mm**.
Pinza sempre orizzontale → la posa è XYZ + apertura. L'IK è in forma chiusa:
- θ1 = atan2(y, x);
- il punto polso è il TCP arretrato di L3 in orizzontale;
- θ2 e l'angolo assoluto dell'avambraccio si ricavano con il teorema del coseno.

## 3. Verifica coppie (SG90 = 1.6 kg·cm @4.8V dichiarati, SF ≥ 2)

| Payload | Gomito senza contrappeso | Spalla senza contrappeso | Con contrappeso montato (10 monete gomito @40 mm, 4 spalla @30 mm) |
|---|---|---|---|
| 0 g | 0.48 kg·cm, SF 3.3 | 0.50, SF 3.2 | ✓ |
| 30 g | 0.86, **SF 1.9** | 0.74, SF 2.2 | ✓ SF 2.9 / 2.5 |
| 50 g | 1.11, **SF 1.4** | 0.90, SF 1.8 | ✓ SF 2.0 / 2.0 |

- **30 g:** si lavora anche senza monete.
- **50 g:** 5 + 5 monete sulla manovella del gomito, a 40 mm, in due coppe (una per faccia) chiuse con 2 viti M3x30.
  Il baricentro resta sul piano della piastra. Sulla coda del braccio vanno 4 monete, bloccate da vite M3 e rondella.
- Le monete si possono togliere o aggiungere in ogni momento per regolare il contrappeso sul payload reale.
- **Base:** 0.19 kg·cm inerziali a 10 rad/s² (SF 9). Nessuna coppia gravitazionale.
- **Pinza:**
  - Pignone modulo 1, z20 (r = 10 mm). Su 170° utili la corsa è **59 mm**.
  - Forza per dito 7.8 N contro 1.6 N richiesti (50 g, μ 0.3, SF 2).
- I carichi radiali sugli alberi SG90 restano sotto ~1.5 N, la stessa classe dei bracci MeArm. Al gomito si usa un perno M3 con dado autobloccante.

## 4. Elettronica (zero saldature, niente componenti industriali)

Niente PCA9685: i 4 SG90 sono pilotati direttamente dal PWM hardware (LEDC) dell'ESP32.
- **Pin:** GPIO33 base, 25 spalla, 26 gomito, 27 pinza.
- **Alimentazione dei servo:** caricatore USB 5V ≥ 3A → bus WAGO → servo. La logica è su una porta USB separata, con massa comune.
- **Schema, pinout, protezioni e checklist:** in [02-cablaggio.md](02-cablaggio.md).

Stallo cumulativo 4 × 0.75 A = **3 A** (caso peggiore teorico). In moto con rampe si stima ≤ 1.2 A.
Taratura per giunto (offset, min, max, µs/°, verso) salvata in NVS dell'ESP32.

## 5. Materiale

**PLA** per tutto:
- È più rigido del PETG (E ≈ 3.5 contro 2.1 GPa): meno flessione dei link.
- Ha migliore precisione dimensionale, che conta per ingranaggi e sedi.
- Le tensioni sono < 2 MPa, quindi lo scorrimento viscoso (creep) non è un problema.
- Gli incastri a scatto sono dimensionati per una deformazione ≤ 2%: il PLA è fragile oltre. Il provino li verifica.
- Parametri consigliati: ugello 0.4, layer 0.2, 3 perimetri, gyroid al 20%, pareti delle sedi servo ≥ 1.6 mm.

## 6. BOM (rev. B)

| Articolo | Qtà | Stato |
|---|---|---|
| SG90 180° | 4 (+4 scorta) | in casa |
| ESP32 DevKit V1 | 1 | |
| Resistenze 10 kΩ (pull-down segnali) | 4 | |
| Caricatore USB 5V ≥3A + 2 cavi USB | 1 | in casa, di solito |
| Elettrolitico 1000–2200 µF ≥10V | 1 | |
| WAGO 221-415 (5 poli) | 4 | 2 × +5V, 2 × GND |
| Breadboard + Dupont | 1 | |
| ESP32-CAM + ESP32-CAM-MB | 1 | futuro |
| Viti M3 (8–30 mm, di cui 3× M3x30), dadi M3 e autobloccanti, rondelle | kit | |
| Monete da 1€ come contrappeso | 14 | |
| PLA | ~250 g | |

## 7. Architettura software (invariata)

- **Browser (Vite + Three.js):** twin, FK, IK, waypoint. Comunica con l'ESP32 via WebSocket in JSON a 20 Hz.
- **Firmware ESP32:**
  - La **sicurezza sta sul device**: limiti, vincolo del parallelogramma, rampe trapezoidali, watchdog di 1 s, E-stop tramite OE.
  - La build finale della web app viene servita dalla LittleFS dell'ESP32.
- **Il twin mostra lo stato comandato**, perché gli SG90 non hanno retroazione.

## 8. Roadmap

1. ✅ Analisi (questo documento).
2. **CAD:**
   - ✅ `test/tolerance_coupon.scad` (da stampare per primo).
   - ✅ `upper_arm.scad`, `crank.scad` (con coppe e distanziale), `turret.scad`.
   - ✅ `assembly.scad` con la verifica delle collisioni su 12 pose.
   - Da fare: base con vano elettronica, bielle, avambraccio, livellamento, pinza, culla ESP32-CAM.
3. ✅ Schema di cablaggio ([02-cablaggio.md](02-cablaggio.md)). Da fare: firmware.
4. Web app.

### Piani lungo l'asse della spalla (Y, mm; 0 = mezzeria torretta)

| Elemento | Piano Y |
|---|---|
| guancia sinistra (servo spalla fuori) | −35.5 … −32.5 |
| squadretta spalla → braccio | −23.4 … −17.4 (coda monete fino a −12.5) |
| biella livellamento | −12.0 … −8.0 |
| montante fisso G | −7.5 … −4.5 |
| biella motrice | −3.5 … 0.5 |
| coppa monete interna | 1.35 … 14.4 |
| piastra manovella + mozzo | 14.4 … 23.4 |
| coppa monete lato guancia | 18.4 … 31.45 |
| guancia destra (servo gomito fuori) | 32.5 … 35.5 |

Asse spalla a 60 mm dalla faccia inferiore del pavimento. Verifica: `openscad -D check=1 -D th2=.. -D phi=.. assembly.scad` → deve risultare vuoto.
