# BRACCIO — Cinematica, taratura e protocollo (contratto firmware ↔ web app)

Unica fonte delle quote meccaniche: `cad/params.scad`. I numeri qui sotto ne sono una copia.
Se cambiano là, vanno aggiornati qui, in `firmware/src/config.h` e in `web/src/robot.js`.

## 1. Giunti (unità di giunto)

| # | Nome | Simbolo | Unità | Limiti default | Riferimento (q_ref → 1500 µs) |
|---|---|---|---|---|---|
| 0 | base (yaw) | q1 | ° | −90 … 90 | 0 (braccio in avanti, +X) |
| 1 | spalla | th2 | ° assoluti dall'orizzontale | 20 … 160 | 90 (braccio verticale) |
| 2 | gomito | phi | ° assoluti dall'orizzontale (angolo avambraccio) | −75 … 75 | 0 (avambraccio orizzontale) |
| 3 | pinza | g | mm di apertura | 0 … 59 | 29.5 |

**Vincolo del parallelogramma** (in aggiunta ai limiti): `20 ≤ th2 − phi ≤ 160`.
Un target fuori vincolo **viene rifiutato** (messaggio `err`), mai "aggiustato" in silenzio.

Il servo del gomito sta sulla torretta e muove la manovella. L'angolo della manovella è psi = phi + 180,
quindi **il servo gomito comanda direttamente phi**: la mappatura resta lineare come per gli altri giunti.

## 2. Frame e cinematica diretta (mm, gradi)

Parametri: `base_h = 40` (tavolo → faccia inferiore torretta), `sh_h = 62` (→ asse spalla), `L1 = 80`, `L2 = 80`,
`L3 = 45` (perno polso → centro dita, orizzontale), `tcp_dz = −10` (quota delle dita rispetto al perno polso),
`crank_r = 20`, `lev_r = 20`, `lev2_r = 20`.

- Mondo: origine sul tavolo nell'asse di yaw, **Z in alto**, X in avanti con q1 = 0.
- Frame yaw: `Tz(base_h) · Rz(q1)`.
- Nel frame yaw:
  - `O = (0, 0, sh_h)` è l'asse della spalla (lungo Y);
  - `u(a) = (cos a, 0, sin a)`;
  - `E = O + L1·u(th2)` è il gomito;
  - `W = E + L2·u(phi)` è il perno del polso.
- **TCP** = `W + (L3, 0, tcp_dz)`: la pinza è livellata e sempre orizzontale. Nel mondo:
  ```
  r = L1 cos th2 + L2 cos phi + L3
  x = r cos q1,  y = r sin q1,  z = base_h + sh_h + L1 sin th2 + L2 sin phi + tcp_dz
  ```

### Frame delle parti (per il digital twin)

Ogni parte STL è modellata in un frame locale. Il posizionamento segue la semantica di OpenSCAD:
`P(p, a) = T(p) · Ry(−a) · Rx(−90)`, dove `Ry(b)` è la rotazione destrorsa attorno a Y.
Così la X locale punta nella direzione `u(a)` e la Z locale va su +Y del mondo.
`y` è il piano della parte lungo l'asse della spalla, letto da `rig.json`. `psi = phi + 180`.

| Parte | Frame | Trasformazione |
|---|---|---|
| base | mondo | identità |
| turret | yaw | identità |
| upper_arm | yaw | `P(O + (0,y,0), th2)` |
| crank | yaw | `P(O + (0,y,0), psi)` |
| drive_rod | yaw | `P(O + crank_r·u(psi) + (0,y,0), th2)` |
| lev_rod | yaw | `P(O + lev_r·u(180) + (0,y,0), th2)` (perno fisso G sulla torretta) |
| forearm | yaw | `P(E + (0,y,0), phi)` |
| lev_link | yaw | `P(E + (0,y,0), 0)` (triangolo al gomito: orientamento costante) |
| lev_rod2 | yaw | `P(E + lev2_r·u(90) + (0,y,0), phi)` |
| wrist | yaw | `P(W + (0,y,0), 0)` (corpo pinza, livellato) |
| jaw_l / jaw_r | wrist | traslazione lungo la Z locale di `+g/2` / `−g/2` |

`web/public/models/rig.json` (lo genera il CAD):

```json
{ "params": { "base_h": 40, "sh_h": 62, "L1": 80, "L2": 80, "L3": 45, "tcp_dz": -10,
              "crank_r": 20, "lev_r": 20, "lev2_r": 20 },
  "parts": [ { "name": "upper_arm", "file": "upper_arm.stl", "y": -23.4, "color": "#e8e8e8" } ] }
```

Una parte senza `file` o con file mancante viene disegnata come segnaposto (box) nello stesso frame.

## 3. Cinematica inversa (forma chiusa)

Input: TCP `(x, y, z)` nel mondo. Output: `q1, th2, phi`, con la configurazione a gomito alto.

```
q1  = atan2(y, x)
r   = hypot(x, y) − L3
zz  = z − base_h − sh_h − tcp_dz
c   = (r² + zz² − L1² − L2²) / (2·L1·L2)        // = cos(th2 − phi)
se |c| > 1 → irraggiungibile
e   = acos(c)                                    // e = th2 − phi, in [0, 180]
th2 = atan2(zz, r) + atan2(L2·sin e, L1 + L2·cos e)
phi = th2 − e
```

