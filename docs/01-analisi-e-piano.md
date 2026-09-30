# Analisi carichi, cinematica e scelte di progetto (rev. C)

Vincoli:
- solo gli SG90 180° già in casa;
- niente alimentatore industriale;
- contrappesi con i piombi da pesca già in casa (6 × 20 g, a oliva 22.2 × 13.7 mm);
- tutto in PLA sulla Anycubic Kobra S1 (250 × 250 × 250).

Numeri riproducibili:
- `python3 calc/torque.py` per le coppie, con assert sui punti di progetto;
- `cad/assembly.scad` per le collisioni, con ferramenta compresa.

## 1. Topologia

Con i servo in serie (servo gomito sul gomito), la spalla di un SG90 porta tutta la catena **più** il servo del gomito a leva piena, e va sotto SF 1.5 già con link da 80 mm.

Si usa quindi la **topologia parallela** (famiglia MeArm/EEZYbot):
- **Servo spalla e servo gomito sulla torretta**, coassiali, uno per guancia.
- **Parallelogramma di comando:** il gomito è mosso da manovella e biella motrice.
  - La manovella ha la stessa lunghezza della leva posteriore dell'avambraccio (20 mm).
  - La biella è lunga quanto il braccio (80 mm).
  - L'angolo del servo gomito è quindi l'angolo **assoluto** dell'avambraccio (phi).
- **Due parallelogrammi passivi di livellamento** tengono la pinza sempre orizzontale:
  - montante fisso G → biella 1 → triangolo al gomito;
  - triangolo al gomito → biella 2 → staffa del polso.
- **Lavoro virtuale:**
  - T_gomito = g·Σ mᵢ·dᵢ, con i momenti della catena dell'avambraccio attorno al gomito.
  - T_spalla = g·(m_braccio·d + M_catena·L1): la catena pesa sulla spalla solo come massa al gomito.
- **Contrappesi:**
  - Piombi sulla **coda della manovella** (arco di 6 sedi a r = 43 mm) e sulla **coda del braccio** (2 sedi a 30 mm).
  - Coda e segmento ruotano insieme, quindi la compensazione vale a ogni angolo.
  - La manovella gira sull'asse della torretta: il suo contrappeso non carica la spalla.

## 2. Giunti e geometria

| Giunto | Servo | Range | Riferimento a 1500 µs |
|---|---|---|---|
| J1 base (yaw) | SG90 in torre, sotto la torretta | −90 … 90° | braccio in avanti |
| J2 spalla (th2, assoluto) | SG90 guancia −Y | 20 … 160° | braccio verticale |
| J3 gomito (phi, assoluto) | SG90 guancia +Y, via manovella | −70 … 70° | avambraccio orizzontale |
| vincolo | — | 20 ≤ th2 − phi ≤ 150 | parallelogramma non degenere, ferramenta libera |
| J4 pinza | SG90 capovolto sulla pinza | 0 … 59 mm | 29.5 mm |

Dimensioni:
- L1 = L2 = 80 mm.
- TCP (centro delle dita) 42 mm avanti e 24 mm sotto il perno del polso.
- Sbraccio orizzontale **202 mm** dall'asse della spalla.
- Asse della spalla a 102 mm dal tavolo.
- Polso roll escluso: servirebbe un contrappeso che non c'è.

I limiti vengono dai piani delle parti lungo l'asse della spalla, compresi teste delle viti e dadi. Il controllo di `cad/assembly.scad` non trova collisioni su una griglia di pose che copre tutto il range, a pinza chiusa e aperta.

## 3. Coppie (SG90 = 1.6 kg·cm @4.8V dichiarati, obiettivo SF ≥ 2)

Masse dai volumi degli STL: PLA al 60% di riempimento effettivo, più servo e ferramenta.

| Configurazione | Payload | Gomito | Spalla |
|---|---|---|---|
| senza contrappeso, senza camera | 50 g | SF 1.4 ✗ | — |
| **4 piombi manovella + 2 braccio, senza camera** | **50 g** | **SF 1.9** | **SF 2.0** |
| stessa, senza camera | 30 g | SF 2.8 | SF 2.5 |
| **4 + 2 piombi, con ESP32-CAM** | **30 g** | **SF 2.1** | **SF 2.1** |
| 6 + 2 piombi, con ESP32-CAM | 50 g | SF 1.8 | SF 1.7 (non consigliato) |

Punti di progetto: **50 g senza camera, 30 g con la camera**.

Base, pinza e corrente:
- **Base:** 0.18 kg·cm di inerzia a 10 rad/s² più 0.45 kg·cm di attrito della corona PLA su PLA, **SF 2.5**. Con il grasso l'attrito cala.
- **Pinza:**
  - pignone m1 z32 (r = 16 mm): la corsa di 59 mm richiede **106°** di servo;
  - forza per dito 4.9 N contro 1.6 N richiesti (50 g, μ 0.3, SF 2).
- **Corrente:** stallo cumulativo 4 × 0.75 A = 3 A. Caricatore USB 5V ≥ 3A.

## 4. Scelte che contano

- **L'albero del servo trasmette solo coppia.** I carichi radiali restano sotto circa 1.5 N, la classe dei bracci MeArm.
  I perni sono viti M3 con autobloccanti "a scorrimento" e distanziali stampati.
- **Ferramenta nei piani giusti.** Dove una testa o un dado finirebbe nel piano di un'altra biella si usano dadi incassati: A nella biella motrice, B nella piastra R, P1 e U nel triangolo.
  Il controllo collisioni modella ogni testa, dado e distanziale.
- **Pinza senza pareti.** Le cremagliere scorrono su code di rondine, lo stesso profilo del provino, che le guidano in tutto tranne lo scorrimento.
  È l'alleggerimento che ha portato la pinza da ~60 a ~40 g.
- **PLA:**
  - è più rigido del PETG (E 3.5 contro 2.1 GPa);
  - è più preciso su ingranaggi e sedi;
  - con tensioni sotto 2 MPa lo scorrimento viscoso non conta;
  - gli incastri a scatto sono dimensionati per una deformazione ≤ 2%.
- **Sicurezza sul device.** Il firmware applica limiti, vincolo, clamp dei µs, rampe, watchdog ed E-stop, qualunque cosa mandi il browser.

## 5. Elettronica

Vedi [02-cablaggio.md](02-cablaggio.md):
- pilotaggio diretto dai GPIO dell'ESP32 (33, 25, 26, 27, con LEDC a 50 Hz);
- 5V dei servo dal caricatore USB tramite WAGO;
- logica su una porta separata, con massa comune;
- pull-down da 10 kΩ sui segnali.

## 6. Software

Vedi [03-protocollo.md](03-protocollo.md): frame, FK, IK in forma chiusa, taratura, WebSocket.
- **Firmware:** PlatformIO con arduino-esp32 2.0.17, planner trapezoidale sincronizzato, test nativi.
- **Web app:** Vite + Three.js, digital twin con gli STL reali, FK, IK con gizmo, waypoint e sequenze, taratura, modalità simulazione.
