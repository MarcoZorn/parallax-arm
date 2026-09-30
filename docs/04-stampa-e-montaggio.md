# Stampa, ferramenta e montaggio

## 0. Prima di tutto: il provino

1. Stampa `cad/stl/00_tolerance_coupon.stl` con **lo stesso PLA e lo stesso profilo** delle parti.
2. Riporta i valori che calzano in `cad/params.scad`:

   | Provino | Parametro |
   |---|---|
   | fori M3 | `clr_hole` |
   | sedi dado, finestre SG90, squadretta, sedi piombo | `clr_pocket` |
   | cursori a coda di rondine | `clr_slide` |
   | colonnine a scatto | `snap_hook` |

3. Misura la tua squadretta doppia (`horn_*`) e la quota `sg_horn_face`. Per `sg_horn_face`: squadretta montata sul servo, distanza dal fondo del servo alla faccia esterna della squadretta.
4. `cad/export.sh` rigenera tutti gli STL, i modelli del digital twin e `web/public/models/rig.json`.
5. `python3 calc/torque.py` ricontrolla le coppie, e `cad/assembly.scad` le collisioni (vedi l'intestazione del file).

## 1. Stampa (Kobra S1, PLA)

Profilo: ugello 0.4, layer 0.2 (0.16 per pignone e ganasce), 3 perimetri, gyroid 20%, **nessun supporto**.
Tutti gli STL sono già orientati sul piatto.

| File | Qtà | Note |
|---|---|---|
| 01_base_tray | 1 | il pezzo più lungo (~4 h) |
| 02_base_lid | 1 | labbro di guida verso l'alto |
| 03_turret | 1 | guance verticali |
| 04_upper_arm + 05_upper_arm_lid | 1 + 1 | |
| 06_crank + 07_crank_lid + 08_crank_spacer | 1 + 1 + 1 | sedi dei piombi aperte sul piatto (ponti da 14 mm) |
| 09_drive_rod, 10_lev_rod, 11_lev_rod2, 12_lev_link | 1 ciascuno | |
| 13_forearm | 1 | stampato di fianco |
| 14_elbow_wrist_spacers | 1 set | 3 distanziali |
| 15_wrist_bracket | 1 | stampato di fianco |
| 16_gripper_housing | 1 | capovolto |
| 17_gripper_base_plate | 1 | code di rondine verso l'alto |
| 18_gripper_pinion | 1 | layer 0.16 |
| 19_gripper_jaw_x2 | **2** | stesso file due volte, layer 0.16 |
| 20_esp32cam_cradle | 1 | solo se monti la camera |

Totale circa 290 g di PLA.

## 2. Ferramenta (tutta M3)

| Vite | Qtà | Dove |
|---|---|---|
| M3x6 | 1 | perno U (biella 2 → triangolo, dado incassato) |
| M3x8 | 8 | B (biella motrice → piastra R), P1 (biella 1 → triangolo), 2 culla camera, 4 coperchio base |
| M3x12 | 6 | G (montante), V (staffa polso), 2 piastra pinza, 2 staffa → piano pinza |
| M3x14 | 1 | A (manovella → distanziale → biella motrice, dado incassato) |
| M3x16 | 4 | coperchi dei piombi (2 braccio, 2 manovella) |
| M3x35 | 1 | perno polso W |
| M3x40 | 1 | perno gomito E |

- Dadi autobloccanti: 4, su E, W, G e V.
- Dadi normali: 10, su A, B, P1, U, 4 per i coperchi dei piombi e 2 per la staffa.
- **Serraggio:** dove ruota qualcosa (E, W, G, V) stringi l'autobloccante finché il giunto non ha gioco assiale **ma gira libero**. Una goccia di olio al silicone o grasso PTFE sui perni e sulla corona della base.

## 3. Montaggio

1. **Base.**
   - Nel vassoio: ESP32 a scatto nella culla (pin in basso) e breadboard nella cornice con il suo biadesivo.
   - WAGO fissati con fascette.
   - SG90 della base nella torre (cavo verso l'asola), poi il coperchio con 4 viti M3x8.
   - Cablaggio secondo [02-cablaggio.md](02-cablaggio.md).
2. **Torretta.** SG90 spalla (guancia −Y) e gomito (guancia +Y) montati **da fuori**, con le viti delle linguette.
3. **Taratura prima delle squadrette.**
   - Carica firmware e web app (sotto), apri la web app, premi **Abilita**.
   - I servo vanno alla posa `home` = [0°, 90°, 0°, 30 mm], cioè 1500 µs per base, spalla e gomito.
4. **Squadrette nella posa di riferimento.** Monta ogni pezzo con il servo in quella posa:
   - **torretta** con il braccio che punta avanti (+X);
   - **braccio verticale**;
   - **manovella orizzontale verso il retro**: così l'avambraccio sarà orizzontale;
   - **pinza semiaperta** (circa 30 mm).
5. **Piombi.**
   - 2 nella coda del braccio.
   - 4 nelle sedi centrali della manovella. Le 2 esterne sono libere per un'eventuale regolazione fine.
   - Chiudi i coperchi.
6. **Catena del gomito.** Monta avambraccio, triangolo e bielle secondo l'ordine delle viti di `cad/linkage.scad`, con distanziali e autobloccanti come in tabella.
   - Il triangolo deve restare **con la leva P1 orizzontale all'indietro e U in verticale**, in qualunque posa.
   - Se ruota insieme all'avambraccio, una biella è montata sul foro sbagliato.
7. **Polso e pinza.**
   - Servo capovolto sul piano, pignone sull'albero con la sua squadretta (vite dal basso), piastra inferiore con 2 viti.
   - Le ganasce si infilano di testa nelle code di rondine, A da +Y e B da −Y, finché ingranano. Con la pinza a 30 mm le dita devono essere simmetriche.
   - La staffa si avvita sul piano superiore.
8. **Rifinitura della taratura** nella scheda *Taratura* della web app:
   - porta ogni giunto su due angoli noti;
   - aggiorna `ref_us` e `k` (il segno di `k` è il verso);
   - salva con `cal_save`.

## 4. Firmware e web app

Dalla cartella del progetto:

```bash
cd web && npm install && npm run build          # scrive la web app compressa in firmware/data/
cd ../firmware
cp include/secrets.example.h include/secrets.h  # opzionale: WiFi di casa (altrimenti AP "BRACCIO")
~/.local/bin/pio run -e esp32dev -t upload      # firmware
~/.local/bin/pio run -e esp32dev -t uploadfs    # web app su LittleFS
```

Poi apri `http://braccio.local`. In alternativa usa l'AP `BRACCIO` (password `braccio-arm`) e vai su `http://192.168.4.1`.

Per sviluppare senza hardware: `cd web && npm run dev`. La web app parte in **simulazione** con lo stesso profilo di moto del firmware.
