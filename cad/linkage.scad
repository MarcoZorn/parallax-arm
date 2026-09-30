// Catena del gomito: avambraccio a U, triangolo di livellamento, tre bielle, distanziali.
// Ogni parte è modellata nel frame locale del contratto (docs/03-protocollo.md §2):
// X lungo la parte, y locale = giù nel mondo, z locale = +Y del mondo a partire dal piano della parte.
// Stampa: bielle, triangolo e distanziali in piano così come sono. L'avambraccio si stampa di fianco:
// part="print_forearm" lo ruota con il bordo piatto (y=+7) sul piatto, senza supporti.
//
// Ferramenta (M3):
//  E  gomito: M3x40 dalla faccia esterna del braccio, distanziali d6 (8 mm) e d5 (8 mm), autobloccante lato +y
//  W  polso:  M3x35 dalla piastra L, distanziale d6 (8 mm), autobloccante lato +y
//  A  manovella: M3x20 dal lato servo della manovella -> distanziale -> biella, dado incassato nella biella
//  B  leva:   M3x10 dalla biella motrice, dado incassato nella piastra R
//  P1, U triangolo: M3x10 da biella 1 / biella 2, dado incassato nel triangolo
//  V  staffa: M3x10 dalla biella 2, autobloccante sul lato +y della leva della staffa
include <params.scad>
use <lib/parts.scad>

part = "all";  // all | drive_rod | lev_rod | lev_rod2 | lev_link | forearm | print_forearm | spacers

fore_t_l = y_fore_l[1] - y_fore_l[0];
fore_z_r = y_fore_r[0] - y_fore_l[0];            // piastra R in z locale
fore_t_r = y_fore_r[1] - y_fore_r[0];
fore_w = 7;                                       // semi-altezza piastre (bordo piatto a y=+7)
link_t = y_link[1] - y_link[0];
pivot_d = m3_d + clr_pivot;
fix_d = m3_d + clr_hole;
// distanziali sul perno E e W (luci tra i piani)
sp_e1 = y_link[0] - y_fore_l[1];                  // piastra L -> triangolo
sp_e2 = y_fore_r[0] - y_link[1];                  // triangolo -> piastra R
sp_w = y_bracket[0] - y_fore_l[1];                // piastra L -> staffa

module rod(len, t) difference() {
    linear_extrude(t) {
        hull() { circle(d = rod_w); translate([len, 0]) circle(d = rod_w); }
        for (x = [0, len]) translate([x, 0]) circle(r = 4);
    }
    for (x = [0, len]) translate([x, 0, -1]) cylinder(d = pivot_d, h = t + 2);
}

// A (manovella) -> B (leva avambraccio). Dado di A incassato sul lato -y: lì sotto passa il montante G.
module drive_rod() difference() {
    rod(L1, rod_t);
    translate([0, 0, -0.01]) hex_pocket(h = 2.6);
}
module lev_rod() rod(L1, rod_t);     // G (montante) -> P1 (triangolo)
module lev_rod2() rod(L2, rod2_t);   // U (triangolo) -> V (staffa polso)

// Triangolo: E nell'origine, P1 indietro (x = -lev_r), U in alto (y locale = -lev2_r).
module lev_link() {
    P1 = [-lev_r, 0];
    U = [0, -lev2_r];
    difference() {
        linear_extrude(link_t) hull() {
            circle(r = 5.5);
            translate(P1) circle(r = 5);
            translate(U) circle(r = 5);
        }
        translate([0, 0, -1]) cylinder(d = pivot_d, h = link_t + 2);
        for (p = [P1, U]) translate([p.x, p.y, -1]) cylinder(d = fix_d, h = link_t + 2);
        // dadi incassati: P1 sul lato -y (z=0), U sul lato +y (z=link_t)
        translate([P1.x, P1.y, -0.01]) hex_pocket(h = 2.6);
        translate([U.x, U.y, link_t - 2.6 + 0.01]) hex_pocket(h = 2.6);
    }
}

// Avambraccio a U: piastra L (lato braccio) e piastra R (con leva B) unite da un ponte sotto l'asse,
// lontano dalla biella 2 (che passa sopra, a >= 30*cos(70) = 10.3 mm) e dal triangolo (< 35 mm da E).
module forearm() {
    difference() {
        union() {
            linear_extrude(fore_t_l) hull() {
                circle(r = fore_w);
                translate([L2, 0]) circle(r = fore_w);
            }
            translate([0, 0, fore_z_r]) linear_extrude(fore_t_r) hull() {
                translate([-crank_r, 0]) circle(r = fore_w);
                translate([L2, 0]) circle(r = fore_w);
            }
            translate([30, 1, 0]) cube([10, fore_w - 1, fore_z_r + fore_t_r]);  // ponte
        }
        translate([0, 0, -1]) cylinder(d = pivot_d, h = 40);   // E: l'avambraccio ruota sulla vite
        translate([L2, 0, -1]) cylinder(d = fix_d, h = 40);    // W: la staffa ruota, la vite no
        translate([-crank_r, 0, -1]) cylinder(d = fix_d, h = 40);  // B
        translate([-crank_r, 0, fore_z_r - 0.01]) hex_pocket(h = 2.6);
        // asole per fascette sul lato esterno della piastra L (cavi pinza e camera)
        for (x = [22, 55]) for (s = [-1, 1]) translate([x - 2, s * 3.5 - 1, -1]) cube([4, 2, fore_t_l + 2]);
    }
}

module tube(d, len) difference() {
    cylinder(d = d, h = len);
    translate([0, 0, -1]) cylinder(d = pivot_d, h = len + 2);
}
module spacers() {
    tube(6, sp_e1 - 0.2);
    translate([10, 0, 0]) tube(5, sp_e2 - 0.2);
    translate([20, 0, 0]) tube(6, sp_w - 0.2);
}

if (part == "all") {
    drive_rod();
    translate([0, 15, 0]) lev_rod();
    translate([0, 30, 0]) lev_rod2();
    translate([30, 60, 0]) lev_link();
    translate([0, 90, 0]) rotate([-90, 0, 0]) translate([0, -fore_w, 0]) forearm();
    translate([100, 0, 0]) spacers();
}
if (part == "drive_rod") drive_rod();
if (part == "lev_rod") lev_rod();
if (part == "lev_rod2") lev_rod2();
if (part == "lev_link") lev_link();
if (part == "forearm") forearm();
if (part == "print_forearm") rotate([-90, 0, 0]) translate([0, -fore_w, 0]) forearm();
if (part == "spacers") spacers();
