// Braccio (spalla -> gomito). Si stampa in piano così com'è: faccia z=0 sul piatto, nessun supporto.
// Asse spalla nell'origine, gomito a +X. La faccia z=0 guarda il servo spalla (squadretta in tasca).
// La faccia z=t guarda l'interno della torretta: lì stanno avambraccio e contrappeso; la canalina è sul lato servo.
//
// Montaggio:
//  1. avvita la squadretta doppia nella tasca con le sue viti autofilettanti (fori pilota da fare con la vite);
//  2. innesta sull'albero SG90 in posizione centrale (90°) con il braccio a 45°, poi vite centrale dal lato z=t;
//  3. gomito: vite M3x25 dalla faccia z=0, poi avambraccio, poi dado autobloccante, serrato "a scorrimento";
//  4. 4 piombi da 20 g nelle sedi di coda, coperchio (part="lid"), 2 viti M3x16 con dado nella sede lato z=0.
include <params.scad>
use <lib/parts.scad>

part = "arm";  // arm | lid | all

t = 6;                     // spessore del braccio
hub_r = 9;                 // mozzo spalla: contiene la squadretta con >= 1.6 mm di parete
elbow_r = 7;
lead_y = (lead_pocket[1] + 2) / 2;               // sedi affiancate, setto di 2 mm
// 4 sedi in fila trasversale: baricentro sempre a cw_shoulder_r, la coda non si allunga verso il pavimento
leads = [for (k = [-3, -1, 1, 3]) [-cw_shoulder_r, k * lead_y]];
screws = [[-cw_shoulder_r - lead_pocket[0] / 2 - 4.5, lead_y], [-cw_shoulder_r - lead_pocket[0] / 2 - 4.5, -lead_y]];
chan_w = 5;                // canalina cavi (pinza SG90 + ESP32-CAM)
chan_d = 3;

module tail_outline(o) hull() {
    for (p = leads) translate(p) lead_outline(o);
    for (p = screws) translate(p) circle(r = 4);
}

module upper_arm() {
    difference() {
        union() {
            linear_extrude(t) {
                hull() {
                    circle(r = hub_r);
                    translate([L1, 0]) circle(r = elbow_r);
                }
                hull() {
                    circle(r = hub_r);
                    tail_outline(lead_wall);
                }
            }
            linear_extrude(cw_t) tail_outline(lead_wall);
            translate([L1, 0, t]) cylinder(d = 7, h = 0.5);  // rondella di scorrimento verso l'avambraccio
        }

        // spalla: squadretta lungo X, vite centrale con lamatura per la testa lato z=t
        horn_pocket(clr_pocket, t + 1);
        translate([0, 0, horn_t + 0.2 + 1.5]) cylinder(d = 5, h = t);

        // gomito: foro M3 (il perno è la vite; l'avambraccio ruota con clr_pivot)
        translate([L1, 0, -1]) cylinder(d = m3_d + clr_hole, h = t + 3);

        // contrappeso: sedi piombi aperte verso z=t, viti del coperchio con dado in sede sul lato z=0
        for (p = leads) translate([p.x, p.y, cw_t - lead_depth]) linear_extrude(lead_depth + 1) lead_outline();
        for (p = screws) translate([p.x, p.y, 0]) {
            translate([0, 0, -1]) cylinder(d = m3_d + clr_hole, h = cw_t + 2);
            translate([0, 0, -0.01]) rotate(30) hex_pocket(h = 2.6);
        }

        // canalina cavi sulla faccia z=0 (lato servo): al gomito il cavo fa l'ansa all'esterno, lontano dall'avambraccio.
        // 3 ponticelli sul piatto trattengono i fili (fessura di 2.2 mm: il piattino si infila di taglio)
        difference() {
            translate([18, -chan_w / 2, -1]) cube([L1 - 18 - elbow_r - 2, chan_w, chan_d + 1]);
            for (x = [30, 46, 62]) translate([x, 0, -1]) difference() {
                translate([0, -chan_w / 2, 0]) cube([3, chan_w, 1.8]);
                translate([-1, -1.1, -1]) cube([5, 2.2, 4]);
            }
        }
    }
}

module arm_lid() difference() {
    linear_extrude(lid_t) tail_outline(lead_wall);
    for (p = screws) translate([p.x, p.y, -1]) cylinder(d = m3_d + clr_hole, h = lid_t + 2);
}

if (part == "arm" || part == "all") upper_arm();
if (part == "lid") arm_lid();
if (part == "all") translate([0, 45, 0]) arm_lid();