La soluzione va poi validata contro i limiti e il vincolo. Se non passa, l'UI la segnala e non manda nulla.
Test obbligatorio: FK(IK(p)) = p entro 0.01 mm su una griglia di punti raggiungibili, e IK(FK(q)) = q.

## 4. Taratura (per giunto, salvata in NVS dell'ESP32)

```
us = ref_us + k · (q − q_ref)          clamp finale del segnale a [500, 2500] µs
```

| Campo | Significato | Default J0 / J1 / J2 / J3 |
|---|---|---|
| `ref_us` | impulso al riferimento | 1500 / 1500 / 1500 / 1500 |
| `k` | µs per unità, il **segno** dà il verso | 11.11 / 11.11 / 11.11 / 31.83 |
| `q_ref` | unità di giunto al riferimento | 0 / 90 / 0 / 29.5 |
| `min`, `max` | limiti di giunto | vedi §1 |

- SG90: 500–2500 µs corrispondono a 180°, cioè 11.11 µs/°.
- Pinza: pignone con r = 10 mm, apertura = 2·r·Δθ, quindi 1 mm di apertura = 2.865° = 31.83 µs.

**Procedura di taratura (UI):**
1. `raw` porta il servo a un impulso esplicito.
2. Si monta la squadretta con il giunto nella posa di riferimento, oppure si regola l'impulso finché il giunto è nella posa di riferimento, e si salva `ref_us`.
3. Si porta il giunto a un secondo angolo noto per ricavare `k` (e il segno).
4. Si verificano i limiti.

## 5. Moto (firmware)

- Loop di controllo a 50 Hz, uno per frame servo.
- Profilo **trapezoidale sincronizzato**: tutti i giunti partono e arrivano insieme, scalati sul giunto più lento.
- Limiti: `vmax` 90 °/s (pinza 60 mm/s), `amax` 180 °/s² (pinza 120 mm/s²), moltiplicati per il fattore `v` ∈ (0, 1] del comando.
- Un nuovo `move` durante il moto riparte dalla posizione e velocità correnti. Il nuovo profilo può partire da velocità non nulla; in alternativa si ferma e riparte, purché il risultato sia senza scatti.
- **La sicurezza sta sul device:** limiti, vincolo del parallelogramma e clamp dei µs sono applicati sempre, qualunque cosa mandi il browser.
- Boot:
  - PWM **non** agganciato: servo senza coppia, linee tenute basse dai pull-down.
  - `enable` aggancia il PWM alla posa `home` salvata in NVS (default `[0, 90, 0, 30]`). Il braccio va lasciato vicino a `home` prima di spegnere.
- Watchdog: se l'ultimo client WebSocket si disconnette durante un moto → `stop` (decelera e tiene la posizione).
- `estop`: sgancia subito il PWM (servo liberi) e mette `enabled = false`.

## 6. Rete

- WiFi:
  - prova la rete di casa per 10 s, con credenziali in `firmware/include/secrets.h` (non versionato; esiste `secrets.example.h`);
  - se fallisce, crea l'**AP `BRACCIO`** con password `braccio-arm`, IP 192.168.4.1.
- mDNS: `braccio.local`.
- HTTP porta 80:
  - `GET /` serve la web app da LittleFS, con file `.gz` precompressi;
  - `GET /api/info` risponde `{fw, ip, mode}`.
- WebSocket su `ws://<host>/ws`, messaggi JSON di testo.

### Browser → ESP32

| Messaggio | Effetto |
|---|---|
| `{"t":"move","q":[q1,th2,phi,g],"v":0.5}` | moto sincronizzato verso il target (validato) |
| `{"t":"stop"}` | decelera e tiene la posizione |
| `{"t":"estop"}` | PWM sganciato subito |
| `{"t":"enable"}` | aggancia il PWM alla posa corrente o `home` |
| `{"t":"raw","j":1,"us":1500}` | taratura: impulso diretto a un giunto (clamp 500–2500), solo se enabled |
| `{"t":"cal_get"}` | risponde `cal` |
| `{"t":"cal_set","cal":[{ref_us,k,q_ref,min,max}×4]}` | aggiorna la taratura in RAM |
| `{"t":"cal_save"}` | salva la taratura in NVS |
| `{"t":"home_set"}` | salva la posa corrente come `home` |

### ESP32 → browser

| Messaggio | Quando |
|---|---|
| `{"t":"state","q":[..4],"target":[..4],"us":[..4],"moving":true,"enabled":true}` | 20 Hz |
| `{"t":"cal","cal":[..4],"home":[..4]}` | risposta a `cal_get` e dopo `cal_set` |
| `{"t":"err","msg":"fuori vincolo: th2-phi=12"}` | comando rifiutato |
| `{"t":"hello","fw":"0.1.0","mode":"sta|ap"}` | alla connessione |

### Pin (vedi 02-cablaggio.md)

J0 base **GPIO33**, J1 spalla **GPIO25**, J2 gomito **GPIO26**, J3 pinza **GPIO27**. PWM a 50 Hz tramite LEDC.
