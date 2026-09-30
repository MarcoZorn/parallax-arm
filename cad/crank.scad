// Manovella gomito: sul servo gomito (guancia destra), porta il perno A della biella motrice
// e il blocco contrappeso: 6 sedi per piombi da 20 g ad arco (r = cw_elbow_r). Se ne riempiono 4 o 6 (calc/torque.py).
// Il blocco sta dal lato servo: baricentro a 1-2 mm dal piano della squadretta, quindi minimo momento sull'albero.
// Frame locale: asse spalla nell'origine, raggio della manovella verso +X, +Z verso la guancia (servo).
// Stampa: faccia z=0 (interna) sul piatto; le sedi piombi si aprono sul piatto, il tetto è un ponte da 14 mm.
//
// Montaggio:
//  1. squadretta nella tasca in cima al mozzo, poi innesto sul servo con la manovella opposta all'avambraccio;
//  2. vite centrale dalla faccia z=0 (lamatura profonda);
//  3. piombi nelle sedi (prima le 4 centrali), coperchio (part="lid") sulla faccia z=0, 2 viti M3x16 con dado lato servo;
//  4. perno A: vite M3x20 dal lato servo -> piastra -> distanziale -> biella (dado incassato nella biella).
include <params.scad>
use <lib/parts.scad>

part = "all";  // all | crank | lid | spacer

hub_h = crank_t + crank_spacer;
step = 2 * asin((lead_pocket[1] + 2) / 2 / cw_elbow_r);  // sedi affiancate con setto di 2 mm
angles = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5] * step;
screws = [for (s = [-1, 1]) 26 * [cos(s * 1.5 * step), sin(s * 1.5 * step)]];
spacer_len = y_crank_in - y_rod[1] - 0.2;  // dalla faccia interna della piastra al piano della biella
echo(str("baricentro piombi: 4 centrali r = ", cw_elbow_r * (cos(0.5 * step) + cos(1.5 * step)) / 2,
          " mm, tutti e 6 r = ", cw_elbow_r * (cos(0.5 * step) + cos(1.5 * step) + cos(2.5 * step)) / 3, " mm (calc: R_CW_ELBOW*)"));

module lead_at(a, o) rotate(a) translate([cw_elbow_r, 0]) lead_outline(o);
// Solo inviluppi di sedi adiacenti: un inviluppo unico chiuderebbe l'arco e coprirebbe il perno A.
module block_outline(o) {
    for (i = [0:len(angles) - 2]) hull() { lead_at(angles[i], o); lead_at(angles[i + 1], o); }
    for (i = [0, 1]) hull() {  // orecchie delle viti, attaccate alla sede alla stessa quota angolare
        lead_at(angles[1 + i * 3], o);
        translate(screws[i]) circle(r = 4);
    }
}

module crank() {
    difference() {
        union() {
            linear_extrude(crank_t) hull() {
                circle(r = 9);
                translate([crank_r, 0]) circle(r = 5);
                block_outline(lead_wall);
            }
            linear_extrude(cw_t) block_outline(lead_wall);
            // mozzo: contiene la squadretta (lungo Y, lontano dal perno A) con 1.8 mm di parete
            linear_extrude(hub_h) { circle(r = 9); rotate(90) offset(r = 1.8) horn_outline(clr_pocket); }
        }
        translate([0, 0, hub_h]) mirror([0, 0, 1]) rotate(90) horn_pocket(clr_pocket, hub_h + 2);
        translate([0, 0, -1]) cylinder(d = 5, h = 1 + hub_h - (horn_t + 0.2) - 1.5);
        translate([crank_r, 0, -1]) cylinder(d = m3_d + clr_hole, h = hub_h + 2);
        // sedi piombi aperte sulla faccia z=0 (coperchio), viti con dado in sede sulla faccia lato servo
        for (a = angles) translate([0, 0, -1]) linear_extrude(lead_depth + 1) lead_at(a, 0);
        for (p = screws) translate([p.x, p.y, 0]) {
            translate([0, 0, -1]) cylinder(d = m3_d + clr_hole, h = cw_t + 2);
            translate([0, 0, cw_t - 2.6 + 0.01]) rotate(30) hex_pocket(h = 2.6);
        }
    }
}

module crank_lid() difference() {
    linear_extrude(lid_t) block_outline(lead_wall);
    for (p = screws) translate([p.x, p.y, -1]) cylinder(d = m3_d + clr_hole, h = lid_t + 2);
}

module spacer() difference() {
    cylinder(d = 7, h = spacer_len);
    translate([0, 0, -1]) cylinder(d = m3_d + clr_hole, h = spacer_len + 2);
}

// Assieme (usato da assembly.scad): coperchio e distanziale al loro posto, con le teste delle viti
module crank_assembly() {
    crank();
    translate([0, 0, -lid_t]) crank_lid();
    for (p = screws) translate([p.x, p.y, -lid_t - 3]) cylinder(d = m3_head_d, h = 3);
    translate([crank_r, 0, 0]) mirror([0, 0, 1]) spacer();
}

if (part == "all") {
    crank();
    translate([-10, -60, 0]) crank_lid();
    translate([-20, -25, 0]) spacer();
}
if (part == "crank") crank();
if (part == "lid") crank_lid();
if (part == "spacer") spacer();
