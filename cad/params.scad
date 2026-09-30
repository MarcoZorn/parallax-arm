// Unica fonte delle quote. Le lunghezze dei link devono coincidere con calc/torque.py.
// Tolleranze: stampa cad/test/tolerance_coupon.scad e riporta qui i valori che calzano.
$fn = 64;

// ---- tolleranze (mm) ----
clr_hole  = 0.2;   // gioco diametrale fori passanti (M3 -> 3.2)
clr_pivot = 0.3;   // gioco diametrale fori su cui qualcosa RUOTA
clr_pocket = 0.2;  // gioco per lato in sedi (servo, squadretta, dado, monete)
clr_slide = 0.3;   // riduzione per lato del pezzo maschio nelle guide a scorrimento
snap_hook = 0.4;   // sporgenza dente a scatto (interferenza)

// ---- geometria braccio ----
L1 = 80;   // spalla -> gomito
L2 = 80;   // gomito -> perno polso
L3 = 45;   // perno polso -> centro dita

// ---- SG90 (misura il tuo e correggi) ----
sg_body   = [22.8, 12.4, 22.7];  // x lungo, y largo, z alto (senza linguette/perno)
sg_tab_len = 32.3;               // ingombro linguette
sg_tab_t  = 2.5;
sg_tab_z  = 15.9;                // quota della faccia inferiore delle linguette
sg_screw_pitch = 27.8;
sg_screw_d = 2.0;
sg_shaft_x = 5.9;                // asse albero dal bordo del corpo lato albero
sg_boss_d = 11.8;
sg_boss_h = 4.0;

// ---- squadretta doppia SG90 (varia tra lotti: misurala) ----
horn_len  = 32.0;  // punta-punta
horn_hub_d = 7.0;
horn_tip_d = 4.0;
horn_t    = 1.4;   // spessore del piatto
horn_screw_d = 2.0; // vite centrale

// ---- viteria ----
m3_d = 3.0;
m3_nut_af = 5.5;     // chiave del dado
m3_nylock_h = 4.0;
m3_head_d = 5.5;

// ---- contrappeso: piombi da pesca a oliva 20 g (misurati col calibro) ----
lead_l = 22.18;
lead_d = 13.70;
lead_pocket = [lead_l + 0.6, lead_d + 2 * clr_pocket];  // sede a stadio: lunghezza, larghezza
lead_depth = lead_d + 0.4;
lead_wall = 1.6;
lid_t = 1.6;                 // coperchio sedi, 2 viti M3x16
cw_t = lead_depth + 1.2;     // spessore del blocco contrappeso (fondo 1.2)
cw_shoulder_r = 30;          // = R_CW_SHOULDER in calc/torque.py
cw_elbow_r = 43;             // raggio dell'arco dei 4 piombi sulla manovella

// ---- SG90 in guancia: quota faccia ESTERNA della squadretta dal fondo del servo (MISURALA, squadretta montata) ----
sg_horn_face = 30.5;

// ---- torretta ----
sh_h = 62;        // asse spalla sopra il fondo del pavimento torretta (z=0 = faccia squadretta base)
cheek_t = 3;
turret_w = 65;    // luce interna tra le guance
floor_t = 4;
floor_r = 52;
horn_gap = sg_horn_face - (sg_tab_z + sg_tab_t) - cheek_t;  // guancia interna -> faccia squadretta (9.1)

// ---- manovella gomito (parallelogramma) ----
crank_r = 20;          // perno biella = leva posteriore avambraccio
crank_t = 4;
crank_spacer = 5;       // mozzo: stacca la piastra dalla squadretta per far stare la coppa lato guancia
rod_t = 4;             // bielle (motrice e livellamento)
lev_r = 20;            // leva di livellamento: perno fisso G = asse spalla + (-lev_r, 0)

// ---- piani lungo Y (0 = mezzeria torretta, guancia sinistra = servo spalla) ----
y_wall = turret_w / 2;
y_arm = -y_wall + horn_gap;                          // faccia z=0 del braccio (lato servo)
y_crank_hub = y_wall - horn_gap;                     // faccia squadretta manovella
y_crank_in = y_crank_hub - crank_spacer - crank_t;   // faccia interna piastra manovella
y_lev = [-3.0, 1.0];        // biella di livellamento
y_post = [1.5, 4.5];        // montante fisso che porta G
y_rod = [5.0, 9.0];          // biella motrice
